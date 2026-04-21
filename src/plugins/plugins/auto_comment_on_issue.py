#!/usr/bin/env python3
"""Issue auto-comment plugin."""

from __future__ import annotations

from typing import Any, Dict, List

from .base import BasePlugin, PluginResult


class AutoCommentOnIssuePlugin(BasePlugin):
    name = "auto_comment_on_issue"
    version = "1.0.0"
    triggers = ["issue.opened", "issue.created"]
    
    AUTO_REPLIES = {
        "bug": "Thanks for reporting this bug! We will investigate and get back to you soon.",
        "question": "Thanks for your question! We will review and respond soon.",
        "enhancement": "Thanks for the enhancement suggestion! We will review it shortly.",
        "feature": "Thanks for the feature request! We will consider it for future releases.",
    }
    
    def should_run(self, event: Dict[str, Any]) -> bool:
        return event.get("type") == "issue" or "issue" in event
    
    def validate(self, context: Dict[str, Any]) -> bool:
        issue = context.get("issue", {})
        return "title" in issue or "body" in issue
    
    def matches_trigger(self, trigger: str) -> bool:
        if not self.triggers:
            return True
        if not trigger:
            return True
        if trigger in self.triggers:
            return True
        if trigger.startswith("issue."):
            return True
        return True
    
    def run(self, event: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        issue = context.get("issue", {})
        labels = [label.lower() for label in issue.get("labels", [])]
        action = issue.get("action", "opened")
        
        reply = None
        for label, message in self.AUTO_REPLIES.items():
            if label in labels:
                reply = message
                break
        
        if not reply:
            reply = "Thanks for opening this issue! We will review it and respond soon."
        
        if action == "opened":
            return [{
                "plugin": self.name,
                "action": "auto_comment",
                "comment": reply,
            }]
        return []
    
    async def execute(self, context: Dict[str, Any]) -> PluginResult:
        """Execute auto comment on issue."""
        if not self.validate(context):
            return PluginResult(
                success=False,
                action="validate",
                message="Invalid context for auto comment",
                plugin=self.name
            )
        
        issue = context.get("issue", {})
        labels = [label.lower() for label in issue.get("labels", [])]
        
        reply = None
        for label, message in self.AUTO_REPLIES.items():
            if label in labels:
                reply = message
                break
        
        if not reply:
            reply = "Thanks for opening this issue! We will review it and respond soon."
        
        return PluginResult(
            success=True,
            action="auto_comment",
            message=reply,
            data={"labels": labels},
            plugin=self.name
        )
    
    def get_info(self) -> Dict[str, Any]:
        """Get plugin info."""
        return {
            "name": self.name,
            "version": self.version,
            "enabled": self.enabled,
            "triggers": self.triggers,
            "auto_replies": list(self.AUTO_REPLIES.keys())
        }
