import os
import shutil
import tempfile
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from git import Repo, GitCommandError
from github import Github, GithubException

logger = logging.getLogger(__name__)

class GitHubManager:
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.github = Github(github_token)
        self.active_repos: Dict[int, Dict[str, Any]] = {}
        # Use persistent directory instead of temp
        self.repos_dir = Path.home() / '.telecode_bot_repos'
        self.repos_dir.mkdir(exist_ok=True)
        
    def set_active_repo(self, user_id: int, repo_url: str) -> Dict[str, Any]:
        """Set active repository for a user."""
        try:
            repo_name = self._extract_repo_name(repo_url)
            github_repo = self.github.get_repo(repo_name)
            
            self.active_repos[user_id] = {
                'url': repo_url,
                'name': repo_name,
                'github_repo': github_repo,
                'local_path': None,
                'last_updated': datetime.now()
            }
            
            logger.info(f"Set active repo for user {user_id}: {repo_name}")
            return {
                'success': True,
                'repo_name': repo_name,
                'description': github_repo.description,
                'language': github_repo.language
            }
            
        except GithubException as e:
            logger.error(f"GitHub error setting repo for user {user_id}: {e}")
            return {'success': False, 'error': f"GitHub error: {e}"}
        except Exception as e:
            logger.error(f"Error setting repo for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_active_repo(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get active repository for a user."""
        return self.active_repos.get(user_id)
    
    async def clone_or_update_repo(self, user_id: int) -> Dict[str, Any]:
        """Clone repository or update existing local copy for persistent access."""
        if user_id not in self.active_repos:
            return {'success': False, 'error': 'No active repository set'}
        
        repo_info = self.active_repos[user_id]
        repo_url = repo_info['url']
        repo_name = repo_info['name']
        
        try:
            # Use persistent directory structure
            local_path = self.repos_dir / f"user_{user_id}" / repo_name.replace('/', '_')
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            clone_url = f"https://{self.github_token}@github.com/{repo_name}.git"
            
            if local_path.exists() and (local_path / '.git').exists():
                # Repository exists, update it
                try:
                    repo = Repo(local_path)
                    origin = repo.remote('origin')
                    origin.fetch()
                    
                    # Ensure we're on main/master for direct commits
                    main_branch = 'main' if 'main' in [ref.name.split('/')[-1] for ref in origin.refs] else 'master'
                    repo.git.checkout(main_branch)
                    repo.git.reset('--hard', f'origin/{main_branch}')
                    
                    logger.info(f"Updated existing repo for user {user_id}: {repo_name} on {main_branch}")
                except Exception as update_error:
                    logger.warning(f"Failed to update repo, re-cloning: {update_error}")
                    shutil.rmtree(local_path)
                    repo = Repo.clone_from(clone_url, local_path)
            else:
                # Fresh clone
                if local_path.exists():
                    shutil.rmtree(local_path)
                repo = Repo.clone_from(clone_url, local_path)
                logger.info(f"Cloned new repo for user {user_id}: {repo_name}")
            
            self.active_repos[user_id]['local_path'] = str(local_path)
            self.active_repos[user_id]['git_repo'] = repo
            
            return {
                'success': True,
                'local_path': str(local_path),
                'branch': repo.active_branch.name
            }
            
        except GitCommandError as e:
            logger.error(f"Git error with repo for user {user_id}: {e}")
            return {'success': False, 'error': f"Git error: {e}"}
        except Exception as e:
            logger.error(f"Error with repo for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_branch(self, user_id: int, branch_name: str) -> Dict[str, Any]:
        """Create a new branch for changes."""
        if user_id not in self.active_repos:
            return {'success': False, 'error': 'No active repository set'}
        
        repo_info = self.active_repos[user_id]
        if 'git_repo' not in repo_info:
            return {'success': False, 'error': 'Repository not cloned locally'}
        
        try:
            git_repo = repo_info['git_repo']
            
            existing_branch = None
            for branch in git_repo.branches:
                if branch.name == branch_name:
                    existing_branch = branch
                    break
            
            if existing_branch:
                git_repo.git.checkout(branch_name)
            else:
                git_repo.git.checkout('-b', branch_name)
            
            logger.info(f"Switched to branch {branch_name} for user {user_id}")
            return {'success': True, 'branch': branch_name, 'created': not existing_branch}
            
        except GitCommandError as e:
            logger.error(f"Git error creating branch for user {user_id}: {e}")
            return {'success': False, 'error': f"Git error: {e}"}
        except Exception as e:
            logger.error(f"Error creating branch for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def commit_and_push(self, user_id: int, commit_message: str, 
                       author_name: str = "TeleCode Bot", 
                       author_email: str = "telecode-bot@telegram.org") -> Dict[str, Any]:
        """Commit changes and push to GitHub."""
        if user_id not in self.active_repos:
            return {'success': False, 'error': 'No active repository set'}
        
        repo_info = self.active_repos[user_id]
        if 'git_repo' not in repo_info:
            return {'success': False, 'error': 'Repository not cloned locally'}
        
        try:
            git_repo = repo_info['git_repo']
            
            # Add all changes
            git_repo.git.add('.')
            
            # Check if there are changes to commit
            if not git_repo.is_dirty() and not git_repo.git.diff('--cached'):
                return {'success': False, 'error': 'No changes to commit'}
            
            # Set git config for the commit
            git_repo.config_writer().set_value("user", "name", author_name).release()
            git_repo.config_writer().set_value("user", "email", author_email).release()
            
            # Make the commit
            commit = git_repo.index.commit(commit_message)
            
            # Push to remote
            origin = git_repo.remote('origin')
            current_branch = git_repo.active_branch.name
            
            # For direct commits to main, ensure we're pushing to the right branch
            try:
                origin.push(refspec=f'{current_branch}:{current_branch}')
            except GitCommandError as push_error:
                # If push fails, try to pull and push again (in case of conflicts)
                logger.warning(f"Initial push failed, trying pull-rebase: {push_error}")
                try:
                    git_repo.git.pull('--rebase', 'origin', current_branch)
                    origin.push(refspec=f'{current_branch}:{current_branch}')
                except GitCommandError as retry_error:
                    logger.error(f"Push failed after rebase: {retry_error}")
                    raise retry_error
            
            commit_url = f"https://github.com/{repo_info['name']}/commit/{commit.hexsha}"
            
            logger.info(f"Committed and pushed changes for user {user_id} to {current_branch}")
            return {
                'success': True,
                'commit_sha': commit.hexsha,
                'commit_url': commit_url,
                'branch': current_branch,
                'message': commit_message,
                'is_main_branch': current_branch in ['main', 'master']
            }
            
        except GitCommandError as e:
            logger.error(f"Git error committing for user {user_id}: {e}")
            return {'success': False, 'error': f"Git error: {e}"}
        except Exception as e:
            logger.error(f"Error committing for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_repo_status(self, user_id: int) -> Dict[str, Any]:
        """Get current repository status."""
        if user_id not in self.active_repos:
            return {'success': False, 'error': 'No active repository set'}
        
        repo_info = self.active_repos[user_id]
        
        status = {
            'success': True,
            'repo_name': repo_info['name'],
            'repo_url': repo_info['url'],
            'last_updated': repo_info['last_updated'].isoformat(),
            'local_path': repo_info.get('local_path'),
            'cloned': 'git_repo' in repo_info
        }
        
        if 'git_repo' in repo_info:
            git_repo = repo_info['git_repo']
            status.update({
                'current_branch': git_repo.active_branch.name,
                'has_changes': git_repo.is_dirty(),
                'last_commit': git_repo.head.commit.hexsha[:8]
            })
        
        return status
    
    def _extract_repo_name(self, repo_url: str) -> str:
        """Extract owner/repo from GitHub URL."""
        if repo_url.startswith('https://github.com/'):
            return repo_url.replace('https://github.com/', '').rstrip('/')
        elif repo_url.startswith('git@github.com:'):
            return repo_url.replace('git@github.com:', '').replace('.git', '')
        else:
            raise ValueError(f"Invalid GitHub URL format: {repo_url}")
    
    def cleanup(self):
        """Clean up old repository clones (keep recent ones)."""
        try:
            # Only clean up repos older than 7 days
            import time
            week_ago = time.time() - (7 * 24 * 60 * 60)
            
            for user_dir in self.repos_dir.glob('user_*'):
                if user_dir.is_dir():
                    # Check if directory is old
                    if user_dir.stat().st_mtime < week_ago:
                        shutil.rmtree(user_dir)
                        logger.info(f"Cleaned up old repo directory: {user_dir}")
                        
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")
    
    def get_local_repo_path(self, user_id: int) -> Optional[str]:
        """Get the local path for user's active repository if it exists."""
        if user_id in self.active_repos and 'local_path' in self.active_repos[user_id]:
            local_path = Path(self.active_repos[user_id]['local_path'])
            if local_path.exists():
                return str(local_path)
        return None
    
    def list_all_repositories(self) -> Dict[str, Any]:
        """List all repositories across all users with their status."""
        repo_list = []
        
        try:
            # Get all user directories
            for user_dir in self.repos_dir.glob('user_*'):
                if not user_dir.is_dir():
                    continue
                    
                try:
                    user_id = int(user_dir.name.split('_')[1])
                except (ValueError, IndexError):
                    continue
                
                # Check each repository in user directory
                for repo_dir in user_dir.iterdir():
                    if not repo_dir.is_dir():
                        continue
                        
                    repo_info = {
                        'user_id': user_id,
                        'repo_name': repo_dir.name.replace('_', '/'),
                        'local_path': str(repo_dir),
                        'exists_locally': repo_dir.exists(),
                        'has_git': (repo_dir / '.git').exists() if repo_dir.exists() else False,
                        'is_active': False,
                        'last_modified': None,
                        'size_mb': None
                    }
                    
                    # Check if this is the active repo for the user
                    if user_id in self.active_repos:
                        active_repo = self.active_repos[user_id]
                        if active_repo.get('local_path') == str(repo_dir):
                            repo_info['is_active'] = True
                            repo_info['repo_name'] = active_repo.get('name', repo_info['repo_name'])
                    
                    # Get additional info if directory exists
                    if repo_dir.exists():
                        try:
                            stat_info = repo_dir.stat()
                            repo_info['last_modified'] = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                            
                            # Calculate directory size
                            total_size = sum(f.stat().st_size for f in repo_dir.rglob('*') if f.is_file())
                            repo_info['size_mb'] = round(total_size / (1024 * 1024), 2)
                            
                        except Exception as e:
                            logger.warning(f"Error getting repo info for {repo_dir}: {e}")
                    
                    repo_list.append(repo_info)
            
            return {
                'success': True,
                'repositories': repo_list,
                'total_repos': len(repo_list),
                'repos_directory': str(self.repos_dir)
            }
            
        except Exception as e:
            logger.error(f"Error listing repositories: {e}")
            return {
                'success': False,
                'error': str(e),
                'repositories': []
            }
    
    def get_user_repositories(self, user_id: int) -> Dict[str, Any]:
        """Get all repositories for a specific user."""
        all_repos = self.list_all_repositories()
        
        if not all_repos['success']:
            return all_repos
        
        user_repos = [repo for repo in all_repos['repositories'] if repo['user_id'] == user_id]
        
        return {
            'success': True,
            'repositories': user_repos,
            'total_repos': len(user_repos),
            'active_repo': self.get_active_repo(user_id)
        }