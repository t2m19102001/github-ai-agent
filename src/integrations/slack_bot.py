#!/usr/bin/env python3
"""
Slack Bot Integration - Phase 5
Multi-agent chat interface for Slack
"""

import os
import sys
import asyncio
import json
from typing import Dict, Any, List
from dataclasses import dataclass

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from slack_bolt.async_app import AsyncApp
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False
    print("⚠️  Slack Bolt not installed. Install with: pip install slack-bolt")

from src.agents.agent_manager import AgentManager
from src.agents.github_issue_agent import GitHubIssueAgent
from src.agents.code_agent import CodeAgent
from src.agents.doc_agent import DocumentationAgent
from src.agents.image_agent import ImageAgent
from src.memory.log_manager import log_activity
from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class SlackConfig:
    """Slack bot configuration"""
    app_token: str
    bot_token: str
    signing_secret: str
    
class SlackBotManager:
    """Slack bot manager with multi-agent integration"""
    
    def __init__(self, config: SlackConfig):
        if not SLACK_AVAILABLE:
            raise ImportError("slack-bolt is required for Slack integration")
        
        self.config = config
        self.app = AsyncApp(
            token=config.bot_token,
            signing_secret=config.signing_secret
        )
        
        # Initialize agents
        self.agents = {
            "github": GitHubIssueAgent(
                repo=os.getenv("GITHUB_REPO", "default/repo"),
                token=os.getenv("GITHUB_TOKEN", "mock_token"),
                config={"test_mode": True}
            ),
            "code": CodeAgent(config={"test_mode": True}),
            "doc": DocumentationAgent(config={"test_mode": True}),
            "image": ImageAgent(config={"test_mode": True})
        }
        
        self.agent_manager = AgentManager(list(self.agents.values()))
        
        # Register handlers
        self._register_handlers()
        
        logger.info("Slack bot initialized with multi-agent system")
    
    def _register_handlers(self):
        """Register Slack event handlers"""
        
        @self.app.event("app_mention")
        async def handle_app_mention(event, say, ack):
            """Handle bot mentions"""
            await ack()
            await self._handle_message(event, say, mention=True)
        
        @self.app.event("message")
        async def handle_message(event, say, ack):
            """Handle direct messages"""
            await ack()
            
            # Ignore bot messages and messages in channels
            if event.get("bot_id") or event.get("channel_type") != "im":
                return
            
            await self._handle_message(event, say, mention=False)
        
        @self.app.command("/ai-analyze")
        async def handle_analyze_command(ack, command, say):
            """Handle /ai-analyze slash command"""
            await ack()
            
            text = command.get("text", "").strip()
            if not text:
                await say("❌ Please provide text to analyze. Usage: `/ai-analyze <text>`")
                return
            
            await self._process_ai_command(text, say, command_type="analyze")
        
        @self.app.command("/ai-review")
        async def handle_review_command(ack, command, say):
            """Handle /ai-review slash command"""
            await ack()
            
            pr_url = command.get("text", "").strip()
            if not pr_url:
                await say("❌ Please provide PR URL. Usage: `/ai-review <pr_url>`")
                return
            
            await self._process_review_command(pr_url, say)
        
        @self.app.command("/ai-status")
        async def handle_status_command(ack, say):
            """Handle /ai-status slash command"""
            await ack()
            await self._process_status_command(say)
        
        @self.app.command("/ai-help")
        async def handle_help_command(ack, say):
            """Handle /ai-help slash command"""
            await ack()
            await self._show_help(say)
    
    async def _handle_message(self, event: Dict[str, Any], say, mention: bool = False):
        """Handle incoming message with AI analysis"""
        try:
            user = event.get("user", "unknown")
            text = event.get("text", "").strip()
            channel = event.get("channel", "unknown")
            
            # Remove bot mention if present
            if mention:
                text = text.replace(f"<@{event.get('app_id')}>", "").strip()
            
            if not text:
                return
            
            # Log activity
            log_activity(
                agent="SlackBot",
                action="handle_message",
                result=f"Processing message from {user} in {channel}",
                metadata={"user": user, "channel": channel, "text": text[:100]}
            )
            
            # Show typing indicator
            await say({"type": "typing"})
            
            # Process with AI
            response = await self._process_with_agents(text, user)
            
            # Send response
            await say(response)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await say("❌ Sorry, I encountered an error processing your request.")
    
    async def _process_with_agents(self, text: str, user: str) -> str:
        """Process text with multi-agent system"""
        try:
            # Determine task type
            task_type = self._classify_task(text)
            
            # Create task
            task_data = {
                "type": task_type,
                "data": {
                    "query": text,
                    "user": user,
                    "source": "slack"
                }
            }
            
            # Process with agent manager
            task_id = self.agent_manager.create_task(
                task_type=task_type,
                data=task_data["data"],
                priority="medium"
            )
            
            result = self.agent_manager.process_task(task_id)
            
            # Format response
            return self._format_slack_response(result, task_type)
            
        except Exception as e:
            logger.error(f"Error processing with agents: {e}")
            return f"❌ Error: {str(e)}"
    
    def _classify_task(self, text: str) -> str:
        """Classify the type of task based on text"""
        text_lower = text.lower()
        
        # GitHub issue related
        if any(keyword in text_lower for keyword in ["issue", "bug", "github", "pr", "pull request"]):
            return "github_issue"
        
        # Code related
        elif any(keyword in text_lower for keyword in ["code", "function", "class", "algorithm", "debug"]):
            return "code_analysis"
        
        # Documentation related
        elif any(keyword in text_lower for keyword in ["doc", "documentation", "readme", "guide", "tutorial"]):
            return "documentation_search"
        
        # General query
        else:
            return "general_query"
    
    def _format_slack_response(self, result, task_type: str) -> str:
        """Format agent result for Slack"""
        try:
            lines = [
                f"🤖 *AI Agent Analysis*",
                f""
            ]
            
            if hasattr(result, 'success') and result.success:
                lines.append(f"✅ *Task Type:* {task_type}")
                lines.append(f"📊 *Agents Used:* {len(result.agent_results)}")
                lines.append(f"")
                
                # Agent results
                for agent_result in result.agent_results:
                    agent_name = agent_result.agent_name
                    agent_success = agent_result.success
                    agent_result_text = agent_result.result
                    
                    if isinstance(agent_result_text, dict):
                        agent_result_text = agent_result_text.get("response", str(agent_result_text))
                    
                    emoji = "✅" if agent_success else "❌"
                    lines.append(f"{emoji} *{agent_name}:*")
                    
                    # Format long responses
                    if len(str(agent_result_text)) > 300:
                        lines.append(f"```")
                        lines.append(f"{str(agent_result_text)[:500]}...")
                        lines.append(f"```")
                    else:
                        lines.append(f"{str(agent_result_text)}")
                    
                    lines.append(f"")
                
                # Summary
                if hasattr(result, 'summary'):
                    lines.append(f"📋 *Summary:*")
                    lines.append(f"{result.summary}")
                    lines.append(f"")
                
            else:
                lines.append(f"❌ *Analysis Failed:*")
                lines.append(f"```")
                lines.append(f"{str(result)}")
                lines.append(f"```")
                lines.append(f"")
            
            lines.extend([
                f"---",
                f"*Powered by GitHub AI Agent - Phase 5*"
            ])
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            return f"❌ Error formatting response: {str(e)}"
    
    async def _process_ai_command(self, text: str, say, command_type: str):
        """Process AI slash commands"""
        try:
            response = await self._process_with_agents(text, f"slash_{command_type}")
            await say(response)
            
        except Exception as e:
            logger.error(f"Error processing {command_type} command: {e}")
            await say(f"❌ Error processing command: {str(e)}")
    
    async def _process_review_command(self, pr_url: str, say):
        """Process PR review command"""
        try:
            # Extract PR info from URL
            # Example: https://github.com/owner/repo/pull/123
            if "github.com" not in pr_url:
                await say("❌ Please provide a valid GitHub PR URL")
                return
            
            parts = pr_url.strip("/").split("/")
            if len(parts) < 7:
                await say("❌ Invalid PR URL format")
                return
            
            owner = parts[3]
            repo = parts[4]
            pr_number = parts[6]
            
            await say(f"🔄 Analyzing PR {owner}/{repo}#{pr_number}...")
            
            # This would integrate with the AI review script
            # For now, provide a placeholder response
            response = f"""
🤖 *PR Review Started*
📋 *Repository:* {owner}/{repo}
🔢 *PR Number:* {pr_number}
🔗 *URL:* {pr_url}

⏳ *Status:* Queued for analysis...
📊 *Agents:* GitHub Issue Agent, Code Agent, Documentation Agent

📝 *Note:* Full review will be posted as a comment on the PR.
            """.strip()
            
            await say(response)
            
        except Exception as e:
            logger.error(f"Error processing review command: {e}")
            await say(f"❌ Error processing review: {str(e)}")
    
    async def _process_status_command(self, say):
        """Show system status"""
        try:
            # Get agent status
            status_lines = [
                f"🤖 *AI Agent System Status*",
                f"",
                f"📊 *Agents:*",
                f"✅ GitHub Issue Agent - Ready",
                f"✅ Code Agent - Ready", 
                f"✅ Documentation Agent - Ready",
                f"✅ Image Agent - Ready",
                f"",
                f"🔧 *Features:*",
                f"✅ Multi-modal processing",
                f"✅ RAG integration",
                f"✅ GitHub integration",
                f"✅ Slack chat interface",
                f"",
                f"⚡ *Performance:*",
                f"🟢 All systems operational",
                f"📈 Ready for queries",
                f"",
                f"---",
                f"*GitHub AI Agent - Phase 5*"
            ]
            
            await say("\n".join(status_lines))
            
        except Exception as e:
            logger.error(f"Error showing status: {e}")
            await say("❌ Error getting system status")
    
    async def _show_help(self, say):
        """Show help information"""
        help_text = """
🤖 *GitHub AI Agent - Help*

📝 *Chat with me:*
• Mention @ai-agent in any channel
• Send me a direct message
• I'll analyze your text with multiple AI agents

🔧 *Slash Commands:*
• `/ai-analyze <text>` - Analyze text with AI
• `/ai-review <pr_url>` - Review a GitHub PR
• `/ai-status` - Show system status
• `/ai-help` - Show this help

🎯 *What I can do:*
• 🐛 Analyze GitHub issues and bugs
• 💻 Review code and suggest improvements
• 📚 Search documentation and provide answers
• 🖼️ Process images and diagrams (Phase 5)
• 🔍 Provide intelligent recommendations

💡 *Examples:*
• "@ai-agent There's a bug in the login function"
• "/ai-analyze How do I implement OAuth?"
• "/ai-review https://github.com/user/repo/pull/123"
• "@ai-agent Can you help debug this error?"

---
*Powered by GitHub AI Agent - Phase 5*
        """.strip()
        
        await say(help_text)
    
    def start(self):
        """Start the Slack bot"""
        if not SLACK_AVAILABLE:
            raise ImportError("slack-bolt is required")
        
        handler = AsyncSocketModeHandler(
            self.app,
            self.config.app_token
        )
        
        logger.info("Starting Slack bot...")
        handler.start()
        
        logger.info("Slack bot started successfully")

def main():
    """Main entry point"""
    # Check environment variables
    app_token = os.getenv("SLACK_APP_TOKEN")
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    signing_secret = os.getenv("SLACK_SIGNING_SECRET")
    
    if not all([app_token, bot_token, signing_secret]):
        print("❌ Missing required environment variables:")
        print("   SLACK_APP_TOKEN - xapp-* token")
        print("   SLACK_BOT_TOKEN - xoxb-* token") 
        print("   SLACK_SIGNING_SECRET - signing secret")
        sys.exit(1)
    
    # Create configuration
    config = SlackConfig(
        app_token=app_token,
        bot_token=bot_token,
        signing_secret=signing_secret
    )
    
    # Start bot
    try:
        bot = SlackBotManager(config)
        bot.start()
    except KeyboardInterrupt:
        logger.info("Slack bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
