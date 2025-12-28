#!/usr/bin/env python3
"""
Base Agent Class
Foundation for all AI agents in the system
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import json
import asyncio

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

try:
    from llm.provider import get_llm_provider
except ImportError:
    from src.llm.provider import get_llm_provider

logger = get_logger(__name__)


@dataclass
class AgentMessage:
    """Message structure for agent communication"""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None


@dataclass
class AgentContext:
    """Context information for agent execution"""
    session_id: str
    user_id: str
    conversation_history: List[AgentMessage]
    tools_available: List[str]
    environment: Dict[str, Any] = None


class BaseAgent(ABC):
    """Base class for all AI agents"""
    
    def __init__(self, name: str, llm_provider=None, config: Dict[str, Any] = None):
        self.name = name
        self.llm_provider = llm_provider or get_llm_provider()
        self.config = config or {}
        self.context = None
        self.tools = {}
        
        # Agent state
        self.is_active = False
        self.last_activity = None
        self.memory = {}
        
        logger.info(f"Initialized agent: {self.name}")
    
    @abstractmethod
    async def process_message(self, message: str, context: AgentContext) -> str:
        """Process incoming message and return response"""
        pass
    
    async def chat(self, prompt: str, context: Optional[AgentContext] = None) -> str:
        """Send prompt to LLM and get response"""
        try:
            # Create context if not provided
            if context is None:
                context = AgentContext(
                    session_id="default",
                    user_id="anonymous",
                    conversation_history=[],
                    tools_available=list(self.tools.keys()),
                    environment={}
                )
            
            # Add user message to history
            user_message = AgentMessage(
                role="user",
                content=prompt,
                timestamp=datetime.now()
            )
            context.conversation_history.append(user_message)
            
            # Process message
            response = await self.process_message(prompt, context)
            
            # Add assistant response to history
            assistant_message = AgentMessage(
                role="assistant", 
                content=response,
                timestamp=datetime.now()
            )
            context.conversation_history.append(assistant_message)
            
            # Update activity
            self.last_activity = datetime.now()
            
            return response
            
        except Exception as e:
            logger.error(f"Error in chat for agent {self.name}: {e}")
            return f"Error: {str(e)}"
    
    async def generate_response(self, prompt: str, system_prompt: str = None) -> str:
        """Generate response using LLM provider"""
        try:
            messages = []
            
            # Add system prompt if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Add user prompt
            messages.append({"role": "user", "content": prompt})
            
            # Generate response
            response = await self.llm_provider.generate_async(messages)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Error generating response: {str(e)}"
    
    def register_tool(self, name: str, tool_func):
        """Register a tool for the agent"""
        self.tools[name] = tool_func
        logger.info(f"Registered tool '{name}' for agent {self.name}")
    
    def get_tool(self, name: str):
        """Get a registered tool"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all available tools"""
        return list(self.tools.keys())
    
    def set_context(self, context: AgentContext):
        """Set agent context"""
        self.context = context
        self.is_active = True
    
    def clear_context(self):
        """Clear agent context"""
        self.context = None
        self.is_active = False
    
    def get_memory(self, key: str) -> Any:
        """Get value from agent memory"""
        return self.memory.get(key)
    
    def set_memory(self, key: str, value: Any):
        """Set value in agent memory"""
        self.memory[key] = value
        logger.debug(f"Set memory {key} for agent {self.name}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "name": self.name,
            "is_active": self.is_active,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "tools_count": len(self.tools),
            "memory_keys": list(self.memory.keys()),
            "config": self.config
        }
    
    def save_state(self) -> Dict[str, Any]:
        """Save agent state"""
        return {
            "name": self.name,
            "config": self.config,
            "memory": self.memory,
            "tools": list(self.tools.keys()),
            "last_activity": self.last_activity.isoformat() if self.last_activity else None
        }
    
    def load_state(self, state: Dict[str, Any]):
        """Load agent state"""
        self.config = state.get("config", {})
        self.memory = state.get("memory", {})
        if state.get("last_activity"):
            self.last_activity = datetime.fromisoformat(state["last_activity"])
        
        logger.info(f"Loaded state for agent {self.name}")
    
    async def cleanup(self):
        """Cleanup resources"""
        self.clear_context()
        self.tools.clear()
        self.memory.clear()
        logger.info(f"Cleaned up agent {self.name}")


class SimpleAgent(BaseAgent):
    """Simple implementation of BaseAgent for testing"""
    
    def __init__(self, name: str = "SimpleAgent", llm_provider=None):
        super().__init__(name, llm_provider)
        
        # Set default system prompt
        self.system_prompt = f"""You are {name}, a helpful AI assistant.
        You provide clear, concise, and accurate responses.
        Always be helpful and professional."""
    
    async def process_message(self, message: str, context: AgentContext) -> str:
        """Process message with simple logic"""
        # Add context to prompt
        context_info = ""
        if context.conversation_history:
            recent_messages = context.conversation_history[-3:]  # Last 3 messages
            context_info = "\nRecent conversation:\n"
            for msg in recent_messages:
                context_info += f"{msg.role}: {msg.content}\n"
        
        full_prompt = f"{context_info}\nUser: {message}\nAssistant:"
        
        # Generate response
        response = await self.generate_response(message, self.system_prompt)
        
        return response


# Factory function
def create_agent(agent_type: str, name: str, config: Dict[str, Any] = None) -> BaseAgent:
    """Factory function to create agents"""
    if agent_type == "simple":
        return SimpleAgent(name)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


# Test function
async def test_base_agent():
    """Test base agent functionality"""
    agent = SimpleAgent("TestAgent")
    
    # Test basic chat
    response = await agent.chat("Hello, how are you?")
    print(f"Agent response: {response}")
    
    # Test with context
    context = AgentContext(
        session_id="test_session",
        user_id="test_user",
        conversation_history=[],
        tools_available=[]
    )
    
    response = await agent.chat("What's my session ID?", context)
    print(f"Context response: {response}")
    
    # Test status
    status = agent.get_status()
    print(f"Agent status: {json.dumps(status, indent=2)}")
    
    await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(test_base_agent())
