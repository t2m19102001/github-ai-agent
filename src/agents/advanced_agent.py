#!/usr/bin/env python3
"""Compatibility advanced agent module used by legacy tests."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def call_llm(prompt: str, provider: str = "mock") -> str:
    return f"[{provider}] {prompt[:120]}"
"""
Advanced AI Agent Framework
Enhanced agent with planning, memory, and tool execution capabilities
"""

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

try:
    from src.agents.base import Tool
except ImportError:
    Tool = object

logger = get_logger(__name__)

@dataclass
class AgentProfile:

    """Agent profile with personality and expertise"""
    name: str
    role: str
    expertise: List[str]
    personality: str
    system_prompt: str = ""
    
    def get_system_instruction(self) -> str:
        """Generate system instruction from profile"""
        if self.system_prompt:
            return self.system_prompt
        
        instruction = f"You are {self.name}, a {self.role}. "
        instruction += f"Your personality: {self.personality}. "
        
        if self.expertise:
            instruction += f"You specialize in: {', '.join(self.expertise)}. "
        
        return instruction


class MemoryStore:
    """Memory management for agent conversations"""
    
    def __init__(self, max_context_messages: int = 50):
        self.max_context_messages = max_context_messages
        self.short_term_memory: List[Dict[str, str]] = []
        self.long_term_memory: List[Dict[str, Any]] = []
    
    def add_to_short_term(self, role: str, content: str) -> None:
        """Add message to short-term memory"""
        self.short_term_memory.append({
            "role": role,
            "content": content
        })
        self._trim_short_term()
    
    def _trim_short_term(self) -> None:
        """Trim short-term memory to max size"""
        if len(self.short_term_memory) > self.max_context_messages:
            self.short_term_memory = self.short_term_memory[-self.max_context_messages:]
    
    def add_to_long_term(self, knowledge: str, metadata: Dict[str, Any] = None) -> None:
        """Add knowledge to long-term memory"""
        self.long_term_memory.append({
            "knowledge": knowledge,
            "metadata": metadata or {},
            "timestamp": self._get_timestamp()
        })
    
    def retrieve_context(self) -> str:
        """Retrieve conversation context"""
        if not self.short_term_memory:
            return ""
        
        context_parts = []
        for msg in self.short_term_memory[-10:]:
            role = msg["role"].capitalize()
            context_parts.append(f"{role}: {msg['content']}")
        
        return "\n".join(context_parts)
    
    def search_knowledge(self, query: str, top_k: int = 5) -> List[str]:
        """Search long-term knowledge"""
        results = []
        query_lower = query.lower()
        
        for item in self.long_term_memory:
            if query_lower in item["knowledge"].lower():
                results.append(item["knowledge"])
                if len(results) >= top_k:
                    break
        
        return results
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        return {
            "short_term_messages": len(self.short_term_memory),
            "long_term_knowledge": len(self.long_term_memory),
            "short_term_count": len(self.short_term_memory)
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()


class PlanningEngine:
    """Planning and reasoning engine for agents"""
    
    def __init__(self):
        self.plans: List[str] = []
        self.history: List[Dict[str, Any]] = []
    
    def decompose_goal(self, goal: str, provider: str = "default") -> List[str]:
        """Decompose a goal into steps"""
        try:
            response = call_llm(
                f"Break down this goal into clear steps: {goal}",
                provider
            )
            
            steps = []
            for line in response.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    steps.append(line.lstrip('0123456789.-) '))
            
            if not steps:
                steps = [s.strip() for s in response.split('.') if s.strip()]
            
            self.plans = steps
            return steps
            
        except Exception as e:
            logger.error(f"Error decomposing goal: {e}")
            return [goal]
    
    def chain_of_thought(self, problem: str, provider: str = "default") -> str:
        """Perform chain of thought reasoning"""
        try:
            prompt = f"""Think step by step about this problem:
            
Problem: {problem}

Provide your reasoning process:
"""
            response = call_llm(prompt, provider)
            self.history.append({"type": "cot", "problem": problem, "reasoning": response})
            return response
            
        except Exception as e:
            logger.error(f"Error in chain of thought: {e}")
            return f"Reasoning: {problem}"
    
    def self_reflection(self, solution: str, problem: str, provider: str = "default") -> str:
        """Reflect on a solution"""
        try:
            prompt = f"""Reflect on this solution:

Problem: {problem}
Solution: {solution}

Provide improvements and feedback:
"""
            response = call_llm(prompt, provider)
            self.history.append({"type": "reflection", "solution": solution, "feedback": response})
            return response
            
        except Exception as e:
            logger.error(f"Error in self reflection: {e}")
            return "Unable to reflect on solution"


class CodeExecutorTool(Tool):
    """Tool for executing code"""
    
    name = "code_executor"
    description = "Executes Python code safely"
    
    def execute(self, code: str, timeout: int = 30, **kwargs) -> Dict[str, Any]:
        """Execute Python code"""
        try:
            from src.tools.executors import PythonExecutor
            executor = PythonExecutor()
            result = executor.execute(code, timeout)
            return {
                "status": "success" if result.get("success") else "error",
                "output": result.get("output", ""),
                "error": result.get("error", ""),
                "return_code": result.get("exit_code", 0)
            }
        except Exception as e:
            return {
                "status": "error",
                "output": "",
                "error": str(e),
                "return_code": 1
            }


class FileOperationsTool(Tool):
    """Tool for file operations"""
    
    name = "file_operations"
    description = "Read, write, and manage files"
    
    def execute(self, operation: str = "read", path: str = "", content: str = "", **kwargs) -> Dict[str, Any]:
        """Perform file operations"""
        try:
            if operation == "read":
                with open(path, 'r', encoding='utf-8') as f:
                    return {"result": f.read()}
            elif operation == "write":
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return {"result": "File written successfully"}
            elif operation == "list":
                import os
                files = os.listdir(path) if path else os.listdir(".")
                return {"result": files}
            else:
                return {"result": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"error": str(e)}


class APICallTool(Tool):
    """Tool for making API calls"""
    
    name = "api_call"
    description = "Makes HTTP API requests"
    
    def execute(self, url: str = "", method: str = "GET", data: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Make API call"""
        try:
            import requests
            if method.upper() == "GET":
                response = requests.get(url, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=30)
            else:
                return {"error": f"Unsupported method: {method}"}
            
            return {
                "status_code": response.status_code,
                "response": response.text[:1000],
                "success": response.ok
            }
        except Exception as e:
            return {"error": str(e), "success": False}


class ToolKit:
    """Manages tools for agents"""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register default tools"""
        self.register_tool(CodeExecutorTool())
        self.register_tool(FileOperationsTool())
        self.register_tool(APICallTool())
    
    def register_tool(self, tool: Tool) -> None:
        """Register a tool"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all available tools"""
        return list(self.tools.keys())


class AdvancedAIAgent:
    """Advanced AI agent with planning and memory"""
    
    def __init__(self, profile: AgentProfile, llm_provider: str = "default"):
        self.profile = profile
        self.llm_provider = llm_provider
        self.memory = MemoryStore()
        self.planning_engine = PlanningEngine()
        self.toolkit = ToolKit()
        self.system_instruction = profile.get_system_instruction()
        
        logger.info(f"Initialized AdvancedAIAgent: {profile.name}")
    
    def chat(self, message: str, provider: str = None) -> str:
        """Chat with the agent"""
        self.memory.add_to_short_term("user", message)
        
        context = self.memory.retrieve_context()
        full_prompt = f"{self.system_instruction}\n\nContext:\n{context}\n\nUser: {message}\nAssistant:"
        
        response = call_llm(full_prompt, provider or self.llm_provider)
        
        self.memory.add_to_short_term("assistant", response)
        return response
    
    def execute_with_planning(self, task: str, provider: str = None) -> str:
        """Execute task with planning"""
        steps = self.planning_engine.decompose_goal(task, provider or self.llm_provider)
        
        results = []
        for i, step in enumerate(steps, 1):
            result = self.chat(f"Execute step {i}: {step}", provider)
            results.append(f"Step {i}: {result}")
        
        return "\n\n".join(results)
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "name": self.profile.name,
            "role": self.profile.role,
            "expertise": self.profile.expertise,
            "agent_name": self.profile.name,
            "agent_role": self.profile.role,
            "tools": self.toolkit.list_tools(),
            "memory_stats": self.memory.get_memory_stats()
        }


def call_llm(prompt: str, provider: str = "default") -> str:
    """Call LLM provider"""
    try:
        from src.llm.provider import get_llm_provider
        provider_instance = get_llm_provider(provider)
        
        import asyncio
        return asyncio.run(provider_instance.generate_response(prompt))
    except Exception as e:
        logger.warning(f"LLM call failed: {e}")
        return f"Response for: {prompt[:50]}..."
