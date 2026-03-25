#!/usr/bin/env python3
"""
Auto Check Code Quality Plugin
Analyzes code changes for quality issues
"""

from typing import Dict, Any, List
from src.agent.plugins.base import BasePlugin, PluginConfig, PluginResult

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class AutoCheckCodeQualityPlugin(BasePlugin):
    """Plugin that automatically checks code quality on PRs/issues"""
    
    def __init__(self):
        config = PluginConfig(
            name="auto_check_code_quality",
            enabled=True,
            priority=40
        )
        super().__init__(config)
        self.quality_rules = [
            {"pattern": r"password\s*=\s*['\"][^'\"]+['\"]", "severity": "high", "message": "Hardcoded password detected"},
            {"pattern": r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", "severity": "high", "message": "Hardcoded API key detected"},
            {"pattern": r"secret\s*=\s*['\"][^'\"]+['\"]", "severity": "high", "message": "Hardcoded secret detected"},
            {"pattern": r"TODO(?!:)", "severity": "low", "message": "Incomplete TODO comment"},
            {"pattern": r"except\s*:\s*$", "severity": "medium", "message": "Bare except clause"},
            {"pattern": r"print\s*\(", "severity": "low", "message": "Debug print statement"},
        ]
    
    def validate(self, context: Dict[str, Any]) -> bool:
        """Check if this plugin should run"""
        return bool(context.get("pull_request") or context.get("code_diff"))
    
    async def execute(self, context: Dict[str, Any]) -> PluginResult:
        """Execute code quality checks"""
        try:
            code_diff = context.get("code_diff", [])
            if isinstance(code_diff, str):
                code_diff = [{"filename": "unknown", "patch": code_diff}]
            
            issues = []
            for file_change in code_diff:
                patch = file_change.get("patch", "")
                filename = file_change.get("filename", "unknown")
                
                file_issues = self._check_patch(patch, filename)
                issues.extend(file_issues)
            
            severity_counts = {"high": 0, "medium": 0, "low": 0}
            for issue in issues:
                severity_counts[issue["severity"]] += 1
            
            github_client = context.get("github_client")
            if github_client and issues:
                self._post_review_comment(github_client, context, issues)
            
            return PluginResult(
                success=True,
                action="code_quality_check",
                message=f"Found {len(issues)} code quality issues",
                data={
                    "total_issues": len(issues),
                    "by_severity": severity_counts,
                    "issues": issues[:10]
                }
            )
            
        except Exception as e:
            logger.error(f"Code quality check failed: {e}")
            return PluginResult(
                success=False,
                action="code_quality_check",
                message=f"Quality check failed: {str(e)}"
            )
    
    def _check_patch(self, patch: str, filename: str) -> List[Dict[str, Any]]:
        """Check a diff patch for quality issues"""
        import re
        issues = []
        
        for line in patch.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                content = line[1:]
                
                for rule in self.quality_rules:
                    if re.search(rule["pattern"], content, re.IGNORECASE):
                        issues.append({
                            "filename": filename,
                            "line": content[:50],
                            "severity": rule["severity"],
                            "message": rule["message"],
                            "type": "code_quality"
                        })
        
        return issues
    
    def _post_review_comment(
        self, 
        github_client, 
        context: Dict[str, Any],
        issues: List[Dict[str, Any]]
    ):
        """Post review comment to GitHub"""
        pr = context.get("pull_request", {})
        repo = pr.get("repo", "owner/repo")
        pr_number = pr.get("number", 0)
        
        if not github_client or not pr_number:
            return
        
        try:
            repo_obj = github_client.get_repo(repo)
            pr_obj = repo_obj.get_pull(pr_number)
            
            comment_body = "## Code Quality Analysis\n\n"
            comment_body += f"Found **{len(issues)}** issues:\n\n"
            
            for issue in issues[:5]:
                emoji = "🔴" if issue["severity"] == "high" else "🟡" if issue["severity"] == "medium" else "⚪"
                comment_body += f"- {emoji} **{issue['filename']}**: {issue['message']}\n"
            
            pr_obj.create_review(body=comment_body, event="COMMENT")
            logger.info(f"Posted quality review to PR #{pr_number}")
            
        except Exception as e:
            logger.warning(f"Failed to post review comment: {e}")


AutoCheckCodeQuality = AutoCheckCodeQualityPlugin
