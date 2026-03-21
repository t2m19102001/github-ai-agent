"""
Agents module - AI agents
Unified exports for all agent-related classes

Architecture:
- base.py: Tool, Executor, Agent (backward compat)
- base_agent.py: BaseAgent, AgentContext, AgentMessage (async support)
"""

from src.agents.base import Tool, Executor, Agent

try:
    from src.agents.base_agent import (
        BaseAgent,
        AgentContext,
        AgentMessage,
        SimpleAgent,
        create_agent
    )
except ImportError:
    BaseAgent = Agent
    AgentContext = None
    AgentMessage = None
    SimpleAgent = None
    create_agent = None

from src.agents.code_agent import CodeChatAgent
from src.agents.github_issue_agent import GitHubIssueAgent
from src.agents.doc_agent import DocumentationAgent
from src.agents.image_agent import ImageAgent
from src.agents.test_agent import TestGenerationAgent
from src.agents.advanced_agent import AdvancedAIAgent

try:
    from src.agents.pr_agent import GitHubPRAgent
except ImportError:
    GitHubPRAgent = None

try:
    from src.agents.orchestrator import MultiAgentOrchestrator
except ImportError:
    MultiAgentOrchestrator = None

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
    "TestGenerationAgent",
    "AdvancedAIAgent",
    "GitHubPRAgent",
    "MultiAgentOrchestrator",
    "create_agent",
]
