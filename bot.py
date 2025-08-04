import os
import logging
import asyncio
import time
from typing import Dict, Any
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from aiohttp import web
from aiohttp.web_request import Request
from github_manager import GitHubManager
from security import SecurityManager
from llm_provider import LLMProvider
from chat_context import ChatContextManager
from localization import LocalizationManager
from approval_manager import ApprovalManager

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

logger = logging.getLogger(__name__)

# Global managers
github_manager = None
security_manager = None
llm_provider = None
chat_context_manager = None
localization_manager = None
approval_manager = None

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)

def safe_markdown_response(response: str) -> str:
    """Clean response text to avoid Markdown parsing issues."""
    # Remove problematic characters that break Markdown parsing
    cleaned = response.replace('\\', '\\\\')
    cleaned = cleaned.replace('`', '\\`')
    cleaned = cleaned.replace('*', '\\*')
    cleaned = cleaned.replace('_', '\\_')
    cleaned = cleaned.replace('[', '\\[')
    cleaned = cleaned.replace(']', '\\]')
    cleaned = cleaned.replace('(', '\\(')
    cleaned = cleaned.replace(')', '\\)')
    return cleaned

async def safe_send_message(update, text: str, parse_mode: str = 'Markdown'):
    """Safely send a message, falling back to plain text if Markdown fails."""
    # Telegram message limit is 4096 characters
    MAX_MESSAGE_LENGTH = 4096
    
    if len(text) > MAX_MESSAGE_LENGTH:
        # Split long messages
        chunks = [text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]
        for i, chunk in enumerate(chunks):
            if i == 0:
                chunk_text = chunk
            else:
                chunk_text = f"...continued from previous message...\n\n{chunk}"
            
            try:
                await update.message.reply_text(chunk_text, parse_mode=parse_mode)
            except Exception as e:
                logger.warning(f"Markdown parsing failed for chunk {i+1}: {e}")
                # Strip markdown formatting and send as plain text
                plain_text = chunk_text.replace('**', '').replace('*', '').replace('`', '').replace('_', '')
                try:
                    await update.message.reply_text(plain_text)
                except Exception as e2:
                    logger.error(f"Plain text also failed for chunk {i+1}: {e2}")
    else:
        try:
            await update.message.reply_text(text, parse_mode=parse_mode)
        except Exception as e:
            logger.warning(f"Markdown parsing failed: {e}")
            # Strip markdown formatting and send as plain text
            plain_text = text.replace('**', '').replace('*', '').replace('`', '').replace('_', '')
            try:
                await update.message.reply_text(plain_text)
            except Exception as e2:
                logger.error(f"Plain text also failed: {e2}")
                await update.message.reply_text("✅ Task completed! Check your repository for the changes.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command handler."""
    user_id = update.effective_user.id
    
    if not security_manager.is_user_authorized(user_id):
        await update.message.reply_text(localization_manager.get_text(user_id, "unauthorized"))
        return
    
    # Build localized welcome message
    title = localization_manager.get_text(user_id, "start_title")
    description = localization_manager.get_text(user_id, "start_description")
    commands_header = localization_manager.get_text(user_id, "start_commands")
    example_header = localization_manager.get_text(user_id, "start_example")
    footer = localization_manager.get_text(user_id, "start_footer")
    
    welcome_message = f"""{title}

{description}

{commands_header}
• {localization_manager.get_text(user_id, "cmd_start")}
• {localization_manager.get_text(user_id, "cmd_repo")}
• {localization_manager.get_text(user_id, "cmd_repos")}
• {localization_manager.get_text(user_id, "cmd_repo_disconnect")}
• {localization_manager.get_text(user_id, "cmd_code")}
• {localization_manager.get_text(user_id, "cmd_status")}
• {localization_manager.get_text(user_id, "cmd_context")}
• {localization_manager.get_text(user_id, "cmd_tokens")}
• {localization_manager.get_text(user_id, "cmd_clear")}
• {localization_manager.get_text(user_id, "cmd_help")}
• {localization_manager.get_text(user_id, "cmd_lang")}
• {localization_manager.get_text(user_id, "cmd_provider")}

{example_header}
/repo `https://github.com/user/repo`
/code `explain how the authentication works`
/code `fix the login validation bug`

{footer}"""
    
    await safe_send_message(update, welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Help command handler."""
    user_id = update.effective_user.id
    
    if not security_manager.is_user_authorized(user_id):
        await update.message.reply_text(localization_manager.get_text(user_id, "unauthorized"))
        return
    
    # Build localized help message
    title = localization_manager.get_text(user_id, "help_title")
    repo_commands = localization_manager.get_text(user_id, "help_repo_commands")
    coding_commands = localization_manager.get_text(user_id, "help_coding_commands")
    context_commands = localization_manager.get_text(user_id, "help_context_commands")
    info_commands = localization_manager.get_text(user_id, "help_info_commands")
    usage_examples = localization_manager.get_text(user_id, "help_usage_examples")
    security = localization_manager.get_text(user_id, "help_security")
    environment = localization_manager.get_text(user_id, "help_environment")
    token_management = localization_manager.get_text(user_id, "help_token_management")
    
    help_text = f"""{title}

{repo_commands}
• /repo `<github_url>` - {localization_manager.get_text(user_id, "help_repo_desc")}
• /repos - {localization_manager.get_text(user_id, "help_repos_desc")}
• /repo_disconnect [clean] - {localization_manager.get_text(user_id, "help_repo_disconnect_desc")}
• /status - {localization_manager.get_text(user_id, "help_status_desc")}

{coding_commands}
• /code `<prompt>` - {localization_manager.get_text(user_id, "help_code_desc")}
  - {localization_manager.get_text(user_id, "help_code_readonly")}
  - {localization_manager.get_text(user_id, "help_code_changes")}

{context_commands}
• /context - {localization_manager.get_text(user_id, "help_context_desc")}
• /tokens - {localization_manager.get_text(user_id, "help_tokens_desc")}
• /clear - {localization_manager.get_text(user_id, "help_clear_desc")}

{info_commands}
• /start - {localization_manager.get_text(user_id, "help_start_desc")}
• /help - {localization_manager.get_text(user_id, "help_help_desc")}
• /lang - {localization_manager.get_text(user_id, "help_lang_desc")}
• /provider - {localization_manager.get_text(user_id, "help_provider_desc")}

{usage_examples}
• /repo `https://github.com/username/my-project`
• /code `explain how the user authentication works`
• /code `add input validation to the login form`
• /code `refactor the database connection module`
• /tokens - See how many tokens your context is using

{security}
{localization_manager.get_text(user_id, "help_security_text")}

{environment}
{localization_manager.get_text(user_id, "help_env_text")}

{token_management}
{localization_manager.get_text(user_id, "help_token_text")}"""
    
    await safe_send_message(update, help_text)

async def repo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Repository setup command handler."""
    user_id = update.effective_user.id
    
    if not security_manager.is_user_authorized(user_id):
        await update.message.reply_text(localization_manager.get_text(user_id, "unauthorized"))
        return
    
    rate_check = security_manager.check_rate_limit(user_id)
    if not rate_check['allowed']:
        if rate_check['reason'] == 'hourly_limit_exceeded':
            await update.message.reply_text(
                localization_manager.get_text(user_id, "hourly_limit", minutes=rate_check['reset_in_minutes'])
            )
        else:
            await update.message.reply_text(
                localization_manager.get_text(user_id, "daily_limit", hours=rate_check['reset_in_hours'])
            )
        return
    
    if not context.args:
        message = localization_manager.get_text(user_id, "repo_usage")
        await safe_send_message(update, message)
        return
    
    repo_url = context.args[0]
    
    # Check if it's a valid GitHub URL format first
    if not (repo_url.startswith('https://github.com/') or repo_url.startswith('git@github.com:')):
        message = localization_manager.get_text(user_id, "repo_invalid_url", input=repo_url)
        await safe_send_message(update, message)
        return
    
    # Validate repository access
    access_check = security_manager.validate_github_repo_access(user_id, repo_url)
    if not access_check['allowed']:
        await update.message.reply_text(
            localization_manager.get_text(user_id, "repo_access_denied", repo_url=repo_url, reason=access_check['reason'])
        )
        return
    
    await update.message.reply_text(localization_manager.get_text(user_id, "repo_setting_up"))
    
    try:
        result = github_manager.set_active_repo(user_id, repo_url)
        
        if result['success']:
            message = f"{localization_manager.get_text(user_id, 'repo_success')}\n\n"
            message += f"**Repository:** {result['repo_name']}\n"
            if result.get('description'):
                message += f"**Description:** {result['description']}\n"
            if result.get('language'):
                message += f"**Language:** {result['language']}\n"
            message += f"\nYou can now use `/code <prompt>` to execute coding tasks!"
            
            await safe_send_message(update, message)
        else:
            await update.message.reply_text(localization_manager.get_text(user_id, "repo_failed", error=result['error']))
            
    except Exception as e:
        logger.error(f"Error in repo command for user {user_id}: {e}")
        await update.message.reply_text(localization_manager.get_text(user_id, "error_occurred"))

async def repos_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all connected repositories and their status."""
    user_id = update.effective_user.id
    
    if not security_manager.is_user_authorized(user_id):
        await update.message.reply_text(localization_manager.get_text(user_id, "unauthorized"))
        return
    
    try:
        user_repos = github_manager.get_user_repositories(user_id)
        
        if not user_repos['success']:
            await update.message.reply_text(f"❌ Error retrieving repositories: {user_repos.get('error', 'Unknown error')}")
            return
            
        if not user_repos['repositories']:
            message = "📂 **No repositories found.**\n\n"
            message += "Use `/repo <github_url>` to connect your first repository!\n"
            message += "Example: `/repo https://github.com/username/my-project`"
            await safe_send_message(update, message)
            return
        
        message = f"📂 **Your Connected Repositories ({user_repos['total_repos']})**\n\n"
        
        for repo in user_repos['repositories']:
            status_emoji = "✅" if repo['is_active'] else "📁"
            git_emoji = "🔄" if repo['has_git'] else "❌"
            
            message += f"{status_emoji} **{repo['repo_name']}**\n"
            
            if repo['is_active']:
                message += f"   🔹 **ACTIVE REPOSITORY**\n"
            
            message += f"   📍 Local: {'✅ Available' if repo['exists_locally'] else '❌ Missing'}\n"
            message += f"   🔄 Git: {'✅ Repository' if repo['has_git'] else '❌ No Git'}\n"
            
            if repo['size_mb'] is not None:
                message += f"   💾 Size: {repo['size_mb']} MB\n"
            
            if repo['last_modified']:
                last_mod = repo['last_modified'][:19].replace('T', ' ')
                message += f"   🕒 Modified: {last_mod}\n"
            
            message += f"   📁 Path: `{repo['local_path']}`\n\n"
        
        active_repo = user_repos.get('active_repo')
        if active_repo:
            message += f"🎯 **Current Active:** {active_repo['name']}\n"
        else:
            message += "ℹ️ No active repository set. Use `/repo <url>` to activate one.\n"
        
        message += f"\n💡 **Tips:**\n"
        message += f"• Use `/repo <url>` to switch active repository\n"
        message += f"• Use `/status` for detailed active repository info\n"
        message += f"• Local files are automatically updated when needed"
        
        await safe_send_message(update, message)
        
    except Exception as e:
        logger.error(f"Error in repos command for user {user_id}: {e}")
        await update.message.reply_text(localization_manager.get_text(user_id, "error_occurred"))

async def repo_disconnect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disconnect from active repository command handler."""
    user_id = update.effective_user.id
    
    if not security_manager.is_user_authorized(user_id):
        await update.message.reply_text(localization_manager.get_text(user_id, "unauthorized"))
        return
    
    try:
        # Check if user wants to cleanup local files
        cleanup_local = False
        if context.args and context.args[0].lower() in ['clean', 'cleanup', 'delete']:
            cleanup_local = True
        
        result = github_manager.disconnect_repo(user_id, cleanup_local)
        
        if result['success']:
            message = localization_manager.get_text(user_id, "repo_disconnect_success", repo_name=result['repo_name'])
            if result.get('local_cleanup'):
                message += f"\n{localization_manager.get_text(user_id, 'repo_disconnect_cleanup')}"
            await safe_send_message(update, message)
        else:
            await update.message.reply_text(localization_manager.get_text(user_id, "repo_disconnect_failed", error=result['error']))
            
    except Exception as e:
        logger.error(f"Error in repo_disconnect command for user {user_id}: {e}")
        await update.message.reply_text(localization_manager.get_text(user_id, "error_occurred"))

async def code_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Code execution command handler."""
    user_id = update.effective_user.id
    
    if not security_manager.is_user_authorized(user_id):
        await update.message.reply_text(localization_manager.get_text(user_id, "unauthorized"))
        return
    
    rate_check = security_manager.check_rate_limit(user_id)
    if not rate_check['allowed']:
        if rate_check['reason'] == 'hourly_limit_exceeded':
            await update.message.reply_text(
                f"⏰ Hourly rate limit exceeded. Try again in {rate_check['reset_in_minutes']} minutes."
            )
        else:
            await update.message.reply_text(
                f"⏰ Daily rate limit exceeded. Try again in {rate_check['reset_in_hours']} hours."
            )
        return
    
    if not context.args:
        message = localization_manager.get_text(user_id, "code_usage")
        await safe_send_message(update, message)
        return
    
    # Check if repository is set
    repo_info = github_manager.get_active_repo(user_id)
    if not repo_info:
        await update.message.reply_text(localization_manager.get_text(user_id, "no_active_repo"))
        return
    
    prompt = ' '.join(context.args)
    
    await update.message.reply_text(localization_manager.get_text(user_id, "processing"), parse_mode='Markdown')
    
    try:
        # Always ensure repository is available locally for context
        clone_result = await github_manager.clone_or_update_repo(user_id)
        if not clone_result['success']:
            await update.message.reply_text(f"❌ Failed to access repository: {clone_result['error']}")
            return
        
        # Get current repository context for chat history
        repo_info = github_manager.get_active_repo(user_id)
        current_repo = repo_info['name'] if repo_info else None
        
        # Add user message to chat context
        chat_context_manager.add_user_message(user_id, prompt, current_repo)
        
        # Get chat context for LLM
        chat_context = chat_context_manager.get_context_for_llm(user_id)
        
        # Execute LLM Provider with repository and chat context
        provider_info = llm_provider.get_provider_info()
        if chat_context:
            user_lang = localization_manager.get_user_language(user_id)
            if user_lang == 'pt-br':
                context_info = f" ({len(chat_context)} mensagens de contexto)"
            else:
                context_info = f" (with {len(chat_context)} messages context)"
        else:
            context_info = ""
            
        await update.message.reply_text(
            localization_manager.get_text(user_id, "code_analyzing", 
                                        provider=provider_info['provider'].title(), 
                                        model=provider_info['model'], 
                                        context=context_info), 
            parse_mode='Markdown'
        )
        
        try:
            final_response = await llm_provider.generate_code_response(
                prompt, 
                clone_result['local_path'],
                chat_context
            )
        except Exception as llm_error:
            logger.error(f"LLM generation failed for user {user_id}: {llm_error}")
            # Send specific error message to user
            await update.message.reply_text(localization_manager.get_text(user_id, "llm_error", error=str(llm_error)))
            return
        
        if not final_response:
            await update.message.reply_text(localization_manager.get_text(user_id, "no_llm_response"))
            return
        
        # Check if the response contains file changes
        has_changes = llm_provider.has_file_changes(final_response)
        
        if has_changes:
            # Extract and create files from AI response
            file_creation_result = llm_provider.extract_and_create_files(
                final_response, 
                clone_result['local_path']
            )
            
            if file_creation_result['success']:
                # Detect changes and create summary for approval
                changes_summary = approval_manager.detect_changes(
                    clone_result['local_path'], 
                    final_response
                )
                
                if changes_summary:
                    # Store pending approval
                    approval_id = approval_manager.store_pending_approval(user_id, changes_summary)
                    
                    # Format changes summary for user
                    summary_text = approval_manager.format_changes_summary(changes_summary)
                    
                    # Create approval keyboard
                    keyboard = [
                        ["✅ Approve & Commit", "❌ Reject Changes"],
                        ["📋 Show Details"]
                    ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
                    
                    approval_message = f"{summary_text}\n\n"
                    approval_message += "**⚠️ Please review and approve these changes before committing to the repository.**\n\n"
                    approval_message += f"⏰ This approval will expire in {approval_manager.approval_timeout // 60} minutes."
                    
                    # Add assistant response to chat context
                    chat_context_manager.add_assistant_message(user_id, final_response, current_repo)
                    
                    await update.message.reply_text(approval_message, reply_markup=reply_markup)
                else:
                    await update.message.reply_text("❌ No changes detected in the repository.")
            else:
                await update.message.reply_text(f"❌ Failed to create files: {file_creation_result.get('error', 'Unknown error')}")
        else:
            # This is a read-only/informational request - no commits needed
            response = f"💬 **Analysis completed (no code changes needed):**\n\n"
            
            # Clean the AI response to avoid markdown parsing issues
            clean_response = safe_markdown_response(final_response[:1500])
            response += f"{clean_response}{'...' if len(final_response) > 1500 else ''}"
            
            # Add assistant response to chat context
            chat_context_manager.add_assistant_message(user_id, final_response, current_repo)
            
            await safe_send_message(update, response)
            
    except Exception as e:
        logger.error(f"Error in code command for user {user_id}: {e}")
        await update.message.reply_text(localization_manager.get_text(user_id, "error_occurred"))

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Status command handler."""
    user_id = update.effective_user.id
    
    if not security_manager.is_user_authorized(user_id):
        await update.message.reply_text(localization_manager.get_text(user_id, "unauthorized"))
        return
    
    try:
        # Get repository status
        repo_status = github_manager.get_repo_status(user_id)
        
        # Get user statistics
        user_stats = security_manager.get_user_stats(user_id)
        
        status_message = "📊 **Current Status**\n\n"
        
        if repo_status['success']:
            status_message += f"**🗂 Active Repository:**\n"
            status_message += f"• Name: {repo_status['repo_name']}\n"
            status_message += f"• URL: {repo_status['repo_url']}\n"
            status_message += f"• Cloned: {'✅' if repo_status['cloned'] else '❌'}\n"
            
            if repo_status['cloned']:
                status_message += f"• Branch: {repo_status['current_branch']}\n"
                status_message += f"• Changes: {'⚠️ Yes' if repo_status['has_changes'] else '✅ Clean'}\n"
                status_message += f"• Last Commit: {repo_status['last_commit']}\n"
        else:
            status_message += "**🗂 Active Repository:** None\n"
            status_message += "Use `/repo <github_url>` to set one!\n"
        
        status_message += f"\n**📈 Usage Statistics:**\n"
        status_message += f"• Hourly: {user_stats['hourly_used']}/{user_stats['hourly_limit']} requests\n"
        status_message += f"• Daily: {user_stats['daily_used']}/{user_stats['daily_limit']} requests\n"
        
        # Add chat context info
        context_summary = chat_context_manager.get_context_summary(user_id)
        status_message += f"\n**💬 Chat Context:**\n"
        status_message += f"• Messages: {context_summary['message_count']}/{chat_context_manager.max_messages}\n"
        if context_summary['last_interaction']:
            status_message += f"• Last interaction: {context_summary['last_interaction'][:19]}\n"
        
        # Add LLM provider info
        provider_info = llm_provider.get_provider_info()
        status_message += f"\n**🤖 LLM Provider:**\n"
        status_message += f"• Provider: {provider_info['provider'].title()}\n"
        status_message += f"• Model: {provider_info['model']}\n"
        status_message += f"• Available: {'✅' if provider_info['available'] else '❌'}\n"
        
        await safe_send_message(update, status_message)
        
    except Exception as e:
        logger.error(f"Error in status command for user {user_id}: {e}")
        await update.message.reply_text(localization_manager.get_text(user_id, "error_occurred"))

async def context_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show chat context history."""
    user_id = update.effective_user.id
    
    if not security_manager.is_user_authorized(user_id):
        await update.message.reply_text(localization_manager.get_text(user_id, "unauthorized"))
        return
    
    try:
        context_summary = chat_context_manager.get_context_summary(user_id)
        chat_history = chat_context_manager.get_context_for_llm(user_id)
        
        if not chat_history:
            await update.message.reply_text(f"{localization_manager.get_text(user_id, 'context_no_context')}\n\n{localization_manager.get_text(user_id, 'context_start_conversation')}")
            return
        
        context_message = f"💬 **Chat Context ({context_summary['message_count']}/{chat_context_manager.max_messages} messages)**\n\n"
        
        for i, msg in enumerate(chat_history[-6:], 1):  # Show last 6 messages
            role_emoji = "👤" if msg['role'] == 'user' else "🤖"
            content_preview = msg['content'][:150] + ('...' if len(msg['content']) > 150 else '')
            context_message += f"{role_emoji} **{msg['role'].title()}:** {content_preview}\n\n"
        
        if len(chat_history) > 6:
            context_message += f"... and {len(chat_history) - 6} earlier messages\n\n"
        
        context_message += "Use `/clear` to reset chat context."
        
        await safe_send_message(update, context_message)
        
    except Exception as e:
        logger.error(f"Error in context command for user {user_id}: {e}")
        await update.message.reply_text(localization_manager.get_text(user_id, "error_occurred"))

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear chat context history."""
    user_id = update.effective_user.id
    
    if not security_manager.is_user_authorized(user_id):
        await update.message.reply_text(localization_manager.get_text(user_id, "unauthorized"))
        return
    
    try:
        success = chat_context_manager.clear_context(user_id)
        
        if success:
            await update.message.reply_text(f"{localization_manager.get_text(user_id, 'clear_success')}\n\n{localization_manager.get_text(user_id, 'clear_description')}")
        else:
            await update.message.reply_text(localization_manager.get_text(user_id, "clear_failed"))
            
    except Exception as e:
        logger.error(f"Error in clear command for user {user_id}: {e}")
        await update.message.reply_text(localization_manager.get_text(user_id, "error_occurred"))

async def tokens_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show token usage for chat context."""
    user_id = update.effective_user.id
    
    if not security_manager.is_user_authorized(user_id):
        await update.message.reply_text(localization_manager.get_text(user_id, "unauthorized"))
        return
    
    try:
        # Get current LLM provider model for accurate token counting
        provider_info = llm_provider.get_provider_info()
        model_name = provider_info.get('model', 'gpt-4')
        
        token_stats = chat_context_manager.get_context_token_stats(user_id, model_name)
        
        if token_stats['total_messages'] == 0:
            await update.message.reply_text(f"{localization_manager.get_text(user_id, 'tokens_no_context')}\n\n{localization_manager.get_text(user_id, 'tokens_start_conversation')}")
            return
        
        tokens_message = f"📊 **Token Usage Analysis**\n\n"
        tokens_message += f"**Model:** {token_stats['model_used']}\n"
        tokens_message += f"**Total Messages:** {token_stats['total_messages']}/{chat_context_manager.max_messages}\n"
        tokens_message += f"**Total Tokens:** {token_stats['total_tokens']:,}\n"
        tokens_message += f"**Context Tokens:** {token_stats['context_tokens']:,}\n"
        tokens_message += f"**Avg per Message:** {token_stats['avg_tokens_per_message']:,}\n\n"
        
        tokens_message += "**Per Message Breakdown:**\n"
        for i, msg_info in enumerate(token_stats['tokens_per_message'][-5:], 1):  # Show last 5
            role_emoji = "👤" if msg_info['role'] == 'user' else "🤖"
            tokens_message += f"{role_emoji} {msg_info['tokens']:,} tokens: {msg_info['content_preview']}\n"
        
        if len(token_stats['tokens_per_message']) > 5:
            tokens_message += f"... and {len(token_stats['tokens_per_message']) - 5} earlier messages\n"
        
        # Add cost estimation for common providers
        if 'gpt-4' in model_name.lower():
            input_cost = token_stats['context_tokens'] * 0.00003  # $0.03 per 1K tokens
            tokens_message += f"\n💰 **Estimated Cost:** ${input_cost:.4f} (input only)\n"
        elif 'gpt-3.5' in model_name.lower():
            input_cost = token_stats['context_tokens'] * 0.0000015  # $0.0015 per 1K tokens  
            tokens_message += f"\n💰 **Estimated Cost:** ${input_cost:.6f} (input only)\n"
        
        tokens_message += f"\n**Environment:** Max messages = {chat_context_manager.max_messages}"
        
        await safe_send_message(update, tokens_message)
        
    except Exception as e:
        logger.error(f"Error in tokens command for user {user_id}: {e}")
        await update.message.reply_text(localization_manager.get_text(user_id, "error_occurred"))

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Language selection command handler."""
    user_id = update.effective_user.id
    
    if not security_manager.is_user_authorized(user_id):
        await update.message.reply_text(localization_manager.get_text(user_id, "unauthorized"))
        return
    
    try:
        if context.args:
            # User specified a language
            lang_arg = context.args[0].lower()
            
            # Map common language inputs to our language codes
            language_map = {
                'en': 'en',
                'english': 'en',
                'pt': 'pt-br',
                'pt-br': 'pt-br',
                'portuguese': 'pt-br',
                'portugues': 'pt-br',
                'brasil': 'pt-br',
                'brazil': 'pt-br'
            }
            
            language = language_map.get(lang_arg)
            
            if language and localization_manager.set_user_language(user_id, language):
                success_msg = localization_manager.get_text(user_id, "lang_changed")
                await update.message.reply_text(success_msg)
            else:
                # Show language selection
                select_msg = localization_manager.get_text(user_id, "lang_select")
                keyboard = [
                    [localization_manager.get_text(user_id, "lang_english")],
                    [localization_manager.get_text(user_id, "lang_portuguese")]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
                await update.message.reply_text(select_msg, reply_markup=reply_markup)
        else:
            # Show current language and selection options
            current_lang = localization_manager.get_text(user_id, "lang_current")
            select_msg = localization_manager.get_text(user_id, "lang_select")
            
            message = f"{current_lang}\n\n{select_msg}"
            
            keyboard = [
                [localization_manager.get_text(user_id, "lang_english")],
                [localization_manager.get_text(user_id, "lang_portuguese")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(message, reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Error in lang command for user {user_id}: {e}")
        await update.message.reply_text(localization_manager.get_text(user_id, "error_occurred"))

async def provider_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provider selection command handler with interactive selection."""
    user_id = update.effective_user.id
    
    if not security_manager.is_user_authorized(user_id):
        await update.message.reply_text(localization_manager.get_text(user_id, "unauthorized"))
        return
    
    try:
        # Show current provider/model and available options with interactive buttons
        provider_info = llm_provider.get_available_providers()
        
        message = f"🤖 **Current LLM Configuration:**\n\n"
        message += f"**Active Provider:** {provider_info['current_provider'].title()}\n"
        message += f"**Active Model:** {llm_provider.model}\n\n"
        
        message += f"**Available Providers ({provider_info['available_count']}/3):**\n\n"
        
        # Build keyboard with available providers
        keyboard = []
        
        for provider_key, provider_data in provider_info['providers'].items():
            if provider_data['available']:
                status_emoji = "🔹" if provider_key == provider_info['current_provider'] else "✅"
                button_text = f"{status_emoji} {provider_data['name']}"
                keyboard.append([button_text])
                
                # Add provider info to message
                active_emoji = "🔹 " if provider_key == provider_info['current_provider'] else ""
                message += f"{active_emoji}✅ **{provider_data['name']}**\n"
                message += f"   • Model: {provider_data['current_model']}\n"
                if provider_key == provider_info['current_provider']:
                    message += f"   • Status: Currently Active\n"
                message += "\n"
        
        # Add unavailable providers to message (but not to keyboard)
        for provider_key, provider_data in provider_info['providers'].items():
            if not provider_data['available']:
                message += f"❌ **{provider_data['name']}**\n"
                message += f"   • Model: {provider_data['current_model']}\n"
                message += f"   • Status: Missing API key\n\n"
        
        if len(keyboard) > 1:  # Only show keyboard if there are providers to switch to
            message += "**Select a provider below:**"
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(message, reply_markup=reply_markup)
        else:
            message += "**No alternative providers available.**\n"
            message += "Configure additional API keys to enable provider switching."
            await safe_send_message(update, message)
            
    except Exception as e:
        logger.error(f"Error in provider command for user {user_id}: {e}")
        await update.message.reply_text(localization_manager.get_text(user_id, "error_occurred"))

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages including language selection."""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Check if this is a language selection
    if message_text in ["🇺🇸 English", "🇧🇷 Português (Brasil)"]:
        language = "en" if "English" in message_text else "pt-br"
        
        if localization_manager.set_user_language(user_id, language):
            success_msg = localization_manager.get_text(user_id, "lang_changed")
            await update.message.reply_text(success_msg)
        else:
            await update.message.reply_text(localization_manager.get_text(user_id, "error_occurred"))
        return
    
    # Check if this is a provider selection
    provider_buttons = ["🔹 OpenAI", "✅ OpenAI", "🔹 Together AI", "✅ Together AI", "🔹 OpenRouter", "✅ OpenRouter"]
    if message_text in provider_buttons:
        # Extract provider name from button text
        provider_map = {
            "🔹 OpenAI": "openai",
            "✅ OpenAI": "openai",
            "🔹 Together AI": "together",
            "✅ Together AI": "together",
            "🔹 OpenRouter": "openrouter",
            "✅ OpenRouter": "openrouter"
        }
        
        new_provider = provider_map.get(message_text)
        if new_provider:
            # Attempt to change provider
            result = llm_provider.change_provider(new_provider)
            
            if result['success']:
                message = f"✅ **LLM Provider Changed Successfully!**\n\n"
                message += f"**From:** {result['old_provider'].title()} ({result['old_model']})\n"
                message += f"**To:** {result['new_provider'].title()} ({result['new_model']})\n\n"
                message += "The new provider will be used for all future `/code` requests."
                
                await safe_send_message(update, message)
            else:
                message = f"❌ **Failed to change LLM provider:**\n\n{result['error']}"
                await safe_send_message(update, message)
        return
    
    # Check if this is an approval/rejection response
    approval_buttons = ["✅ Approve & Commit", "❌ Reject Changes", "📋 Show Details"]
    if message_text in approval_buttons:
        if message_text == "✅ Approve & Commit":
            await handle_approval(update, user_id, approve=True)
        elif message_text == "❌ Reject Changes":
            await handle_approval(update, user_id, approve=False)
        elif message_text == "📋 Show Details":
            await handle_show_details(update, user_id)
        return
    
    # Default echo response
    if security_manager.is_user_authorized(user_id):
        help_text = localization_manager.get_text(user_id, "start_description")
        await update.message.reply_text(f"👋 {help_text} Use /help to see what I can do for you!")
    else:
        await update.message.reply_text(localization_manager.get_text(user_id, "unauthorized"))

async def handle_approval(update: Update, user_id: int, approve: bool):
    """Handle approval or rejection of pending changes."""
    try:
        if approve:
            # Get and approve pending changes
            changes = approval_manager.approve_changes(user_id)
            if not changes:
                await update.message.reply_text("❌ No pending changes found to approve.")
                return
            
            await update.message.reply_text("⚡ Committing approved changes...")
            
            # Check Git strategy for branching
            git_strategy = os.environ.get('GIT_STRATEGY', 'branch').lower()
            
            if git_strategy != 'direct':
                # Create branch for changes
                branch_name = f"telecode-{int(time.time())}"
                branch_result = github_manager.create_branch(user_id, branch_name)
                if not branch_result['success']:
                    await update.message.reply_text(f"❌ Failed to create branch: {branch_result['error']}")
                    return
            
            # Commit and push changes
            commit_result = github_manager.commit_and_push(
                user_id,
                changes.commit_message,
                author_name="TeleCode Bot",
                author_email="telecode-bot@telegram.org"
            )
            
            if commit_result['success']:
                is_main_branch = commit_result.get('is_main_branch', False)
                
                if git_strategy == 'direct' and is_main_branch:
                    response = "✅ **Changes committed directly to main branch!**\n\n"
                    response += "🚀 **Railway should automatically deploy these changes.**\n\n"
                else:
                    response = "✅ **Changes committed successfully!**\n\n"
                
                response += f"**Repository:** {changes.repo_name}\n"
                response += f"**Branch:** {commit_result['branch']}\n"
                response += f"**Files:** {len(changes.files_created + changes.files_modified + changes.files_deleted)} files affected\n"
                response += f"**Commit:** [View Changes]({commit_result['commit_url']})"
                
                await safe_send_message(update, response)
            else:
                await update.message.reply_text(f"❌ Failed to commit changes: {commit_result['error']}")
        else:
            # Reject changes
            if approval_manager.reject_changes(user_id):
                await update.message.reply_text("❌ **Changes rejected and discarded.**\n\nThe repository remains unchanged.")
            else:
                await update.message.reply_text("❌ No pending changes found to reject.")
                
    except Exception as e:
        logger.error(f"Error handling approval for user {user_id}: {e}")
        await update.message.reply_text("❌ An error occurred while processing your approval.")

async def handle_show_details(update: Update, user_id: int):
    """Show detailed information about pending changes."""
    try:
        changes = approval_manager.get_pending_approval(user_id)
        if not changes:
            await update.message.reply_text("❌ No pending changes found.")
            return
        
        # Format detailed view
        details = []
        details.append(f"📋 **Detailed Changes for {changes.repo_name}**")
        details.append(f"🌿 **Branch:** {changes.branch_name}")
        details.append("")
        
        # Show actual file contents for small changes
        for file_change in changes.file_changes[:3]:  # Limit to first 3 files
            details.append(f"**📄 {file_change.file_path}** ({file_change.change_type})")
            
            if file_change.change_type == 'created' and file_change.new_content:
                content_preview = file_change.new_content[:500]
                details.append(f"```\n{content_preview}{'...' if len(file_change.new_content) > 500 else ''}\n```")
            elif file_change.change_type == 'modified':
                details.append(f"Lines: +{file_change.lines_added} -{file_change.lines_removed}")
            
            details.append("")
        
        if len(changes.file_changes) > 3:
            details.append(f"... and {len(changes.file_changes) - 3} more files")
        
        details.append(f"**💬 Commit Message:**")
        details.append(f"```\n{changes.commit_message}\n```")
        
        # Recreate approval keyboard
        keyboard = [
            ["✅ Approve & Commit", "❌ Reject Changes"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text("\n".join(details), reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error showing details for user {user_id}: {e}")
        await update.message.reply_text("❌ An error occurred while retrieving change details.")

async def webhook_handler(request: Request) -> web.Response:
    """Handle incoming webhook requests."""
    application = request.app['application']
    await application.update_queue.put(
        Update.de_json(data=await request.json(), bot=application.bot)
    )
    return web.Response(status=200)

async def main() -> None:
    """Start the bot."""
    global github_manager, security_manager, llm_provider, chat_context_manager, localization_manager, approval_manager
    
    # Check required environment variables based on LLM provider
    llm_provider_type = os.environ.get('LLM_PROVIDER', 'openai').lower()
    
    required_vars = ['BOT_TOKEN', 'GITHUB_TOKEN']
    
    if llm_provider_type == 'together':
        required_vars.append('TOGETHER_API_KEY')
    elif llm_provider_type == 'openai':
        required_vars.append('OPENAI_API_KEY')
    elif llm_provider_type == 'openrouter':
        required_vars.append('OPENROUTER_API_KEY')
    else:
        logger.error(f"Unsupported LLM provider: {llm_provider_type}. Supported providers: 'openai', 'together', 'openrouter'")
        return
    
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return
    
    # Initialize managers
    github_manager = GitHubManager(os.environ.get('GITHUB_TOKEN'))
    security_manager = SecurityManager()
    llm_provider = LLMProvider()
    chat_context_manager = ChatContextManager()
    localization_manager = LocalizationManager()
    approval_manager = ApprovalManager()
    
    token = os.environ.get('BOT_TOKEN')
    application = Application.builder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('repo', repo_command))
    application.add_handler(CommandHandler('repos', repos_command))
    application.add_handler(CommandHandler('repo_disconnect', repo_disconnect_command))
    application.add_handler(CommandHandler('code', code_command))
    application.add_handler(CommandHandler('status', status_command))
    application.add_handler(CommandHandler('context', context_command))
    application.add_handler(CommandHandler('tokens', tokens_command))
    application.add_handler(CommandHandler('clear', clear_command))
    application.add_handler(CommandHandler('lang', lang_command))
    application.add_handler(CommandHandler('provider', provider_command))
    
    # Add message handler for non-commands
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    port = int(os.environ.get('PORT', 8000))
    webhook_url = os.environ.get('RAILWAY_STATIC_URL')
    
    if webhook_url:
        await application.initialize()
        await application.start()
        
        await application.bot.set_webhook(url=f"https://{webhook_url}/webhook")
        
        app = web.Application()
        app['application'] = application
        app.router.add_post('/webhook', webhook_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        
        logger.info(f"Webhook server started on port {port}")
        
        import signal
        import asyncio
        
        def signal_handler():
            logger.info("Received exit signal")
            raise KeyboardInterrupt()
        
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, lambda s, f: signal_handler())
        
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await application.stop()
            await application.shutdown()
            await runner.cleanup()
            
            # Cleanup managers
            if github_manager:
                github_manager.cleanup()
            if chat_context_manager:
                chat_context_manager.cleanup_old_contexts()
    else:
        await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())