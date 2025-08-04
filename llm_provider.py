import os
import logging
import time
from openai import AsyncOpenAI
from typing import List, Dict, Any
from dataclasses import dataclass
from advanced_context import AdvancedRepositoryContext

logger = logging.getLogger(__name__)

@dataclass
class LLMMessage:
    role: str
    content: str

class LLMProvider:
    def __init__(self):
        self.provider = os.environ.get('LLM_PROVIDER', 'openai').lower()
        self.advanced_context = AdvancedRepositoryContext()
        self.setup_client()
    
    def setup_client(self):
        """Setup the appropriate LLM client based on provider."""
        if self.provider == 'together':
            self.client = AsyncOpenAI(
                api_key=os.environ.get('TOGETHER_API_KEY'),
                base_url="https://api.together.xyz/v1"
            )
            self.model = os.environ.get('TOGETHER_MODEL', 'meta-llama/Llama-3.3-70B-Instruct-Turbo')
            logger.info(f"Using Together AI with model: {self.model}")
            
        elif self.provider == 'openai':
            self.client = AsyncOpenAI(
                api_key=os.environ.get('OPENAI_API_KEY')
            )
            self.model = os.environ.get('OPENAI_MODEL', 'gpt-4')
            logger.info(f"Using OpenAI with model: {self.model}")
            
        elif self.provider == 'openrouter':
            # OpenRouter uses OpenAI-compatible API with custom headers
            self.client = AsyncOpenAI(
                api_key=os.environ.get('OPENROUTER_API_KEY'),
                base_url="https://openrouter.ai/api/v1"
            )
            self.model = os.environ.get('OPENROUTER_MODEL', 'openai/gpt-4o')
            
            # Add optional headers for OpenRouter
            self.openrouter_headers = {}
            if os.environ.get('OPENROUTER_SITE_URL'):
                self.openrouter_headers['HTTP-Referer'] = os.environ.get('OPENROUTER_SITE_URL')
            if os.environ.get('OPENROUTER_SITE_NAME'):
                self.openrouter_headers['X-Title'] = os.environ.get('OPENROUTER_SITE_NAME')
                
            logger.info(f"Using OpenRouter with model: {self.model}")
            
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}. Supported providers: 'openai', 'together', 'openrouter'")
    
    async def generate_code_response(self, prompt: str, repo_path: str = None, chat_context: List[Dict[str, str]] = None) -> str:
        """Generate a response using the configured LLM provider."""
        max_retries = int(os.environ.get('LLM_MAX_RETRIES', '2'))
        retry_delay = float(os.environ.get('LLM_RETRY_DELAY', '5.0'))
        
        for attempt in range(max_retries + 1):
            try:
                use_streaming = os.environ.get('LLM_STREAMING', 'false').lower() == 'true'
                
                if use_streaming:
                    return await self._generate_with_streaming(prompt, repo_path, chat_context)
                else:
                    return await self._generate_with_openai_compatible(prompt, repo_path, chat_context)
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error generating response with {self.provider} (attempt {attempt + 1}/{max_retries + 1}): {e}")
                
                # Don't retry certain types of errors
                if any(keyword in error_msg.lower() for keyword in ['authentication', 'unauthorized', 'token limit', 'rate limit']):
                    logger.info("Not retrying due to error type")
                    raise
                
                # If this was the last attempt, raise the error
                if attempt == max_retries:
                    raise
                
                # Wait before retrying
                if attempt < max_retries:
                    import asyncio
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
    
    
    async def _generate_with_openai_compatible(self, prompt: str, repo_path: str = None, chat_context: List[Dict[str, str]] = None) -> str:
        """Generate response using OpenAI-compatible API (Together AI, OpenAI, etc.)."""
        
        # Build context-aware prompt for coding tasks
        system_prompt = self._build_system_prompt(repo_path)
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add chat context if available (preserve conversation history)
        if chat_context:
            messages.extend(chat_context)
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        # Add comprehensive repository context if available
        if repo_path and os.path.exists(repo_path):
            try:
                context_result = self.advanced_context.get_comprehensive_context(repo_path, prompt)
                formatted_context = self.advanced_context.format_context_for_llm(context_result)
                
                if formatted_context:
                    messages.insert(-1, {
                        "role": "system", 
                        "content": f"Repository context:\n{formatted_context}"
                    })
                    logger.info(f"Added comprehensive context: {context_result.total_files} files, ~{context_result.total_tokens} tokens")
            except Exception as e:
                logger.error(f"Failed to get advanced context, falling back to basic: {e}")
                # Fallback to basic context
                repo_context = self._get_repository_context(repo_path)
                if repo_context:
                    messages.insert(-1, {
                        "role": "system", 
                        "content": f"Repository context:\n{repo_context}"
                    })
        
        response = await self._make_api_call(messages)
        return response
    
    async def _generate_with_streaming(self, prompt: str, repo_path: str = None, chat_context: List[Dict[str, str]] = None) -> str:
        """Generate response using streaming API for real-time output."""
        
        # Build context-aware prompt for coding tasks
        system_prompt = self._build_system_prompt(repo_path)
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add chat context if available (preserve conversation history)
        if chat_context:
            messages.extend(chat_context)
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        # Add comprehensive repository context if available
        if repo_path and os.path.exists(repo_path):
            try:
                context_result = self.advanced_context.get_comprehensive_context(repo_path, prompt)
                formatted_context = self.advanced_context.format_context_for_llm(context_result)
                
                if formatted_context:
                    messages.insert(-1, {
                        "role": "system", 
                        "content": f"Repository context:\n{formatted_context}"
                    })
                    logger.info(f"Added comprehensive context: {context_result.total_files} files, ~{context_result.total_tokens} tokens")
            except Exception as e:
                logger.error(f"Failed to get advanced context, falling back to basic: {e}")
                # Fallback to basic context
                repo_context = self._get_repository_context(repo_path)
                if repo_context:
                    messages.insert(-1, {
                        "role": "system", 
                        "content": f"Repository context:\n{repo_context}"
                    })
        
        response = await self._make_streaming_api_call(messages)
        return response
    
    def _build_system_prompt(self, repo_path: str = None) -> str:
        """Build system prompt for coding tasks."""
        base_prompt = """You are an expert software engineer and coding assistant. You help developers with:

1. Code analysis and debugging
2. Feature implementation
3. Code refactoring and optimization
4. Writing tests and documentation
5. Best practices and security considerations

When working with code:
- Analyze the existing codebase structure and patterns
- Follow the project's coding conventions
- Provide complete, working code solutions
- Explain your changes clearly
- Consider edge cases and error handling
- Write clean, maintainable, and well-documented code

IMPORTANT: When you need to create or modify files, provide the complete file contents in a clear format. Use this structure:

**File: filename.ext**
```language
[complete file content here]
```

Always provide practical, actionable solutions that can be directly implemented."""

        if repo_path:
            base_prompt += f"\n\nYou are currently working in the repository at: {repo_path}"
            base_prompt += "\nAnalyze the existing codebase structure and follow established patterns."
        
        return base_prompt
    
    def _get_repository_context(self, repo_path: str, max_files: int = 10) -> str:
        """Get basic repository context for better code generation."""
        try:
            context_parts = []
            
            # Get repository structure
            structure = self._get_repo_structure(repo_path, max_files)
            if structure:
                context_parts.append(f"Repository structure:\n{structure}")
            
            # Get key configuration files
            config_files = ['package.json', 'requirements.txt', 'Cargo.toml', 'go.mod', 'pom.xml']
            for config_file in config_files:
                config_path = os.path.join(repo_path, config_file)
                if os.path.exists(config_path):
                    try:
                        with open(config_path, 'r', encoding='utf-8') as f:
                            content = f.read()[:1000]  # Limit content size
                            context_parts.append(f"{config_file}:\n{content}")
                    except Exception:
                        continue
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.warning(f"Error getting repository context: {e}")
            return ""
    
    def _get_repo_structure(self, repo_path: str, max_files: int = 10) -> str:
        """Get a simple repository structure."""
        try:
            structure_lines = []
            file_count = 0
            
            for root, dirs, files in os.walk(repo_path):
                # Skip hidden directories and common build/cache directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'target', 'build']]
                
                level = root.replace(repo_path, '').count(os.sep)
                indent = '  ' * level
                structure_lines.append(f"{indent}{os.path.basename(root)}/")
                
                subindent = '  ' * (level + 1)
                for file in files[:5]:  # Limit files per directory
                    if not file.startswith('.'):
                        structure_lines.append(f"{subindent}{file}")
                        file_count += 1
                        if file_count >= max_files:
                            structure_lines.append(f"{subindent}... (truncated)")
                            return "\n".join(structure_lines)
            
            return "\n".join(structure_lines)
            
        except Exception as e:
            logger.warning(f"Error getting repository structure: {e}")
            return ""
    
    async def _make_api_call(self, messages: List[Dict[str, str]]) -> str:
        """Make API call to the configured provider."""
        import asyncio
        
        # Get configurable timeout (default 5 minutes)
        timeout_seconds = float(os.environ.get('LLM_TIMEOUT_SECONDS', '300'))
        debug_mode = os.environ.get('DEBUG_LLM', 'false').lower() == 'true'
        
        # Calculate request statistics
        total_chars = sum(len(str(msg.get('content', ''))) for msg in messages)
        estimated_tokens = total_chars // 4  # Rough estimation
        
        if debug_mode:
            logger.info(f"🔍 LLM Request Debug Info:")
            logger.info(f"   Provider: {self.provider}")
            logger.info(f"   Model: {self.model}")
            logger.info(f"   Messages: {len(messages)}")
            logger.info(f"   Total characters: {total_chars:,}")
            logger.info(f"   Estimated tokens: {estimated_tokens:,}")
            logger.info(f"   Timeout: {timeout_seconds}s")
            
            # Log message structure (truncated)
            for i, msg in enumerate(messages):
                role = msg.get('role', 'unknown')
                content = str(msg.get('content', ''))
                content_preview = content[:100] + '...' if len(content) > 100 else content
                logger.info(f"   Message {i+1} ({role}): {content_preview}")
        
        start_time = time.time()
        logger.info(f"🚀 Starting LLM API call to {self.provider} ({self.model})")
        
        try:
            # Prepare request parameters
            request_params = {
                'model': self.model,
                'messages': messages,
                'max_tokens': int(os.environ.get('LLM_MAX_TOKENS', '8000')),
                'temperature': float(os.environ.get('LLM_TEMPERATURE', '0.1')),
                'stream': False
            }
            
            # Add OpenRouter headers if using OpenRouter
            if self.provider == 'openrouter' and hasattr(self, 'openrouter_headers'):
                request_params['extra_headers'] = self.openrouter_headers
            
            # Set timeout for API calls
            response = await asyncio.wait_for(
                self.client.chat.completions.create(**request_params),
                timeout=timeout_seconds
            )
            
            elapsed_time = time.time() - start_time
            
            if not response.choices or not response.choices[0].message.content:
                raise Exception("Empty response from LLM provider")
            
            response_content = response.choices[0].message.content
            response_tokens = len(response_content) // 4  # Rough estimation
            
            logger.info(f"✅ LLM API call completed successfully")
            logger.info(f"   Duration: {elapsed_time:.2f}s")
            logger.info(f"   Response length: {len(response_content):,} characters")
            logger.info(f"   Estimated response tokens: {response_tokens:,}")
            
            if debug_mode:
                logger.info(f"📝 LLM Response preview: {response_content[:200]}...")
                
            return response_content
            
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            logger.error(f"⏰ API call timed out after {elapsed_time:.2f}s (limit: {timeout_seconds}s)")
            raise Exception(f"Request timed out after {timeout_seconds}s - the task might be too complex. Please try breaking it into smaller parts.")
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = str(e)
            logger.error(f"❌ API call failed after {elapsed_time:.2f}s: {error_msg}")
            
            # Provide more specific error messages
            if "rate limit" in error_msg.lower():
                raise Exception("Rate limit exceeded. Please wait a few minutes before trying again.")
            elif "token" in error_msg.lower() and "limit" in error_msg.lower():
                raise Exception("Request too large. Please try a smaller or simpler task.")
            elif "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
                raise Exception("Authentication error. Please check API key configuration.")
            else:
                raise Exception(f"Failed to generate response: {error_msg}")
    
    async def _make_streaming_api_call(self, messages: List[Dict[str, str]]) -> str:
        """Make streaming API call to the configured provider."""
        import asyncio
        
        # Get configurable timeout (default 10 minutes for streaming)
        timeout_seconds = float(os.environ.get('LLM_STREAMING_TIMEOUT_SECONDS', '600'))
        debug_mode = os.environ.get('DEBUG_LLM', 'false').lower() == 'true'
        
        # Calculate request statistics
        total_chars = sum(len(str(msg.get('content', ''))) for msg in messages)
        estimated_tokens = total_chars // 4
        
        logger.info(f"🌊 Starting STREAMING LLM API call to {self.provider} ({self.model})")
        
        if debug_mode:
            logger.info(f"🔍 Streaming Request Debug Info:")
            logger.info(f"   Messages: {len(messages)}")
            logger.info(f"   Total characters: {total_chars:,}")
            logger.info(f"   Estimated tokens: {estimated_tokens:,}")
            logger.info(f"   Timeout: {timeout_seconds}s")
        
        start_time = time.time()
        collected_content = []
        
        try:
            # Prepare request parameters
            request_params = {
                'model': self.model,
                'messages': messages,
                'max_tokens': int(os.environ.get('LLM_MAX_TOKENS', '8000')),
                'temperature': float(os.environ.get('LLM_TEMPERATURE', '0.1')),
                'stream': True
            }
            
            # Add OpenRouter headers if using OpenRouter
            if self.provider == 'openrouter' and hasattr(self, 'openrouter_headers'):
                request_params['extra_headers'] = self.openrouter_headers
            
            stream = await asyncio.wait_for(
                self.client.chat.completions.create(**request_params),
                timeout=timeout_seconds
            )
            
            chunk_count = 0
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    collected_content.append(content)
                    chunk_count += 1
                    
                    if debug_mode and chunk_count % 10 == 0:  # Log every 10th chunk
                        logger.info(f"📝 Received chunk {chunk_count}, content: {content[:50]}...")
                    elif not debug_mode and chunk_count % 50 == 0:  # Less frequent for normal mode
                        elapsed = time.time() - start_time
                        logger.info(f"🌊 Streaming progress: {chunk_count} chunks received ({elapsed:.1f}s)")
            
            full_response = ''.join(collected_content)
            elapsed_time = time.time() - start_time
            
            if not full_response.strip():
                raise Exception("Empty response from streaming LLM provider")
            
            logger.info(f"✅ Streaming LLM API call completed successfully")
            logger.info(f"   Duration: {elapsed_time:.2f}s")
            logger.info(f"   Chunks received: {chunk_count}")
            logger.info(f"   Response length: {len(full_response):,} characters")
            
            if debug_mode:
                logger.info(f"📝 Final response preview: {full_response[:200]}...")
                
            return full_response
            
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            logger.error(f"⏰ Streaming API call timed out after {elapsed_time:.2f}s (limit: {timeout_seconds}s)")
            raise Exception(f"Streaming request timed out after {timeout_seconds}s - the task might be too complex.")
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = str(e)
            logger.error(f"❌ Streaming API call failed after {elapsed_time:.2f}s: {error_msg}")
            raise Exception(f"Streaming failed: {error_msg}")
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current provider configuration."""
        return {
            'provider': self.provider,
            'model': getattr(self, 'model', 'unknown'),
            'available': self._check_provider_availability()
        }
    
    def _check_provider_availability(self) -> bool:
        """Check if the current provider is properly configured."""
        try:
            if self.provider == 'together':
                return bool(os.environ.get('TOGETHER_API_KEY'))
            elif self.provider == 'openai':
                return bool(os.environ.get('OPENAI_API_KEY'))
            elif self.provider == 'openrouter':
                return bool(os.environ.get('OPENROUTER_API_KEY'))
            return False
        except Exception:
            return False
    
    def change_provider(self, new_provider: str, new_model: str = None) -> Dict[str, Any]:
        """Change the LLM provider and optionally the model."""
        supported_providers = ['openai', 'together', 'openrouter']
        
        if new_provider.lower() not in supported_providers:
            return {
                'success': False,
                'error': f"Unsupported provider: {new_provider}. Supported: {', '.join(supported_providers)}"
            }
        
        old_provider = self.provider
        old_model = getattr(self, 'model', 'unknown')
        
        try:
            # Set new provider
            self.provider = new_provider.lower()
            
            # Override model if provided
            if new_model:
                os.environ[f'{self.provider.upper()}_MODEL'] = new_model
            
            # Reinitialize client with new provider
            self.setup_client()
            
            # Check if new provider is available
            if not self._check_provider_availability():
                # Rollback
                self.provider = old_provider
                self.setup_client()
                return {
                    'success': False,
                    'error': f"Provider {new_provider} is not properly configured (missing API key)"
                }
            
            logger.info(f"Successfully changed LLM provider from {old_provider} to {self.provider}")
            return {
                'success': True,
                'old_provider': old_provider,
                'old_model': old_model,
                'new_provider': self.provider,
                'new_model': self.model
            }
            
        except Exception as e:
            # Rollback on error
            self.provider = old_provider
            try:
                self.setup_client()
            except:
                pass
            
            logger.error(f"Error changing provider to {new_provider}: {e}")
            return {
                'success': False,
                'error': f"Failed to change provider: {str(e)}"
            }
    
    def get_available_providers(self) -> Dict[str, Any]:
        """Get list of available providers with their configuration status."""
        providers = {
            'openai': {
                'name': 'OpenAI',
                'available': bool(os.environ.get('OPENAI_API_KEY')),
                'default_model': 'gpt-4',
                'current_model': os.environ.get('OPENAI_MODEL', 'gpt-4')
            },
            'together': {
                'name': 'Together AI',
                'available': bool(os.environ.get('TOGETHER_API_KEY')),
                'default_model': 'meta-llama/Llama-3.3-70B-Instruct-Turbo',
                'current_model': os.environ.get('TOGETHER_MODEL', 'meta-llama/Llama-3.3-70B-Instruct-Turbo')
            },
            'openrouter': {
                'name': 'OpenRouter',
                'available': bool(os.environ.get('OPENROUTER_API_KEY')),
                'default_model': 'openai/gpt-4o',
                'current_model': os.environ.get('OPENROUTER_MODEL', 'openai/gpt-4o')
            }
        }
        
        return {
            'current_provider': self.provider,
            'providers': providers,
            'available_count': sum(1 for p in providers.values() if p['available'])
        }
    
    def has_file_changes(self, response: str) -> bool:
        """Check if the AI response contains file creation/modification instructions."""
        import re
        
        # Pattern to match **File: filename.ext** followed by code block
        pattern = r'\*\*File:\s*([^\*]+)\*\*\s*```[a-zA-Z]*\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        
        return len(matches) > 0
    
    def extract_and_create_files(self, response: str, repo_path: str) -> Dict[str, Any]:
        """Extract file contents from AI response and create files."""
        import re
        
        try:
            files_created = []
            
            # Pattern to match **File: filename.ext** followed by code block
            pattern = r'\*\*File:\s*([^\*]+)\*\*\s*```[a-zA-Z]*\n(.*?)```'
            matches = re.findall(pattern, response, re.DOTALL)
            
            for filename, content in matches:
                filename = filename.strip()
                content = content.strip()
                
                # Create full file path
                file_path = os.path.join(repo_path, filename)
                
                # Create directories if they don't exist (only if filename contains directories)
                dir_path = os.path.dirname(file_path)
                if dir_path and dir_path != repo_path:
                    os.makedirs(dir_path, exist_ok=True)
                
                # Write file content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                files_created.append(filename)
                logger.info(f"Created file: {filename}")
            
            return {
                'success': True,
                'files_created': files_created,
                'count': len(files_created)
            }
            
        except Exception as e:
            logger.error(f"Error creating files from AI response: {e}")
            return {
                'success': False,
                'error': str(e),
                'files_created': []
            }