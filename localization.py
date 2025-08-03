"""
Localization system for TeleCode Bot
Supports English and Portuguese (Brazil) languages
"""

import json
import os
from typing import Dict, Any, Optional

class LocalizationManager:
    """Manages user language preferences and translations."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.user_languages_file = os.path.join(data_dir, "user_languages.json")
        self.default_language = "en"
        self.supported_languages = ["en", "pt-br"]
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Load user language preferences
        self.user_languages = self._load_user_languages()
        
        # Initialize translations
        self.translations = self._load_translations()
    
    def _load_user_languages(self) -> Dict[str, str]:
        """Load user language preferences from file."""
        if os.path.exists(self.user_languages_file):
            try:
                with open(self.user_languages_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_user_languages(self):
        """Save user language preferences to file."""
        try:
            with open(self.user_languages_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_languages, f, ensure_ascii=False, indent=2)
        except IOError:
            pass  # Fail silently for now
    
    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """Load all translations."""
        return {
            "en": {
                # Commands
                "start_title": "🤖 **TeleCode Bot**",
                "start_description": "I can help you with coding tasks and GitHub operations!",
                "start_commands": "**Commands:**",
                "start_example": "**Example:**",
                "start_footer": "Let's get started! 🚀",
                
                # Command descriptions
                "cmd_start": "/start - Show this help message",
                "cmd_repo": "/repo `<github_url>` - Set active repository",
                "cmd_repos": "/repos - List all connected repositories",
                "cmd_repo_disconnect": "/repo_disconnect [clean] - Disconnect from active repository", 
                "cmd_code": "/code `<prompt>` - Ask questions or make code changes",
                "cmd_status": "/status - Show current repository and usage stats",
                "cmd_context": "/context - Show chat context history",
                "cmd_tokens": "/tokens - Show token usage for chat context",
                "cmd_clear": "/clear - Clear chat context history",
                "cmd_help": "/help - Show detailed help",
                "cmd_lang": "/lang - Change language (English/Portuguese)",
                
                # Help command
                "help_title": "📚 **TeleCode Bot Help**",
                "help_repo_commands": "**🔧 Repository Commands:**",
                "help_coding_commands": "**💻 Coding Commands:**",
                "help_context_commands": "**💬 Chat Context Commands:**",
                "help_info_commands": "**ℹ️ Information Commands:**",
                "help_usage_examples": "**📝 Usage Examples:**",
                "help_security": "**🔒 Security & Limits:**",
                "help_environment": "**⚙️ Environment Configuration:**",
                "help_token_management": "**📊 Token Management:**",
                
                # Help descriptions
                "help_repo_desc": "Set your active repository",
                "help_repos_desc": "List all connected repositories and their status",
                "help_repo_disconnect_desc": "Disconnect from active repository (add 'clean' to delete local files)",
                "help_status_desc": "Show current repository, usage stats, and chat context",
                "help_code_desc": "Ask questions or make code changes",
                "help_code_readonly": "Read-only: \"explain the authentication flow\"",
                "help_code_changes": "Code changes: \"fix the login validation bug\"",
                "help_context_desc": "View your recent conversation history",
                "help_tokens_desc": "Analyze token usage for your chat context",
                "help_clear_desc": "Clear your conversation history (start fresh)",
                "help_start_desc": "Show welcome message and basic commands",
                "help_help_desc": "Show this detailed help (current command)",
                "help_lang_desc": "Change language between English and Portuguese",
                
                # Security text
                "help_security_text": "• All operations are logged for security\n• Rate limits apply to prevent abuse (see /status)\n• Only authorized users can access the bot\n• Chat context is persistent and private per user",
                
                # Environment text
                "help_env_text": "• Max chat messages: Configurable via `CHAT_CONTEXT_MAX_MESSAGES`\n• Git strategy: Set `GIT_STRATEGY=direct` for Railway auto-deployment\n• Repository files are stored locally for faster access\n• Supports multiple LLM providers (OpenAI, Together AI)",
                
                # Token management text
                "help_token_text": "The bot tracks conversation context to provide better responses. Use /tokens to monitor usage and costs, /clear to reset when needed.",
                
                # Common messages
                "unauthorized": "❌ You are not authorized to use this bot.",
                "processing": "🔄 **Processing your request...**\nThis may take a few minutes.",
                "error_occurred": "❌ An error occurred while processing your request.",
                "success": "✅ Success!",
                
                # Rate limiting
                "hourly_limit": "⏰ Hourly rate limit exceeded. Try again in {minutes} minutes.",
                "daily_limit": "⏰ Daily rate limit exceeded. Try again in {hours} hours.",
                
                # Repository commands
                "repo_usage": "❌ Please provide a GitHub repository URL.\n\n**Usage:** /repo `<github_url>`\n**Example:** /repo `https://github.com/username/repository`",
                "repo_setting_up": "🔄 Setting up repository...",
                "repo_success": "✅ **Repository set successfully!**",
                "repo_failed": "❌ Failed to set repository: {error}",
                "repo_access_denied": "❌ Access denied to repository: {repo_url}\n\nReason: {reason}",
                "no_active_repo": "❌ No active repository set. Use /repo `<github_url>` first!",
                "repo_disconnect_success": "✅ **Disconnected from repository:** {repo_name}",
                "repo_disconnect_cleanup": "🧹 **Local files cleaned up.**",
                "repo_disconnect_failed": "❌ Failed to disconnect from repository: {error}",
                
                # Code commands
                "code_usage": "❌ Please provide a coding prompt.\n\n**Usage:** /code `<your_prompt>`\n**Example:** /code `fix the authentication bug in login.py`",
                "code_analyzing": "🤖 **{provider} ({model}) is analyzing your request{context}...**",
                "code_committing": "🔄 **Committing changes directly to main branch...**",
                "code_branch_created": "🔄 **Created branch: {branch}**",
                "code_success": "✅ **Code changes implemented successfully!**",
                "code_success_main": "✅ **Code changes committed directly to main branch!**",
                "code_railway_deploy": "🚀 **Railway should automatically deploy these changes.**",
                "code_analysis": "💬 **Analysis completed (no code changes needed):**",
                "no_llm_response": "❌ No response from LLM provider.",
                "llm_error": "❌ **Error generating response:**\n\n{error}",
                "commit_failed": "❌ Failed to commit changes: {error}",
                "branch_failed": "❌ Failed to create branch: {error}",
                "repo_access_failed": "❌ Failed to access repository: {error}",
                
                # Language command
                "lang_select": "🌐 **Select Language / Selecione o Idioma**\n\nChoose your preferred language:",
                "lang_english": "🇺🇸 English",
                "lang_portuguese": "🇧🇷 Português (Brasil)",
                "lang_changed": "✅ Language changed to English!",
                "lang_current": "🌐 **Current language:** English",
                
                # Status command
                "status_title": "📊 **Current Status**",
                "status_active_repo": "**🗂 Active Repository:**",
                "status_no_repo": "**🗂 Active Repository:** None",
                "status_use_repo": "Use /repo `<github_url>` to set one!",
                "status_usage_stats": "**📈 Usage Statistics:**",
                "status_chat_context": "**💬 Chat Context:**",
                "status_name": "• Name: {name}",
                "status_url": "• URL: {url}",
                "status_cloned": "• Cloned: {status}",
                "status_branch": "• Branch: {branch}",
                "status_changes": "• Changes: {status}",
                "status_last_commit": "• Last Commit: {commit}",
                "status_hourly": "• Hourly: {used}/{limit} requests",
                "status_daily": "• Daily: {used}/{limit} requests",
                "status_messages": "• Messages: {count}/{max}",
                "status_last_interaction": "• Last interaction: {time}",
                "status_clean": "✅ Clean",
                "status_has_changes": "⚠️ Yes",
                
                # Repos command
                "repos_title": "📂 **Your Connected Repositories ({count})**",
                "repos_no_repos": "📂 **No repositories found.**",
                "repos_use_repo": "Use /repo `<github_url>` to connect your first repository!",
                "repos_example": "Example: /repo `https://github.com/username/my-project`",
                "repos_active": "🔹 **ACTIVE REPOSITORY**",
                "repos_local": "📍 Local: {status}",
                "repos_git": "🔄 Git: {status}",
                "repos_size": "💾 Size: {size} MB",
                "repos_modified": "🕒 Modified: {time}",
                "repos_path": "📁 Path: `{path}`",
                "repos_current_active": "🎯 **Current Active:** {name}",
                "repos_no_active": "ℹ️ No active repository set. Use /repo `<url>` to activate one.",
                "repos_tips": "💡 **Tips:**",
                "repos_tip_switch": "• Use /repo `<url>` to switch active repository",
                "repos_tip_status": "• Use /status for detailed active repository info",
                "repos_tip_files": "• Local files are automatically updated when needed",
                "repos_available": "✅ Available",
                "repos_missing": "❌ Missing",
                "repos_repository": "✅ Repository",
                "repos_no_git": "❌ No Git",
                
                # Context command
                "context_title": "💬 **Chat Context ({count}/{max} messages)**",
                "context_no_context": "📭 **No chat context found.**",
                "context_start_conversation": "Start a conversation with /code `<prompt>` to build context!",
                "context_user": "👤 **User:**",
                "context_assistant": "🤖 **Assistant:**", 
                "context_earlier_messages": "... and {count} earlier messages",
                "context_use_clear": "Use /clear to reset chat context.",
                
                # Clear command
                "clear_success": "🧹 **Chat context cleared!**",
                "clear_description": "Starting fresh - previous conversation history has been removed.",
                "clear_failed": "❌ Failed to clear chat context.",
                
                # Tokens command
                "tokens_title": "📊 **Token Usage Analysis**",
                "tokens_no_context": "📊 **No chat context found.**",
                "tokens_start_conversation": "Start a conversation with /code `<prompt>` to see token usage!",
                "tokens_model": "**Model:** {model}",
                "tokens_total_messages": "**Total Messages:** {total}/{max}",
                "tokens_total_tokens": "**Total Tokens:** {tokens:,}",
                "tokens_context_tokens": "**Context Tokens:** {tokens:,}",
                "tokens_avg_per_message": "**Avg per Message:** {avg:,}",
                "tokens_breakdown": "**Per Message Breakdown:**",
                "tokens_earlier_messages": "... and {count} earlier messages",
                "tokens_estimated_cost": "💰 **Estimated Cost:** ${cost:.4f} (input only)",
                "tokens_estimated_cost_precise": "💰 **Estimated Cost:** ${cost:.6f} (input only)",
                "tokens_environment": "**Environment:** Max messages = {max}",
            },
            
            "pt-br": {
                # Commands
                "start_title": "🤖 **TeleCode Bot**",
                "start_description": "Posso ajudar você com tarefas de programação e operações no GitHub!",
                "start_commands": "**Comandos:**",
                "start_example": "**Exemplo:**",
                "start_footer": "Vamos começar! 🚀",
                
                # Command descriptions
                "cmd_start": "/start - Mostrar esta mensagem de ajuda",
                "cmd_repo": "/repo `<github_url>` - Definir repositório ativo",
                "cmd_repos": "/repos - Listar todos os repositórios conectados",
                "cmd_repo_disconnect": "/repo_disconnect [clean] - Desconectar do repositório ativo",
                "cmd_code": "/code `<prompt>` - Fazer perguntas ou alterações no código",
                "cmd_status": "/status - Mostrar repositório atual e estatísticas de uso",
                "cmd_context": "/context - Mostrar histórico do chat",
                "cmd_tokens": "/tokens - Mostrar uso de tokens do contexto do chat",
                "cmd_clear": "/clear - Limpar histórico do chat",
                "cmd_help": "/help - Mostrar ajuda detalhada",
                "cmd_lang": "/lang - Alterar idioma (Inglês/Português)",
                
                # Help command
                "help_title": "📚 **Ajuda do TeleCode Bot**",
                "help_repo_commands": "**🔧 Comandos de Repositório:**",
                "help_coding_commands": "**💻 Comandos de Programação:**",
                "help_context_commands": "**💬 Comandos de Contexto do Chat:**",
                "help_info_commands": "**ℹ️ Comandos de Informação:**",
                "help_usage_examples": "**📝 Exemplos de Uso:**",
                "help_security": "**🔒 Segurança e Limites:**",
                "help_environment": "**⚙️ Configuração do Ambiente:**",
                "help_token_management": "**📊 Gerenciamento de Tokens:**",
                
                # Help descriptions
                "help_repo_desc": "Definir seu repositório ativo",
                "help_repos_desc": "Listar todos os repositórios conectados e seus status",
                "help_repo_disconnect_desc": "Desconectar do repositório ativo (adicione 'clean' para deletar arquivos locais)",
                "help_status_desc": "Mostrar repositório atual, estatísticas de uso e contexto do chat",
                "help_code_desc": "Fazer perguntas ou alterações no código",
                "help_code_readonly": "Somente leitura: \"explique o fluxo de autenticação\"",
                "help_code_changes": "Alterações no código: \"corrigir o bug de validação de login\"",
                "help_context_desc": "Ver seu histórico de conversa recente",
                "help_tokens_desc": "Analisar uso de tokens do seu contexto de chat",
                "help_clear_desc": "Limpar seu histórico de conversa (começar do zero)",
                "help_start_desc": "Mostrar mensagem de boas-vindas e comandos básicos",
                "help_help_desc": "Mostrar esta ajuda detalhada (comando atual)",
                "help_lang_desc": "Alterar idioma entre Inglês e Português",
                
                # Security text
                "help_security_text": "• Todas as operações são registradas para segurança\n• Limites de taxa se aplicam para prevenir abuso (veja /status)\n• Apenas usuários autorizados podem acessar o bot\n• Contexto do chat é persistente e privado por usuário",
                
                # Environment text
                "help_env_text": "• Máximo de mensagens do chat: Configurável via `CHAT_CONTEXT_MAX_MESSAGES`\n• Estratégia Git: Defina `GIT_STRATEGY=direct` para auto-deploy no Railway\n• Arquivos do repositório são armazenados localmente para acesso mais rápido\n• Suporta múltiplos provedores de LLM (OpenAI, Together AI)",
                
                # Token management text
                "help_token_text": "O bot rastreia o contexto da conversa para fornecer melhores respostas. Use /tokens para monitorar uso e custos, /clear para resetar quando necessário.",
                
                # Common messages
                "unauthorized": "❌ Você não está autorizado a usar este bot.",
                "processing": "🔄 **Processando sua solicitação...**\nIsso pode levar alguns minutos.",
                "error_occurred": "❌ Ocorreu um erro ao processar sua solicitação.",
                "success": "✅ Sucesso!",
                
                # Rate limiting
                "hourly_limit": "⏰ Limite de taxa por hora excedido. Tente novamente em {minutes} minutos.",
                "daily_limit": "⏰ Limite de taxa diário excedido. Tente novamente em {hours} horas.",
                
                # Repository commands
                "repo_usage": "❌ Por favor, forneça uma URL do repositório GitHub.\n\n**Uso:** /repo `<github_url>`\n**Exemplo:** /repo `https://github.com/usuario/repositorio`",
                "repo_setting_up": "🔄 Configurando repositório...",
                "repo_success": "✅ **Repositório definido com sucesso!**",
                "repo_failed": "❌ Falha ao definir repositório: {error}",
                "repo_access_denied": "❌ Acesso negado ao repositório: {repo_url}\n\nMotivo: {reason}",
                "no_active_repo": "❌ Nenhum repositório ativo definido. Use /repo `<github_url>` primeiro!",
                "repo_disconnect_success": "✅ **Desconectado do repositório:** {repo_name}",
                "repo_disconnect_cleanup": "🧹 **Arquivos locais limpos.**",
                "repo_disconnect_failed": "❌ Falha ao desconectar do repositório: {error}",
                
                # Code commands
                "code_usage": "❌ Por favor, forneça um prompt de codificação.\n\n**Uso:** /code `<seu_prompt>`\n**Exemplo:** /code `corrigir o bug de autenticação no login.py`",
                "code_analyzing": "🤖 **{provider} ({model}) está analisando sua solicitação{context}...**",
                "code_committing": "🔄 **Fazendo commit das alterações diretamente na branch principal...**",
                "code_branch_created": "🔄 **Branch criada: {branch}**",
                "code_success": "✅ **Alterações no código implementadas com sucesso!**",
                "code_success_main": "✅ **Alterações no código commitadas diretamente na branch principal!**",
                "code_railway_deploy": "🚀 **Railway deve fazer deploy automático dessas alterações.**",
                "code_analysis": "💬 **Análise concluída (nenhuma alteração no código necessária):**",
                "no_llm_response": "❌ Nenhuma resposta do provedor LLM.",
                "llm_error": "❌ **Erro ao gerar resposta:**\n\n{error}",
                "commit_failed": "❌ Falha ao fazer commit das alterações: {error}",
                "branch_failed": "❌ Falha ao criar branch: {error}",
                "repo_access_failed": "❌ Falha ao acessar repositório: {error}",
                
                # Language command
                "lang_select": "🌐 **Select Language / Selecione o Idioma**\n\nEscolha seu idioma preferido:",
                "lang_english": "🇺🇸 English",
                "lang_portuguese": "🇧🇷 Português (Brasil)",
                "lang_changed": "✅ Idioma alterado para Português (Brasil)!",
                "lang_current": "🌐 **Idioma atual:** Português (Brasil)",
                
                # Status command
                "status_title": "📊 **Status Atual**",
                "status_active_repo": "**🗂 Repositório Ativo:**",
                "status_no_repo": "**🗂 Repositório Ativo:** Nenhum",
                "status_use_repo": "Use /repo `<github_url>` para definir um!",
                "status_usage_stats": "**📈 Estatísticas de Uso:**",
                "status_chat_context": "**💬 Contexto do Chat:**",
                "status_name": "• Nome: {name}",
                "status_url": "• URL: {url}",
                "status_cloned": "• Clonado: {status}",
                "status_branch": "• Branch: {branch}",
                "status_changes": "• Alterações: {status}",
                "status_last_commit": "• Último Commit: {commit}",
                "status_hourly": "• Por hora: {used}/{limit} solicitações",
                "status_daily": "• Diário: {used}/{limit} solicitações",
                "status_messages": "• Mensagens: {count}/{max}",
                "status_last_interaction": "• Última interação: {time}",
                "status_clean": "✅ Limpo",
                "status_has_changes": "⚠️ Sim",
                
                # Repos command
                "repos_title": "📂 **Seus Repositórios Conectados ({count})**",
                "repos_no_repos": "📂 **Nenhum repositório encontrado.**",
                "repos_use_repo": "Use /repo `<github_url>` para conectar seu primeiro repositório!",
                "repos_example": "Exemplo: /repo `https://github.com/usuario/meu-projeto`",
                "repos_active": "🔹 **REPOSITÓRIO ATIVO**",
                "repos_local": "📍 Local: {status}",
                "repos_git": "🔄 Git: {status}",
                "repos_size": "💾 Tamanho: {size} MB",
                "repos_modified": "🕒 Modificado: {time}",
                "repos_path": "📁 Caminho: `{path}`",
                "repos_current_active": "🎯 **Atual Ativo:** {name}",
                "repos_no_active": "ℹ️ Nenhum repositório ativo definido. Use /repo `<url>` para ativar um.",
                "repos_tips": "💡 **Dicas:**",
                "repos_tip_switch": "• Use /repo `<url>` para trocar de repositório ativo",
                "repos_tip_status": "• Use /status para informações detalhadas do repositório ativo",
                "repos_tip_files": "• Arquivos locais são atualizados automaticamente quando necessário",
                "repos_available": "✅ Disponível",
                "repos_missing": "❌ Ausente",
                "repos_repository": "✅ Repositório",
                "repos_no_git": "❌ Sem Git",
                
                # Context command
                "context_title": "💬 **Contexto do Chat ({count}/{max} mensagens)**",
                "context_no_context": "📭 **Nenhum contexto de chat encontrado.**",
                "context_start_conversation": "Inicie uma conversa com /code `<prompt>` para construir contexto!",
                "context_user": "👤 **Usuário:**",
                "context_assistant": "🤖 **Assistente:**", 
                "context_earlier_messages": "... e {count} mensagens anteriores",
                "context_use_clear": "Use /clear para resetar o contexto do chat.",
                
                # Clear command
                "clear_success": "🧹 **Contexto do chat limpo!**",
                "clear_description": "Começando do zero - histórico de conversa anterior foi removido.",
                "clear_failed": "❌ Falha ao limpar contexto do chat.",
                
                # Tokens command
                "tokens_title": "📊 **Análise de Uso de Tokens**",
                "tokens_no_context": "📊 **Nenhum contexto de chat encontrado.**",
                "tokens_start_conversation": "Inicie uma conversa com /code `<prompt>` para ver o uso de tokens!",
                "tokens_model": "**Modelo:** {model}",
                "tokens_total_messages": "**Total de Mensagens:** {total}/{max}",
                "tokens_total_tokens": "**Total de Tokens:** {tokens:,}",
                "tokens_context_tokens": "**Tokens de Contexto:** {tokens:,}",
                "tokens_avg_per_message": "**Média por Mensagem:** {avg:,}",
                "tokens_breakdown": "**Detalhamento por Mensagem:**",
                "tokens_earlier_messages": "... e {count} mensagens anteriores",
                "tokens_estimated_cost": "💰 **Custo Estimado:** ${cost:.4f} (apenas entrada)",
                "tokens_estimated_cost_precise": "💰 **Custo Estimado:** ${cost:.6f} (apenas entrada)",
                "tokens_environment": "**Ambiente:** Máximo de mensagens = {max}",
            }
        }
    
    def set_user_language(self, user_id: int, language: str) -> bool:
        """Set language preference for a user."""
        if language not in self.supported_languages:
            return False
        
        self.user_languages[str(user_id)] = language
        self._save_user_languages()
        return True
    
    def get_user_language(self, user_id: int) -> str:
        """Get language preference for a user."""
        return self.user_languages.get(str(user_id), self.default_language)
    
    def get_text(self, user_id: int, key: str, **kwargs) -> str:
        """Get localized text for a user."""
        language = self.get_user_language(user_id)
        text = self.translations.get(language, {}).get(key)
        
        if text is None:
            # Fallback to default language
            text = self.translations.get(self.default_language, {}).get(key, key)
        
        # Format with provided kwargs
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass  # Return unformatted text if formatting fails
        
        return text
    
    def is_supported_language(self, language: str) -> bool:
        """Check if a language is supported."""
        return language in self.supported_languages
    
    def get_supported_languages(self) -> list:
        """Get list of supported languages."""
        return self.supported_languages.copy()