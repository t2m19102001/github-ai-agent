#!/usr/bin/env python3
"""
Security Issue Detection.

Production-grade implementation with:
- Security pattern detection
- Vulnerability identification
- Secret detection
- Injection vulnerability detection
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class SecurityIssueType(Enum):
    """Security issue types."""
    SECRET_LEAK = "secret_leak"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    AUTH_BYPASS = "auth_bypass"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    HARDcoded_CREDENTIALS = "hardcoded_credentials"
    INSECURE_RANDOM = "insecure_random"
    UNVALIDATED_INPUT = "unvalidated_input"


@dataclass
class SecurityIssue:
    """Security issue."""
    type: SecurityIssueType
    severity: Severity
    file_path: str
    line_number: int
    description: str
    recommendation: Optional[str] = None
    cve_reference: Optional[str] = None


@dataclass
class SecurityAnalysis:
    """Security analysis result."""
    issues: List[SecurityIssue] = field(default_factory=list)
    total_issues: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_issues": self.total_issues,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "issues": [
                {
                    "type": issue.type.value,
                    "severity": issue.severity.value,
                    "file_path": issue.file_path,
                    "line_number": issue.line_number,
                    "description": issue.description,
                    "recommendation": issue.recommendation,
                    "cve_reference": issue.cve_reference,
                }
                for issue in self.issues
            ],
        }


class SecurityReviewer:
    """
    Security reviewer.
    
    Detects security issues in code changes.
    """
    
    # Security patterns to detect
    SECRET_PATTERNS = [
        r"password\s*=",
        r"api_key\s*=",
        r"secret\s*=",
        r"token\s*=",
        r"private_key\s*=",
        r"credential\s*=",
    ]
    
    SQL_INJECTION_PATTERNS = [
        r"execute\s*\(",
        r"exec\s*\(",
        r"query\s*\+\s*",
        r"format\s*\(.*\%.*\)",
    ]
    
    XSS_PATTERNS = [
        r"innerHTML\s*=",
        r"outerHTML\s*=",
        r"document\.write",
        r"eval\s*\(",
    ]
    
    def __init__(self):
        """Initialize security reviewer."""
        logger.info("SecurityReviewer initialized")
    
    def analyze(self, diff_data: Dict[str, Any]) -> SecurityAnalysis:
        """
        Analyze security issues.
        
        Args:
            diff_data: GitHub diff data
            
        Returns:
            Security analysis
        """
        analysis = SecurityAnalysis()
        
        files = diff_data.get("files", [])
        
        for file in files:
            path = file.get("filename", "")
            patch = file.get("patch", "")
            
            if not patch:
                continue
            
            # Analyze patch for security issues
            file_issues = self._analyze_patch(path, patch)
            analysis.issues.extend(file_issues)
        
        # Calculate statistics
        analysis.total_issues = len(analysis.issues)
        analysis.critical_count = sum(1 for i in analysis.issues if i.severity == Severity.CRITICAL)
        analysis.high_count = sum(1 for i in analysis.issues if i.severity == Severity.HIGH)
        analysis.medium_count = sum(1 for i in analysis.issues if i.severity == Severity.MEDIUM)
        analysis.low_count = sum(1 for i in analysis.issues if i.severity == Severity.LOW)
        
        return analysis
    
    def _analyze_patch(self, file_path: str, patch: str) -> List[SecurityIssue]:
        """
        Analyze patch for security issues.
        
        Args:
            file_path: File path
            patch: Git patch content
            
        Returns:
            List of security issues
        """
        issues = []
        
        lines = patch.split("\n")
        line_number = 0
        
        for line in lines:
            if line.startswith("+"):
                line_number += 1
                content = line[1:]  # Remove + prefix
                
                # Check for security issues
                issues.extend(self._check_line_security(file_path, content, line_number))
            elif line.startswith("@@"):
                # Extract line number from hunk header
                parts = line.split(" ")
                if len(parts) > 2:
                    try:
                        line_number = int(parts[2].split(",")[0].lstrip("+"))
                    except (ValueError, IndexError):
                        pass
        
        return issues
    
    def _check_line_security(self, file_path: str, content: str, line_number: int) -> List[SecurityIssue]:
        """
        Check line for security issues.
        
        Args:
            file_path: File path
            content: Line content
            line_number: Line number
            
        Returns:
            List of security issues
        """
        issues = []
        content_lower = content.lower()
        
        # Check for hardcoded secrets
        for pattern in self.SECRET_PATTERNS:
            if pattern in content_lower:
                issues.append(SecurityIssue(
                    type=SecurityIssueType.SECRET_LEAK,
                    severity=Severity.CRITICAL,
                    file_path=file_path,
                    line_number=line_number,
                    description=f"Potential hardcoded credential: {pattern}",
                    recommendation="Use environment variables or secret management",
                ))
        
        # Check for SQL injection patterns
        for pattern in self.SQL_INJECTION_PATTERNS:
            if pattern in content_lower:
                issues.append(SecurityIssue(
                    type=SecurityIssueType.SQL_INJECTION,
                    severity=Severity.HIGH,
                    file_path=file_path,
                    line_number=line_number,
                    description=f"Potential SQL injection: {pattern}",
                    recommendation="Use parameterized queries",
                    cve_reference="CWE-89",
                ))
        
        # Check for XSS patterns
        for pattern in self.XSS_PATTERNS:
            if pattern in content_lower:
                issues.append(SecurityIssue(
                    type=SecurityIssueType.XSS,
                    severity=Severity.HIGH,
                    file_path=file_path,
                    line_number=line_number,
                    description=f"Potential XSS vulnerability: {pattern}",
                    recommendation="Use safe HTML sanitization",
                    cve_reference="CWE-79",
                ))
        
        return issues
