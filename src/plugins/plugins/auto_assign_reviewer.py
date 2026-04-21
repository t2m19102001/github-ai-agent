#!/usr/bin/env python3
"""
Auto Assign Reviewer Plugin
Automatically assigns reviewers to pull requests
"""

from typing import Any, Dict, List

from .base import BasePlugin, PluginResult


class AutoAssignReviewerPlugin(BasePlugin):
    """Plugin that automatically assigns reviewers to PRs"""
    
    name = "auto_assign_reviewer"
    version = "1.0.0"
    triggers = ["pull_request.opened", "pull_request.synchronize"]
    enabled = True
    
    def should_run(self, event: Dict[str, Any]) -> bool:
        return "pull_request" in event
    
    def validate(self, context: Dict[str, Any]) -> bool:
        """Check if this plugin should run"""
        return context.get("pull_request") is not None
    
    async def execute(self, context: Dict[str, Any]) -> PluginResult:
        """Execute reviewer assignment logic"""
        try:
            pr = context.get("pull_request", {})
            files_changed = context.get("files_changed", [])
            
            suggested_reviewers = self._determine_reviewers(files_changed, pr)
            
            return PluginResult(
                success=True,
                action="assign_reviewer",
                message=f"Suggested {len(suggested_reviewers)} reviewers",
                data={
                    "pr_number": pr.get("number"),
                    "reviewers_suggested": suggested_reviewers
                },
                plugin=self.name
            )
            
        except Exception as e:
            return PluginResult(
                success=False,
                action="assign_reviewer",
                message=f"Reviewer assignment failed: {str(e)}",
                plugin=self.name
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
    
    def get_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "enabled": self.enabled,
            "triggers": self.triggers
        }


AutoAssignReviewer = AutoAssignReviewerPlugin
