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
from src.tools.tools import FileReadTool, FileWriteTool, ListFilesTool
from src.tools.codebase_rag import retrieve, get_context
from src.tools.git_tool import GitCommitTool, GitBranchTool, GitStatusTool
from src.tools.autofix_tool import AutoFixTool, PytestTool
from src.memory import save_memory, get_memory
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
        self.project_files = []
        self.session_id = str(uuid.uuid4())  # Unique session ID
        self.load_project_files()
        
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
    
    def load_project_files(self):
        """Load all code files from project"""
        for ext in CODE_EXTENSIONS:
            pattern = f"{PROJECT_ROOT}/**/*{ext}"
            files = glob.glob(pattern, recursive=True)
            # Filter out venv and __pycache__
            self.project_files.extend([
                f for f in files 
                if '.venv' not in f and '__pycache__' not in f and '.git' not in f
            ])
        
        logger.info(f"✅ Loaded {len(self.project_files)} code files")
    
    def build_context(self, limit: int = 5) -> str:
        """Build code context for LLM"""
        context = "# PROJECT CODE CONTEXT\n\n"
        
        files_to_include = self.project_files[:limit]
        
        for file_path in files_to_include:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                relative_path = Path(file_path).relative_to(PROJECT_ROOT)
                context += f"## File: {relative_path}\n"
                context += "```python\n" if file_path.endswith('.py') else "```\n"
                context += content[:1500]  # Limit per file
                context += "\n```\n\n"
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
        
        return context
    
    def think(self, prompt: str) -> str:
        """Analyze prompt and generate response"""
        # Build messages with context
        messages = [
            {
                "role": "system",
                "content": self._get_system_prompt()
            },
            {
                "role": "system",
                "content": f"Project Context:\n{self.build_context()}"
            }
        ]
        
        # Add conversation history (last 5 messages)
        for msg in self.conversation_history[-5:]:
            messages.append(msg)
        
        # Add user message
        messages.append({"role": "user", "content": prompt})
        
        # Call LLM
        response = self.llm.call(messages)
        
        return response or "❌ Error: Could not generate response"
    
    def act(self, action: str) -> bool:
        """Execute an action (placeholder for now)"""
        # Will implement in next iteration with tool execution
        logger.info(f"Action: {action}")
        return True
    
    def chat(self, user_message: str, session_id: Optional[str] = None) -> str:
        """Main chat interface with RAG-enhanced context and long-term memory"""
        # Use provided session_id or default to instance session_id
        active_session = session_id or self.session_id
        
        # 1. Retrieve long-term memory
        try:
            memory_context = get_memory(active_session, k=20)
            logger.info(f"✅ Retrieved memory for session: {active_session}")
        except Exception as e:
            logger.warning(f"⚠️ Memory retrieval failed: {e}")
            memory_context = ""
        
        # 2. Retrieve relevant code snippets using RAG
        try:
            rag_context = get_context(user_message, k=15)
            logger.info(f"✅ RAG retrieved relevant code snippets")
        except Exception as e:
            logger.warning(f"⚠️ RAG retrieval failed: {e}")
            rag_context = ""
        
        # 3. Build prompt with both memory and RAG context
        prompt = f"""# Previous conversation:\n{memory_context}\n\n# Codebase context:\n{rag_context}\n\n# Question: {user_message}"""
        
        # 4. Get response from agent
        response = self.run(prompt)
        
        # 5. Save to memory
        try:
            save_memory(active_session, user_message, response)
            logger.info(f"💾 Saved conversation to memory")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save memory: {e}")
        
        return response
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for code assistant"""
        return """Bạn là một AI Code Assistant thông minh. Bạn có khả năng:
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
