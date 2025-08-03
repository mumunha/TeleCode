import os
import logging
import hashlib
import time
from typing import Set, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self):
        self.authorized_users: Set[int] = self._load_authorized_users()
        self.rate_limits: Dict[int, Dict] = {}
        self.session_tokens: Dict[int, str] = {}
        
        self.max_requests_per_hour = int(os.environ.get('MAX_REQUESTS_PER_HOUR', '10'))
        self.max_requests_per_day = int(os.environ.get('MAX_REQUESTS_PER_DAY', '50'))
        
    def _load_authorized_users(self) -> Set[int]:
        """Load authorized user IDs from environment variable."""
        users_env = os.environ.get('AUTHORIZED_TELEGRAM_USERS', '')
        if not users_env:
            logger.warning("No authorized users configured. Bot will be open to all users.")
            return set()
        
        try:
            user_ids = [int(uid.strip()) for uid in users_env.split(',') if uid.strip()]
            logger.info(f"Loaded {len(user_ids)} authorized users")
            return set(user_ids)
        except ValueError as e:
            logger.error(f"Error parsing authorized users: {e}")
            return set()
    
    def is_user_authorized(self, user_id: int) -> bool:
        """Check if user is authorized to use the bot."""
        if not self.authorized_users:
            return True
        
        is_authorized = user_id in self.authorized_users
        if not is_authorized:
            logger.warning(f"Unauthorized access attempt from user {user_id}")
        
        return is_authorized
    
    def check_rate_limit(self, user_id: int) -> Dict[str, any]:
        """Check if user has exceeded rate limits."""
        current_time = datetime.now()
        
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = {
                'hourly': {'count': 0, 'reset_time': current_time + timedelta(hours=1)},
                'daily': {'count': 0, 'reset_time': current_time + timedelta(days=1)}
            }
        
        user_limits = self.rate_limits[user_id]
        
        if current_time > user_limits['hourly']['reset_time']:
            user_limits['hourly'] = {'count': 0, 'reset_time': current_time + timedelta(hours=1)}
        
        if current_time > user_limits['daily']['reset_time']:
            user_limits['daily'] = {'count': 0, 'reset_time': current_time + timedelta(days=1)}
        
        if user_limits['hourly']['count'] >= self.max_requests_per_hour:
            reset_in_minutes = int((user_limits['hourly']['reset_time'] - current_time).total_seconds() / 60)
            return {
                'allowed': False,
                'reason': 'hourly_limit_exceeded',
                'reset_in_minutes': reset_in_minutes,
                'current_count': user_limits['hourly']['count'],
                'limit': self.max_requests_per_hour
            }
        
        if user_limits['daily']['count'] >= self.max_requests_per_day:
            reset_in_hours = int((user_limits['daily']['reset_time'] - current_time).total_seconds() / 3600)
            return {
                'allowed': False,
                'reason': 'daily_limit_exceeded',
                'reset_in_hours': reset_in_hours,
                'current_count': user_limits['daily']['count'],
                'limit': self.max_requests_per_day
            }
        
        user_limits['hourly']['count'] += 1
        user_limits['daily']['count'] += 1
        
        return {
            'allowed': True,
            'hourly_remaining': self.max_requests_per_hour - user_limits['hourly']['count'],
            'daily_remaining': self.max_requests_per_day - user_limits['daily']['count']
        }
    
    def generate_session_token(self, user_id: int) -> str:
        """Generate a session token for a user."""
        timestamp = str(int(time.time()))
        data = f"{user_id}:{timestamp}:{os.environ.get('BOT_TOKEN', 'default_secret')}"
        token = hashlib.sha256(data.encode()).hexdigest()[:16]
        
        self.session_tokens[user_id] = token
        logger.info(f"Generated session token for user {user_id}")
        
        return token
    
    def validate_session_token(self, user_id: int, token: str) -> bool:
        """Validate a session token for a user."""
        stored_token = self.session_tokens.get(user_id)
        is_valid = stored_token == token
        
        if not is_valid:
            logger.warning(f"Invalid session token for user {user_id}")
        
        return is_valid
    
    def revoke_session_token(self, user_id: int):
        """Revoke a user's session token."""
        if user_id in self.session_tokens:
            del self.session_tokens[user_id]
            logger.info(f"Revoked session token for user {user_id}")
    
    def get_user_stats(self, user_id: int) -> Dict[str, any]:
        """Get usage statistics for a user."""
        if user_id not in self.rate_limits:
            return {
                'hourly_used': 0,
                'hourly_limit': self.max_requests_per_hour,
                'daily_used': 0,
                'daily_limit': self.max_requests_per_day
            }
        
        user_limits = self.rate_limits[user_id]
        current_time = datetime.now()
        
        hourly_used = user_limits['hourly']['count'] if current_time <= user_limits['hourly']['reset_time'] else 0
        daily_used = user_limits['daily']['count'] if current_time <= user_limits['daily']['reset_time'] else 0
        
        return {
            'hourly_used': hourly_used,
            'hourly_limit': self.max_requests_per_hour,
            'hourly_remaining': self.max_requests_per_hour - hourly_used,
            'daily_used': daily_used,
            'daily_limit': self.max_requests_per_day,
            'daily_remaining': self.max_requests_per_day - daily_used,
            'next_hourly_reset': user_limits['hourly']['reset_time'].isoformat() if current_time <= user_limits['hourly']['reset_time'] else None,
            'next_daily_reset': user_limits['daily']['reset_time'].isoformat() if current_time <= user_limits['daily']['reset_time'] else None
        }
    
    def log_security_event(self, event_type: str, user_id: int, details: str = ""):
        """Log security-related events."""
        timestamp = datetime.now().isoformat()
        logger.info(f"SECURITY_EVENT: {timestamp} | {event_type} | User: {user_id} | {details}")
    
    def validate_github_repo_access(self, user_id: int, repo_url: str) -> Dict[str, any]:
        """Validate if user can access a specific GitHub repository."""
        allowed_repos_env = os.environ.get(f'ALLOWED_REPOS_USER_{user_id}', '')
        
        if not allowed_repos_env:
            global_repos = os.environ.get('ALLOWED_REPOS_GLOBAL', '')
            if not global_repos:
                return {'allowed': True, 'reason': 'no_restrictions'}
            allowed_repos_env = global_repos
        
        allowed_repos = [repo.strip() for repo in allowed_repos_env.split(',') if repo.strip()]
        
        for allowed_repo in allowed_repos:
            if allowed_repo in repo_url or repo_url.endswith(allowed_repo):
                self.log_security_event("REPO_ACCESS_GRANTED", user_id, f"Repository: {repo_url}")
                return {'allowed': True, 'reason': 'explicitly_allowed'}
        
        self.log_security_event("REPO_ACCESS_DENIED", user_id, f"Repository: {repo_url}")
        return {
            'allowed': False, 
            'reason': 'not_in_allowed_list',
            'allowed_repos': allowed_repos
        }
    
    def sanitize_commit_message(self, message: str) -> str:
        """Sanitize commit messages to prevent injection attacks."""
        max_length = 200
        forbidden_chars = ['`', '$', '\\', ';', '|', '&']
        
        sanitized = message[:max_length]
        
        for char in forbidden_chars:
            sanitized = sanitized.replace(char, '')
        
        sanitized = sanitized.strip()
        
        if not sanitized:
            sanitized = "TeleCode automated commit"
        
        return sanitized
    
    def is_safe_file_operation(self, file_path: str) -> bool:
        """Check if a file operation is safe to perform."""
        dangerous_paths = [
            '.git/',
            '../',
            '~/',
            '/etc/',
            '/var/',
            '/usr/',
            '.env',
            'config.py',
            'settings.py'
        ]
        
        dangerous_extensions = ['.exe', '.bat', '.sh', '.ps1', '.cmd']
        
        for dangerous_path in dangerous_paths:
            if dangerous_path in file_path:
                return False
        
        for ext in dangerous_extensions:
            if file_path.lower().endswith(ext):
                return False
        
        return True