"""
SWE-1.6 Interface Module.

Purpose: JSON contract for communication with SWE-1.6 execution agent.
Defines Pydantic models for request/response schemas.

Contract:
    PlanRequest (Local Agent → SWE-1.6) → PlanResponse (SWE-1.6 → Local Agent)
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Literal
from enum import Enum
from datetime import datetime
import uuid


class ChangeType(str, Enum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    RENAME = "rename"


class ValidationType(str, Enum):
    SYNTAX_CHECK = "syntax_check"
    TYPE_CHECK = "type_check"
    LINT_CHECK = "lint_check"
    TEST_RUN = "test_run"
    IMPORT_CHECK = "import_check"


class ValidationStep(BaseModel):
    """A validation step to run after changes."""
    type: ValidationType
    target: str
    command: Optional[str] = None
    expected_exit_code: int = 0
    
    @validator('command')
    def validate_command(cls, v, values):
        if values['type'] == ValidationType.TEST_RUN and not v:
            raise ValueError("Test run validation requires a command")
        return v


class FileLocation(BaseModel):
    """Location within a file."""
    start_line: int = Field(..., ge=1, description="1-indexed start line")
    end_line: int = Field(..., ge=1, description="1-indexed end line")
    
    @validator('end_line')
    def end_after_start(cls, v, values):
        if v < values['start_line']:
            raise ValueError("end_line must be >= start_line")
        return v


class RetrievedChunk(BaseModel):
    """A code chunk retrieved for context."""
    file: str
    lines: str  # "start-end" format
    content: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)


class FileChange(BaseModel):
    """A proposed change to a file."""
    file_path: str
    change_type: ChangeType
    description: str
    rationale: str
    suggested_code: Optional[str] = None
    location: Optional[FileLocation] = None
    dependencies: List[int] = Field(default_factory=list)
    
    @validator('suggested_code')
    def code_required_for_modify(cls, v, values):
        if values.get('change_type') in [ChangeType.CREATE, ChangeType.MODIFY] and not v:
            raise ValueError("suggested_code required for create/modify")
        return v


class PlanConstraints(BaseModel):
    """Constraints for plan execution."""
    auto_execute: bool = Field(default=False, description="Whether to auto-execute")
    require_approval: bool = Field(default=True, description="Require human approval")
    max_files: int = Field(default=5, ge=1, le=20)
    timeout_seconds: int = Field(default=300, ge=60, le=3600)
    allowed_extensions: List[str] = Field(default_factory=lambda: [".py"])


class PlanRequest(BaseModel):
    """Request from Local Agent to SWE-1.6 (or other execution agent)."""
    version: str = Field(default="1.0", const=True)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    goal: str = Field(..., min_length=10, max_length=1000)
    context: Dict[str, Any] = Field(..., description="Repository context")
    retrieved_chunks: List[RetrievedChunk] = Field(default_factory=list)
    changes: List[FileChange] = Field(..., min_items=1)
    validation_steps: List[ValidationStep] = Field(default_factory=list)
    constraints: PlanConstraints = Field(default_factory=PlanConstraints)
    
    @validator('changes')
    def validate_change_count(cls, v, values):
        constraints = values.get('constraints', PlanConstraints())
        if len(v) > constraints.max_files:
            raise ValueError(f"Too many files: {len(v)} > {constraints.max_files}")
        return v


class ChangeStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"


class ValidationResult(BaseModel):
    """Result of a validation step."""
    type: ValidationType
    status: Literal["passed", "failed", "error"]
    details: str
    duration_ms: Optional[int]


class ChangeResult(BaseModel):
    """Result of applying a change."""
    file_path: str
    status: ChangeStatus
    diff: Optional[str] = None
    error: Optional[str] = None
    line_changes: Optional[Dict[str, int]] = None  # {"added": 5, "removed": 3}


class ExecutionMetrics(BaseModel):
    """Metrics from execution."""
    execution_time_ms: int
    files_changed: int
    lines_added: int
    lines_removed: int
    validations_passed: int
    validations_failed: int


class LogEntry(BaseModel):
    """A log entry."""
    timestamp: datetime
    level: Literal["info", "warn", "error", "debug"]
    message: str
    details: Optional[Dict[str, Any]] = None


class PlanResponse(BaseModel):
    """Response from SWE-1.6 back to Local Agent."""
    version: str = Field(default="1.0", const=True)
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    status: Literal["completed", "failed", "partial", "cancelled"]
    changes_applied: List[ChangeResult] = Field(default_factory=list)
    validation_results: List[ValidationResult] = Field(default_factory=list)
    metrics: ExecutionMetrics
    logs: List[LogEntry] = Field(default_factory=list)
    
    # If failed
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    failed_step: Optional[int] = None


class PlanError(BaseModel):
    """Error response."""
    version: str = "1.0"
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: Literal["failed"] = "failed"
    
    error_code: Literal[
        "VALIDATION_FAILED",
        "EXECUTION_ERROR",
        "TIMEOUT",
        "PERMISSION_DENIED",
        "CONSTRAINT_VIOLATION",
        "INTERNAL_ERROR"
    ]
    error_message: str
    details: Optional[Dict[str, Any]] = None
