"""
Output Schema Module.

Purpose: Dataclasses for PlanOutput and related types.
"""

from dataclasses import dataclass
from typing import List, Optional, Literal
from enum import Enum


class ChangeType(Enum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    RENAME = "rename"


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class CodeChange:
    """A specific code change."""
    type: ChangeType
    description: str
    location: str
    suggested_code: Optional[str]
    rationale: str


@dataclass
class FileChange:
    """All changes for a single file."""
    path: str
    rationale: str
    current_state_summary: str
    changes: List[CodeChange]
    confidence: float


@dataclass
class PlanStep:
    """A single step in an implementation plan."""
    order: int
    action: str
    target_file: str
    description: str
    depends_on: List[int]
    validation: str
    estimated_time_minutes: int
    confidence: float


@dataclass
class RiskItem:
    """An identified risk."""
    description: str
    severity: Severity
    probability: float
    mitigation: str
    contingency: Optional[str]


@dataclass
class PlanOutput:
    """Complete implementation plan."""
    goal: str
    assumptions: List[str]
    files_to_change: List[FileChange]
    steps: List[PlanStep]
    risks: List[RiskItem]
    validation_overall: str
    estimated_effort: str
    overall_confidence: float
    confidence_rationale: str
