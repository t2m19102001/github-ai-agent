"""
Agents module - AI agents
Unified exports for all agent-related classes

Architecture:
- base.py: Tool, Executor, Agent (backward compat)
- base_agent.py: BaseAgent, AgentContext, AgentMessage (async support)
"""
from src.agents.base import Agent, Tool, Executor


def __getattr__(name):
    """Lazy exports to avoid circular imports during package initialization."""
    if name == "CodeChatAgent":
        from src.plugins.code_agent import CodeChatAgent

        return CodeChatAgent
    raise AttributeError(f"module 'src.agents' has no attribute {name!r}")

__all__ = ["CodeChatAgent", "Agent", "Tool", "Executor"]
