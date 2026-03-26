#!/usr/bin/env python3
"""Issue auto-comment plugin."""

from __future__ import annotations

from typing import Any, Dict, List

from .base import PluginBase


class AutoCommentOnIssuePlugin(PluginBase):
    name = "auto_comment_on_issue"

    def should_run(self, event: Dict[str, Any]) -> bool:
        return event.get("type") == "issue"

    def run(self, event: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        labels = [label.lower() for label in event.get("labels", [])]
        if "question" in labels:
            return [{
                "plugin": self.name,
                "action": "comment",
                "comment": "Auto Reply: Thanks for your question. We will review and respond soon.",
            }]
        return []
