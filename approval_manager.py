"""
Approval Manager for TeleCode Bot

Manages the approval process for code changes before committing to repositories.
Provides change detection, summary generation, and user approval workflows.
"""

import os
import logging
import time
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import subprocess
import tempfile

logger = logging.getLogger(__name__)

@dataclass
class FileChange:
    """Represents a change to a file."""
    file_path: str
    change_type: str  # 'created', 'modified', 'deleted'
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    lines_added: int = 0
    lines_removed: int = 0

@dataclass
class ChangesSummary:
    """Summary of all changes to be committed."""
    user_id: int
    repo_path: str
    repo_name: str
    branch_name: str
    files_created: List[str]
    files_modified: List[str]
    files_deleted: List[str]
    total_lines_added: int
    total_lines_removed: int
    file_changes: List[FileChange]
    commit_message: str
    timestamp: float
    llm_response: str

class ApprovalManager:
    """Manages approval workflow for repository changes."""
    
    def __init__(self):
        # Storage for pending approvals
        self.pending_approvals: Dict[int, ChangesSummary] = {}
        self.approval_timeout = int(os.environ.get('APPROVAL_TIMEOUT_MINUTES', '10')) * 60  # Default 10 minutes
        
        # Data directory for persistence
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.pending_file = self.data_dir / "pending_approvals.json"
        
        # Load any existing pending approvals
        self._load_pending_approvals()
    
    def detect_changes(self, repo_path: str, llm_response: str) -> Optional[ChangesSummary]:
        """Detect changes in the repository and create a summary."""
        try:
            logger.info(f"Detecting changes in repository: {repo_path}")
            
            # Get git status to see what files have changed
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            if not result.stdout.strip():
                logger.info("No changes detected in repository")
                return None
            
            # Parse git status output
            file_changes = []
            files_created = []
            files_modified = []
            files_deleted = []
            
            for line in result.stdout.strip().split('\n'):
                if len(line) < 3:
                    continue
                    
                status = line[:2]
                file_path = line[3:].strip()
                
                # Determine change type
                if status.startswith('A') or status.startswith('??'):
                    change_type = 'created'
                    files_created.append(file_path)
                elif status.startswith('M'):
                    change_type = 'modified'
                    files_modified.append(file_path)
                elif status.startswith('D'):
                    change_type = 'deleted'
                    files_deleted.append(file_path)
                else:
                    change_type = 'modified'
                    files_modified.append(file_path)
                
                # Get file content and changes
                file_change = self._analyze_file_change(repo_path, file_path, change_type)
                if file_change:
                    file_changes.append(file_change)
            
            # Calculate totals
            total_lines_added = sum(fc.lines_added for fc in file_changes)
            total_lines_removed = sum(fc.lines_removed for fc in file_changes)
            
            # Get repository info
            repo_name = self._get_repo_name(repo_path)
            branch_name = self._get_current_branch(repo_path)
            
            # Generate commit message from LLM response
            commit_message = self._generate_commit_message(llm_response, file_changes)
            
            summary = ChangesSummary(
                user_id=0,  # Will be set by caller
                repo_path=repo_path,
                repo_name=repo_name,
                branch_name=branch_name,
                files_created=files_created,
                files_modified=files_modified,
                files_deleted=files_deleted,
                total_lines_added=total_lines_added,
                total_lines_removed=total_lines_removed,
                file_changes=file_changes,
                commit_message=commit_message,
                timestamp=time.time(),
                llm_response=llm_response
            )
            
            logger.info(f"Changes detected: {len(files_created)} created, {len(files_modified)} modified, {len(files_deleted)} deleted")
            return summary
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error detecting changes: {e}")
            return None
    
    def _analyze_file_change(self, repo_path: str, file_path: str, change_type: str) -> Optional[FileChange]:
        """Analyze a specific file change."""
        try:
            full_path = os.path.join(repo_path, file_path)
            
            old_content = None
            new_content = None
            lines_added = 0
            lines_removed = 0
            
            if change_type == 'created':
                # New file
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        new_content = f.read()
                    lines_added = len(new_content.splitlines()) if new_content else 0
                    
            elif change_type == 'modified':
                # Get diff information
                try:
                    # Get the diff
                    diff_result = subprocess.run(
                        ['git', 'diff', 'HEAD', file_path],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    # Parse diff to count lines
                    for line in diff_result.stdout.split('\n'):
                        if line.startswith('+') and not line.startswith('+++'):
                            lines_added += 1
                        elif line.startswith('-') and not line.startswith('---'):
                            lines_removed += 1
                    
                    # Get current content
                    if os.path.exists(full_path):
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            new_content = f.read()
                            
                except subprocess.CalledProcessError:
                    # Fallback: just count current file lines as added
                    if os.path.exists(full_path):
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            new_content = f.read()
                        lines_added = len(new_content.splitlines()) if new_content else 0
                        
            elif change_type == 'deleted':
                # File was deleted
                lines_removed = 1  # Approximate
            
            return FileChange(
                file_path=file_path,
                change_type=change_type,
                old_content=old_content,
                new_content=new_content,
                lines_added=lines_added,
                lines_removed=lines_removed
            )
            
        except Exception as e:
            logger.warning(f"Could not analyze file change for {file_path}: {e}")
            return FileChange(
                file_path=file_path,
                change_type=change_type,
                lines_added=0,
                lines_removed=0
            )
    
    def _get_repo_name(self, repo_path: str) -> str:
        """Get repository name from git remote."""
        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            remote_url = result.stdout.strip()
            if 'github.com' in remote_url:
                # Extract repo name from GitHub URL
                if remote_url.startswith('https://github.com/'):
                    return remote_url.replace('https://github.com/', '').rstrip('/')
                elif 'git@github.com:' in remote_url:
                    return remote_url.split('git@github.com:')[1].replace('.git', '')
            
            return os.path.basename(repo_path)
            
        except Exception:
            return os.path.basename(repo_path)
    
    def _get_current_branch(self, repo_path: str) -> str:
        """Get current git branch."""
        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip() or 'main'
        except Exception:
            return 'main'
    
    def _generate_commit_message(self, llm_response: str, file_changes: List[FileChange]) -> str:
        """Generate a commit message based on LLM response and changes."""
        # Extract the first meaningful sentence from LLM response as base
        lines = llm_response.split('\n')
        base_message = ""
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('**'):
                base_message = line[:100]  # Limit length
                break
        
        if not base_message:
            # Fallback based on file changes
            created_count = len([fc for fc in file_changes if fc.change_type == 'created'])
            modified_count = len([fc for fc in file_changes if fc.change_type == 'modified'])
            
            if created_count > 0 and modified_count > 0:
                base_message = f"Add {created_count} new files and update {modified_count} existing files"
            elif created_count > 0:
                base_message = f"Add {created_count} new files"
            elif modified_count > 0:
                base_message = f"Update {modified_count} files"
            else:
                base_message = "Update repository files"
        
        # Clean up the message
        base_message = base_message.rstrip('.')
        
        return f"{base_message}\n\n🤖 Generated with TeleCode Bot\n\nCo-Authored-By: TeleCode <noreply@telecode.bot>"
    
    def store_pending_approval(self, user_id: int, changes_summary: ChangesSummary) -> str:
        """Store changes pending approval and return approval ID."""
        changes_summary.user_id = user_id
        approval_id = f"{user_id}_{int(time.time())}"
        
        # Clean up expired approvals first
        self._cleanup_expired_approvals()
        
        # Store the pending approval
        self.pending_approvals[user_id] = changes_summary
        
        # Persist to file
        self._save_pending_approvals()
        
        logger.info(f"Stored pending approval for user {user_id}: {approval_id}")
        return approval_id
    
    def get_pending_approval(self, user_id: int) -> Optional[ChangesSummary]:
        """Get pending approval for a user."""
        return self.pending_approvals.get(user_id)
    
    def approve_changes(self, user_id: int) -> Optional[ChangesSummary]:
        """Approve and remove pending changes."""
        if user_id in self.pending_approvals:
            changes = self.pending_approvals.pop(user_id)
            self._save_pending_approvals()
            logger.info(f"Approved changes for user {user_id}")
            return changes
        return None
    
    def reject_changes(self, user_id: int) -> bool:
        """Reject and remove pending changes."""
        if user_id in self.pending_approvals:
            del self.pending_approvals[user_id]
            self._save_pending_approvals()
            logger.info(f"Rejected changes for user {user_id}")
            return True
        return False
    
    def _cleanup_expired_approvals(self):
        """Remove expired pending approvals."""
        current_time = time.time()
        expired_users = []
        
        for user_id, changes in self.pending_approvals.items():
            if current_time - changes.timestamp > self.approval_timeout:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            logger.info(f"Removing expired approval for user {user_id}")
            del self.pending_approvals[user_id]
    
    def _save_pending_approvals(self):
        """Save pending approvals to file."""
        try:
            # Convert to serializable format
            data = {}
            for user_id, changes in self.pending_approvals.items():
                # Convert FileChange objects to dicts
                file_changes_data = []
                for fc in changes.file_changes:
                    fc_dict = asdict(fc)
                    # Limit content size for storage
                    if fc_dict.get('new_content') and len(fc_dict['new_content']) > 5000:
                        fc_dict['new_content'] = fc_dict['new_content'][:5000] + "...[truncated]"
                    if fc_dict.get('old_content') and len(fc_dict['old_content']) > 5000:
                        fc_dict['old_content'] = fc_dict['old_content'][:5000] + "...[truncated]"
                    file_changes_data.append(fc_dict)
                
                changes_dict = asdict(changes)
                changes_dict['file_changes'] = file_changes_data
                data[str(user_id)] = changes_dict
            
            with open(self.pending_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save pending approvals: {e}")
    
    def _load_pending_approvals(self):
        """Load pending approvals from file."""
        if not self.pending_file.exists():
            return
        
        try:
            with open(self.pending_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for user_id_str, changes_dict in data.items():
                user_id = int(user_id_str)
                
                # Convert file changes back to objects
                file_changes = []
                for fc_dict in changes_dict.get('file_changes', []):
                    file_changes.append(FileChange(**fc_dict))
                
                changes_dict['file_changes'] = file_changes
                changes_summary = ChangesSummary(**changes_dict)
                
                # Only load if not expired
                if time.time() - changes_summary.timestamp <= self.approval_timeout:
                    self.pending_approvals[user_id] = changes_summary
                    
        except Exception as e:
            logger.error(f"Failed to load pending approvals: {e}")
    
    def format_changes_summary(self, changes: ChangesSummary) -> str:
        """Format changes summary for display to user."""
        summary_parts = []
        
        summary_parts.append(f"📋 **Changes Summary for {changes.repo_name}**")
        summary_parts.append(f"🌿 **Branch:** {changes.branch_name}")
        summary_parts.append("")
        
        # Files overview
        total_files = len(changes.files_created) + len(changes.files_modified) + len(changes.files_deleted)
        summary_parts.append(f"📊 **Overview:** {total_files} files affected")
        
        if changes.total_lines_added > 0 or changes.total_lines_removed > 0:
            summary_parts.append(f"📈 **Lines:** +{changes.total_lines_added} -{changes.total_lines_removed}")
        
        summary_parts.append("")
        
        # File details
        if changes.files_created:
            summary_parts.append(f"✨ **Files Created ({len(changes.files_created)}):**")
            for file_path in changes.files_created[:5]:  # Limit display
                summary_parts.append(f"   • {file_path}")
            if len(changes.files_created) > 5:
                summary_parts.append(f"   • ... and {len(changes.files_created) - 5} more")
            summary_parts.append("")
        
        if changes.files_modified:
            summary_parts.append(f"✏️ **Files Modified ({len(changes.files_modified)}):**")
            for file_path in changes.files_modified[:5]:  # Limit display
                summary_parts.append(f"   • {file_path}")
            if len(changes.files_modified) > 5:
                summary_parts.append(f"   • ... and {len(changes.files_modified) - 5} more")
            summary_parts.append("")
        
        if changes.files_deleted:
            summary_parts.append(f"🗑️ **Files Deleted ({len(changes.files_deleted)}):**")
            for file_path in changes.files_deleted:
                summary_parts.append(f"   • {file_path}")
            summary_parts.append("")
        
        # Commit message preview
        commit_lines = changes.commit_message.split('\n')
        summary_parts.append(f"💬 **Commit Message:**")
        summary_parts.append(f"   {commit_lines[0]}")
        summary_parts.append("")
        
        # Time info
        time_ago = int((time.time() - changes.timestamp) / 60)
        summary_parts.append(f"⏰ **Generated:** {time_ago} minutes ago")
        
        return "\n".join(summary_parts)