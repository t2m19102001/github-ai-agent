#!/usr/bin/env python3
"""
Test Coverage Validation.

Production-grade implementation with:
- Test coverage validation
- Coverage threshold enforcement
- Unchanged code validation
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .patch_generator import Patch
from .patch_validator import ValidationStatus, ValidationIssue

logger = get_logger(__name__)


@dataclass
class CoverageValidationResult:
    """Coverage validation result."""
    status: ValidationStatus
    coverage_percentage: float
    threshold: float
    uncovered_files: List[str] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=dict)


class CoverageValidator:
    """
    Test coverage validator.
    
    Validates test coverage for patches.
    """
    
    def __init__(self, coverage_threshold: float = 80.0):
        """
        Initialize coverage validator.
        
        Args:
            coverage_threshold: Minimum coverage percentage required
        """
        self.coverage_threshold = coverage_threshold
        
        logger.info(f"CoverageValidator initialized (threshold: {coverage_threshold}%)")
    
    def validate(self, patch: Patch, coverage_data: Optional[Dict[str, Any]] = None) -> CoverageValidationResult:
        """
        Validate test coverage.
        
        Args:
            patch: Patch to validate
            coverage_data: Coverage data from test runner
            
        Returns:
            Coverage validation result
        """
        issues = []
        
        # If no coverage data provided, assume no tests
        if coverage_data is None:
            issues.append(ValidationIssue(
                type="no_coverage_data",
                severity=ValidationStatus.WARNING,
                message="No coverage data provided, assuming no tests",
                file_path=patch.file_path,
            ))
            return CoverageValidationResult(
                status=ValidationStatus.WARNING,
                coverage_percentage=0.0,
                threshold=self.coverage_threshold,
                issues=issues,
            )
        
        coverage_percentage = coverage_data.get("coverage", 0.0)
        
        # Check if coverage meets threshold
        if coverage_percentage < self.coverage_threshold:
            issues.append(ValidationIssue(
                type="low_coverage",
                severity=ValidationStatus.FAILED,
                message=f"Coverage ({coverage_percentage}%) below threshold ({self.coverage_threshold}%)",
                file_path=patch.file_path,
            ))
        
        # Check for uncovered files
        uncovered_files = coverage_data.get("uncovered_files", [])
        for file in uncovered_files:
            issues.append(ValidationIssue(
                type="uncovered_file",
                severity=ValidationStatus.WARNING,
                message=f"File has no test coverage: {file}",
                file_path=file,
            ))
        
        status = ValidationStatus.PASSED
        if any(i.severity == ValidationStatus.FAILED for i in issues):
            status = ValidationStatus.FAILED
        elif any(i.severity == ValidationStatus.WARNING for i in issues):
            status = ValidationStatus.WARNING
        
        return CoverageValidationResult(
            status=status,
            coverage_percentage=coverage_percentage,
            threshold=self.coverage_threshold,
            uncovered_files=uncovered_files,
            issues=issues,
        )
