#!/usr/bin/env python3
"""
GitHub AI Agent - Cloud LLM Only
Tự động xử lý GitHub Issues sử dụng GROQ & HuggingFace (Cloud LLM)
"""

import os
import json
import requests
import logging
import re
from dotenv import load_dotenv
from github import Github
from typing import Optional
import time

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_FULL_NAME = os.getenv("REPO_FULL_NAME")
MODE = os.getenv("MODE", "cloud")  # Only 'cloud' mode
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Cloud Mode (GROQ) - Primary
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"  # GROQ free tier model (updated)

# Cloud Mode (HuggingFace) - Fallback
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-2-7b-chat-hf")

# Validation constraints
MAX_PROMPT_LENGTH = 4000
MAX_ISSUE_BODY_LENGTH = 2000

def sanitize_text(text: str, max_length: int = MAX_ISSUE_BODY_LENGTH) -> str:
    """
    Sanitize input text to prevent injection attacks
    """
    if not text:
        return ""
    
    # Truncate to max length
    text = text[:max_length]
    
    # Remove potentially dangerous characters (but keep markdown)
    # Keep alphanumeric, spaces, common punctuation, newlines, and markdown
    safe_chars = re.compile(r'[^a-zA-Z0-9\s\-_.,:;!?()\[\]{}*`#\n\r/\\@]')
    text = safe_chars.sub('', text)
    
    return text.strip()

def validate_prompt(prompt: str) -> bool:
    """
    Validate prompt before sending to LLM
    """
    if not prompt or len(prompt) == 0:
        logger.warning("Empty prompt provided")
        return False
    
    if len(prompt) > MAX_PROMPT_LENGTH:
        logger.warning(f"Prompt too long: {len(prompt)} > {MAX_PROMPT_LENGTH}")
        return False
    
    return True

class GitHubAIAgent:
    def __init__(self):
        """Initialize the AI Agent"""
        self.gh = Github(GITHUB_TOKEN)
        self.repo = self.gh.get_repo(REPO_FULL_NAME)
        self.mode = "cloud"  # Only cloud mode supported
        
    def get_response_huggingface(self, prompt: str) -> Optional[str]:
        """
        Get response từ HuggingFace Inference API (Cloud)
        """
        if not validate_prompt(prompt):
            return None
        
        try:
            if DEBUG:
                print(f"📡 Calling HuggingFace API...")
            
            headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_length": 500,
                    "temperature": 0.7,
                }
            }
            
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{HUGGINGFACE_MODEL}",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "").strip()
            return None
        except Exception as e:
            if DEBUG:
                print(f"❌ HuggingFace error: {e}")
            return None
    
    def get_response_groq(self, prompt: str) -> Optional[str]:
        """
        Get response từ GROQ API (Cloud - Fast inference)
        """
        if not validate_prompt(prompt):
            return None
        
        try:
            if DEBUG:
                logger.info(f"📡 Calling GROQ API with model {GROQ_MODEL}...")
            
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "model": GROQ_MODEL,
                "temperature": 0.7,
                "max_tokens": 1024,
            }
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0].get("message", {}).get("content", "").strip()
            return None
        except requests.exceptions.Timeout:
            if DEBUG:
                logger.error(f"❌ GROQ timeout")
            return None
        except requests.exceptions.ConnectionError:
            if DEBUG:
                logger.error(f"❌ GROQ connection error")
            return None
        except Exception as e:
            if DEBUG:
                logger.error(f"❌ GROQ error: {e}")
            return None
    
    def get_llm_response(self, prompt: str) -> Optional[str]:
        """
        Get response từ LLM (Cloud Mode)
        Thử GROQ → HuggingFace theo priority
        """
        if DEBUG:
            logger.info("🔄 Mode: Cloud")
        
        # Try GROQ first (faster)
        if GROQ_API_KEY:
            if DEBUG:
                logger.info("🔄 Trying GROQ API...")
            response = self.get_response_groq(prompt)
            if response:
                return response
            if DEBUG:
                logger.warning("⚠️ GROQ failed, trying HuggingFace...")
        
        # Try HuggingFace as fallback
        if HUGGINGFACE_TOKEN:
            if DEBUG:
                logger.info("🔄 Trying HuggingFace API...")
            response = self.get_response_huggingface(prompt)
            if response:
                return response
        
        return None
    
    def get_issue_context(self, issue):
        """
        Lấy thông tin chi tiết về issue
        """
        issue_body = sanitize_text(issue.body if issue.body else "No description provided", MAX_ISSUE_BODY_LENGTH)
        labels = ', '.join([label.name for label in issue.labels]) if issue.labels else "None"
        
        context = f"""
GitHub Issue Analysis
======================
Title: {issue.title}
Number: #{issue.number}
State: {issue.state}
Author: @{issue.user.login}
Created: {issue.created_at}

Body:
{issue_body}

Labels: {labels}
"""
        return context
    
    def generate_analysis(self, issue) -> Optional[str]:
        """
        Generate AI analysis cho issue
        """
        context = self.get_issue_context(issue)
        
        prompt = f"""{context}

Bạn là một senior software engineer với 10 năm kinh nghiệm. Hãy phân tích GitHub Issue này một cách chi tiết và chuyên nghiệp.

**Yêu cầu phân tích:**

1. **Tóm tắt vấn đề** (2-3 câu)
   - Nêu rõ vấn đề chính, tác động và độ ưu tiên

2. **Root cause analysis** (2-3 đoạn)
   - Phân tích nguyên nhân gốc rễ
   - Các yếu tố liên quan

3. **Giải pháp được đề xuất** (2-3 phương án)
   - Liệt kê các cách tiếp cận khác nhau
   - Đánh giá ưu/nhược điểm của mỗi giải pháp

4. **Thực hiện chi tiết** 
   - Các bước cụ thể để giải quyết
   - Ước tính độ phức tạp (Easy/Medium/Hard)

5. **Code example** (nếu có liên quan)
   - Cung cấp code snippet minh họa
   - Sử dụng markdown code blocks

6. **Testing approach**
   - Cách test solution
   - Test cases cần kiểm tra

7. **Rủi ro tiềm ẩn**
   - Những vấn đề có thể gặp
   - Cách giảm thiểu rủi ro

8. **Tài liệu tham khảo**
   - Links hoặc tips hữu ích (nếu có)

**Lưu ý:**
- Trả lời bằng **Tiếng Việt**
- Chi tiết và chuyên nghiệp
- Tập trung vào tính khả thi
- Dễ hiểu cho developer của dự án
"""
        
        # Validate prompt
        if not validate_prompt(prompt):
            logger.error(f"Invalid prompt for issue #{issue.number}")
            return None
        
        if DEBUG:
            logger.info(f"🧠 Generating AI analysis for issue #{issue.number}...")
        
        response = self.get_llm_response(prompt)
        return response
    
    def process_issue(self, issue_number: int):
        """
        Xử lý một GitHub Issue
        """
        print(f"\n{'='*60}")
        print(f"🔍 Processing Issue #{issue_number}...")
        print(f"{'='*60}")
        
        try:
            issue = self.repo.get_issue(issue_number)
            
            print(f"📌 Title: {issue.title}")
            print(f"👤 Author: @{issue.user.login}")
            print(f"📝 Status: {issue.state}")
            
            # Check if already commented
            comments = list(issue.get_comments())
            for comment in comments:
                if "AI Agent" in comment.body or "🤖" in comment.body:
                    print("⏭️  Already analyzed by AI Agent, skipping...")
                    logger.info(f"Issue #{issue_number} already analyzed, skipping")
                    return
            
            # Generate analysis
            analysis = self.generate_analysis(issue)
            
            if analysis:
                print("✅ AI Analysis generated successfully")
                
                # Comment on issue
                comment_body = f"""## 🤖 AI Agent Analysis

{analysis}

---
*Generated by GitHub AI Agent (Hybrid Local & Cloud LLM)*
*Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}*
"""
                issue.create_comment(comment_body)
                print("✅ Comment posted on issue")
                logger.info(f"Issue #{issue_number} analysis completed and commented")
            else:
                print("❌ Failed to generate analysis")
                logger.warning(f"Failed to generate analysis for issue #{issue_number}")
                # Post error comment
                issue.create_comment("""
## ❌ AI Agent Error

Sorry, I couldn't generate analysis at this moment.
Please try again later or check the configuration.

---
*GitHub AI Agent*
""")
        
        except Exception as e:
            print(f"❌ Error processing issue: {e}")
            logger.error(f"Error processing issue #{issue_number}: {e}", exc_info=True)
    
    def process_open_issues(self, limit: int = 5):
        """
        Xử lý tất cả các open issues
        """
        print(f"\n{'='*60}")
        print(f"📊 Fetching open issues from {self.repo.full_name}...")
        print(f"{'='*60}")
        
        try:
            issues = self.repo.get_issues(state="open")
            
            count = 0
            for issue in issues:
                if count >= limit:
                    break
                if not issue.pull_request:  # Skip PRs
                    self.process_issue(issue.number)
                    count += 1
                    time.sleep(2)  # Rate limiting
            
            print(f"\n✅ Processed {count} issues")
        
        except Exception as e:
            print(f"❌ Error fetching issues: {e}")
    
    def test_connection(self) -> bool:
        """
        Test connections to GitHub & LLM
        """
        print("\n" + "="*60)
        print("🧪 Testing Connections...")
        print("="*60)
        
        # Test GitHub
        try:
            repo = self.repo
            print(f"✅ GitHub: Connected to {repo.full_name}")
        except Exception as e:
            print(f"❌ GitHub: {e}")
            logger.error(f"GitHub connection failed: {e}")
            return False
        
        # Test GROQ
        test_prompt = "Say 'Hello' in one word"
        
        if GROQ_API_KEY:
            print(f"\n📡 Testing GROQ API...")
            response = self.get_response_groq(test_prompt)
            if response:
                print(f"✅ GROQ: Connected")
            else:
                print(f"⚠️  GROQ: Connection issue")
                if not HUGGINGFACE_TOKEN:
                    logger.error("GROQ failed and no HuggingFace token")
                    return False
        else:
            print(f"⚠️  GROQ_API_KEY: Not provided")
        
        # Test HuggingFace fallback
        if HUGGINGFACE_TOKEN:
            print(f"\n📡 Testing HuggingFace API...")
            response = self.get_response_huggingface(test_prompt)
            if response:
                print(f"✅ HuggingFace: Connected")
            else:
                print(f"⚠️  HuggingFace: Connection issue")
        else:
            print(f"⚠️  HUGGINGFACE_TOKEN: Not provided (recommended to add as fallback)")
        
        if not GROQ_API_KEY and not HUGGINGFACE_TOKEN:
            print(f"\n❌ No LLM API keys configured!")
            return False
        
        return True

def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("🚀 GitHub AI Agent Starting...")
    print("="*60)
    print(f"Mode: Cloud (GROQ + HuggingFace)")
    print(f"Repository: {REPO_FULL_NAME}")
    
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not found in environment variables")
        logger.error("GITHUB_TOKEN not configured")
        return
    
    if not REPO_FULL_NAME:
        print("❌ REPO_FULL_NAME not found in environment variables")
        logger.error("REPO_FULL_NAME not configured")
        return
    
    if not GROQ_API_KEY and not HUGGINGFACE_TOKEN:
        print("❌ At least one LLM API key required (GROQ_API_KEY or HUGGINGFACE_TOKEN)")
        logger.error("No LLM API keys configured")
        return
    
    try:
        agent = GitHubAIAgent()
        
        # Test connections
        if not agent.test_connection():
            print("\n❌ Connection test failed!")
            logger.error("Connection test failed")
            return
        
        # Process issues
        print("\n" + "="*60)
        agent.process_open_issues(limit=5)
        
        print("\n" + "="*60)
        print("✅ GitHub AI Agent completed!")
        print("="*60)
        logger.info("GitHub AI Agent completed successfully")
    
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.error(f"Fatal error in main: {e}", exc_info=True)

if __name__ == "__main__":
    main()