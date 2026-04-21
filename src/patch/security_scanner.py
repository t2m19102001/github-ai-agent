#!/usr/bin/env python3
"""
Security Scanner.

Production-grade implementation with:
- Dangerous code detection
- Secret detection
- Forbidden pattern detection
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .patch_generator import Patch
from .patch_validator import ValidationStatus

logger = get_logger(__name__)


class SecurityIssueType(Enum):
    """Security issue types."""
    SECRET_LEAK = "secret_leak"
    DANGEROUS_CODE = "dangerous_code"
    FORBIDDEN_PATTERN = "forbidden_pattern"
    INSECURE_FUNCTION = "insecure_function"
    VULNERABLE_DEPENDENCY = "vulnerable_dependency"


@dataclass
class SecurityFinding:
    """Security finding."""
    type: SecurityIssueType
    severity: ValidationStatus
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    recommendation: Optional[str] = None
    cve_reference: Optional[str] = None


class SecurityScanner:
    """
    Security scanner.
    
    Scans patches for security issues.
    """
    
    # Secret patterns
    SECRET_PATTERNS = [
        r"password\s*[=:]",
        r"api_key\s*[=:]",
        r"secret\s*[=:]",
        r"token\s*[=:]",
        r"private_key\s*[=:]",
        r"credential\s*[=:]",
        r"aws_access_key",
        r"aws_secret_key",
        r"bearer\s+token",
    ]
    
    # Dangerous code patterns
    DANGEROUS_PATTERNS = [
        r"exec\s*\(",
        r"eval\s*\(",
        r"system\s*\(",
        r"subprocess\.call\s*\(",
        r"__import__\s*\(",
        r"getattr\s*\(",
        r"setattr\s*\(",
        r"compile\s*\(",
        r"pickle\.loads",
        r"marshal\.loads",
        r"yaml\.load\s*\(",
    ]
    
    # Forbidden patterns
    FORBIDDEN_PATTERNS = [
        r"debug\s*=",
        r"debugger",
        r"pdb\.set_trace",
        r"ipdb\.set_trace",
        r"console\.log",
        r"TODO\s*:",
        r"FIXME\s*:",
        r"XXX\s*:",
        r"HACK\s*:",
    ]
    
    def __init__(self):
        """Initialize security scanner."""
        logger.info("SecurityScanner initialized")
    
    def scan(self, patch: Patch) -> List[SecurityFinding]:
        """
        Scan patch for security issues.
        
        Args:
            patch: Patch to scan
            
        Returns:
            List of security findings
        """
        findings = []
        
        # Scan for secrets
        secret_findings = self._scan_secrets(patch)
        findings.extend(secret_findings)
        
        # Scan for dangerous code
        dangerous_findings = self._scan_dangerous_code(patch)
        findings.extend(dangerous_findings)
        
        # Scan for forbidden patterns
        forbidden_findings = self._scan_forbidden_patterns(patch)
        findings.extend(forbidden_findings)
        
        logger.info(f"Security scan complete: {len(findings)} findings")
        
        return findings
    
    def _scan_secrets(self, patch: Patch) -> List[SecurityFinding]:
        """Scan for secret leaks."""
        findings = []
        
        lines = patch.new_content.splitlines()
        
        for line_num, line in enumerate(lines, start=1):
            line_lower = line.lower()
            
            for pattern in self.SECRET_PATTERNS:
                if pattern in line_lower:
                    findings.append(SecurityFinding(
                        type=SecurityIssueType.SECRET_LEAK,
                        severity=ValidationStatus.FAILED,
                        description=f"Potential secret leak: {pattern}",
                        file_path=patch.file_path,
                        line_number=line_num,
                        recommendation="Use environment variables or secret management",
                    ))
                    break  # Only report once per line
        
        return findings
    
    def _scan_dangerous_code(self, patch: Patch) -> List[SecurityFinding]:
        """Scan for dangerous code patterns."""
        findings = []
        
        lines = patch.new_content.splitlines()
        
        for line_num, line in enumerate(lines, start=1):
            line_lower = line.lower()
            
            for pattern in self.DANGEROUS_PATTERNS:
                if pattern in line_lower:
                    findings.append(SecurityFinding(
                        type=SecurityIssueType.DANGEROUS_CODE,
                        severity=ValidationStatus.FAILED,
                        description=f"Dangerous code pattern: {pattern}",
                        file_path=patch.file_path,
                        line_number=line_num,
                        recommendation="Review and remove or sanitize input",
                    ))
                    break  # Only report once per line
        
        return findings
    
    def _scan_forbidden_patterns(self, patch: Patch) -> List[SecurityFinding]:
        """Scan for forbidden patterns."""
        findings = []
        
        lines = patch.new_content.splitlines()
        
        for line_num, line in enumerate(lines, start=1):
            line_lower = line.lower()
            
            for pattern in self.FORBIDDEN_PATTERNS:
                if pattern in line_lower:
                    findings.append(SecurityFinding(
                        type=SecurityIssueType.FORBIDDEN_PATTERN,
                        severity=ValidationStatus.WARNING,
                        description=f"Forbidden pattern: {pattern}",
                        file_path=patch.file_path,
                        line_number=line_num,
                        recommendation="Remove or create tracking issue",
                    ))
                    break  # Only report once per line
        
        return findings
