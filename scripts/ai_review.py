#!/usr/bin/env python3
"""
AI Code Review Script for GitHub Actions - Phase 5
Automatically reviews Pull Requests using multi-agent analysis
"""

import os
import sys
import json
import asyncio
import requests
from typing import List, Dict, Any
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.plugins.agent_manager import AgentManager
from src.plugins.github_issue_agent import GitHubIssueAgent
from src.plugins.doc_agent import DocumentationAgent
from src.memory.log_manager import log_activity
from src.utils.logger import get_logger

logger = get_logger(__name__)

class GitHubPRReviewer:
    """AI-powered Pull Request reviewer"""
    
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repo = os.getenv("GITHUB_REPOSITORY")
        self.pr_number = os.getenv("PR_NUMBER")
        
        if not all([self.github_token, self.repo, self.pr_number]):
            raise ValueError("Missing required environment variables")
        
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Initialize agents
        self.agents = {
            "github": GitHubIssueAgent(
                repo=self.repo,
                token=self.github_token,
                config={"test_mode": False}
            ),
            "doc": DocumentationAgent(config={"test_mode": False})
        }
        
        self.agent_manager = AgentManager({
            "github_issue": self.agents["github"],
            "documentation": self.agents["doc"]
        })
        
        logger.info(f"Initialized PR reviewer for {self.repo}#{self.pr_number}")
    
    def get_pr_details(self) -> Dict[str, Any]:
        """Get Pull Request details"""
        url = f"https://api.github.com/repos/{self.repo}/pulls/{self.pr_number}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_pr_files(self) -> List[Dict[str, Any]]:
        """Get files changed in the Pull Request"""
        url = f"https://api.github.com/repos/{self.repo}/pulls/{self.pr_number}/files"
        
        files = []
        page = 1
        per_page = 100
        
        while True:
            response = requests.get(
                url, 
                headers=self.headers,
                params={"page": page, "per_page": per_page}
            )
            response.raise_for_status()
            
            page_files = response.json()
            if not page_files:
                break
                
            files.extend(page_files)
            page += 1
        
        logger.info(f"Retrieved {len(files)} files from PR")
        return files
    
    def analyze_file(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single file using agents"""
        filename = file_data["filename"]
        patch = file_data.get("patch", "")
        status = file_data.get("status", "modified")
        
        # Create issue-like task for agents
        task_data = {
            "type": "github_issue_analysis",
            "data": {
                "filename": filename,
                "patch": patch,
                "status": status,
                "additions": file_data.get("additions", 0),
                "deletions": file_data.get("deletions", 0),
                "changes": file_data.get("changes", 0)
            }
        }
        
        # Process with agent manager
        try:
            task_id = self.agent_manager.create_task(
                task_type="github_issue_analysis",
                data=task_data["data"],
                priority="high"
            )
            
            result = asyncio.run(self.agent_manager.process_task(task_id))
            
            return {
                "filename": filename,
                "status": status,
                "analysis": result,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error analyzing file {filename}: {e}")
            return {
                "filename": filename,
                "status": status,
                "error": str(e),
                "success": False
            }
    
    def generate_review_comment(self, pr_details: Dict[str, Any], 
                            file_analyses: List[Dict[str, Any]]) -> str:
        """Generate comprehensive review comment"""
        pr_title = pr_details.get("title", "")
        pr_description = pr_details.get("body", "")
        author = pr_details.get("user", {}).get("login", "unknown")
        
        # Start comment
        comment_lines = [
            f"## 🤖 AI Code Review",
            f"",
            f"**PR:** #{self.pr_number} - {pr_title}",
            f"**Author:** @{author}",
            f"**Review Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"",
            f"---",
            f""
        ]
        
        # Summary
        successful_analyses = [a for a in file_analyses if a.get("success")]
        failed_analyses = [a for a in file_analyses if not a.get("success")]
        
        comment_lines.extend([
            f"### 📊 Review Summary",
            f"- ✅ **Files Analyzed:** {len(successful_analyses)}",
            f"- ❌ **Analysis Failed:** {len(failed_analyses)}",
            f"- 📁 **Total Files:** {len(file_analyses)}",
            f""
        ])
        
        # File-by-file analysis
        if successful_analyses:
            comment_lines.extend([
                f"### 📋 Detailed Analysis",
                f""
            ])
            
            for analysis in successful_analyses:
                filename = analysis["filename"]
                status = analysis["status"]
                result = analysis["analysis"]
                
                # Status emoji
                status_emoji = {
                    "added": "➕",
                    "modified": "📝", 
                    "removed": "➖",
                    "renamed": "🔄"
                }.get(status, "📁")
                
                comment_lines.extend([
                    f"#### {status_emoji} `{filename}`",
                    f""
                ])
                
                # Agent results
                if hasattr(result, 'agent_results'):
                    for agent_result in result.agent_results:
                        agent_name = agent_result.agent_name
                        agent_success = agent_result.success
                        agent_result_text = agent_result.result
                        
                        if isinstance(agent_result_text, dict):
                            agent_result_text = agent_result_text.get("response", str(agent_result_text))
                        
                        emoji = "✅" if agent_success else "❌"
                        comment_lines.append(f"- **{emoji} {agent_name}:** {agent_result_text}")
                
                comment_lines.append("")
        
        # Errors
        if failed_analyses:
            comment_lines.extend([
                f"### ❌ Analysis Errors",
                f""
            ])
            
            for analysis in failed_analyses:
                filename = analysis["filename"]
                error = analysis.get("error", "Unknown error")
                comment_lines.append(f"- **{filename}:** {error}")
            
            comment_lines.append("")
        
        # Recommendations
        comment_lines.extend([
            f"### 💡 Recommendations",
            f"",
            f"1. 📖 **Review the detailed analysis** above for each file",
            f"2. 🔍 **Address any issues** identified by the agents",
            f"3. 📚 **Check related documentation** for best practices",
            f"4. 🧪 **Add tests** for new functionality",
            f"",
            f"---",
            f"",
            f"*This review was generated by GitHub AI Agent - Phase 5*",
            f"*Multi-agent analysis: GitHub Issue Agent, Documentation Agent*"
        ])
        
        return "\n".join(comment_lines)
    
    def post_comment(self, body: str) -> Dict[str, Any]:
        """Post comment to Pull Request"""
        url = f"https://api.github.com/repos/{self.repo}/issues/{self.pr_number}/comments"
        
        data = {
            "body": body
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Posted comment: {result.get('html_url')}")
        return result
    
    def run_review(self):
        """Main review process"""
        try:
            # Log activity
            log_activity(
                agent="GitHubPRReviewer",
                action="start_review",
                result=f"Starting review for PR #{self.pr_number}",
                task_id=f"pr_{self.pr_number}"
            )
            
            # Get PR details
            logger.info("Getting PR details...")
            pr_details = self.get_pr_details()
            
            # Get files
            logger.info("Getting PR files...")
            files = self.get_pr_files()
            
            if not files:
                logger.warning("No files found in PR")
                return
            
            # Analyze files
            logger.info("Analyzing files...")
            file_analyses = []
            
            for i, file_data in enumerate(files):
                logger.info(f"Analyzing file {i+1}/{len(files)}: {file_data['filename']}")
                analysis = self.analyze_file(file_data)
                file_analyses.append(analysis)
            
            # Generate comment
            logger.info("Generating review comment...")
            comment = self.generate_review_comment(pr_details, file_analyses)
            
            # Post comment
            logger.info("Posting review comment...")
            self.post_comment(comment)
            
            # Log completion
            log_activity(
                agent="GitHubPRReviewer",
                action="complete_review",
                result=f"Completed review for PR #{self.pr_number} with {len(file_analyses)} files",
                task_id=f"pr_{self.pr_number}",
                processing_time=0  # Could be measured if needed
            )
            
            logger.info(f"✅ Review completed for PR #{self.pr_number}")
            
        except Exception as e:
            logger.error(f"Review failed: {e}")
            
            # Log error
            log_activity(
                agent="GitHubPRReviewer",
                action="review_error",
                result=f"Review failed for PR #{self.pr_number}: {str(e)}",
                task_id=f"pr_{self.pr_number}",
                status="error"
            )
            
            raise

def main():
    """Main entry point"""
    try:
        reviewer = GitHubPRReviewer()
        reviewer.run_review()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
