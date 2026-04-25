#!/usr/bin/env python3
"""Compatibility advanced agent module used by legacy tests."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def call_llm(prompt: str, provider: str = "mock") -> str:
    return f"[{provider}] {prompt[:120]}"


@dataclass
class AgentProfile:
    name: str
    role: str
    expertise: List[str]
    personality: str
    system_prompt: str

    def get_system_instruction(self) -> str:
        if self.system_prompt:
            return self.system_prompt
        expertise = ", ".join(self.expertise) if self.expertise else "general reasoning"
        return f"You are {self.name}, a {self.role} expert in {expertise}. {self.personality}".strip()


class MemoryStore:
    def __init__(self, max_context_messages: int = 10):
        self.max_context_messages = max_context_messages
        self.short_term_memory: List[Dict[str, str]] = []
        self.long_term_memory: List[Dict[str, Any]] = []

    def add_to_short_term(self, role: str, content: str) -> None:
        self.short_term_memory.append({"role": role, "content": content})
        if len(self.short_term_memory) > self.max_context_messages:
            self.short_term_memory = self.short_term_memory[-self.max_context_messages :]

    def add_to_long_term(self, knowledge: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.long_term_memory.append({"knowledge": knowledge, "metadata": metadata or {}})

    def retrieve_context(self) -> str:
        return "\n".join(f"{m['role']}: {m['content']}" for m in self.short_term_memory)

    def search_knowledge(self, query: str, top_k: int = 3) -> List[str]:
        q = query.lower()
        found = [m["knowledge"] for m in self.long_term_memory if q in m["knowledge"].lower()]
        return found[:top_k]

    def get_memory_stats(self) -> Dict[str, int]:
        return {
            "short_term_messages": len(self.short_term_memory),
            "long_term_knowledge": len(self.long_term_memory),
            "short_term_count": len(self.short_term_memory),
            "long_term_count": len(self.long_term_memory),
        }


class PlanningEngine:
    def decompose_goal(self, goal: str, llm_provider: str) -> List[str]:
        response = call_llm(f"Decompose goal into steps: {goal}", llm_provider)
        lines = [line.strip(" -") for line in response.splitlines() if line.strip()]
        return lines or [f"Analyze: {goal}", "Plan", "Implement", "Validate"]

    def chain_of_thought(self, prompt: str, llm_provider: str) -> str:
        return call_llm(f"Reason step by step: {prompt}", llm_provider)

    def self_reflection(self, solution: str, problem: str, llm_provider: str) -> str:
        return call_llm(f"Reflect on solution '{solution}' for '{problem}'", llm_provider)


class Tool:
    name = "tool"
    description = "base tool"

    def execute(self, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "result": kwargs}


class CodeExecutorTool(Tool):
    name = "code_executor"
    description = "Run Python snippets safely for tests"

    def execute(self, code: str) -> Dict[str, Any]:
        python_exe = sys.executable
        result = subprocess.run([python_exe, "-c", code], capture_output=True, text=True)
        if result.returncode == 0:
            return {"status": "success", "output": result.stdout, "return_code": result.returncode}
        return {
            "status": "error",
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode,
        }


class FileOperationsTool(Tool):
    name = "file_operations"
    description = "Read and write files"

    def execute(self, operation: str, path: str, content: str = "") -> Dict[str, Any]:
        if operation == "read":
            with open(path, "r", encoding="utf-8") as f:
                return {"status": "success", "result": f.read()}
        if operation == "write":
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"status": "success", "result": "written"}
        return {"status": "error", "result": f"Unknown operation: {operation}"}


class APICallTool(Tool):
    name = "api_call"
    description = "Mock API call"

    def execute(self, url: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "success", "method": method, "url": url, "payload": payload or {}}


class ToolList(list):
    """List wrapper allowing membership checks by tool name."""

    def __contains__(self, item: object) -> bool:
        if isinstance(item, str):
            return any(isinstance(entry, dict) and entry.get("name") == item for entry in self)
        return super().__contains__(item)

    def names(self) -> List[str]:
        return [
            entry["name"]
            for entry in self
            if isinstance(entry, dict) and "name" in entry
        ]


class ToolKit:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def list_tools(self) -> List[Any]:
        tools = ToolList()
        for name, tool in self.tools.items():
            tools.append({"name": name, "description": tool.description})
        return tools


class AdvancedAIAgent:
    def __init__(self, profile: AgentProfile, llm_provider: str = "mock"):
        self.profile = profile
        self.llm_provider = llm_provider
        self.memory = MemoryStore()
        self.planner = PlanningEngine()
        self.toolkit = ToolKit()
        self.toolkit.register_tool(CodeExecutorTool())
        self.toolkit.register_tool(FileOperationsTool())

    def chat(self, message: str, llm_provider: Optional[str] = None) -> str:
        provider = llm_provider or self.llm_provider
        self.memory.add_to_short_term("user", message)
        response = call_llm(f"{self.profile.get_system_instruction()}\n\nUser: {message}", provider)
        self.memory.add_to_short_term("assistant", response)
        return response

    def execute_with_planning(self, task: str, llm_provider: Optional[str] = None) -> str:
        provider = llm_provider or self.llm_provider
        steps = self.planner.decompose_goal(task, provider)
        return "\n".join(steps)

    def get_agent_status(self) -> Dict[str, Any]:
        return {
            "name": self.profile.name,
            "role": self.profile.role,
            "expertise": self.profile.expertise,
            "agent_name": self.profile.name,
            "agent_role": self.profile.role,
            "registered_tools": self.toolkit.list_tools(),
        }
