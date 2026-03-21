#!/usr/bin/env python3
"""
Base classes and interfaces for agents
Abstract base classes that all agents should inherit from

NOTE: This module is kept for backward compatibility.
New code should use src.agents.base_agent instead.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class Tool(ABC):
    """Base class for tools that agents can use"""
    
    name: str = "Tool"
    description: str = "Base tool"
    
    def __init__(self, name: str = None, description: str = None):
        if name:
            self.name = name
        if description:
            self.description = description
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute the tool"""
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"


class Executor(ABC):
    """Base class for code/command executors"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def execute(self, code: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Execute code/command
        
        Returns:
            {
                "success": bool,
                "output": str,
                "error": str,
                "exit_code": int
            }
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"


class LLMProvider(ABC):
    """Base class for LLM providers"""
    
    def __init__(self, name: str, model: str = ""):
        self.name = name
        self.model = model
    
    @abstractmethod
    def call(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """Call the LLM"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, model={self.model})"


try:
    from src.agents.base_agent import BaseAgent
except ImportError:
    BaseAgent = None


class Agent(BaseAgent if BaseAgent else ABC):
    """Base class for AI agents (sync wrapper around BaseAgent)
    
    DEPRECATED: Use src.agents.base_agent.BaseAgent instead.
    This class is kept for backward compatibility.
    """
    
    def __init__(self, name: str, description: str = ""):
        if BaseAgent:
            super().__init__(name=name, llm_provider=None)
        else:
            self.name = name
            self.description = description
            self.tools: List[Tool] = []
            self.conversation_history: List[Dict[str, str]] = []
    
    def think(self, prompt: str) -> str:
        """Think/analyze the prompt (sync version)"""
        return f"Response for: {prompt[:50]}..."
    
    def act(self, action: str) -> Any:
        """Execute an action (sync version)"""
        return {"action": action, "status": "executed"}
    
    def register_tool(self, tool: Tool) -> None:
        """Register a tool for this agent"""
        if BaseAgent:
            super().register_tool(tool.name, tool)
        else:
            self.tools.append(tool)
        logger.info(f"✅ Tool registered: {tool.name}")
    
    def run(self, user_input: str) -> str:
        """Main run loop (sync version)"""
        self.conversation_history.append({"role": "user", "content": user_input})
        response = self.think(user_input)
        self.conversation_history.append({"role": "assistant", "content": response})
        return response
    
    def get_tools_description(self) -> str:
        """Get description of all available tools"""
        if not self.tools:
            return "No tools available"
        
        descriptions = []
        for tool in self.tools:
            descriptions.append(f"- {tool.name}: {tool.description}")
        
        return "\n".join(descriptions)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, tools={len(self.tools)})"


__all__ = ["Tool", "Executor", "Agent", "BaseAgent", "LLMProvider"]
