#!/usr/bin/env python3
"""Issue auto-comment plugin."""

from __future__ import annotations

from typing import Any, Dict, List

from .base import PluginBase, PluginResult


class AutoCommentOnIssuePlugin(PluginBase):
    name = "auto_comment_on_issue"

    def should_run(self, event: Dict[str, Any]) -> bool:
        event_type = (event.get("type") or "").lower()
        return event_type in {"issue", "issues"}

    def run(self, event: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        labels = [label.lower() for label in event.get("labels", [])]
        is_question = "question" in labels or event.get("is_question") is True
        if is_question:
            return [
                PluginResult(
                    plugin=self.name,
                    action="comment",
                    comment="Auto Reply: Thanks for your question. We will review and respond soon.",
                ).to_dict()
            ]
        return []
