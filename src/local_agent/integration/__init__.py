"""
Integration Module.

Purpose: External API integrations.
Input: Plans, requests
Output: JSON responses

Components:
    swe16_interface: SWE-1.6 JSON contract (Pydantic models)

Contract:
    PlanRequest → SWE-1.6 → PlanResponse
"""

from src.local_agent.integration.swe16_interface import (
    ChangeType,
    ValidationType,
    ValidationStep,
    FileLocation,
    RetrievedChunk,
    FileChange,
    PlanConstraints,
    PlanRequest,
    ChangeStatus,
    ValidationResult,
    ChangeResult,
    ExecutionMetrics,
    LogEntry,
    PlanResponse,
    PlanError,
)
from src.local_agent.integration.plan_builder import PlanRequestBuilder

__all__ = [
    "ChangeType",
    "ValidationType",
    "ValidationStep",
    "FileLocation",
    "RetrievedChunk",
    "FileChange",
    "PlanConstraints",
    "PlanRequest",
    "ChangeStatus",
    "ValidationResult",
    "ChangeResult",
    "ExecutionMetrics",
    "LogEntry",
    "PlanResponse",
    "PlanError",
    "PlanRequestBuilder",
]
