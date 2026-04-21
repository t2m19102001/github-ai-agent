#!/usr/bin/env python3
"""
Migration Safety Validator.

Production-grade implementation with:
- Migration validation before deployment
- Database safety checks
- Rollback plan validation
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class MigrationType(Enum):
    """Migration types."""
    SCHEMA = "schema"
    DATA = "data"
    INDEX = "index"
    FUNCTION = "function"
    TRIGGER = "trigger"


class MigrationRisk(Enum):
    """Migration risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MigrationValidationResult:
    """Migration validation result."""
    is_safe: bool
    risk_level: MigrationRisk
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    can_rollback: bool = True
    rollback_steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MigrationValidator:
    """
    Migration validator.
    
    Validates migrations for safety before deployment.
    """
    
    # Dangerous SQL patterns
    DANGEROUS_PATTERNS = [
        "DROP TABLE",
        "DROP DATABASE",
        "TRUNCATE",
        "DELETE FROM",
        "ALTER TABLE.*DROP COLUMN",
        "ALTER TABLE.*DROP CONSTRAINT",
    ]
    
    # Data loss patterns
    DATA_LOSS_PATTERNS = [
        "DROP COLUMN",
        "DROP TABLE",
        "TRUNCATE",
        "DELETE FROM",
    ]
    
    def __init__(self):
        """Initialize migration validator."""
        logger.info("MigrationValidator initialized")
    
    def validate(self, migration_sql: str, rollback_sql: Optional[str] = None) -> MigrationValidationResult:
        """
        Validate migration SQL.
        
        Args:
            migration_sql: Migration SQL
            rollback_sql: Rollback SQL (if available)
            
        Returns:
            Migration validation result
        """
        issues = []
        warnings = []
        risk_level = MigrationRisk.LOW
        
        # Check for dangerous patterns
        dangerous_issues = self._check_dangerous_patterns(migration_sql)
        issues.extend(dangerous_issues)
        
        if dangerous_issues:
            risk_level = max(risk_level, MigrationRisk.CRITICAL)
        
        # Check for data loss
        data_loss_issues = self._check_data_loss(migration_sql)
        issues.extend(data_loss_issues)
        
        if data_loss_issues:
            risk_level = max(risk_level, MigrationRisk.HIGH)
        
        # Check for rollback availability
        can_rollback = self._check_rollback_availability(rollback_sql)
        
        if not can_rollback:
            risk_level = max(risk_level, MigrationRisk.HIGH)
            warnings.append("No rollback SQL provided")
        
        # Determine safety
        is_safe = (
            len(issues) == 0 and
            risk_level in {MigrationRisk.LOW, MigrationRisk.MEDIUM} and
            can_rollback
        )
        
        # Generate rollback steps
        rollback_steps = self._generate_rollback_steps(rollback_sql)
        
        return MigrationValidationResult(
            is_safe=is_safe,
            risk_level=risk_level,
            issues=issues,
            warnings=warnings,
            can_rollback=can_rollback,
            rollback_steps=rollback_steps,
            metadata={
                "migration_length": len(migration_sql),
                "has_rollback": rollback_sql is not None,
            }
        )
    
    def _check_dangerous_patterns(self, sql: str) -> List[str]:
        """Check for dangerous SQL patterns."""
        import re
        
        issues = []
        
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                issues.append(f"Dangerous pattern detected: {pattern}")
        
        return issues
    
    def _check_data_loss(self, sql: str) -> List[str]:
        """Check for data loss patterns."""
        import re
        
        issues = []
        
        for pattern in self.DATA_LOSS_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                issues.append(f"Data loss risk: {pattern}")
        
        return issues
    
    def _check_rollback_availability(self, rollback_sql: Optional[str]) -> bool:
        """Check if rollback SQL is available."""
        return rollback_sql is not None and len(rollback_sql.strip()) > 0
    
    def _generate_rollback_steps(self, rollback_sql: Optional[str]) -> List[str]:
        """Generate rollback steps."""
        if not rollback_sql:
            return ["No rollback SQL available - manual rollback required"]
        
        # Parse rollback SQL into steps
        steps = []
        statements = rollback_sql.split(";")
        
        for i, statement in enumerate(statements, start=1):
            statement = statement.strip()
            if statement:
                steps.append(f"Step {i}: {statement[:100]}...")
        
        return steps
