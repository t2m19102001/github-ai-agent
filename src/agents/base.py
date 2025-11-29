#!/usr/bin/env python3
"""
Base classes and interfaces for agents
Abstract base classes that all agents should inherit from
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class Tool(ABC):
    """Base class for tools that agents can use"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute the tool"""
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"


class Agent(ABC):
    """Base class for AI agents"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.tools: List[Tool] = []
        self.conversation_history: List[Dict[str, str]] = []
    
    def register_tool(self, tool: Tool) -> None:
        """Register a tool for this agent"""
        self.tools.append(tool)
        logger.info(f"✅ Tool registered: {tool.name}")
    
    @abstractmethod
    def think(self, prompt: str) -> str:
        """Think/analyze the prompt"""
        pass
    
    @abstractmethod
    def act(self, action: str) -> Any:
        """Execute an action"""
        pass
    
    def run(self, user_input: str) -> str:
        """Main run loop"""
        # Store in history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Think about the input
        response = self.think(user_input)
        
        # Store response
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
    
    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model
    
    @abstractmethod
    def call(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """
        Call the LLM
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            LLM response or None if failed
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, model={self.model})"
