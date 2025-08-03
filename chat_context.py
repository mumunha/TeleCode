import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import deque

logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str
    repo_context: Optional[str] = None  # Repository name when message was sent
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        return cls(**data)

class ChatContextManager:
    def __init__(self, max_messages: int = None):
        # Use environment variable or default to 10
        self.max_messages = max_messages or int(os.environ.get('CHAT_CONTEXT_MAX_MESSAGES', '10'))
        self.context_dir = Path.home() / '.telecode_bot_context'
        self.context_dir.mkdir(exist_ok=True)
        self.contexts: Dict[int, deque] = {}
        self._load_all_contexts()
    
    def _get_context_file(self, user_id: int) -> Path:
        """Get the context file path for a user."""
        return self.context_dir / f"user_{user_id}_context.json"
    
    def _load_user_context(self, user_id: int) -> None:
        """Load chat context for a specific user from disk."""
        context_file = self._get_context_file(user_id)
        
        try:
            if context_file.exists():
                with open(context_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    messages = [ChatMessage.from_dict(msg_data) for msg_data in data.get('messages', [])]
                    self.contexts[user_id] = deque(messages, maxlen=self.max_messages)
                    logger.debug(f"Loaded {len(messages)} messages for user {user_id}")
            else:
                self.contexts[user_id] = deque(maxlen=self.max_messages)
        except Exception as e:
            logger.error(f"Error loading context for user {user_id}: {e}")
            self.contexts[user_id] = deque(maxlen=self.max_messages)
    
    def _load_all_contexts(self) -> None:
        """Load all existing user contexts on startup."""
        try:
            for context_file in self.context_dir.glob("user_*_context.json"):
                try:
                    user_id = int(context_file.stem.split('_')[1])
                    self._load_user_context(user_id)
                except (ValueError, IndexError):
                    logger.warning(f"Invalid context file name: {context_file}")
                    continue
        except Exception as e:
            logger.error(f"Error loading contexts: {e}")
    
    def _save_user_context(self, user_id: int) -> None:
        """Save chat context for a specific user to disk."""
        if user_id not in self.contexts:
            return
        
        context_file = self._get_context_file(user_id)
        
        try:
            context_data = {
                'user_id': user_id,
                'last_updated': datetime.now().isoformat(),
                'messages': [msg.to_dict() for msg in self.contexts[user_id]]
            }
            
            with open(context_file, 'w', encoding='utf-8') as f:
                json.dump(context_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved context for user {user_id}: {len(self.contexts[user_id])} messages")
        except Exception as e:
            logger.error(f"Error saving context for user {user_id}: {e}")
    
    def add_user_message(self, user_id: int, content: str, repo_context: Optional[str] = None) -> None:
        """Add a user message to the chat context."""
        if user_id not in self.contexts:
            self._load_user_context(user_id)
        
        message = ChatMessage(
            role='user',
            content=content,
            timestamp=datetime.now().isoformat(),
            repo_context=repo_context
        )
        
        self.contexts[user_id].append(message)
        self._save_user_context(user_id)
        logger.debug(f"Added user message for {user_id}: {content[:50]}...")
    
    def add_assistant_message(self, user_id: int, content: str, repo_context: Optional[str] = None) -> None:
        """Add an assistant message to the chat context."""
        if user_id not in self.contexts:
            self._load_user_context(user_id)
        
        message = ChatMessage(
            role='assistant',
            content=content,
            timestamp=datetime.now().isoformat(),
            repo_context=repo_context
        )
        
        self.contexts[user_id].append(message)
        self._save_user_context(user_id)
        logger.debug(f"Added assistant message for {user_id}: {content[:50]}...")
    
    def get_context_for_llm(self, user_id: int) -> List[Dict[str, str]]:
        """Get chat context formatted for LLM providers (OpenAI format)."""
        if user_id not in self.contexts:
            self._load_user_context(user_id)
        
        if not self.contexts[user_id]:
            return []
        
        # Convert to OpenAI format
        llm_messages = []
        for msg in self.contexts[user_id]:
            llm_messages.append({
                'role': msg.role,
                'content': msg.content
            })
        
        return llm_messages
    
    def get_context_summary(self, user_id: int) -> Dict[str, Any]:
        """Get a summary of the user's chat context."""
        if user_id not in self.contexts:
            self._load_user_context(user_id)
        
        messages = list(self.contexts[user_id])
        
        if not messages:
            return {
                'message_count': 0,
                'last_interaction': None,
                'current_repo': None
            }
        
        # Find the most recent repository context
        current_repo = None
        for msg in reversed(messages):
            if msg.repo_context:
                current_repo = msg.repo_context
                break
        
        return {
            'message_count': len(messages),
            'last_interaction': messages[-1].timestamp if messages else None,
            'current_repo': current_repo,
            'first_message_time': messages[0].timestamp if messages else None
        }
    
    def clear_context(self, user_id: int) -> bool:
        """Clear chat context for a user."""
        try:
            if user_id in self.contexts:
                self.contexts[user_id].clear()
                self._save_user_context(user_id)
            
            # Also remove the file
            context_file = self._get_context_file(user_id)
            if context_file.exists():
                context_file.unlink()
            
            logger.info(f"Cleared context for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing context for user {user_id}: {e}")
            return False
    
    def cleanup_old_contexts(self, days_old: int = 30) -> None:
        """Remove context files older than specified days."""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_old)
            
            for context_file in self.context_dir.glob("user_*_context.json"):
                try:
                    # Check file modification time
                    if datetime.fromtimestamp(context_file.stat().st_mtime) < cutoff_time:
                        context_file.unlink()
                        logger.info(f"Removed old context file: {context_file}")
                        
                        # Also remove from memory if loaded
                        try:
                            user_id = int(context_file.stem.split('_')[1])
                            if user_id in self.contexts:
                                del self.contexts[user_id]
                        except (ValueError, IndexError):
                            continue
                            
                except Exception as e:
                    logger.warning(f"Error processing context file {context_file}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error during context cleanup: {e}")
    
    def count_tokens(self, text: str, model: str = "gpt-4") -> int:
        """Count tokens in text using tiktoken for accurate estimates."""
        try:
            import tiktoken
            
            # Map common models to their tiktoken encodings
            model_map = {
                'gpt-4': 'cl100k_base',
                'gpt-3.5-turbo': 'cl100k_base', 
                # Note: Claude models removed, using OpenAI encoding as approximation for any future models
                'meta-llama/Llama-3.3-70B-Instruct-Turbo': 'cl100k_base'  # Approximate
            }
            
            encoding_name = model_map.get(model, 'cl100k_base')
            encoding = tiktoken.get_encoding(encoding_name)
            
            return len(encoding.encode(text))
            
        except ImportError:
            logger.warning("tiktoken not available, using rough estimate")
            # Rough estimate: ~4 characters per token
            return len(text) // 4
        except Exception as e:
            logger.warning(f"Error counting tokens: {e}, using rough estimate")
            return len(text) // 4
    
    def get_context_token_stats(self, user_id: int, model: str = "gpt-4") -> Dict[str, Any]:
        """Get token statistics for user's chat context."""
        if user_id not in self.contexts:
            self._load_user_context(user_id)
        
        if not self.contexts[user_id]:
            return {
                'total_messages': 0,
                'total_tokens': 0,
                'tokens_per_message': [],
                'model_used': model
            }
        
        messages = list(self.contexts[user_id])
        tokens_per_message = []
        total_tokens = 0
        
        for msg in messages:
            token_count = self.count_tokens(msg.content, model)
            tokens_per_message.append({
                'role': msg.role,
                'tokens': token_count,
                'content_preview': msg.content[:50] + ('...' if len(msg.content) > 50 else '')
            })
            total_tokens += token_count
        
        # Calculate tokens for the entire conversation context
        full_context = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])
        context_tokens = self.count_tokens(full_context, model)
        
        return {
            'total_messages': len(messages),
            'total_tokens': total_tokens,
            'context_tokens': context_tokens,  # Total when sent as context
            'tokens_per_message': tokens_per_message,
            'model_used': model,
            'avg_tokens_per_message': total_tokens // len(messages) if messages else 0
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics about stored contexts."""
        total_users = len(list(self.context_dir.glob("user_*_context.json")))
        loaded_users = len(self.contexts)
        total_messages = sum(len(ctx) for ctx in self.contexts.values())
        
        return {
            'total_users_with_context': total_users,
            'loaded_users': loaded_users,
            'total_messages_in_memory': total_messages,
            'context_directory': str(self.context_dir),
            'max_messages_per_user': self.max_messages
        }