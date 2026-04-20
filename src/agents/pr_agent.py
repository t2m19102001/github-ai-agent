#!/usr/bin/env python3
"""
PR Analysis Agent
Analyzes pull requests for code quality, security, and best practices
"""

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

try:
    from src.agents.base_agent import BaseAgent, AgentContext
except ImportError:
    from src.agents.base import Agent

from src.tools.pr_tools import (
    SecurityCheckTool,
    PerformanceCheckTool,
    CodeQualityTool,
    DiffAnalysisTool,
    CoverageAnalysisTool
)

logger = get_logger(__name__)


@dataclass
class PRAnalysisResult:
    """Result of PR analysis"""
    pr_number: int
    title: str
    security_issues: List[Dict[str, Any]]
    performance_issues: List[Dict[str, Any]]
    quality_issues: List[Dict[str, Any]]
    summary: str
    recommendations: List[str]
    risk_score: float
    can_merge: bool


class GitHubPRAgent:
    """Agent for analyzing GitHub pull requests"""
    
    name = "GitHubPRAgent"
    description = "Analyzes PRs for security, performance, and code quality"
    
    def __init__(self, github_token: str = None):
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.llm = None
        
        self.security_tool = SecurityCheckTool()
        self.performance_tool = PerformanceCheckTool()
        self.quality_tool = CodeQualityTool()
        self.diff_tool = DiffAnalysisTool()
        self.coverage_tool = CoverageAnalysisTool()
        
        logger.info(f"GitHubPRAgent initialized with token: {'Yes' if self.github_token else 'No'}")
    
    def analyze_pr(
        self,
        pr_data: Dict[str, Any],
        code_diff: str = None,
        files_changed: List[Dict[str, str]] = None
    ) -> PRAnalysisResult:
        """Analyze a pull request"""
        security_issues = []
        performance_issues = []
        quality_issues = []
        recommendations = []
        
        if files_changed:
            for file_info in files_changed:
                filename = file_info.get("filename", "unknown")
                content = file_info.get("content", file_info.get("patch", ""))
                
                if file_info.get("patch"):
                    content = "\n".join([
                        line for line in file_info["patch"].split("\n")
                        if line.startswith("+") and not line.startswith("+++")
                    ])
                
                security_issues.extend(self.security_tool.execute(content, filename))
                performance_issues.extend(self.performance_tool.execute(content, filename))
                quality_issues.extend(self.quality_tool.execute(content, filename))
        
        elif code_diff:
            security_issues = self.security_tool.execute(code_diff, "diff")
            performance_issues = self.performance_tool.execute(code_diff, "diff")
            quality_issues = self.quality_tool.execute(code_diff, "diff")
        
        risk_score = self._calculate_risk_score(
            security_issues,
            performance_issues,
            quality_issues
        )
        
        can_merge = risk_score < 7.0 and not any(
            s["severity"] == "high" for s in security_issues
        )
        
        summary = self._generate_summary(
            pr_data.get("title", ""),
            security_issues,
            performance_issues,
            quality_issues
        )
        
        recommendations = self._generate_recommendations(
            security_issues,
            performance_issues,
            quality_issues
        )
        
        return PRAnalysisResult(
            pr_number=pr_data.get("number", 0),
            title=pr_data.get("title", ""),
            security_issues=security_issues,
            performance_issues=performance_issues,
            quality_issues=quality_issues,
            summary=summary,
            recommendations=recommendations,
            risk_score=risk_score,
            can_merge=can_merge
        )
    
    def _calculate_risk_score(
        self,
        security_issues: List[Dict],
        performance_issues: List[Dict],
        quality_issues: List[Dict]
    ) -> float:
        """Calculate overall risk score (0-10)"""
        score = 0.0
        
        severity_weights = {"high": 3.0, "medium": 1.5, "low": 0.5, "info": 0.1}
        
        for issue in security_issues:
            score += severity_weights.get(issue.get("severity", "low"), 1.0) * 2
        
        for issue in performance_issues:
            score += severity_weights.get(issue.get("severity", "low"), 1.0)
        
        for issue in quality_issues:
            if issue.get("severity") in ["medium", "high"]:
                score += 0.5
        
        return min(score, 10.0)
    
    def _generate_summary(
        self,
        title: str,
        security_issues: List[Dict],
        performance_issues: List[Dict],
        quality_issues: List[Dict]
    ) -> str:
        """Generate a summary of the analysis"""
        high_severity_security = sum(
            1 for i in security_issues if i.get("severity") == "high"
        )
        
        total_issues = len(security_issues) + len(performance_issues) + len(quality_issues)
        
        summary_parts = [f"Found {total_issues} total issues in PR: '{title}'"]
        
        if high_severity_security > 0:
            summary_parts.append(f"⚠️ {high_severity_security} HIGH severity security issues")
        
        if security_issues:
            summary_parts.append(f"Security: {len(security_issues)} issues")
        if performance_issues:
            summary_parts.append(f"Performance: {len(performance_issues)} issues")
        if quality_issues:
            summary_parts.append(f"Code Quality: {len(quality_issues)} issues")
        
        return ". ".join(summary_parts)
    
    def _generate_recommendations(
        self,
        security_issues: List[Dict],
        performance_issues: List[Dict],
        quality_issues: List[Dict]
    ) -> List[str]:
        """Generate recommendations based on issues"""
        recommendations = []
        
        if any(i.get("type") == "hardcoded_password" for i in security_issues):
            recommendations.append("Use environment variables or secrets manager for sensitive data")
        
        if any(i.get("type") == "sql_injection" for i in security_issues):
            recommendations.append("Use parameterized queries to prevent SQL injection")
        
        if any(i.get("type") == "n_plus_one_query" for i in performance_issues):
            recommendations.append("Consider eager loading or batch queries to reduce database calls")
        
        if any(i.get("type") == "bare_except" for i in quality_issues):
            recommendations.append("Catch specific exceptions instead of using bare except")
        
        if any(i.get("type") == "debug_print" for i in quality_issues):
            recommendations.append("Remove debug print statements or use proper logging")
        
        if any(i.get("type") == "incomplete_todo" for i in quality_issues):
            recommendations.append("Complete or remove TODO comments before merging")
        
        if not recommendations:
            recommendations.append("No critical issues found. PR looks good to merge!")
        
        return recommendations
    
    def get_review_comment(self, analysis: PRAnalysisResult) -> str:
        """Generate a GitHub PR review comment"""
        comment = f"""## 📊 PR Analysis Results

### Summary
{analysis.summary}

### Risk Score: {analysis.risk_score}/10
**Status:** {'✅ Can Merge' if analysis.can_merge else '❌ Needs Attention'}

"""

        if analysis.security_issues:
            comment += "### 🛡️ Security Issues ({count})\n".format(count=len(analysis.security_issues))
            for issue in analysis.security_issues[:5]:
                severity_emoji = "🔴" if issue.get("severity") == "high" else "🟡"
                comment += f"- {severity_emoji} `{issue.get('file', 'file')}:{issue.get('line', '?')}` - {issue.get('message', 'Issue')}\n"
            comment += "\n"

        if analysis.performance_issues:
            comment += "### ⚡ Performance Issues ({count})\n".format(count=len(analysis.performance_issues))
            for issue in analysis.performance_issues[:5]:
                comment += f"- 🟠 `{issue.get('file', 'file')}:{issue.get('line', '?')}` - {issue.get('message', 'Issue')}\n"
            comment += "\n"

        if analysis.quality_issues:
            comment += "### 💎 Code Quality ({count})\n".format(count=len(analysis.quality_issues))
            for issue in analysis.quality_issues[:5]:
                comment += f"- ⚪ `{issue.get('file', 'file')}:{issue.get('line', '?')}` - {issue.get('message', 'Issue')}\n"
            comment += "\n"

        if analysis.recommendations:
            comment += "### 💡 Recommendations\n"
            for rec in analysis.recommendations:
                comment += f"- {rec}\n"

        comment += f"\n---\n*Analyzed by GitHub AI Agent*"
        
        return comment


def get_pr_agent(github_token: str = None) -> GitHubPRAgent:
    """Factory function to get PR agent instance"""
    return GitHubPRAgent(github_token)


__all__ = ["GitHubPRAgent", "PRAnalysisResult", "get_pr_agent"]
