from typing import Dict, Any
from src.agent.plugins.base import AgentPluginBase


class AutoCommentOnIssuePlugin(AgentPluginBase):
    name = "auto_comment_on_issue"
    description = "Post helpful auto comment on issues with specific labels"

    def matches(self, event: Dict[str, Any]) -> bool:
        return event.get("type") == "issue" and any(l in (event.get("labels") or []) for l in ["question", "discussion"])

    def run(self, event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        comment = (
            "## 🤖 Auto Reply\n\n"
            "Cảm ơn bạn đã tạo issue! Team sẽ sớm phản hồi.\n\n"
            "Trong lúc chờ, vui lòng cung cấp thêm: steps to reproduce, expected vs actual, logs."
        )
        return {"action": "comment", "comment": comment}

