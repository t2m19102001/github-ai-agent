#!/usr/bin/env python3
"""
GitHub AI Agent - Hybrid Local & Cloud LLM
Tự động xử lý GitHub Issues sử dụng Ollama (Local) hoặc HuggingFace (Cloud)
"""

import os
import json
import requests
from dotenv import load_dotenv
from github import Github
from typing import Optional
import time

load_dotenv()

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_FULL_NAME = os.getenv("REPO_FULL_NAME")
MODE = os.getenv("MODE", "hybrid")  # hybrid, local, cloud
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Local Mode (Ollama)
OLLAMA_API = os.getenv("OLLAMA_API", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# Cloud Mode (HuggingFace)
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "mistralai/Mistral-7B-Instruct-v0.1")

class GitHubAIAgent:
    def __init__(self):
        """Initialize the AI Agent"""
        self.gh = Github(GITHUB_TOKEN)
        self.repo = self.gh.get_repo(REPO_FULL_NAME)
        self.mode = MODE
        
    def get_response_ollama(self, prompt: str) -> Optional[str]:
        """
        Get response từ Ollama (Local LLM)
        """
        try:
            if DEBUG:
                print(f"📡 Calling Ollama at {OLLAMA_API}...")
            
            response = requests.post(
                f"{OLLAMA_API}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                },
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "").strip()
        except requests.exceptions.ConnectionError:
            if DEBUG:
                print(f"❌ Ollama not available at {OLLAMA_API}")
            return None
        except Exception as e:
            if DEBUG:
                print(f"❌ Ollama error: {e}")
            return None
    
    def get_response_huggingface(self, prompt: str) -> Optional[str]:
        """
        Get response từ HuggingFace Inference API (Cloud)
        """
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
    
    def get_llm_response(self, prompt: str) -> Optional[str]:
        """
        Get response từ LLM (Hybrid Mode)
        Thử Ollama trước, nếu fail thì chuyển HuggingFace
        """
        if self.mode in ["hybrid", "local"]:
            if DEBUG:
                print("🔄 Mode: Local (Ollama)")
            response = self.get_response_ollama(prompt)
            if response:
                return response
            
            if self.mode == "local":
                return None
            
            if DEBUG:
                print("⚠️ Ollama failed, falling back to HuggingFace...")
        
        if self.mode in ["hybrid", "cloud"]:
            if DEBUG:
                print("🔄 Mode: Cloud (HuggingFace)")
            response = self.get_response_huggingface(prompt)
            if response:
                return response
        
        return None
    
    def get_issue_context(self, issue):
        """
        Lấy thông tin chi tiết về issue
        """
        context = f"""
GitHub Issue Analysis
======================
Title: {issue.title}
Number: #{issue.number}
State: {issue.state}
Author: @{issue.user.login}
Created: {issue.created_at}

Body:
{issue.body if issue.body else "No description provided"}

Labels: {', '.join([label.name for label in issue.labels]) if issue.labels else "None"}
"""
        return context
    
    def generate_analysis(self, issue) -> Optional[str]:
        """
        Generate AI analysis cho issue
        """
        context = self.get_issue_context(issue)
        
        prompt = f"""{context}

Bạn là một software engineer giỏi. Hãy phân tích GitHub Issue này và đưa ra giải pháp chi tiết:

Vui lòng:
1. **Tóm tắt vấn đề** - Nêu rõ vấn đề chính
2. **Root cause analysis** - Phân tích nguyên nhân gốc rễ
3. **Giải pháp được đề xuất** - Đưa ra 2-3 giải pháp cụ thể
4. **Implementation steps** - Các bước thực hiện
5. **Code example** - Ví dụ code nếu có liên quan
6. **Testing approach** - Cách test solution
7. **Potential risks** - Những rủi ro có thể gặp

Trả lời bằng Tiếng Việt, chi tiết và chuyên nghiệp.
"""
        
        if DEBUG:
            print(f"🧠 Generating AI analysis for issue #{issue.number}...")
        
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
            else:
                print("❌ Failed to generate analysis")
                # Post error comment
                issue.create_comment("""
## ❌ AI Agent Error

Sorry, I couldn't generate analysis at this moment.
Please try again later.

---
*GitHub AI Agent*
""")
        
        except Exception as e:
            print(f"❌ Error processing issue: {e}")
    
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
            return False
        
        # Test LLM modes
        test_prompt = "Say 'Hello' in one word"
        
        if self.mode in ["hybrid", "local"]:
            print(f"\n📡 Testing Ollama at {OLLAMA_API}...")
            response = self.get_response_ollama(test_prompt)
            if response:
                print(f"✅ Ollama: Connected")
            else:
                print(f"⚠️  Ollama: Not available")
                if self.mode == "local":
                    return False
        
        if self.mode in ["hybrid", "cloud"]:
            print(f"\n📡 Testing HuggingFace API...")
            if not HUGGINGFACE_TOKEN:
                print(f"❌ HuggingFace: Token not provided")
                if self.mode == "cloud":
                    return False
            else:
                response = self.get_response_huggingface(test_prompt)
                if response:
                    print(f"✅ HuggingFace: Connected")
                else:
                    print(f"⚠️  HuggingFace: Connection issue")
                    if self.mode == "cloud":
                        return False
        
        return True

def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("🚀 GitHub AI Agent Starting...")
    print("="*60)
    print(f"Mode: {MODE}")
    print(f"Repository: {REPO_FULL_NAME}")
    
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not found in environment variables")
        return
    
    if not REPO_FULL_NAME:
        print("❌ REPO_FULL_NAME not found in environment variables")
        return
    
    agent = GitHubAIAgent()
    
    # Test connections
    if not agent.test_connection():
        print("\n❌ Connection test failed!")
        return
    
    # Process issues
    print("\n" + "="*60)
    agent.process_open_issues(limit=5)
    
    print("\n" + "="*60)
    print("✅ GitHub AI Agent completed!")
    print("="*60)

if __name__ == "__main__":
    main()