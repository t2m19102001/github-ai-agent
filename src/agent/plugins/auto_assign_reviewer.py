#!/usr/bin/env python3
"""
Auto Assign Reviewer Plugin
Automatically assigns reviewers to pull requests
"""

from typing import Dict, Any, List
from src.agent.plugins.base import BasePlugin, PluginConfig, PluginResult

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class AutoAssignReviewerPlugin(BasePlugin):
    """Plugin that automatically assigns reviewers to PRs"""
    
    name = "auto_assign_reviewer"
    version = "1.0.0"
    description = "Automatically assigns code reviewers based on file changes"
    triggers = ["pull_request.opened", "pull_request.synchronize"]
    
    def __init__(self):
        config = PluginConfig(
            name=self.name,
            enabled=True,
            priority=30
        )
        super().__init__(config)
        self.codeowners_patterns = {}
    
    def validate(self, context: Dict[str, Any]) -> bool:
        """Check if this plugin should run"""
        return context.get("pull_request") is not None
    
    async def execute(self, context: Dict[str, Any]) -> PluginResult:
        """Execute reviewer assignment logic"""
        try:
            pr = context["pull_request"]
            files_changed = context.get("files_changed", [])
            
            suggested_reviewers = self._determine_reviewers(files_changed, pr)
            
            github_client = context.get("github_client")
            if github_client and suggested_reviewers:
                repo = pr.get("repo", "owner/repo")
                pr_number = pr.get("number", 0)
                
                try:
                    repo_obj = github_client.get_repo(repo)
                    pr_obj = repo_obj.get_pull(pr_number)
                    pr_obj.create_review_request(reviewers=suggested_reviewers)
                    logger.info(f"Requested reviewers for PR #{pr_number}: {suggested_reviewers}")
                except Exception as e:
                    logger.warning(f"Could not request reviewers: {e}")
            
            return PluginResult(
                success=True,
                action="assign_reviewer",
                message=f"Suggested {len(suggested_reviewers)} reviewers",
                data={
                    "pr_number": pr.get("number"),
                    "reviewers_suggested": suggested_reviewers
                }
            )
            
        except Exception as e:
            logger.error(f"Auto-assign reviewer failed: {e}")
            return PluginResult(
                success=False,
                action="assign_reviewer",
                message=f"Reviewer assignment failed: {str(e)}"
            )
    
    def _determine_reviewers(self, files: List[str], pr: Dict[str, Any]) -> List[str]:
        """Determine appropriate reviewers based on file changes"""
        reviewers = []
        
        file_domains = {
            "frontend": ["src/web", "src/ui", "templates", ".html", ".css", ".js", ".jsx", ".tsx"],
            "backend": ["src/api", "src/services", "src/models", ".py"],
            "database": ["src/db", "migrations", "schema", ".sql"],
            "devops": ["docker", ".github", "scripts", ".yml", ".yaml", "kubernetes"]
        }
        
        affected_domains = set()
        for file_path in files:
            for domain, patterns in file_domains.items():
                if any(p in file_path for p in patterns):
                    affected_domains.add(domain)
        
        if "frontend" in affected_domains:
            reviewers.append("frontend-reviewer")
        if "backend" in affected_domains:
            reviewers.append("backend-reviewer")
        if "database" in affected_domains:
            reviewers.append("db-reviewer")
        if "devops" in affected_domains:
            reviewers.append("devops-reviewer")
        
        if len(files) > 10:
            reviewers.append("senior-reviewer")
        
        return reviewers[:3]


AutoAssignReviewer = AutoAssignReviewerPlugin
