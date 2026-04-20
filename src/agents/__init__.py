"""
Agents module - AI agents
"""
from src.agents.base import Agent, Tool, Executor


def __getattr__(name):
    """Lazy exports to avoid circular imports during package initialization."""
    if name == "CodeChatAgent":
        from src.agents.code_agent import CodeChatAgent

        return CodeChatAgent
    raise AttributeError(f"module 'src.agents' has no attribute {name!r}")

__all__ = ["CodeChatAgent", "Agent", "Tool", "Executor"]
