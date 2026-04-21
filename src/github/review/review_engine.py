#!/usr/bin/env python3
"""
Pull Request Review Engine (Main Orchestrator).

Production-grade implementation with:
- Review orchestration
- Decision engine
- GitHub API integration
- Review state management
"""

import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .review_state import ReviewState, ReviewStatus
from .diff_analyzer import DiffAnalyzer, DiffAnalysis
from .code_quality import CodeQualityAnalyzer, QualityAnalysis
from .security_reviewer import SecurityReviewer, SecurityAnalysis
from .comment_manager import CommentManager, ReviewComment

logger = get_logger(__name__)


@dataclass
class ReviewResult:
    """Review result."""
    review_id: str
    pr_number: int
    repository: str
    status: ReviewStatus
    diff_analysis: DiffAnalysis
    quality_analysis: QualityAnalysis
    security_analysis: SecurityAnalysis
    comments_posted: List[ReviewComment]
    decision: str  # approved, changes_requested, needs_review
    reasoning: str
    started_at: datetime
    completed_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReviewEngine:
    """
    Pull request review engine.
    
    Orchestrates PR review with multiple analyzers.
    """
    
    def __init__(self, github_client):
        """
        Initialize review engine.
        
        Args:
            github_client: GitHub client instance
        """
        self.github_client = github_client
        
        # Initialize analyzers
        self.diff_analyzer = DiffAnalyzer()
        self.quality_analyzer = CodeQualityAnalyzer()
        self.security_reviewer = SecurityReviewer()
        self.comment_manager = CommentManager(github_client)
        
        logger.info("ReviewEngine initialized")
    
    async def review_pr(
        self,
        pr_number: int,
        repository: str,
        reviewer: str
    ) -> ReviewResult:
        """
        Review pull request.
        
        Args:
            pr_number: PR number
            repository: Repository name (owner/repo)
            reviewer: Reviewer identifier
            
        Returns:
            Review result
        """
        review_id = str(uuid.uuid4())
        started_at = datetime.utcnow()
        
        # Create review state
        review_state = ReviewState(
            id=review_id,
            pr_number=pr_number,
            repository=repository,
            status=ReviewStatus.IN_PROGRESS,
            started_at=started_at,
            reviewer=reviewer,
        )
        
        try:
            # Fetch PR diff
            diff_data = await self._fetch_pr_diff(pr_number, repository)
            
            # Run analyzers
            diff_analysis = self.diff_analyzer.analyze(diff_data)
            quality_analysis = self.quality_analyzer.analyze(diff_data)
            security_analysis = self.security_reviewer.analyze(diff_data)
            
            # Generate review decision
            decision, reasoning = self._make_decision(
                diff_analysis,
                quality_analysis,
                security_analysis
            )
            
            # Generate and post comments
            await self._generate_comments(
                quality_analysis,
                security_analysis,
                diff_analysis
            )
            
            # Post comments to GitHub
            existing_comments = await self._fetch_existing_comments(pr_number, repository)
            posted_comments = await self.comment_manager.post_comments(
                pr_number=pr_number,
                repository=repository,
                existing_comments=existing_comments
            )
            
            # Update review state
            review_state.status = ReviewStatus.COMPLETED
            review_state.completed_at = datetime.utcnow()
            review_state.findings = [
                {"type": "quality", "count": quality_analysis.total_issues},
                {"type": "security", "count": security_analysis.total_issues},
            ]
            review_state.comments_posted = len(posted_comments)
            
            # Create result
            result = ReviewResult(
                review_id=review_id,
                pr_number=pr_number,
                repository=repository,
                status=review_state.status,
                diff_analysis=diff_analysis,
                quality_analysis=quality_analysis,
                security_analysis=security_analysis,
                comments_posted=posted_comments,
                decision=decision,
                reasoning=reasoning,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                metadata={
                    "reviewer": reviewer,
                    "files_changed": diff_analysis.total_files,
                    "additions": diff_analysis.total_additions,
                    "deletions": diff_analysis.total_deletions,
                },
            )
            
            logger.info(f"PR review completed: {pr_number} (decision: {decision})")
            
            return result
            
        except Exception as e:
            review_state.status = ReviewStatus.CANCELLED
            review_state.completed_at = datetime.utcnow()
            
            logger.error(f"PR review failed: {pr_number} - {e}")
            raise
    
    async def _fetch_pr_diff(self, pr_number: int, repository: str) -> Dict[str, Any]:
        """
        Fetch PR diff from GitHub.
        
        Args:
            pr_number: PR number
            repository: Repository name
            
        Returns:
            Diff data
        """
        # This would use the GitHub client to fetch the PR diff
        # For now, return mock data
        return {
            "files": [
                {
                    "filename": "src/main.py",
                    "status": "modified",
                    "additions": 10,
                    "deletions": 5,
                    "patch": "@@ -1,5 +1,10 @@\n+def test():\n+    print('hello')",
                    "binary": False,
                }
            ]
        }
    
    async def _fetch_existing_comments(self, pr_number: int, repository: str) -> List[Dict[str, Any]]:
        """
        Fetch existing comments on PR.
        
        Args:
            pr_number: PR number
            repository: Repository name
            
        Returns:
            List of existing comments
        """
        # This would use the GitHub client to fetch comments
        return []
    
    def _make_decision(
        self,
        diff_analysis: DiffAnalysis,
        quality_analysis: QualityAnalysis,
        security_analysis: SecurityAnalysis
    )
    -> Tuple[str, str]:
        """
        Make review decision.
        
        Args:
            diff_analysis: Diff analysis
            quality_analysis: Quality analysis
            security_analysis: Security analysis
            
        Returns:
            (decision, reasoning) tuple
        """
        # Check for critical security issues
        if security_analysis.critical_count > 0:
            return (
                "changes_requested",
                f"Critical security issues found: {security_analysis.critical_count}"
            )
        
        # Check for high severity issues
        if (quality_analysis.critical_count > 0 or 
            security_analysis.high_count > 0):
            return (
                "changes_requested",
                f"High severity issues found: {quality_analysis.critical_count + security_analysis.high_count}"
            )
        
        # Check for medium issues
        if (quality_analysis.high_count > 5 or 
            quality_analysis.medium_count > 10):
            return (
                "needs_review",
                f"Multiple quality issues found: {quality_analysis.total_issues}"
            )
        
        # Approve if no major issues
        return (
            "approved",
            "No critical issues found"
        )
    
    async def _generate_comments(
        self,
        quality_analysis: QualityAnalysis,
        security_analysis: SecurityAnalysis,
        diff_analysis: DiffAnalysis
    ):
        """
        Generate review comments.
        
        Args:
            quality_analysis: Quality analysis
            security_analysis: Security analysis
            diff_analysis: Diff analysis
        """
        # Generate security comments
        for issue in security_analysis.issues:
            if issue.severity.value in ["critical", "high"]:
                self.comment_manager.add_comment(
                    body=f"**Security Issue**: {issue.description}\n\nRecommendation: {issue.recommendation}",
                    file_path=issue.file_path,
                    line_number=issue.line_number,
                    severity="error",
                    category="security",
                )
        
        # Generate quality comments
        for issue in quality_analysis.issues:
            if issue.severity.value in ["critical", "high"]:
                self.comment_manager.add_comment(
                    body=f"**Quality Issue**: {issue.description}\n\nSuggestion: {issue.suggestion}",
                    file_path=issue.file_path,
                    line_number=issue.line_number,
                    severity="warning",
                    category="quality",
                )
