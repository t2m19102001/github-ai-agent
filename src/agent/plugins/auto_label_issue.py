#!/usr/bin/env python3
"""
Auto Label Issue Plugin
Automatically labels GitHub issues based on content analysis
"""

from typing import Any, Dict, List

from .base import BasePlugin, PluginResult


class AutoLabelIssuePlugin(BasePlugin):
    """Plugin that automatically labels GitHub issues"""
    
    name = "auto_label_issue"
    version = "1.0.0"
    triggers = ["issue.opened", "issue.edited", "pull_request.opened"]
    enabled = True
    
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
    
    def should_run(self, event: Dict[str, Any]) -> bool:
        return "issue" in event or "pull_request" in event
    
    def validate(self, context: Dict[str, Any]) -> bool:
        """Check if this plugin should run"""
        return bool(context.get("issue") or context.get("pull_request"))
    
    async def execute(self, context: Dict[str, Any]) -> PluginResult:
        """Execute auto-label logic"""
        try:
            issue = context.get("issue") or context.get("pull_request", {})
            title = issue.get("title", "").lower()
            body = issue.get("body", "").lower()
            content = f"{title} {body}"
            
            suggested_labels = self._analyze_content(content)
            
            return PluginResult(
                success=True,
                action="auto_label",
                message=f"Suggested {len(suggested_labels)} labels",
                data={
                    "issue_number": issue.get("number"),
                    "labels_suggested": suggested_labels
                },
                plugin=self.name
            )
            
        except Exception as e:
            return PluginResult(
                success=False,
                action="auto_label",
                message=f"Labeling failed: {str(e)}",
                plugin=self.name
            )
    
    def _analyze_content(self, content: str) -> List[str]:
        """Analyze content and suggest labels"""
        scores = {}
        
        for label, rules in self.label_rules.items():
            score = sum(1 for kw in rules["keywords"] if kw in content)
            if score > 0:
                scores[label] = score
        
        sorted_labels = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        suggestions = [label for label, _ in sorted_labels[:3]]
        
        return suggestions if suggestions else ["question"]
    
    def get_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "enabled": self.enabled,
            "triggers": self.triggers,
            "label_rules": list(self.label_rules.keys())
        }


AutoLabelIssue = AutoLabelIssuePlugin
