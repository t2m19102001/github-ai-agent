#!/usr/bin/env python3
"""
Review Comment Manager.

Production-grade implementation with:
- Safe GitHub comment posting
- Duplicate comment prevention
- Comment formatting
- Review traceability
"""

import uuid
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ReviewComment:
    """Review comment."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    body: str = ""
    severity: str = "info"  # info, warning, error
    category: str = "general"  # quality, security, performance, etc.
    posted: bool = False
    posted_at: Optional[datetime] = None
    comment_id: Optional[str] = None


class CommentManager:
    """
    Comment manager.
    
    Manages review comments with duplicate prevention.
    """
    
    def __init__(self, github_client):
        """
        Initialize comment manager.
        
        Args:
            github_client: GitHub client instance
        """
        self.github_client = github_client
        self._posted_comments: Set[str] = set()
        self._pending_comments: List[ReviewComment] = []
        
        logger.info("CommentManager initialized")
    
    def add_comment(
        self,
        body: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        severity: str = "info",
        category: str = "general"
    ) -> ReviewComment:
        """
        Add comment to pending queue.
        
        Args:
            body: Comment body
            file_path: File path (for inline comments)
            line_number: Line number (for inline comments)
            severity: Comment severity
            category: Comment category
            
        Returns:
            Review comment
        """
        comment = ReviewComment(
            body=body,
            file_path=file_path,
            line_number=line_number,
            severity=severity,
            category=category,
        )
        
        self._pending_comments.append(comment)
        
        logger.debug(f"Added comment: {category} - {severity}")
        
        return comment
    
    def is_duplicate(self, comment: ReviewComment, existing_comments: List[Dict[str, Any]]) -> bool:
        """
        Check if comment is duplicate.
        
        Args:
            comment: Comment to check
            existing_comments: Existing comments on PR
            
        Returns:
            True if duplicate, False otherwise
        """
        comment_hash = self._generate_comment_hash(comment)
        
        # Check against pending comments
        for pending in self._pending_comments:
            pending_hash = self._generate_comment_hash(pending)
            if comment_hash == pending_hash and pending.id != comment.id:
                return True
        
        # Check against posted comments
        for existing in existing_comments:
            existing_hash = self._generate_comment_hash_from_dict(existing)
            if comment_hash == existing_hash:
                return True
        
        return False
    
    def _generate_comment_hash(self, comment: ReviewComment) -> str:
        """Generate hash for duplicate detection."""
        import hashlib
        
        content = f"{comment.file_path}:{comment.line_number}:{comment.body}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _generate_comment_hash_from_dict(self, comment_dict: Dict[str, Any]) -> str:
        """Generate hash from comment dictionary."""
        import hashlib
        
        file_path = comment_dict.get("path", "")
        line_number = comment_dict.get("line", 0)
        body = comment_dict.get("body", "")
        
        content = f"{file_path}:{line_number}:{body}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def post_comments(
        self,
        pr_number: int,
        repository: str,
        existing_comments: Optional[List[Dict[str, Any]]] = None
    ) -> List[ReviewComment]:
        """
        Post pending comments to GitHub.
        
        Args:
            pr_number: PR number
            repository: Repository name (owner/repo)
            existing_comments: Existing comments for duplicate checking
            
        Returns:
            List of posted comments
        """
        existing_comments = existing_comments or []
        posted = []
        
        for comment in self._pending_comments:
            # Check for duplicates
            if self.is_duplicate(comment, existing_comments):
                logger.debug(f"Skipping duplicate comment")
                continue
            
            # Post comment
            try:
                if comment.file_path and comment.line_number:
                    # Inline comment
                    comment_id = await self.github_client.create_review_comment(
                        repository=repository,
                        pr_number=pr_number,
                        body=comment.body,
                        commit_id=None,  # Use latest commit
                        path=comment.file_path,
                        line=comment.line_number,
                    )
                else:
                    # General review comment
                    comment_id = await self.github_client.create_issue_comment(
                        repository=repository,
                        issue_number=pr_number,
                        body=comment.body,
                    )
                
                comment.posted = True
                comment.posted_at = datetime.utcnow()
                comment.comment_id = comment_id
                
                posted.append(comment)
                self._posted_comments.add(self._generate_comment_hash(comment))
                
                logger.info(f"Posted comment: {comment.category}")
                
            except Exception as e:
                logger.error(f"Failed to post comment: {e}")
        
        return posted
    
    def get_pending_comments(self) -> List[ReviewComment]:
        """Get pending comments."""
        return self._pending_comments.copy()
    
    def clear_pending(self):
        """Clear pending comments."""
        self._pending_comments.clear()
        logger.debug("Cleared pending comments")
