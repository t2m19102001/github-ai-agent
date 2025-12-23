#!/usr/bin/env python3
"""
GitHub PR Analysis Agent
Automatically analyzes pull requests and provides intelligent feedback
"""

from typing import Dict, List, Optional, Any
from github import Github, PullRequest
from src.agents.base import Agent
from src.llm.groq import GroqProvider
from src.agent.plugins.base import PluginManager
from src.agent.plugins.auto_check_code_quality import AutoCheckCodeQualityPlugin
from src.core.config import AGENT_PLUGINS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GitHubPRAgent(Agent):
    """
    AI Agent for analyzing GitHub Pull Requests
    
    Features:
    - Analyzes code changes in PRs
    - Detects bugs, security issues, performance problems
    - Provides actionable feedback
    - Posts review comments automatically
    """
    
    def __init__(self, github_token: str, llm_provider: Optional[GroqProvider] = None):
        """
        Initialize PR Agent
        
        Args:
            github_token: GitHub personal access token
            llm_provider: LLM provider (default: GroqProvider)
        """
        super().__init__(
            name="GitHubPRAgent",
            description="Analyzes pull requests and provides intelligent code review"
        )
        
        self.github = Github(github_token)
        self.llm = llm_provider or GroqProvider()
        self.plugins = self._init_plugins()
        logger.info("✅ GitHubPRAgent initialized")
    
    def think(self, prompt: str) -> str:
        """
        Analyze and think about the input
        
        Args:
            prompt: Input to analyze
            
        Returns:
            Analysis result
        """
        messages = [{"role": "user", "content": prompt}]
        result = self.llm.call(messages)
        return result if result else "Error generating response"
    
    def act(self, action: str) -> bool:
        """
        Execute an action
        
        Args:
            action: Action to execute
            
        Returns:
            True if successful
        """
        # Actions will be implemented based on the analysis
        logger.info(f"Executing action: {action}")
        return True
    
    def analyze_pr(self, repo_name: str, pr_number: int) -> Dict[str, Any]:
        """
        Analyze a pull request
        
        Args:
            repo_name: Repository name (owner/repo)
            pr_number: PR number
            
        Returns:
            Analysis results with issues, suggestions, and summary
        """
        logger.info(f"🔍 Analyzing PR #{pr_number} in {repo_name}")
        
        try:
            # Get repository and PR
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            
            # Get PR details
            pr_data = self._get_pr_data(pr)
            
            # Analyze changes
            analysis = self._analyze_changes(pr, pr_data)

            # Run plugins for PR event (labels based)
            labels = [l.name for l in pr.get_labels()]
            event = {"type": "pr", "labels": labels, "files_data": pr_data["files_changed"]}
            plugin_results = self.plugins.run_plugins(event, {"repo": repo_name, "pr_number": pr_number})
            analysis["plugins"] = plugin_results
            
            logger.info(f"✅ Analysis complete for PR #{pr_number}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing PR: {e}")
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    def _get_pr_data(self, pr: PullRequest.PullRequest) -> Dict[str, Any]:
        """Extract PR metadata and changes"""
        files_changed = []
        total_additions = 0
        total_deletions = 0
        
        for file in pr.get_files():
            files_changed.append({
                'filename': file.filename,
                'status': file.status,
                'additions': file.additions,
                'deletions': file.deletions,
                'changes': file.changes,
                'patch': file.patch if hasattr(file, 'patch') else None
            })
            total_additions += file.additions
            total_deletions += file.deletions
        
        return {
            'title': pr.title,
            'description': pr.body or '',
            'author': pr.user.login,
            'state': pr.state,
            'files_changed': files_changed,
            'files_count': len(files_changed),
            'additions': total_additions,
            'deletions': total_deletions,
            'commits': pr.commits,
            'created_at': pr.created_at.isoformat(),
            'url': pr.html_url
        }
    
    def _analyze_changes(self, pr: PullRequest.PullRequest, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI to analyze code changes
        
        Returns comprehensive analysis including:
        - Security issues
        - Performance concerns
        - Code quality suggestions
        - Best practices violations
        """
        # Build context for AI
        context = self._build_analysis_context(pr_data)
        
        # Get AI analysis
        prompt = f"""You are an expert code reviewer. Analyze this pull request and provide detailed feedback.

PR Title: {pr_data['title']}
Description: {pr_data['description']}
Files Changed: {pr_data['files_count']}
Additions: {pr_data['additions']} lines
Deletions: {pr_data['deletions']} lines

Changes:
{context}

Provide analysis in the following format:

## 🔍 Summary
[Brief overview of what this PR does]

## ✅ Strengths
[What's good about these changes]

## ⚠️ Issues Found
[List any bugs, security issues, or problems - be specific with file names and line numbers]

## 💡 Suggestions
[Actionable improvements]

## 🎯 Overall Assessment
[Final verdict: APPROVE / REQUEST CHANGES / COMMENT]

Be thorough but concise. Focus on important issues."""

        logger.info("🤖 Getting AI analysis...")
        messages = [{"role": "user", "content": prompt}]
        analysis_text = self.llm.call(messages)
        
        if not analysis_text:
            analysis_text = "Error: Unable to generate analysis"
        
        # Parse analysis results
        return {
            'pr_number': pr.number,
            'pr_url': pr_data['url'],
            'status': 'success',
            'analysis': analysis_text,
            'metadata': {
                'files_changed': pr_data['files_count'],
                'additions': pr_data['additions'],
                'deletions': pr_data['deletions'],
                'commits': pr_data['commits']
            },
            'timestamp': pr_data['created_at']
        }
    
    def _build_analysis_context(self, pr_data: Dict[str, Any]) -> str:
        """Build context string from PR changes"""
        context_parts = []
        
        for file_data in pr_data['files_changed'][:10]:  # Limit to first 10 files
            context_parts.append(f"\n### File: {file_data['filename']}")
            context_parts.append(f"Status: {file_data['status']}")
            context_parts.append(f"Changes: +{file_data['additions']} -{file_data['deletions']}")
            
            if file_data['patch']:
                # Truncate large patches
                patch = file_data['patch']
                if len(patch) > 2000:
                    patch = patch[:2000] + "\n... (truncated)"
                context_parts.append(f"\n```diff\n{patch}\n```")
        
        if len(pr_data['files_changed']) > 10:
            context_parts.append(f"\n... and {len(pr_data['files_changed']) - 10} more files")
        
        return "\n".join(context_parts)
    
    def post_review_comment(self, repo_name: str, pr_number: int, comment: str) -> bool:
        """
        Post a review comment on a PR
        
        Args:
            repo_name: Repository name (owner/repo)
            pr_number: PR number
            comment: Comment text
            
        Returns:
            True if successful
        """
        try:
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            
            # Post comment
            pr.create_issue_comment(comment)
            
            logger.info(f"✅ Posted comment on PR #{pr_number}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error posting comment: {e}")
            return False
    
    def auto_review_pr(self, repo_name: str, pr_number: int, auto_comment: bool = True) -> Dict[str, Any]:
        """
        Automatically review a PR and optionally post comments
        
        Args:
            repo_name: Repository name (owner/repo)
            pr_number: PR number
            auto_comment: If True, automatically post review as comment
            
        Returns:
            Analysis results
        """
        logger.info(f"🤖 Auto-reviewing PR #{pr_number}")
        
        # Analyze PR
        analysis = self.analyze_pr(repo_name, pr_number)
        
        if analysis.get('status') == 'success' and auto_comment:
            # Format comment
            comment = f"""## 🤖 AI Code Review

{analysis['analysis']}

---
*Automated review by AI Agent*  
*Analyzed {analysis['metadata']['files_changed']} files with {analysis['metadata']['additions']} additions and {analysis['metadata']['deletions']} deletions*
"""
            
            # Post comment
            self.post_review_comment(repo_name, pr_number, comment)
            analysis['comment_posted'] = True

        # Post any plugin comments
        for res in analysis.get("plugins", []):
            if res.get("action") == "comment" and res.get("comment"):
                self.post_review_comment(repo_name, pr_number, res.get("comment"))
        
        return analysis

    def _init_plugins(self) -> PluginManager:
        mgr = PluginManager()
        enabled = set(AGENT_PLUGINS or [])
        # Enable AutoCheckCodeQuality by default or when configured
        if not enabled or "auto_check_code_quality" in enabled:
            mgr.register(AutoCheckCodeQualityPlugin())
        # Other plugins can be added here based on env
        return mgr
    
    def analyze_pr_from_webhook(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze PR from webhook payload
        
        Args:
            webhook_data: GitHub webhook payload
            
        Returns:
            Analysis results or None if not applicable
        """
        action = webhook_data.get('action')
        
        # Only analyze on opened or synchronized events
        if action not in ['opened', 'synchronize', 'reopened']:
            logger.info(f"Skipping action: {action}")
            return None
        
        pr = webhook_data.get('pull_request', {})
        repo = webhook_data.get('repository', {})
        
        repo_name = repo.get('full_name')
        pr_number = pr.get('number')
        
        if not repo_name or not pr_number:
            logger.error("Invalid webhook data")
            return None
        
        logger.info(f"📨 Webhook received for PR #{pr_number} in {repo_name}")
        
        # Auto-review with comment
        return self.auto_review_pr(repo_name, pr_number, auto_comment=True)


if __name__ == "__main__":
    # Test the agent
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    github_token = os.getenv('GITHUB_TOKEN')
    repo_name = os.getenv('REPO_FULL_NAME', 't2m19102001/github-ai-agent')
    
    if not github_token:
        print("❌ GITHUB_TOKEN not found in .env")
        exit(1)
    
    # Create agent
    agent = GitHubPRAgent(github_token)
    
    # Test with a PR number
    print("\n" + "="*70)
    print("🧪 Testing PR Analysis")
    print("="*70 + "\n")
    
    # You can change this to test with a real PR
    pr_number = 1
    
    result = agent.analyze_pr(repo_name, pr_number)
    
    if result.get('status') == 'success':
        print("✅ Analysis successful!")
        print(f"\n{result['analysis']}")
    else:
        print(f"❌ Error: {result.get('error')}")
