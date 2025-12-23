from typing import Dict, Any
from src.agent.plugins.base import AgentPluginBase
from src.tools.git_tool import git_create_branch, git_commit


class AutoCreatePRPlugin(AgentPluginBase):
    name = "auto_create_pr"
    description = "Create a PR scaffold when instructed"

    def matches(self, event: Dict[str, Any]) -> bool:
        return event.get("type") == "command" and event.get("command") == "create_pr"

    def run(self, event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        branch = event.get("branch", "feature/auto-pr")
        message = event.get("message", "AI scaffolds PR")
        res_branch = git_create_branch(branch)
        res_commit = git_commit(message)
        ok = res_branch.get("success") and res_commit.get("success")
        note = "✅ Created branch and commit" if ok else f"❌ Error: {res_branch.get('error') or res_commit.get('error')}"
        return {"action": "note", "note": note}

