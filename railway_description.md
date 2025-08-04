# Deploy and Host TeleCode on Railway

TeleCode is a powerful Telegram bot that transforms your mobile phone into a complete GitHub development environment. Connect to existing repositories, analyze code, edit files, commit changes, and manage your projects—all through simple Telegram commands. Use `/ask` for read-only code analysis and `/code` for making changes. Perfect for developers who want to code anywhere, anytime.

## About Hosting TeleCode

Hosting TeleCode involves deploying a Python-based Telegram bot that integrates with GitHub APIs and multiple LLM providers. The bot handles user authentication, repository management, AI-powered code generation, and automated Git operations. Railway's platform-as-a-service model is ideal for TeleCode as it provides persistent storage for user data, automatic SSL certificates for webhook endpoints, and seamless environment variable management. The deployment includes setting up webhook endpoints for Telegram, configuring GitHub access tokens, and establishing connections to AI providers like OpenRouter (recommended), Together AI, or OpenAI.

## Common Use Cases

- **Mobile Development Workflows** - Fix bugs, add features, and deploy updates using only your smartphone while commuting, traveling, or away from your computer
- **Existing Repository Management** - Connect to any GitHub repository, manage branches, edit files, and commit changes through simple Telegram commands
- **Multilingual Development Teams** - Support international teams with built-in English and Portuguese language support for all bot interactions
- **AI-Assisted Coding** - Generate code, debug issues, and implement features using integrated LLM providers (OpenRouter, Together AI, OpenAI) with repository context awareness
- **Code Analysis and Learning** - Use `/ask` command for read-only code analysis, understanding complex systems, and learning from existing codebases without making changes
- **Emergency Hotfixes** - Deploy critical fixes instantly from anywhere using just your phone when urgent production issues arise  
- **Mobile Code Editing** - Edit existing codebases, add new features, and maintain projects through Telegram's intuitive interface

## Dependencies for TeleCode Hosting

- **Telegram Bot Token** - Create a bot via [@BotFather](https://t.me/botfather) on Telegram
- **GitHub Personal Access Token** - Generate with repository permissions for Git operations
- **LLM Provider API Key** - OpenRouter API key (recommended for 200+ models), Together AI, or OpenAI for AI-powered coding assistance
- **Python 3.11+** - Runtime environment (automatically provided by Railway)

### Deployment Dependencies

- [Telegram BotFather](https://t.me/botfather) - Create and configure your Telegram bot
- [GitHub Personal Access Tokens](https://github.com/settings/tokens) - Generate tokens with repository access
- [OpenRouter Platform](https://openrouter.ai/) - Recommended LLM provider with 200+ models from OpenAI, Anthropic, Google, Meta, and more
- [Together AI Platform](https://api.together.xyz/) - Cost-effective LLM provider with open-source models
- [OpenAI API Platform](https://platform.openai.com/api-keys) - Direct access to GPT models
- [Railway Documentation](https://docs.railway.app/) - Platform-specific deployment guides

### Implementation Details

**Essential Environment Variables:**

**Telegram Configuration:**
- `BOT_TOKEN` - Your Telegram bot token from @BotFather

**GitHub Integration:**
- `GITHUB_TOKEN` - Personal access token with repository permissions
- `GIT_STRATEGY` - Set to "direct" for main branch commits or "branch" for feature branches

**LLM Provider (choose one):**
- `LLM_PROVIDER` - Set to "openrouter" (recommended), "together", or "openai"
- `OPENROUTER_API_KEY` - OpenRouter API key for access to 200+ models
- `OPENROUTER_MODEL` - Model to use (default: "openai/gpt-4o")
- `OPENROUTER_SITE_URL` - Optional: Your site URL for leaderboards
- `OPENROUTER_SITE_NAME` - Optional: Your site name for leaderboards
- `TOGETHER_API_KEY` - Together AI API key for open-source models
- `OPENAI_API_KEY` - OpenAI API key for direct GPT model access

**Security & Rate Limiting:**
- `AUTHORIZED_TELEGRAM_USERS` - Comma-separated list of authorized Telegram user IDs
- `MAX_REQUESTS_PER_HOUR` - Hourly rate limit (default: 10)
- `MAX_REQUESTS_PER_DAY` - Daily rate limit (default: 50)

**Railway Auto-Configuration (set automatically):**
- `PORT` - Server port (Railway sets this to 8080)
- `RAILWAY_STATIC_URL` - Your app's Railway URL

**Key Features Configuration:**
- **Multi-language Support**: Automatic language detection with persistent user preferences (English and Portuguese)
- **Chat Context Management**: Configurable conversation history (`CHAT_CONTEXT_MAX_MESSAGES=25`) with token counting and cost estimation
- **Intelligent Repository Context**: Advanced codebase analysis with smart file selection (`REPO_CONTEXT_MAX_FILES=20`, `REPO_CONTEXT_MAX_TOKENS=15000`)
- **Code Analysis Commands**: `/code` for modifications and commits, `/ask` for read-only analysis and questions
- **Approval System**: Review and approve code changes before committing to repository
- **Debug Mode**: Enable detailed logging with `DEBUG_LLM=true`
- **Streaming Responses**: Real-time AI responses with `LLM_STREAMING=true`

## Why Deploy TeleCode on Railway?

<!-- Recommended: Keep this section as shown below -->
Railway is a singular platform to deploy your infrastructure stack. Railway will host your infrastructure so you don't have to deal with configuration, while allowing you to vertically and horizontally scale it.

By deploying TeleCode on Railway, you are one step closer to supporting a complete full-stack application with minimal burden. Host your servers, databases, AI agents, and more on Railway.
<!-- End recommended section -->

**Additional Railway Benefits for TeleCode:**

- **Automatic HTTPS**: Secure webhook endpoints for Telegram integration without SSL certificate management
- **Persistent Storage**: User preferences and chat context preserved across deployments  
- **Environment Variables**: Secure storage for API keys and sensitive configuration
- **Automatic Deployments**: Git-based deployments with zero-downtime updates
- **Global Edge Network**: Low-latency bot responses worldwide for better user experience
- **Built-in Monitoring**: Track bot performance, API usage, and error rates through Railway's dashboard