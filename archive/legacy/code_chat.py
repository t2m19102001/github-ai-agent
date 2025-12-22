#!/usr/bin/env python3
"""
Code Chat Interface - Interactive AI Code Assistant
Giao diện chat với AI có thể đọc, phân tích và chỉnh sửa code
"""

import os
import json
import requests
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, List, Dict
import glob

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"
PROJECT_ROOT = Path(__file__).parent

# Code extensions to analyze
CODE_EXTENSIONS = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rb', '.php']


class CodeChatAssistant:
    """AI Assistant for code analysis and chat"""
    
    def __init__(self):
        self.conversation_history = []
        self.project_files = []
        self.load_project_files()
        
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
    
    def read_file(self, file_path: str) -> Optional[str]:
        """Read a file from the project"""
        full_path = PROJECT_ROOT / file_path
        
        if not full_path.exists():
            return None
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return None
    
    def write_file(self, file_path: str, content: str) -> bool:
        """Write content to a file"""
        full_path = PROJECT_ROOT / file_path
        
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"✅ File saved: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing file: {e}")
            return False
    
    def get_file_list(self) -> List[str]:
        """Get list of all code files in project"""
        relative_paths = [
            str(Path(f).relative_to(PROJECT_ROOT)) 
            for f in self.project_files
        ]
        return sorted(relative_paths)
    
    def build_context(self, files_to_include: List[str] = None) -> str:
        """Build code context for AI"""
        context = "# PROJECT CODE CONTEXT\n\n"
        
        files = files_to_include or self.project_files[:5]  # Default: first 5 files
        
        for file_path in files:
            content = self.read_file(str(Path(file_path).relative_to(PROJECT_ROOT)))
            if content:
                context += f"## File: {file_path}\n"
                context += "```python\n" if file_path.endswith('.py') else "```\n"
                context += content[:2000]  # Limit to 2000 chars per file
                context += "\n```\n\n"
        
        return context
    
    def call_groq_api(self, messages: List[Dict]) -> Optional[str]:
        """Call GROQ API for chat"""
        try:
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messages": messages,
                "model": GROQ_MODEL,
                "temperature": 0.7,
                "max_tokens": 2048,
            }
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0].get("message", {}).get("content", "").strip()
            
            return None
        except Exception as e:
            logger.error(f"GROQ API error: {e}")
            return None
    
    def chat(self, user_message: str, include_code_context: bool = True) -> str:
        """Chat with AI assistant"""
        
        # Build messages
        messages = []
        
        # System prompt
        system_prompt = """Bạn là một AI Code Assistant thông minh. Bạn có khả năng:
- Đọc và phân tích code
- Đề xuất cải tiến
- Giải thích các hàm/lớp
- Viết code mới
- Debug vấn đề
- Trả lời câu hỏi về project

Luôn cố gắng được hữu ích và cụ thể. Khi được yêu cầu sửa code, hãy trả lời dưới dạng JSON:
{
    "type": "code_modification",
    "file": "path/to/file.py",
    "action": "create|modify|delete",
    "content": "new code here"
}

Khi được hỏi các câu hỏi chung, trả lời bằng text thường."""
        
        messages.append({"role": "system", "content": system_prompt})
        
        # Add code context nếu có request
        if include_code_context and len(self.project_files) > 0:
            context = self.build_context()
            messages.append({
                "role": "system",
                "content": f"Project context:\n{context}"
            })
        
        # Add conversation history (last 5 messages)
        for msg in self.conversation_history[-5:]:
            messages.append(msg)
        
        # Add user message
        messages.append({"role": "user", "content": user_message})
        
        # Call API
        response = self.call_groq_api(messages)
        
        if response:
            # Store in history
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # Handle code modifications
            if response.startswith("{") and response.endswith("}"):
                try:
                    data = json.loads(response)
                    if data.get("type") == "code_modification":
                        self.handle_code_modification(data)
                except json.JSONDecodeError:
                    pass
            
            return response
        
        return "❌ Error: Không thể kết nối với AI. Vui lòng kiểm tra GROQ API key."
    
    def handle_code_modification(self, modification: Dict):
        """Handle code modification request"""
        action = modification.get("action")
        file_path = modification.get("file")
        content = modification.get("content")
        
        if action == "create":
            if self.write_file(file_path, content):
                logger.info(f"✅ Created file: {file_path}")
        elif action == "modify":
            if self.write_file(file_path, content):
                logger.info(f"✅ Modified file: {file_path}")
        elif action == "delete":
            full_path = PROJECT_ROOT / file_path
            if full_path.exists():
                full_path.unlink()
                logger.info(f"✅ Deleted file: {file_path}")


def interactive_chat():
    """Interactive chat loop"""
    assistant = CodeChatAssistant()
    
    print("\n" + "="*70)
    print("🤖 CODE CHAT ASSISTANT")
    print("="*70)
    print("Commands:")
    print("  'list' - Liệt kê tất cả code files")
    print("  'read <file>' - Đọc file")
    print("  'context' - Xem code context")
    print("  'quit' - Thoát")
    print("="*70 + "\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("Goodbye! 👋")
                break
            
            elif user_input.lower() == 'list':
                files = assistant.get_file_list()
                print(f"\n📁 Project Files ({len(files)}):")
                for f in files:
                    print(f"  - {f}")
                print()
                continue
            
            elif user_input.lower().startswith('read '):
                file_path = user_input[5:].strip()
                content = assistant.read_file(file_path)
                if content:
                    print(f"\n📄 File: {file_path}")
                    print(f"```\n{content}\n```\n")
                else:
                    print(f"❌ File not found: {file_path}\n")
                continue
            
            elif user_input.lower() == 'context':
                context = assistant.build_context()
                print(f"\n📚 Code Context:\n{context}\n")
                continue
            
            # Regular chat
            print("\n🤖 Assistant: ", end="", flush=True)
            response = assistant.chat(user_input)
            print(response)
            print()
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"❌ Error: {e}\n")


if __name__ == "__main__":
    interactive_chat()
