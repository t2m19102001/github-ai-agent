#!/usr/bin/env python3
"""
Code Chat Agent - Interactive AI code assistant
Can read, analyze, modify code, and execute commands
"""

import glob
from pathlib import Path
from typing import Optional, List
from src.agents.base import Agent, LLMProvider
from src.utils.logger import get_logger
from src.core.config import PROJECT_ROOT, CODE_EXTENSIONS
from src.config.settings import MAX_CONTEXT_TOKENS
from src.tools.tools import FileReadTool, FileWriteTool, ListFilesTool
from src.tools.codebase_rag import retrieve, get_context
from src.tools.git_tool import GitCommitTool, GitBranchTool, GitStatusTool
from src.tools.autofix_tool import AutoFixTool, PytestTool
from src.memory import save_memory, get_memory
from src.utils.token_manager import TokenManager
import uuid

logger = get_logger(__name__)


class CodeChatAgent(Agent):
    """AI agent for code chat and analysis"""
    
    def __init__(self, llm_provider: LLMProvider):
        super().__init__(
            name="CodeChat",
            description="Interactive AI code assistant"
        )
        self.llm = llm_provider
        self.session_id = str(uuid.uuid4())  # Unique session ID
        self.token_manager = TokenManager()
        
        # Register tools
        self.register_tool(FileReadTool())
        self.register_tool(FileWriteTool())
        self.register_tool(ListFilesTool())
        
        # Register Git tools
        self.register_tool(GitCommitTool())
        self.register_tool(GitBranchTool())
        self.register_tool(GitStatusTool())
        
        # Register Auto-fix tools
        self.register_tool(AutoFixTool(agent=self))
        self.register_tool(PytestTool())
        
        logger.info("✅ CodeChatAgent initialized with TokenManager")
    
    def think(self, prompt: str) -> str:
        """Analyze prompt and generate response"""
        # Build messages
        # Note: We rely on 'chat' method to inject RAG context into the prompt
        messages = [
            {
                "role": "system",
                "content": self._get_system_prompt()
            }
        ]
        
        # Add conversation history
        # We add more history here, trusting TokenManager to prune it if needed
        for msg in self.conversation_history[-10:]:
            messages.append(msg)
        
        # Add user message
        messages.append({"role": "user", "content": prompt})
        
        # Optimize context to fit token limit
        optimized_messages = self.token_manager.limit_context(
            messages, 
            max_tokens=MAX_CONTEXT_TOKENS
        )
        
        # Call LLM - support both custom providers and LangChain LLMs
        try:
            # Try custom provider interface first (has .call method)
            response = self.llm.call(optimized_messages)
        except AttributeError:
            # Fallback to LangChain interface (ChatGroq, OllamaLLM, etc.)
            # Convert messages to string for invoke (some chains prefer strings, some list of msgs)
            # But LangChain Chat models usually take list of messages.
            # However, our 'llm' object might be a simple wrapper or a raw LangChain object.
            
            # If it's a ChatGroq or OllamaLLM, they support invoke with list of BaseMessage
            # But here we have dicts. Let's convert to string to be safe and generic for now,
            # or try to map to LangChain message types if we want to be fancy.
            # Given the previous code used string concatenation, we'll stick to that but smarter.
            
            formatted_prompt = ""
            for msg in optimized_messages:
                role = msg['role'].upper()
                content = msg['content']
                formatted_prompt += f"{role}: {content}\n\n"
                
            result = self.llm.invoke(formatted_prompt)
            response = result.content if hasattr(result, 'content') else str(result)
        
        return response or "❌ Error: Could not generate response"
    
    def chat(self, user_message: str, session_id: Optional[str] = None) -> str:
        """Main chat interface with RAG-enhanced context and long-term memory"""
        # Use provided session_id or default to instance session_id
        active_session = session_id or self.session_id
        
        def _is_general_query(text: str) -> bool:
            t = (text or "").lower()
            signals = ["def ", "class ", "error", ".py", ".ts", ".java", "traceback", "import ", "function"]
            if any(s in t for s in signals):
                return False
            general = ["odoo", "react", "python", "docker", "kubernetes", "aws", "linux", "fastapi", "flask"]
            return any(g in t for g in general)

        # 1. Retrieve long-term memory
        from concurrent.futures import ThreadPoolExecutor
        memory_context = ""
        rag_context = ""
        try:
            with ThreadPoolExecutor(max_workers=2) as ex:
                fut_mem = ex.submit(get_memory, active_session, 10)
                fut_rag = ex.submit((lambda: "") if _is_general_query(user_message) else (lambda: get_context(user_message, 8)))
                memory_context = fut_mem.result()
                rag_context = fut_rag.result()
            logger.info(f"✅ Retrieved memory for session: {active_session}")
            logger.info(f"✅ RAG retrieved relevant code snippets")
        except Exception as e:
            logger.warning(f"⚠️ Context retrieval failed: {e}")
        
        # 3. Build prompt with intelligent token allocation
        # Budget:
        # - System Prompt: ~500 (handled in think)
        # - Memory: ~2000
        # - RAG: ~6000
        # - User Query: Remainder
        
        truncated_memory = self.token_manager.truncate_text(memory_context, 2000)
        truncated_rag = self.token_manager.truncate_text(rag_context, 6000)
        
        # Construct the augmented prompt
        # We explicitly label sections for the LLM
        prompt = f"""# Previous conversation summary:
{truncated_memory}

# Codebase context (Relevant snippets):
{truncated_rag}

# User Question:
{user_message}
"""
        
        # 4. Get response from agent
        response = self.run(prompt)
        
        # 5. Save to memory
        try:
            save_memory(active_session, user_message, response)
            logger.info(f"💾 Saved conversation to memory")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save memory: {e}")
        
        return response

    def act(self, action: str) -> bool:
        """
        Execute an action.
        Currently a placeholder. In the future, this will parse JSON tool calls
        and execute them using the registered tools.
        """
        logger.info(f"Action requested: {action}")
        # TODO: Implement tool execution logic
        return True
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for code assistant"""
        return """Bạn là một AI Code Assistant thông minh. Trả lời trực tiếp và tập trung vào câu hỏi. Với câu hỏi chung về công nghệ (ví dụ: Odoo), cung cấp tổng quan, tính năng chính, cài đặt, mô-đun quan trọng và ứng dụng thực tế.
- Đọc và phân tích code từ project
- Giải thích functions, classes, và architecture
- Đề xuất cải tiến và best practices
- Viết code mới theo yêu cầu
- Debug vấn đề và lỗi
- Trả lời câu hỏi chi tiết về codebase
- Thực hiện Git operations (commit, branch, status)

Available tools:
- read_file: Đọc file content
- write_file: Tạo/chỉnh sửa file
- list_files: Liệt kê tất cả files
- git_commit: Commit changes với message (ví dụ: /git_commit "fix bug")
- git_create_branch: Tạo branch mới (ví dụ: /git_create_branch "feature-x")
- git_status: Kiểm tra Git status
- auto_fix: Tự động test và fix code (max 5 vòng) (ví dụ: /autofix)
- run_pytest: Chạy pytest với arguments

Khi user yêu cầu commit hoặc tạo branch, hãy sử dụng Git tools tự động.
Khi user yêu cầu auto-fix hoặc test & fix, hãy sử dụng auto_fix tool.
Luôn cố gắng được hữu ích, cụ thể, và chuyên nghiệp.
Khi được yêu cầu sửa code, hãy trả lời chi tiết."""
