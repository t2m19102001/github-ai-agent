#!/usr/bin/env python3
"""
Auto Label Issue Plugin
Automatically labels GitHub issues based on content analysis
"""

from typing import Dict, Any
from src.agent.plugins.base import BasePlugin, PluginConfig, PluginResult

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class AutoLabelIssuePlugin(BasePlugin):
    """Plugin that automatically labels GitHub issues"""
    
    name = "auto_label_issue"
    version = "1.0.0"
    description = "Automatically labels issues based on content"
    triggers = ["issue.opened", "issue.edited", "pull_request.opened"]
    
    label_rules = {
        "bug": {
            "keywords": ["bug", "error", "crash", "fail", "broken", "issue", "wrong", "incorrect"],
            "priority": 10
        },
        "enhancement": {
            "keywords": ["feature", "enhancement", "improvement", "optimize", "refactor", "better"],
            "priority": 20
        },
        "security": {
            "keywords": ["security", "vulnerability", "exploit", "injection", "xss", "csrf"],
            "priority": 5
        },
        "documentation": {
            "keywords": ["docs", "documentation", "readme", "comment", "docstring"],
            "priority": 30
        },
        "question": {
            "keywords": ["how", "what", "why", "when", "?", "question", "help"],
            "priority": 40
        },
        "good first issue": {
            "keywords": ["easy", "starter", "beginner", "simple", "intro"],
            "priority": 50
        }
    }
    
    def __init__(self):
        config = PluginConfig(
            name=self.name,
            enabled=True,
            priority=60
        )
        super().__init__(config)
    
    def validate(self, context: Dict[str, Any]) -> bool:
        """Check if this plugin should run"""
        return context.get("issue") or context.get("pull_request")
    
    async def execute(self, context: Dict[str, Any]) -> PluginResult:
        """Execute auto-label logic"""
        try:
            issue = context.get("issue") or context.get("pull_request", {})
            title = issue.get("title", "").lower()
            body = issue.get("body", "").lower()
            content = f"{title} {body}"
            
            suggested_labels = self._analyze_content(content)
            
            github_client = context.get("github_client")
            if github_client:
                repo = issue.get("repo", "owner/repo")
                issue_number = issue.get("number", 0)
                
                try:
                    repo_obj = github_client.get_repo(repo)
                    issue_obj = repo_obj.get_issue(issue_number)
                    
                    for label in suggested_labels:
                        try:
                            issue_obj.add_to_labels(label)
                        except Exception:
                            pass
                    
                    logger.info(f"Added labels to issue #{issue_number}: {suggested_labels}")
                except Exception as e:
                    logger.warning(f"Could not add labels: {e}")
            
            return PluginResult(
                success=True,
                action="auto_label",
                message=f"Suggested {len(suggested_labels)} labels",
                data={
                    "issue_number": issue.get("number"),
                    "labels_suggested": suggested_labels
                }
            )
            
        except Exception as e:
            logger.error(f"Auto-label failed: {e}")
            return PluginResult(
                success=False,
                action="auto_label",
                message=f"Labeling failed: {str(e)}"
            )
    
    def _analyze_content(self, content: str) -> list:
        """Analyze content and suggest labels"""
        suggestions = []
        scores = {}
        
        for label, rules in self.label_rules.items():
            score = sum(1 for kw in rules["keywords"] if kw in content)
            if score > 0:
                scores[label] = score
        
        sorted_labels = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        suggestions = [label for label, _ in sorted_labels[:3]]
        
        return suggestions if suggestions else ["question"]


AutoLabelIssue = AutoLabelIssuePlugin
