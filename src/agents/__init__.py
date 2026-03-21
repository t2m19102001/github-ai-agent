"""
Agents module - AI agents
Unified exports for all agent-related classes
"""

from src.agents.base import Tool, Executor

try:
    from src.agents.base_agent import BaseAgent, AgentContext, AgentMessage, SimpleAgent
    Agent = BaseAgent
except ImportError:
    from src.agents.base import Agent as Agent

from src.agents.code_agent import CodeChatAgent
from src.agents.github_issue_agent import GitHubIssueAgent
from src.agents.doc_agent import DocumentationAgent

try:
    from src.agents.image_agent import ImageAgent
except (ImportError, ModuleNotFoundError):
    ImageAgent = None

__all__ = [
    "Agent",
    "BaseAgent", 
    "Tool", 
    "Executor",
    "AgentContext",
    "AgentMessage",
    "SimpleAgent",
    "CodeChatAgent",
    "GitHubIssueAgent",
    "DocumentationAgent",
    "ImageAgent",
]
