# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TeleCode is a Telegram bot that integrates multiple LLM providers (Together AI, OpenAI) to perform coding tasks and automatically commit changes to GitHub repositories. The bot receives coding prompts via Telegram, processes them using AI, creates/modifies files, and commits the results to GitHub with proper branching. The bot supports multi-language interactions (English and Portuguese) with persistent user preferences.

## Architecture

The codebase follows a modular architecture with clear separation of concerns:

- **`bot.py`**: Main application entry point with Telegram webhook/polling handlers, command routing, and localization
- **`llm_provider.py`**: Abstraction layer supporting multiple LLM providers (OpenAI, Together AI) with unified interface  
- **`github_manager.py`**: GitHub API integration for repository operations, cloning, branching, and commits
- **`security.py`**: User authentication, rate limiting, and repository access control
- **`chat_context.py`**: Persistent chat context management for improved AI responses
- **`localization.py`**: Multi-language support system (English/Portuguese) with user preference storage
- **Environment-driven configuration**: All providers and security settings configured via environment variables

## Development Commands

### Running the Bot
```bash
# Local development (uses polling)
python bot.py

# Production deployment (uses webhooks when RAILWAY_STATIC_URL is set)
python bot.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt

# For Anthropic Claude Code SDK support (optional)
npm install -g @anthropic-ai/claude-code
```

### Environment Setup
```bash
cp .env.example .env
# Edit .env with required tokens and configuration
```

## LLM Provider Architecture

The `LLMProvider` class in `llm_provider.py` abstracts multiple LLM providers:

- **Together AI**: Uses AsyncOpenAI client with `https://api.together.xyz/v1` base URL, default model: `meta-llama/Llama-3.3-70B-Instruct-Turbo`
- **OpenAI**: Direct AsyncOpenAI client integration, default model: `gpt-4`
- **OpenRouter**: Uses AsyncOpenAI client with `https://openrouter.ai/api/v1` base URL, default model: `openai/gpt-4o`, supports optional site headers for leaderboards

Provider selection is controlled by `LLM_PROVIDER` environment variable (options: `together`, `openai`, `openrouter`). Each provider has specific system prompts optimized for code generation and repository context analysis.

### File Creation Protocol

The bot uses a specific format for AI responses to create actual files:

```
**File: filename.ext**
```language
[complete file content]
```
```

The `extract_and_create_files()` method parses this format and creates files in the repository.

## GitHub Integration Flow

1. **Repository Setup**: User sets active repo via `/repo` command → `GitHubManager.set_active_repo()`
2. **Code Request**: User sends `/code` prompt → clones/updates repo to temp directory  
3. **Branch Creation**: Creates feature branch with timestamp: `telecode-{timestamp}` (unless `GIT_STRATEGY=direct`)
4. **AI Processing**: LLM generates response with repository context and chat history
5. **File Operations**: Extracts and creates files from AI response using file protocol
6. **Commit & Push**: Commits all changes with sanitized commit message and bot attribution

## Security Architecture

`SecurityManager` implements multi-layer security:

- **User Authorization**: Whitelist via `AUTHORIZED_TELEGRAM_USERS`
- **Rate Limiting**: Configurable hourly/daily limits per user
- **Repository Access Control**: Global and per-user repository restrictions
- **Input Sanitization**: Commit message and file path validation
- **Session Management**: Token-based session tracking

## Message Handling

Telegram message parsing uses defensive programming with `safe_send_message()` function:
1. Attempts Markdown formatting first
2. Falls back to plain text if Markdown parsing fails
3. Uses `safe_markdown_response()` to escape problematic characters
4. Prevents bot crashes from malformed responses

## Multi-Language Support

The bot supports English and Portuguese (Brazil) with persistent user preferences:

- **Language Selection**: Users can switch languages via `/lang` command
- **Persistent Storage**: Language preferences saved in `data/user_languages.json`
- **Localization System**: All user-facing messages translated via `LocalizationManager`
- **Interactive Selection**: Keyboard buttons for easy language switching
- **Real-time Updates**: Language changes apply immediately to all commands

## Chat Context Management

The bot maintains conversation history for improved responses:

- **Persistent Context**: Chat history stored per user with configurable message limits
- **Repository Awareness**: Context includes repository information for each message
- **Token Management**: Built-in token counting and cost estimation
- **Context Commands**: `/context`, `/tokens`, `/clear` for context management
- **Environment Configuration**: `CHAT_CONTEXT_MAX_MESSAGES` controls history size

## Configuration Management

Environment variables are validated at startup based on selected LLM provider:
- Base requirements: `BOT_TOKEN`, `GITHUB_TOKEN`
- Provider-specific: `{PROVIDER}_API_KEY`, `{PROVIDER}_MODEL`
- Security and rate limiting: `AUTHORIZED_TELEGRAM_USERS`, `MAX_REQUESTS_PER_*`
- Chat context: `CHAT_CONTEXT_MAX_MESSAGES`
- Git strategy: `GIT_STRATEGY` (direct/branch)

### OpenRouter Configuration

For OpenRouter provider, set:
- `LLM_PROVIDER=openrouter`
- `OPENROUTER_API_KEY` - Your OpenRouter API key
- `OPENROUTER_MODEL` - Model name (default: `openai/gpt-4o`)
- `OPENROUTER_SITE_URL` - Optional: Your site URL for leaderboards
- `OPENROUTER_SITE_NAME` - Optional: Your site name for leaderboards

## Deployment Architecture

- **Railway Production**: Uses webhooks with `RAILWAY_STATIC_URL`
- **Local Development**: Uses polling mode
- **Process Definition**: `Procfile` specifies `web: python bot.py`
- **Runtime**: Python 3.11 specified in `runtime.txt`

## Error Handling Patterns

- **Async Operations**: All LLM and GitHub operations are async with proper exception handling
- **Graceful Degradation**: Message formatting failures fall back to plain text
- **User Feedback**: All errors provide user-friendly messages while logging technical details
- **Resource Cleanup**: Temporary directories cleaned up via `GitHubManager.cleanup()`

## Advanced Repository Context System

The bot uses an intelligent context system to provide comprehensive codebase awareness:

### Core Features
- **Intelligent File Selection**: Analyzes prompt keywords to select most relevant files
- **Actual Code Content**: Includes real source code content, not just file names
- **Multi-Language Support**: Understands 25+ programming languages
- **File Relationship Mapping**: Tracks imports and dependencies between files
- **Token-Aware Management**: Optimizes context within LLM token limits

### Context Collection Process
1. **Repository Scanning**: Discovers all relevant files in the codebase
2. **Prompt Analysis**: Extracts keywords and technical terms from user requests
3. **Relevance Scoring**: Ranks files by importance and relevance to the prompt
4. **Smart Selection**: Chooses optimal file set within token/count limits
5. **Content Reading**: Includes actual source code content for selected files
6. **Relationship Analysis**: Maps file dependencies and imports
7. **Caching**: Caches results for improved performance

### Configuration Options
- `REPO_CONTEXT_MAX_TOKENS`: Maximum tokens for repository context (default: 15000)
- `REPO_CONTEXT_MAX_FILES`: Maximum number of files to include (default: 20)  
- `REPO_CONTEXT_MAX_FILE_SIZE`: Maximum characters per file (default: 10000)
- `REPO_CONTEXT_DEPTH`: Maximum directory depth to scan (default: 3)

### Supported Languages
Python, JavaScript, TypeScript, Java, C/C++, C#, Go, Rust, PHP, Ruby, Swift, Kotlin, Scala, R, SQL, HTML, CSS, YAML, JSON, Markdown, and more.

## Available Commands

### Core Commands
- `/start` - Show welcome message and basic commands
- `/help` - Show detailed help documentation
- `/lang` - Change language between English and Portuguese

### Repository Management
- `/repo <github_url>` - Set active repository for coding tasks
- `/repos` - List all connected repositories and their status
- `/status` - Show current repository, usage stats, and chat context

### Code Operations
- `/code <prompt>` - Execute coding tasks (analysis, file changes, etc.)

### Chat Context Management
- `/context` - View recent conversation history
- `/tokens` - Analyze token usage and costs for chat context
- `/clear` - Clear conversation history (start fresh)

## Bot Workflow Example

1. Set repository: `/repo https://github.com/username/my-project`
2. Ask questions: `/code explain the authentication system`  
3. Make changes: `/code add input validation to the login form`
4. Check context: `/tokens` to see token usage
5. Clear history: `/clear` when starting new topic