#!/usr/bin/env python3
"""
Unit tests for Comment Manager.
"""

import pytest
from unittest.mock import AsyncMock

from src.github.review.comment_manager import CommentManager, ReviewComment


class TestCommentManager:
    """Test CommentManager."""
    
    def test_manager_initialization(self):
        """Test manager initialization."""
        github_client = AsyncMock()
        manager = CommentManager(github_client)
        
        assert manager is not None
    
    def test_add_comment(self):
        """Test adding comment."""
        github_client = AsyncMock()
        manager = CommentManager(github_client)
        
        comment = manager.add_comment(
            body="Test comment",
            file_path="src/main.py",
            line_number=10,
            severity="warning",
            category="quality"
        )
        
        assert comment.body == "Test comment"
        assert comment.file_path == "src/main.py"
        assert comment.line_number == 10
        assert comment.severity == "warning"
        assert comment.category == "quality"
        assert comment.posted is False
    
    def test_duplicate_detection(self):
        """Test duplicate comment detection."""
        github_client = AsyncMock()
        manager = CommentManager(github_client)
        
        comment1 = manager.add_comment(
            body="Test comment",
            file_path="src/main.py",
            line_number=10
        )
        
        comment2 = manager.add_comment(
            body="Test comment",
            file_path="src/main.py",
            line_number=10
        )
        
        # Check if duplicate
        is_duplicate = manager.is_duplicate(comment2, [])
        
        assert is_duplicate is True
    
    def test_get_pending_comments(self):
        """Test getting pending comments."""
        github_client = AsyncMock()
        manager = CommentManager(github_client)
        
        manager.add_comment(body="Comment 1")
        manager.add_comment(body="Comment 2")
        
        pending = manager.get_pending_comments()
        
        assert len(pending) == 2
    
    def test_clear_pending(self):
        """Test clearing pending comments."""
        github_client = AsyncMock()
        manager = CommentManager(github_client)
        
        manager.add_comment(body="Comment 1")
        manager.clear_pending()
        
        pending = manager.get_pending_comments()
        
        assert len(pending) == 0
