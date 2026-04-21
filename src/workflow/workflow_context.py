#!/usr/bin/env python3
"""
Workflow Context.

Production-grade implementation with:
- Distributed tracing context
- Request ID tracking
- Metadata management
"""

import uuid
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from src.observability.tracing import TraceContext

logger = get_logger(__name__)


@dataclass
class WorkflowContext:
    """Workflow execution context."""
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_context: Optional[TraceContext] = None
    github_event_id: Optional[str] = None
    github_event_type: Optional[str] = None
    repository: Optional[str] = None
    pr_number: Optional[int] = None
    issue_number: Optional[int] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "request_id": self.request_id,
            "trace_id": self.trace_context.trace_id if self.trace_context else None,
            "github_event_id": self.github_event_id,
            "github_event_type": self.github_event_type,
            "repository": self.repository,
            "pr_number": self.pr_number,
            "issue_number": self.issue_number,
            "started_at": self.started_at.isoformat(),
            "metadata": self.metadata,
        }
