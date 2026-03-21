#!/usr/bin/env python3
"""
Auto Comment On Issue Plugin
Automatically adds helpful comments to GitHub issues
"""

from typing import Dict, Any
from src.agent.plugins.base import BasePlugin, PluginConfig, PluginResult

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class AutoCommentOnIssuePlugin(BasePlugin):
    """Plugin that automatically comments on GitHub issues"""
    
    def __init__(self):
        config = PluginConfig(
            name="auto_comment_on_issue",
            enabled=True,
            priority=50
        )
        super().__init__(config)
        self.comment_templates = {
            "bug": "Thank you for reporting this bug! Our team will investigate shortly.",
            "enhancement": "Thanks for the enhancement suggestion! We'll review it for the next sprint.",
            "question": "Thanks for your question! We'll respond as soon as possible."
        }
    
    def validate(self, context: Dict[str, Any]) -> bool:
        """Check if this plugin should run for the given issue"""
        if not context.get("issue"):
            return False
        
        issue = context["issue"]
        action = issue.get("action", "")
        
        return action in ["opened", "created"]
    
    async def execute(self, context: Dict[str, Any]) -> PluginResult:
        """Execute the auto-comment logic"""
        try:
            issue = context["issue"]
            title = issue.get("title", "").lower()
            body = issue.get("body", "").lower()
            labels = issue.get("labels", [])
            
            comment_type = self._determine_comment_type(title, body, labels)
            comment = self._generate_comment(comment_type, issue)
            
            github_client = context.get("github_client")
            if github_client:
                repo = issue.get("repo", "owner/repo")
                issue_number = issue.get("number", 0)
                
                repo_obj = github_client.get_repo(repo)
                issue_obj = repo_obj.get_issue(issue_number)
                issue_obj.comment(comment)
                
                logger.info(f"Added comment to issue #{issue_number}")
                
                return PluginResult(
                    success=True,
                    action="auto_comment",
                    message=f"Added {comment_type} comment to issue",
                    data={
                        "issue_number": issue_number,
                        "comment_type": comment_type,
                        "comment_preview": comment[:100]
                    }
                )
            
            return PluginResult(
                success=True,
                action="auto_comment",
                message=f"Would add {comment_type} comment (no GitHub client)",
                data={"comment_type": comment_type}
            )
            
        except Exception as e:
            logger.error(f"Auto-comment failed: {e}")
            return PluginResult(
                success=False,
                action="auto_comment",
                message=f"Failed to add comment: {str(e)}"
            )
    
    def _determine_comment_type(
        self, 
        title: str, 
        body: str, 
        labels: list
    ) -> str:
        """Determine what type of comment to add"""
        combined = f"{title} {body}"
        
        if any(w in combined for w in ["bug", "error", "crash", "fail", "broken"]):
            return "bug"
        if any(w in combined for w in ["?", "how", "what", "why", "when"]):
            return "question"
        
        for label in labels:
            label_lower = label.lower() if isinstance(label, str) else label.get("name", "").lower()
            if label_lower in self.comment_templates:
                return label_lower
        
        return "enhancement"
    
    def _generate_comment(self, comment_type: str, issue: Dict[str, Any]) -> str:
        """Generate the comment message"""
        template = self.comment_templates.get(comment_type, self.comment_templates["enhancement"])
        
        return f"""{template}

---
*This is an automated comment from GitHub AI Agent.*
**Issue:** {issue.get('title', 'N/A')}
**Labels:** {', '.join(issue.get('labels', []))}
"""


AutoCommentOnIssue = AutoCommentOnIssuePlugin
