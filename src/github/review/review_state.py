#!/usr/bin/env python3
"""
Review State Management.

Production-grade implementation with:
- Review status tracking
- State transitions
- Review metadata
"""

import uuid
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class ReviewStatus(Enum):
    """Review status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    CANCELLED = "cancelled"


@dataclass
class ReviewState:
    """Review state."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pr_number: int = 0
    repository: str = ""
    status: ReviewStatus = ReviewStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    reviewer: Optional[str] = None
    findings: List[Dict[str, Any]] = field(default_factory=list)
    comments_posted: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "pr_number": self.pr_number,
            "repository": self.repository,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "reviewer": self.reviewer,
            "findings_count": len(self.findings),
            "comments_posted": self.comments_posted,
            "metadata": self.metadata,
        }
