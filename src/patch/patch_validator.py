#!/usr/bin/env python3
"""
Patch Validator.

Production-grade implementation with:
- Patch validation before application
- Size limit validation
- Format validation
- Syntax validation
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .patch_generator import Patch

logger = get_logger(__name__)


class ValidationStatus(Enum):
    """Validation status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


@dataclass
class ValidationIssue:
    """Validation issue."""
    type: str
    severity: ValidationStatus
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class ValidationResult:
    """Validation result."""
    status: ValidationStatus
    issues: List[ValidationIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.status == ValidationStatus.PASSED
    
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues."""
        return any(i.severity == ValidationStatus.FAILED for i in self.issues)


class PatchValidator:
    """
    Patch validator.
    
    Validates patches before application.
    """
    
    def __init__(
        self,
        max_patch_size: int = 1024 * 1024,  # 1MB
        max_line_length: int = 120,
        allow_binary: bool = False
    ):
        """
        Initialize patch validator.
        
        Args:
            max_patch_size: Maximum patch size in bytes
            max_line_length: Maximum line length
            allow_binary: Allow binary files
        """
        self.max_patch_size = max_patch_size
        self.max_line_length = max_line_length
        self.allow_binary = allow_binary
        
        logger.info(f"PatchValidator initialized (max_size: {max_patch_size} bytes)")
    
    def validate(self, patch: Patch) -> ValidationResult:
        """
        Validate patch.
        
        Args:
            patch: Patch to validate
            
        Returns:
            Validation result
        """
        issues = []
        
        # Validate size
        size_issues = self._validate_size(patch)
        issues.extend(size_issues)
        
        # Validate content
        content_issues = self._validate_content(patch)
        issues.extend(content_issues)
        
        # Validate syntax (for code files)
        syntax_issues = self._validate_syntax(patch)
        issues.extend(syntax_issues)
        
        # Determine overall status
        status = ValidationStatus.PASSED
        if any(i.severity == ValidationStatus.FAILED for i in issues):
            status = ValidationStatus.FAILED
        elif any(i.severity == ValidationStatus.WARNING for i in issues):
            status = ValidationStatus.WARNING
        
        return ValidationResult(
            status=status,
            issues=issues,
            metadata={
                "patch_size": patch.get_size(),
                "line_count": patch.get_line_count(),
                "file_path": patch.file_path,
            }
        )
    
    def _validate_size(self, patch: Patch) -> List[ValidationIssue]:
        """Validate patch size."""
        issues = []
        
        size = patch.get_size()
        if size > self.max_patch_size:
            issues.append(ValidationIssue(
                type="size_limit",
                severity=ValidationStatus.FAILED,
                message=f"Patch size ({size} bytes) exceeds limit ({self.max_patch_size} bytes)",
                file_path=patch.file_path,
            ))
        
        return issues
    
    def _validate_content(self, patch: Patch) -> List[ValidationIssue]:
        """Validate patch content."""
        issues = []
        
        lines = patch.new_content.splitlines()
        
        for line_num, line in enumerate(lines, start=1):
            # Check line length
            if len(line) > self.max_line_length:
                issues.append(ValidationIssue(
                    type="line_length",
                    severity=ValidationStatus.WARNING,
                    message=f"Line too long ({len(line)} characters, max: {self.max_line_length})",
                    file_path=patch.file_path,
                    line_number=line_num,
                ))
            
            # Check for null bytes
            if "\x00" in line:
                issues.append(ValidationIssue(
                    type="null_byte",
                    severity=ValidationStatus.FAILED,
                    message="Null byte detected in line",
                    file_path=patch.file_path,
                    line_number=line_num,
                ))
        
        return issues
    
    def _validate_syntax(self, patch: Patch) -> List[ValidationIssue]:
        """Validate syntax for code files."""
        issues = []
        
        # Only validate syntax for Python files
        if patch.file_path.endswith(".py"):
            try:
                compile(patch.new_content, patch.file_path, "exec")
            except SyntaxError as e:
                issues.append(ValidationIssue(
                    type="syntax_error",
                    severity=ValidationStatus.FAILED,
                    message=f"Syntax error: {e.msg}",
                    file_path=patch.file_path,
                    line_number=e.lineno,
                ))
        
        return issues
