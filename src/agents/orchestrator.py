from typing import Dict, Any
from src.agents.base import LLMProvider


class PlannerAgent:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def plan(self, payload: Dict[str, Any]) -> str:
        title = str(payload.get("title") or payload.get("issue", {}).get("title") or "")
        return f"Plan: analyze '{title}' and propose changes"


class CoderAgent:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def code(self, payload: Dict[str, Any]) -> str:
        return "CodeChanges: placeholder"


class ReviewerAgent:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def review(self, payload: Dict[str, Any]) -> str:
        title = str(payload.get("title") or payload.get("pull_request", {}).get("title") or "")
        return f"Review: '{title}' looks acceptable"


class Orchestrator:
    def __init__(self, llm_provider: LLMProvider):
        self.planner = PlannerAgent(llm_provider)
        self.coder = CoderAgent(llm_provider)
        self.reviewer = ReviewerAgent(llm_provider)

    def handle_issue_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        plan = self.planner.plan(payload)
        return {"plan": plan}

    def handle_pull_request_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        plan = self.planner.plan(payload)
        code = self.coder.code(payload)
        review = self.reviewer.review(payload)
        return {"plan": plan, "code_changes": code, "review": review}
