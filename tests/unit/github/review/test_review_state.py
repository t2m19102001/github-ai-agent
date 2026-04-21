#!/usr/bin/env python3
"""
Unit tests for Review State.
"""

import pytest
from datetime import datetime

from src.github.review.review_state import ReviewState, ReviewStatus


class TestReviewState:
    """Test ReviewState."""
    
    def test_review_state_creation(self):
        """Test review state creation."""
        state = ReviewState(
            pr_number=123,
            repository="owner/repo",
            status=ReviewStatus.IN_PROGRESS,
        )
        
        assert state.pr_number == 123
        assert state.repository == "owner/repo"
        assert state.status == ReviewStatus.IN_PROGRESS
        assert state.id is not None
    
    def test_review_state_to_dict(self):
        """Test review state serialization."""
        state = ReviewState(
            pr_number=123,
            repository="owner/repo",
            status=ReviewStatus.COMPLETED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        
        state_dict = state.to_dict()
        
        assert state_dict["pr_number"] == 123
        assert state_dict["status"] == "completed"
        assert state_dict["started_at"] is not None
