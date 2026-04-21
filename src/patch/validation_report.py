#!/usr/bin/env python3
"""
Validation Report.

Production-grade implementation with:
- Comprehensive validation report
- Issue aggregation
- Summary generation
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .patch_generator import Patch
from .patch_validator import ValidationResult
from .security_scanner import SecurityFinding
from .coverage_validator import CoverageValidationResult
from .rollback_validator import RollbackValidationResult

logger = get_logger(__name__)


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    patch_id: str
    file_path: str
    validation_result: ValidationResult
    security_findings: List[SecurityFinding]
    coverage_result: Optional[CoverageValidationResult]
    rollback_result: RollbackValidationResult
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_safe_to_apply(self) -> bool:
        """Check if patch is safe to apply."""
        # Must pass validation
        if not self.validation_result.is_valid():
            return False
        
        # Must have no critical security findings
        critical_security = any(
            f.severity.value == "failed" for f in self.security_findings
        )
        if critical_security:
            return False
        
        # Must be able to rollback
        if not self.rollback_result.can_rollback:
            return False
        
        return True
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        return {
            "patch_id": self.patch_id,
            "file_path": self.file_path,
            "is_safe_to_apply": self.is_safe_to_apply(),
            "validation_status": self.validation_result.status.value,
            "validation_issues_count": len(self.validation_result.issues),
            "security_findings_count": len(self.security_findings),
            "critical_security_count": sum(
                1 for f in self.security_findings if f.severity.value == "failed"
            ),
            "coverage_percentage": self.coverage_result.coverage_percentage if self.coverage_result else None,
            "can_rollback": self.rollback_result.can_rollback,
            "generated_at": self.generated_at.isoformat(),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "patch_id": self.patch_id,
            "file_path": self.file_path,
            "validation_result": {
                "status": self.validation_result.status.value,
                "issues": [
                    {
                        "type": i.type,
                        "severity": i.severity.value,
                        "message": i.message,
                        "file_path": i.file_path,
                        "line_number": i.line_number,
                    }
                    for i in self.validation_result.issues
                ],
            },
            "security_findings": [
                {
                    "type": f.type.value,
                    "severity": f.severity.value,
                    "description": f.description,
                    "file_path": f.file_path,
                    "line_number": f.line_number,
                    "recommendation": f.recommendation,
                    "cve_reference": f.cve_reference,
                }
                for f in self.security_findings
            ],
            "coverage_result": {
                "status": self.coverage_result.status.value if self.coverage_result else None,
                "coverage_percentage": self.coverage_result.coverage_percentage if self.coverage_result else None,
                "threshold": self.coverage_result.threshold if self.coverage_result else None,
            } if self.coverage_result else None,
            "rollback_result": {
                "status": self.rollback_result.status.value,
                "can_rollback": self.rollback_result.can_rollback,
                "rollback_strategy": self.rollback_result.rollback_strategy,
            },
            "is_safe_to_apply": self.is_safe_to_apply(),
            "generated_at": self.generated_at.isoformat(),
        }


class ValidationReportGenerator:
    """
    Validation report generator.
    
    Generates comprehensive validation reports.
    """
    
    def __init__(self):
        """Initialize report generator."""
        logger.info("ValidationReportGenerator initialized")
    
    def generate(
        self,
        patch: Patch,
        validation_result: ValidationResult,
        security_findings: List[SecurityFinding],
        coverage_result: Optional[CoverageValidationResult],
        rollback_result: RollbackValidationResult
    ) -> ValidationReport:
        """
        Generate validation report.
        
        Args:
            patch: Patch being validated
            validation_result: Validation result
            security_findings: Security findings
            coverage_result: Coverage validation result
            rollback_result: Rollback validation result
            
        Returns:
            Validation report
        """
        report = ValidationReport(
            patch_id=patch.id,
            file_path=patch.file_path,
            validation_result=validation_result,
            security_findings=security_findings,
            coverage_result=coverage_result,
            rollback_result=rollback_result,
        )
        
        logger.info(f"Generated validation report for {patch.file_path}")
        
        return report
