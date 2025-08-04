"""
Advanced Repository Context Manager for TeleCode Bot

This module provides comprehensive codebase context collection including:
- Intelligent file content reading
- Prompt-aware file selection
- Token management and optimization
- File relationship mapping
- Configurable context depth
"""

import os
import re
import logging
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict
import time

logger = logging.getLogger(__name__)

@dataclass
class FileInfo:
    """Information about a file in the repository."""
    path: str
    relative_path: str
    size: int
    extension: str
    content: str = ""
    importance_score: float = 0.0
    tokens_estimate: int = 0
    last_modified: float = 0.0
    language: str = ""

@dataclass
class ContextResult:
    """Result of context collection."""
    files: List[FileInfo]
    total_tokens: int
    total_files: int
    truncated: bool
    structure: str
    config_info: str

class AdvancedRepositoryContext:
    """Advanced repository context manager with intelligent file selection."""
    
    def __init__(self):
        # Configuration from environment variables
        self.max_context_tokens = int(os.environ.get('REPO_CONTEXT_MAX_TOKENS', '15000'))
        self.max_files = int(os.environ.get('REPO_CONTEXT_MAX_FILES', '20'))
        self.max_file_size = int(os.environ.get('REPO_CONTEXT_MAX_FILE_SIZE', '10000'))  # chars
        self.context_depth = int(os.environ.get('REPO_CONTEXT_DEPTH', '3'))  # directory levels
        
        # File type configurations
        self.code_extensions = {
            '.py': 'python',
            '.js': 'javascript', 
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.r': 'r',
            '.sql': 'sql',
            '.sh': 'bash',
            '.bat': 'batch',
            '.ps1': 'powershell',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.json': 'json',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.md': 'markdown',
            '.dockerfile': 'dockerfile',
            '.tf': 'terraform'
        }
        
        self.config_files = {
            'package.json', 'requirements.txt', 'Cargo.toml', 'go.mod', 'pom.xml',
            'Gemfile', 'composer.json', 'pubspec.yaml', 'build.gradle', 'CMakeLists.txt',
            '.gitignore', 'README.md', 'LICENSE', 'Dockerfile', 'docker-compose.yml',
            'pyproject.toml', 'setup.py', 'Makefile', 'webpack.config.js', 'tsconfig.json'
        }
        
        self.ignore_patterns = {
            # Directories to skip
            'node_modules', '__pycache__', '.git', 'target', 'build', 'dist',
            '.next', '.nuxt', 'coverage', '.pytest_cache', '.mypy_cache',
            'vendor', 'venv', 'env', '.venv', '.env', 'htmlcov',
            # File patterns to skip
            '*.log', '*.tmp', '*.cache', '*.lock', '*.pyc', '*.pyo',
            '*.class', '*.o', '*.so', '*.dylib', '*.dll', '*.exe'
        }
        
        # Cache for file contents and analysis
        self.file_cache = {}
        self.context_cache = {}
        self.relationship_cache = {}
        self.last_scan_time = 0
        self.cache_ttl = 300  # 5 minutes
    
    def get_comprehensive_context(self, repo_path: str, user_prompt: str = "") -> ContextResult:
        """Get comprehensive repository context with intelligent file selection."""
        try:
            start_time = time.time()
            logger.info(f"Starting comprehensive context collection for: {repo_path}")
            
            # Check cache first
            cache_key = self._generate_cache_key(repo_path, user_prompt)
            cached_result = self._get_cached_context(cache_key)
            if cached_result:
                logger.info(f"Using cached context for: {repo_path}")
                return cached_result
            
            # Scan repository for all relevant files
            all_files = self._scan_repository(repo_path)
            logger.info(f"Found {len(all_files)} files in repository")
            
            # Analyze prompt for relevant keywords and file hints
            prompt_keywords = self._extract_prompt_keywords(user_prompt)
            logger.info(f"Extracted prompt keywords: {prompt_keywords[:5]}...")  # Log first 5
            
            # Score and prioritize files based on relevance
            scored_files = self._score_file_relevance(all_files, prompt_keywords, user_prompt)
            
            # Select files within token and count limits
            selected_files = self._select_optimal_files(scored_files)
            
            # Read file contents for selected files
            files_with_content = self._read_file_contents(selected_files, repo_path)
            
            # Generate repository structure
            structure = self._generate_enhanced_structure(repo_path, selected_files)
            
            # Get configuration info
            config_info = self._get_config_information(repo_path)
            
            # Calculate final statistics
            total_tokens = sum(f.tokens_estimate for f in files_with_content)
            truncated = len(scored_files) > len(files_with_content)
            
            elapsed = time.time() - start_time
            logger.info(f"Context collection completed in {elapsed:.2f}s: {len(files_with_content)} files, ~{total_tokens} tokens")
            
            result = ContextResult(
                files=files_with_content,
                total_tokens=total_tokens,
                total_files=len(files_with_content),
                truncated=truncated,
                structure=structure,
                config_info=config_info
            )
            
            # Cache the result
            self._cache_context(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error collecting comprehensive context: {e}")
            # Fallback to basic context
            return self._get_fallback_context(repo_path)
    
    def _scan_repository(self, repo_path: str) -> List[FileInfo]:
        """Scan repository and collect file metadata."""
        files = []
        repo_path_obj = Path(repo_path)
        
        for root, dirs, filenames in os.walk(repo_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self._should_ignore_directory(d)]
            
            # Check depth limit
            current_depth = Path(root).relative_to(repo_path_obj).parts
            if len(current_depth) > self.context_depth:
                continue
            
            for filename in filenames:
                if self._should_ignore_file(filename):
                    continue
                
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, repo_path)
                
                try:
                    stat_info = os.stat(file_path)
                    file_size = stat_info.st_size
                    
                    # Skip very large files
                    if file_size > self.max_file_size * 4:  # Rough char estimate
                        continue
                    
                    extension = Path(filename).suffix.lower()
                    language = self.code_extensions.get(extension, 'text')
                    
                    file_info = FileInfo(
                        path=file_path,
                        relative_path=relative_path,
                        size=file_size,
                        extension=extension,
                        last_modified=stat_info.st_mtime,
                        language=language
                    )
                    
                    files.append(file_info)
                    
                except (OSError, IOError) as e:
                    logger.warning(f"Could not access file {file_path}: {e}")
                    continue
        
        return files
    
    def _extract_prompt_keywords(self, prompt: str) -> List[str]:
        """Extract relevant keywords from user prompt for file selection."""
        if not prompt:
            return []
        
        # Common programming keywords and patterns
        keywords = []
        
        # Extract quoted strings (likely file/function names)
        quoted_matches = re.findall(r'["\']([^"\']+)["\']', prompt)
        keywords.extend(quoted_matches)
        
        # Extract probable file names with extensions
        file_matches = re.findall(r'\b\w+\.\w+\b', prompt)
        keywords.extend(file_matches)
        
        # Extract probable function/class names (CamelCase, snake_case)
        identifier_matches = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', prompt)
        keywords.extend([m for m in identifier_matches if len(m) > 2])
        
        # Extract technical terms and action words
        tech_words = re.findall(r'\b(?:function|class|method|component|service|controller|model|view|router|handler|middleware|config|setup|init|create|update|delete|get|post|put|api|endpoint|database|db|auth|login|register|user|admin|dashboard|form|button|input|validation|error|exception|test|spec|mock|util|helper|lib|library|module|package|import|export)\b', prompt.lower())
        keywords.extend(tech_words)
        
        # Remove duplicates and filter short words
        unique_keywords = list(set(k for k in keywords if len(k) > 1))
        
        return unique_keywords[:50]  # Limit to prevent overwhelming
    
    def _build_file_relationships(self, files: List[FileInfo]) -> Dict[str, Set[str]]:
        """Build a map of file relationships based on imports and references."""
        relationships = defaultdict(set)
        
        # Quick scan for import patterns in code files
        for file_info in files:
            if file_info.extension not in self.code_extensions:
                continue
                
            try:
                # Read file content for import analysis (limited read)
                with open(file_info.path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(2000)  # Read first 2000 chars for import analysis
                
                # Extract imports based on file type
                referenced_files = self._extract_file_references(content, file_info.language, file_info.relative_path)
                
                # Map references to actual files in the repository
                for ref in referenced_files:
                    for other_file in files:
                        if self._matches_reference(other_file.relative_path, ref):
                            relationships[other_file.relative_path].add(file_info.relative_path)
                            break
                            
            except Exception as e:
                # Skip files we can't read for relationship analysis
                continue
        
        return dict(relationships)
    
    def _extract_file_references(self, content: str, language: str, current_file: str) -> List[str]:
        """Extract file references from source code based on language."""
        references = []
        
        if language == 'python':
            # Python imports
            import_patterns = [
                r'from\s+([a-zA-Z_][a-zA-Z0-9_\.]*)\s+import',
                r'import\s+([a-zA-Z_][a-zA-Z0-9_\.]*)',
            ]
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                references.extend(matches)
        
        elif language in ['javascript', 'typescript']:
            # JavaScript/TypeScript imports
            import_patterns = [
                r'import.*from\s+["\']([^"\']+)["\']',
                r'require\(["\']([^"\']+)["\']\)',
                r'import\(["\']([^"\']+)["\']\)',
            ]
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                references.extend(matches)
        
        elif language == 'java':
            # Java imports
            import_pattern = r'import\s+([a-zA-Z_][a-zA-Z0-9_\.]*)'
            matches = re.findall(import_pattern, content)
            references.extend(matches)
        
        elif language == 'go':
            # Go imports
            import_patterns = [
                r'import\s+"([^"]+)"',
                r'import\s+\(\s*\n((?:\s*"[^"]+"\s*\n)*)\s*\)',
            ]
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                if isinstance(matches, list) and len(matches) > 0:
                    if isinstance(matches[0], str) and '\n' in matches[0]:
                        # Multi-line import block
                        sub_imports = re.findall(r'"([^"]+)"', matches[0])
                        references.extend(sub_imports)
                    else:
                        references.extend(matches)
        
        elif language in ['c', 'cpp']:
            # C/C++ includes
            include_pattern = r'#include\s+[<"]([^>"]+)[>"]'
            matches = re.findall(include_pattern, content)
            references.extend(matches)
        
        return references
    
    def _matches_reference(self, file_path: str, reference: str) -> bool:
        """Check if a file path matches an import reference."""
        # Simple matching logic - can be enhanced
        file_path_lower = file_path.lower()
        reference_lower = reference.lower()
        
        # Direct name match
        if reference_lower in file_path_lower:
            return True
        
        # Python module style matching
        if '.' in reference:
            module_path = reference.replace('.', '/')
            if module_path in file_path_lower:
                return True
        
        # File extension matching
        base_ref = reference.split('/')[-1].split('.')[0]
        file_base = file_path.split('/')[-1].split('.')[0]
        if base_ref == file_base:
            return True
        
        return False
    
    def _score_file_relevance(self, files: List[FileInfo], keywords: List[str], prompt: str) -> List[FileInfo]:
        """Score files based on relevance to the prompt and general importance."""
        
        # Build file relationship map
        file_relationships = self._build_file_relationships(files)
        
        for file_info in files:
            score = 0.0
            
            # Base score for file type importance
            if file_info.extension in self.code_extensions:
                score += 5.0
            
            # Config files are important
            if file_info.relative_path.split('/')[-1] in self.config_files:
                score += 8.0
            
            # Main entry points are important
            main_files = ['main.py', 'index.js', 'app.py', 'server.js', 'main.go', 'main.rs']
            if any(main_file in file_info.relative_path.lower() for main_file in main_files):
                score += 6.0
            
            # Shorter paths are often more important (closer to root)
            path_depth = len(file_info.relative_path.split('/'))
            score += max(0, 5 - path_depth)
            
            # Recently modified files are more relevant
            days_old = (time.time() - file_info.last_modified) / (24 * 3600)
            if days_old < 7:
                score += 3.0
            elif days_old < 30:
                score += 1.0
            
            # Keyword matching in file path/name
            file_text = file_info.relative_path.lower()
            for keyword in keywords:
                if keyword.lower() in file_text:
                    score += 3.0
            
            # Prompt keyword matching (more sophisticated)
            prompt_lower = prompt.lower()
            if any(keyword.lower() in file_text for keyword in keywords):
                score += 2.0
            
            # File relationship bonus - files that are imported/referenced by high-score files
            if file_info.relative_path in file_relationships:
                relationship_bonus = len(file_relationships[file_info.relative_path]) * 0.5
                score += min(relationship_bonus, 3.0)  # Cap the bonus
            
            file_info.importance_score = score
        
        # Sort by importance score (descending)
        return sorted(files, key=lambda f: f.importance_score, reverse=True)
    
    def _select_optimal_files(self, scored_files: List[FileInfo]) -> List[FileInfo]:
        """Select optimal set of files within limits."""
        selected = []
        estimated_tokens = 0
        
        for file_info in scored_files:
            # Skip files with very low relevance (unless they're config files)
            if file_info.importance_score < 1.0 and file_info.relative_path.split('/')[-1] not in self.config_files:
                continue
            
            # Estimate tokens for this file (rough calculation)
            file_tokens = min(file_info.size // 3, self.max_file_size // 3)  # Conservative estimate
            
            # Check if adding this file would exceed limits
            if (len(selected) >= self.max_files or 
                estimated_tokens + file_tokens > self.max_context_tokens):
                break
            
            selected.append(file_info)
            estimated_tokens += file_tokens
        
        return selected
    
    def _read_file_contents(self, selected_files: List[FileInfo], repo_path: str) -> List[FileInfo]:
        """Read actual file contents for selected files."""
        files_with_content = []
        
        for file_info in selected_files:
            try:
                with open(file_info.path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(self.max_file_size)
                    
                    # Estimate tokens (rough: 1 token ≈ 3-4 characters)
                    tokens_estimate = len(content) // 3
                    
                    file_info.content = content
                    file_info.tokens_estimate = tokens_estimate
                    
                    files_with_content.append(file_info)
                    
            except (OSError, IOError, UnicodeDecodeError) as e:
                logger.warning(f"Could not read file {file_info.path}: {e}")
                continue
        
        return files_with_content
    
    def _generate_enhanced_structure(self, repo_path: str, selected_files: List[FileInfo]) -> str:
        """Generate enhanced repository structure focused on selected files."""
        structure_lines = []
        
        # Build directory tree with selected files highlighted
        dirs_with_files = set()
        for file_info in selected_files:
            path_parts = file_info.relative_path.split('/')
            for i in range(len(path_parts)):
                dir_path = '/'.join(path_parts[:i+1])
                dirs_with_files.add(dir_path)
        
        # Create simplified structure showing context files
        structure_lines.append("Repository Structure (showing context files):")
        for file_info in selected_files[:15]:  # Show top 15
            indent = "  " * (len(file_info.relative_path.split('/')) - 1)
            score_indicator = f"[{file_info.importance_score:.1f}]" if file_info.importance_score > 0 else ""
            structure_lines.append(f"{indent}📄 {file_info.relative_path} {score_indicator}")
        
        if len(selected_files) > 15:
            structure_lines.append(f"  ... and {len(selected_files) - 15} more files")
        
        return "\n".join(structure_lines)
    
    def _get_config_information(self, repo_path: str) -> str:
        """Get important configuration file information."""
        config_info = []
        
        for config_file in self.config_files:
            config_path = os.path.join(repo_path, config_file)
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(1500)  # Limit config file content
                        config_info.append(f"{config_file}:\n{content}")
                except Exception as e:
                    logger.warning(f"Could not read config file {config_file}: {e}")
        
        return "\n\n".join(config_info)
    
    def _should_ignore_directory(self, dirname: str) -> bool:
        """Check if directory should be ignored."""
        return dirname.startswith('.') or dirname in self.ignore_patterns
    
    def _should_ignore_file(self, filename: str) -> bool:
        """Check if file should be ignored."""
        if filename.startswith('.') and filename not in {'.gitignore', '.env.example'}:
            return True
        
        for pattern in self.ignore_patterns:
            if '*' in pattern:
                # Simple glob pattern matching
                if pattern.replace('*', '') in filename:
                    return True
            elif filename == pattern:
                return True
        
        return False
    
    def _get_fallback_context(self, repo_path: str) -> ContextResult:
        """Fallback to basic context if advanced collection fails."""
        try:
            # Simple file listing
            files = []
            for root, dirs, filenames in os.walk(repo_path):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for filename in filenames[:5]:
                    if not filename.startswith('.'):
                        file_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(file_path, repo_path)
                        files.append(FileInfo(
                            path=file_path,
                            relative_path=relative_path,
                            size=0,
                            extension="",
                            importance_score=1.0
                        ))
                        
            structure = "Basic repository structure:\n" + "\n".join(f.relative_path for f in files[:10])
            
            return ContextResult(
                files=files[:5],
                total_tokens=100,
                total_files=len(files),
                truncated=True,
                structure=structure,
                config_info=""
            )
            
        except Exception as e:
            logger.error(f"Even fallback context failed: {e}")
            return ContextResult(
                files=[],
                total_tokens=0,
                total_files=0,
                truncated=False,
                structure="Could not analyze repository structure",
                config_info=""
            )
    
    def format_context_for_llm(self, context: ContextResult) -> str:
        """Format collected context for LLM consumption."""
        formatted_parts = []
        
        # Repository overview
        formatted_parts.append(f"Repository Analysis ({context.total_files} relevant files, ~{context.total_tokens} tokens):")
        formatted_parts.append("")
        
        # Structure
        if context.structure:
            formatted_parts.append(context.structure)
            formatted_parts.append("")
        
        # Configuration information
        if context.config_info:
            formatted_parts.append("Configuration Files:")
            formatted_parts.append(context.config_info)
            formatted_parts.append("")
        
        # File contents
        if context.files:
            formatted_parts.append("Relevant Source Files:")
            formatted_parts.append("")
            
            for file_info in context.files:
                formatted_parts.append(f"--- {file_info.relative_path} ({file_info.language}) ---")
                formatted_parts.append(file_info.content)
                formatted_parts.append("")
        
        # Truncation notice
        if context.truncated:
            formatted_parts.append("Note: Some files were excluded due to token/size limits.")
        
        return "\n".join(formatted_parts)
    
    def _generate_cache_key(self, repo_path: str, user_prompt: str) -> str:
        """Generate a cache key for the context request."""
        import hashlib
        
        # Include repo path, prompt, and recent file modification times
        key_components = [repo_path, user_prompt[:100]]  # Limit prompt length for key
        
        try:
            # Add repository modification indicator (latest file mod time)
            latest_mod = 0
            for root, dirs, files in os.walk(repo_path):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for filename in files[:10]:  # Sample files for mod time
                    try:
                        file_path = os.path.join(root, filename)
                        mod_time = os.path.getmtime(file_path)
                        latest_mod = max(latest_mod, mod_time)
                    except:
                        continue
                        
            key_components.append(str(int(latest_mod)))
        except:
            key_components.append(str(time.time()))
        
        key_string = "|".join(key_components)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_context(self, cache_key: str) -> Optional[ContextResult]:
        """Get cached context if available and not expired."""
        if cache_key not in self.context_cache:
            return None
        
        cached_entry = self.context_cache[cache_key]
        cache_time = cached_entry.get('timestamp', 0)
        
        # Check if cache is expired
        if time.time() - cache_time > self.cache_ttl:
            del self.context_cache[cache_key]
            return None
        
        return cached_entry.get('result')
    
    def _cache_context(self, cache_key: str, result: ContextResult):
        """Cache the context result."""
        self.context_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
        
        # Clean up old cache entries (keep only last 10)
        if len(self.context_cache) > 10:
            oldest_keys = sorted(self.context_cache.keys(), 
                               key=lambda k: self.context_cache[k]['timestamp'])
            for old_key in oldest_keys[:-10]:
                del self.context_cache[old_key]