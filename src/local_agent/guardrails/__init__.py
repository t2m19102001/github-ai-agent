"""
Guardrails Module.

Purpose: Safety validation and filtering.
Input: File paths, suggestions
Output: Validation results

Components:
    validators: Input/output validation
    filters: Content filtering (read-only patterns)
    limits: Resource limits

Safety Rules:
    - Read-only patterns: *.json, *.yaml, .env*, config
    - Max lines without review: 1000
    - Skip generated code detection
    - Require approval for: __init__.py, conftest.py, settings.py
"""

from src.local_agent.guardrails.validators import ScopeValidator, SAFEGUARD_RULES
from src.local_agent.guardrails.filters import FileGuardrails
from src.local_agent.guardrails.limits import ResourceLimiter

__all__ = ["ScopeValidator", "SAFEGUARD_RULES", "FileGuardrails", "ResourceLimiter"]
