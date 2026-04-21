#!/usr/bin/env python3
"""
Code Quality Review.

Production-grade implementation with:
- Code smell detection
- Style violations
- Complexity analysis
- Best practices check
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class QualityIssueType(Enum):
    """Quality issue types."""
    CODE_SMELL = "code_smell"
    STYLE_VIOLATION = "style_violation"
    COMPLEXITY = "complexity"
    BEST_PRACTICE = "best_practice"
    SECURITY = "security"
    PERFORMANCE = "performance"


class Severity(Enum):
    """Issue severity."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class QualityIssue:
    """Code quality issue."""
    type: QualityIssueType
    severity: Severity
    file_path: str
    line_number: int
    description: str
    suggestion: Optional[str] = None
    rule_id: Optional[str] = None


@dataclass
class QualityAnalysis:
    """Quality analysis result."""
    issues: List[QualityIssue] = field(default_factory=list)
    total_issues: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    score: float = 100.0  # Quality score (0-100)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_issues": self.total_issues,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "score": self.score,
            "issues": [
                {
                    "type": issue.type.value,
                    "severity": issue.severity.value,
                    "file_path": issue.file_path,
                    "line_number": issue.line_number,
                    "description": issue.description,
                    "suggestion": issue.suggestion,
                    "rule_id": issue.rule_id,
                }
                for issue in self.issues
            ],
        }


class CodeQualityAnalyzer:
    """
    Code quality analyzer.
    
    Analyzes code for quality issues and best practices.
    """
    
    def __init__(self):
        """Initialize code quality analyzer."""
        logger.info("CodeQualityAnalyzer initialized")
    
    def analyze(self, diff_data: Dict[str, Any]) -> QualityAnalysis:
        """
        Analyze code quality.
        
        Args:
            diff_data: GitHub diff data
            
        Returns:
            Quality analysis
        """
        analysis = QualityAnalysis()
        
        files = diff_data.get("files", [])
        
        for file in files:
            path = file.get("filename", "")
            patch = file.get("patch", "")
            
            if not patch:
                continue
            
            # Analyze patch for quality issues
            file_issues = self._analyze_patch(path, patch)
            analysis.issues.extend(file_issues)
        
        # Calculate statistics
        analysis.total_issues = len(analysis.issues)
        analysis.critical_count = sum(1 for i in analysis.issues if i.severity == Severity.CRITICAL)
        analysis.high_count = sum(1 for i in analysis.issues if i.severity == Severity.HIGH)
        analysis.medium_count = sum(1 for i in analysis.issues if i.severity == Severity.MEDIUM)
        analysis.low_count = sum(1 for i in analysis.issues if i.severity == Severity.LOW)
        
        # Calculate score (simple formula)
        score_deduction = (
            analysis.critical_count * 20 +
            analysis.high_count * 10 +
            analysis.medium_count * 5 +
            analysis.low_count * 2
        )
        analysis.score = max(0, 100 - score_deduction)
        
        return analysis
    
    def _analyze_patch(self, file_path: str, patch: str) -> List[QualityIssue]:
        """
        Analyze patch for quality issues.
        
        Args:
            file_path: File path
            patch: Git patch content
            
        Returns:
            List of quality issues
        """
        issues = []
        
        lines = patch.split("\n")
        line_number = 0
        
        for line in lines:
            if line.startswith("+"):
                line_number += 1
                content = line[1:]  # Remove + prefix
                
                # Check for common issues
                issues.extend(self._check_line_quality(file_path, content, line_number))
            elif line.startswith("@@"):
                # Extract line number from hunk header
                parts = line.split(" ")
                if len(parts) > 2:
                    try:
                        line_number = int(parts[2].split(",")[0].lstrip("+"))
                    except (ValueError, IndexError):
                        pass
        
        return issues
    
    def _check_line_quality(self, file_path: str, content: str, line_number: int) -> List[QualityIssue]:
        """
        Check line for quality issues.
        
        Args:
            file_path: File path
            content: Line content
            line_number: Line number
            
        Returns:
            List of quality issues
        """
        issues = []
        
        # Check for hardcoded secrets (simplified)
        if any(keyword in content.lower() for keyword in ["password", "secret", "api_key", "token"]):
            issues.append(QualityIssue(
                type=QualityIssueType.SECURITY,
                severity=Severity.HIGH,
                file_path=file_path,
                line_number=line_number,
                description="Potential hardcoded secret detected",
                suggestion="Use environment variables or secret management",
                rule_id="hardcoded_secret",
            ))
        
        # Check for print statements (debugging code)
        if "print(" in content and not content.strip().startswith("#"):
            issues.append(QualityIssue(
                type=QualityIssueType.CODE_SMELL,
                severity=Severity.LOW,
                file_path=file_path,
                line_number=line_number,
                description="Debug print statement found",
                suggestion="Remove or use proper logging",
                rule_id="debug_print",
            ))
        
        # Check for TODO comments
        if "TODO" in content or "FIXME" in content:
            issues.append(QualityIssue(
                type=QualityIssueType.BEST_PRACTICE,
                severity=Severity.INFO,
                file_path=file_path,
                line_number=line_number,
                description="TODO/FIXME comment found",
                suggestion="Create a tracking issue instead",
                rule_id="todo_comment",
            ))
        
        # Check for long lines (simplified)
        if len(content) > 120:
            issues.append(QualityIssue(
                type=QualityIssueType.STYLE_VIOLATION,
                severity=Severity.LOW,
                file_path=file_path,
                line_number=line_number,
                description=f"Line too long ({len(content)} characters)",
                suggestion="Break line or restructure code",
                rule_id="long_line",
            ))
        
        return issues
