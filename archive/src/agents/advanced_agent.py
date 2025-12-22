#!/usr/bin/env python3
"""
Advanced AI-Agent Framework - Chuẩn quốc tế
Gồm 4 thành phần chính: Brain, Memory, Planning, Tools
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import re
from abc import ABC, abstractmethod

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# 1. THE BRAIN (Profiling) - Định hình nhân cách và vai trò của Agent
# ============================================================================

@dataclass
class AgentProfile:
    """Định nghĩa nhân cách và vai trò của Agent"""
    name: str
    role: str  # "Python Expert", "DevOps Engineer", "Product Manager", etc.
    expertise: List[str]  # ["Python", "Docker", "AWS", ...]
    personality: str  # "Professional", "Friendly", "Detailed", "Concise"
    system_prompt: str  # Prompt hệ thống định hình hành vi
    
    def get_system_instruction(self) -> str:
        """Tạo instruction hệ thống chi tiết"""
        return f"""You are {self.name}, a {self.role}.

Expertise: {', '.join(self.expertise)}
Personality: {self.personality}

{self.system_prompt}

Important:
- Provide accurate, actionable advice
- Explain your reasoning clearly
- Suggest improvements when appropriate
- Ask clarifying questions if needed
- Consider edge cases and potential issues
"""


# ============================================================================
# 2. MEMORY SYSTEM - Bộ nhớ ngắn hạn & dài hạn
# ============================================================================

class MemoryStore:
    """Quản lý bộ nhớ - Short-term (Context) + Long-term (RAG)"""
    
    def __init__(self, max_context_messages: int = 20):
        self.short_term_memory: List[Dict[str, str]] = []  # Conversation context
        self.long_term_memory: List[Dict[str, Any]] = []  # Knowledge base
        self.max_context_messages = max_context_messages
        
    def add_to_short_term(self, role: str, content: str) -> None:
        """Lưu vào trí nhớ ngắn hạn (Context window)"""
        self.short_term_memory.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Giữ chỉ những tin nhắn gần nhất để tránh tràn context
        if len(self.short_term_memory) > self.max_context_messages:
            self.short_term_memory = self.short_term_memory[-self.max_context_messages:]
            logger.info(f"Trimmed short-term memory to {self.max_context_messages} messages")
    
    def add_to_long_term(self, knowledge: str, metadata: Dict[str, Any] = None) -> None:
        """Lưu vào trí nhớ dài hạn (Knowledge base)"""
        self.long_term_memory.append({
            "knowledge": knowledge,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
            "embedding_vector": None  # For future RAG implementation
        })
    
    def retrieve_context(self, query: str = None) -> str:
        """Truy xuất context từ short-term memory"""
        if not self.short_term_memory:
            return ""
        
        context = "\nPrevious Conversation Context:\n"
        for msg in self.short_term_memory[-5:]:  # Last 5 messages
            context += f"{msg['role'].upper()}: {msg['content']}\n"
        return context
    
    def search_knowledge(self, query: str, top_k: int = 3) -> List[str]:
        """Tìm kiếm kiến thức liên quan (RAG - Retrieval Augmented Generation)"""
        if not self.long_term_memory:
            return []
        
        # Simple keyword matching (Future: use semantic search with embeddings)
        results = []
        query_words = set(query.lower().split())
        
        for item in self.long_term_memory:
            knowledge_words = set(item['knowledge'].lower().split())
            score = len(query_words & knowledge_words)
            if score > 0:
                results.append((item['knowledge'], score))
        
        # Sort by relevance score and return top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in results[:top_k]]
    
    def get_memory_stats(self) -> Dict[str, int]:
        """Thống kê bộ nhớ"""
        return {
            "short_term_messages": len(self.short_term_memory),
            "long_term_knowledge": len(self.long_term_memory),
            "max_context": self.max_context_messages
        }


# ============================================================================
# 3. PLANNING & REASONING - Lập kế hoạch & Tự phản biện
# ============================================================================

class PlanningEngine:
    """Engine để phân rã mục tiêu, lập kế hoạch và tự phản biện"""
    
    @staticmethod
    def decompose_goal(goal: str, llm_provider) -> List[str]:
        """Phân rã một mục tiêu lớn thành các bước nhỏ (Goal Decomposition)"""
        prompt = f"""Break down this complex goal into 3-5 specific, actionable steps:

Goal: {goal}

Provide steps in a clear format. Each step should be:
1. Specific and measurable
2. Achievable independently
3. Logically ordered

Format:
Step 1: [action]
Step 2: [action]
...
"""
        response = llm_provider.call(prompt)
        
        # Parse response to extract steps
        steps = []
        lines = response.split('\n')
        for line in lines:
            if line.strip().startswith(('Step', 'step', '1:', '2:', '3:')):
                # Clean up the step
                step = re.sub(r'^(Step\s*\d+:|^\d+:)', '', line).strip()
                if step:
                    steps.append(step)
        
        return steps if steps else [goal]  # Fallback
    
    @staticmethod
    def chain_of_thought(problem: str, llm_provider) -> Dict[str, str]:
        """Chain of Thought - Hiển thị quá trình suy luận từng bước"""
        prompt = f"""Solve this problem step by step, showing your reasoning:

Problem: {problem}

Please think through:
1. What is the core issue?
2. What information do we have?
3. What are the possible approaches?
4. What is the best solution?
5. Why is this the best approach?

Format your answer clearly with each step numbered.
"""
        response = llm_provider.call(prompt)
        
        return {
            "problem": problem,
            "reasoning": response,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def self_reflection(solution: str, problem: str, llm_provider) -> Dict[str, Any]:
        """Self-Reflection - Tự kiểm tra và cải thiện kết quả"""
        prompt = f"""Review this solution and identify potential improvements:

Original Problem: {problem}

Proposed Solution:
{solution}

Please analyze:
1. Are there any logical flaws?
2. Are there edge cases not covered?
3. Could this be simplified?
4. What are the potential issues?
5. How can this be improved?

Provide a detailed analysis and suggestions for improvement.
"""
        response = llm_provider.call(prompt)
        
        return {
            "original_solution": solution,
            "analysis": response,
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# 4. TOOLS & ACTIONS - "Đôi tay" cho phép Agent tương tác thế giới
# ============================================================================

class Tool(ABC):
    """Base class cho tất cả các Tool"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Thực thi tool"""
        pass
    
    def get_info(self) -> Dict[str, str]:
        """Mô tả tool"""
        return {
            "name": self.name,
            "description": self.description
        }


class CodeExecutorTool(Tool):
    """Tool để thực thi code Python"""
    
    def __init__(self):
        super().__init__(
            "code_executor",
            "Execute Python code and return results"
        )
    
    def execute(self, code: str) -> Dict[str, Any]:
        """Thực thi code an toàn"""
        import subprocess
        import tempfile
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Execute
            result = subprocess.run(
                ['python3', temp_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return {
                "status": "success",
                "output": result.stdout,
                "error": result.stderr,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Execution timeout (>10s)"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


class FileOperationsTool(Tool):
    """Tool để đọc/ghi file"""
    
    def __init__(self):
        super().__init__(
            "file_operations",
            "Read and write files"
        )
    
    def execute(self, operation: str, file_path: str, content: str = None) -> Dict[str, Any]:
        """Thực hiện thao tác file"""
        try:
            if operation == "read":
                with open(file_path, 'r') as f:
                    return {
                        "status": "success",
                        "operation": "read",
                        "content": f.read()
                    }
            elif operation == "write":
                with open(file_path, 'w') as f:
                    f.write(content)
                return {
                    "status": "success",
                    "operation": "write",
                    "file": file_path
                }
            else:
                return {"status": "error", "error": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


class APICallTool(Tool):
    """Tool để gọi API bên ngoài"""
    
    def __init__(self):
        super().__init__(
            "api_call",
            "Call external APIs"
        )
    
    def execute(self, url: str, method: str = "GET", headers: Dict = None, 
                data: Dict = None) -> Dict[str, Any]:
        """Gọi API"""
        import requests
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=10)
            else:
                return {"status": "error", "error": f"Unsupported method: {method}"}
            
            return {
                "status": "success",
                "status_code": response.status_code,
                "data": response.json() if response.headers.get('content-type') == 'application/json' else response.text
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


class ToolKit:
    """Tập hợp tất cả các Tool mà Agent có thể sử dụng"""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {
            "code_executor": CodeExecutorTool(),
            "file_operations": FileOperationsTool(),
            "api_call": APICallTool()
        }
    
    def register_tool(self, tool: Tool) -> None:
        """Đăng ký một Tool mới"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Lấy một Tool"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, str]]:
        """Liệt kê tất cả Tool"""
        return [tool.get_info() for tool in self.tools.values()]
    
    def execute_tool(self, name: str, *args, **kwargs) -> Any:
        """Thực thi một Tool"""
        tool = self.get_tool(name)
        if not tool:
            return {"status": "error", "error": f"Tool not found: {name}"}
        
        logger.info(f"Executing tool: {name}")
        return tool.execute(*args, **kwargs)


# ============================================================================
# ADVANCED AI-AGENT - Kết hợp tất cả 4 thành phần
# ============================================================================

class AdvancedAIAgent:
    """
    Advanced AI-Agent theo chuẩn quốc tế
    Gồm: Brain + Memory + Planning + Tools
    """
    
    def __init__(self, profile: AgentProfile, llm_provider):
        self.profile = profile
        self.llm_provider = llm_provider
        self.memory = MemoryStore()
        self.planning_engine = PlanningEngine()
        self.toolkit = ToolKit()
        
        logger.info(f"✅ Initialized Advanced AI-Agent: {profile.name}")
    
    def chat(self, user_input: str) -> str:
        """
        Main chat interface - Đơn giản nhưng có đủ 4 thành phần
        """
        # 1. Add to short-term memory
        self.memory.add_to_short_term("user", user_input)
        
        # 2. Search for relevant knowledge
        relevant_knowledge = self.memory.search_knowledge(user_input)
        
        # 3. Build prompt with context
        context = self.memory.retrieve_context(user_input)
        knowledge_context = "\nRelevant Knowledge:\n" + "\n".join(relevant_knowledge) if relevant_knowledge else ""
        
        full_prompt = f"""{self.profile.get_system_instruction()}

{context}
{knowledge_context}

USER: {user_input}

Please provide a helpful response."""
        
        # 4. Get response from Brain (LLM)
        response = self.llm_provider.call(full_prompt)
        
        # 5. Add response to memory
        self.memory.add_to_short_term("assistant", response)
        
        # 6. Save to long-term memory (knowledge)
        self.memory.add_to_long_term(f"Q: {user_input}\nA: {response}")
        
        return response
    
    def execute_with_planning(self, task: str) -> Dict[str, Any]:
        """
        Execute task với planning - Phân rã mục tiêu & tự phản biện
        """
        logger.info(f"🎯 Starting task with planning: {task}")
        
        # 1. Decompose goal
        steps = self.planning_engine.decompose_goal(task, self.llm_provider)
        logger.info(f"📋 Decomposed into {len(steps)} steps")
        
        # 2. Execute each step
        results = []
        for i, step in enumerate(steps, 1):
            logger.info(f"Step {i}: {step}")
            result = self.chat(step)
            results.append({
                "step": i,
                "action": step,
                "result": result
            })
        
        # 3. Combine results
        combined_result = "\n".join([f"Step {r['step']}: {r['result']}" for r in results])
        
        # 4. Self-reflection - Kiểm tra kết quả
        reflection = self.planning_engine.self_reflection(
            combined_result, task, self.llm_provider
        )
        
        return {
            "task": task,
            "steps": steps,
            "results": results,
            "combined_result": combined_result,
            "reflection": reflection,
            "memory_stats": self.memory.get_memory_stats()
        }
    
    def execute_code_task(self, description: str, code: str) -> Dict[str, Any]:
        """
        Execute task có liên quan đến code
        """
        logger.info(f"🔧 Executing code task: {description}")
        
        # Execute code
        execution_result = self.toolkit.execute_tool("code_executor", code)
        
        # Add to memory
        self.memory.add_to_short_term("system", f"Code execution: {description}")
        
        return {
            "description": description,
            "code": code,
            "execution_result": execution_result
        }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Lấy trạng thái hiện tại của Agent"""
        return {
            "agent_name": self.profile.name,
            "agent_role": self.profile.role,
            "memory_stats": self.memory.get_memory_stats(),
            "available_tools": self.toolkit.list_tools(),
            "expertise": self.profile.expertise
        }
