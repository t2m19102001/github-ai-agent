#!/usr/bin/env python3
"""
Issue Classification Strategy.

Production-grade implementation with:
- Issue categories
- Priority detection
- Severity detection
- Classification logic
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class IssueCategory(Enum):
    """Issue categories."""
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"
    SECURITY = "security"
    MAINTENANCE = "maintenance"
    QUESTION = "question"
    ENHANCEMENT = "enhancement"
    INFRASTRUCTURE = "infrastructure"
    TESTING = "testing"
    OTHER = "other"


class IssuePriority(Enum):
    """Issue priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueSeverity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRIVIAL = "trivial"


@dataclass
class ClassificationResult:
    """Classification result."""
    category: IssueCategory
    priority: IssuePriority
    severity: IssueSeverity
    confidence: float
    reasoning: str
    metadata: Dict[str, Any]


class IssueClassifier:
    """
    Issue classifier.
    
    Classifies GitHub issues into categories, priorities, and severities.
    """
    
    # Keywords for category detection
    CATEGORY_KEYWORDS = {
        IssueCategory.BUG: [
            "bug", "error", "crash", "broken", "fix", "regression",
            "doesn't work", "not working", "fail", "exception", "issue",
            "defect", "flaw", "glitch", "problem"
        ],
        IssueCategory.FEATURE_REQUEST: [
            "feature", "request", "add", "implement", "support",
            "new", "enhancement", "improvement", "wish", "suggestion",
            "would like", "it would be great"
        ],
        IssueCategory.DOCUMENTATION: [
            "doc", "documentation", "readme", "guide", "tutorial",
            "example", "clarify", "explain", "docs", "typo", "spelling"
        ],
        IssueCategory.PERFORMANCE: [
            "slow", "performance", "latency", "optimize", "speed",
            "memory", "cpu", "benchmark", "scalability", "efficiency"
        ],
        IssueCategory.SECURITY: [
            "security", "vulnerability", "exploit", "attack", "hack",
            "xss", "csrf", "injection", "auth", "permission", "access",
            "sensitive", "credential", "token"
        ],
        IssueCategory.MAINTENANCE: [
            "refactor", "cleanup", "deprecation", "remove", "rename",
            "reorganize", "technical debt", "maintenance", "update"
        ],
        IssueCategory.QUESTION: [
            "question", "how", "what", "why", "help", "confused",
            "unclear", "clarify", "understand", "example", "usage"
        ],
        IssueCategory.INFRASTRUCTURE: [
            "ci", "cd", "deployment", "build", "pipeline", "docker",
            "infrastructure", "setup", "configuration", "environment"
        ],
        IssueCategory.TESTING: [
            "test", "unit test", "integration test", "e2e", "coverage",
            "testing", "spec", "assertion", "mock", "stub"
        ],
    }
    
    # Keywords for priority detection
    PRIORITY_KEYWORDS = {
        IssuePriority.CRITICAL: [
            "critical", "urgent", "blocker", "emergency", "production",
            "down", "outage", "severe", "major", "p0", "p1"
        ],
        IssuePriority.HIGH: [
            "high", "important", "priority", "p2", "soon", "asap",
            "important", "significant"
        ],
        IssuePriority.MEDIUM: [
            "medium", "normal", "p3", "eventually", "when possible"
        ],
        IssuePriority.LOW: [
            "low", "minor", "nice to have", "p4", "wishlist",
            "eventually", "someday"
        ],
    }
    
    # Keywords for severity detection
    SEVERITY_KEYWORDS = {
        IssueSeverity.CRITICAL: [
            "crash", "data loss", "security", "production", "down",
            "outage", "corruption", "critical", "severe", "blocker"
        ],
        IssueSeverity.HIGH: [
            "major", "significant", "important", "high impact",
            "frequently", "often", "regularly"
        ],
        IssueSeverity.MEDIUM: [
            "moderate", "some", "occasional", "sometimes",
            "inconvenient", "workaround"
        ],
        IssueSeverity.LOW: [
            "minor", "small", "rare", "infrequently", "cosmetic",
            "trivial", "nitpick"
        ],
        IssueSeverity.TRIVIAL: [
            "trivial", "cosmetic", "typo", "spelling", "formatting",
            "style", "whitespace", "comment"
        ],
    }
    
    def __init__(self):
        """Initialize issue classifier."""
        logger.info("IssueClassifier initialized")
    
    def classify(
        self,
        title: str,
        body: str,
        labels: Optional[list] = None
    ) -> ClassificationResult:
        """
        Classify issue.
        
        Args:
            title: Issue title
            body: Issue body
            labels: Existing GitHub labels
            
        Returns:
            Classification result
        """
        combined_text = f"{title} {body}".lower()
        
        # Detect category
        category = self._detect_category(combined_text, labels)
        
        # Detect priority
        priority = self._detect_priority(combined_text, labels)
        
        # Detect severity
        severity = self._detect_severity(combined_text, category)
        
        # Calculate confidence
        confidence = self._calculate_confidence(category, priority, severity, combined_text)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(category, priority, severity, combined_text)
        
        result = ClassificationResult(
            category=category,
            priority=priority,
            severity=severity,
            confidence=confidence,
            reasoning=reasoning,
            metadata={
                "title": title,
                "labels": labels or [],
            }
        )
        
        logger.info(
            f"Issue classified: {category.value} / {priority.value} / {severity.value} "
            f"(confidence: {confidence:.2f})"
        )
        
        return result
    
    def _detect_category(self, text: str, labels: Optional[list]) -> IssueCategory:
        """Detect issue category."""
        scores = {category: 0 for category in IssueCategory}
        
        # Check keywords
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[category] += 1
        
        # Check labels
        if labels:
            for label in labels:
                label_lower = label.lower()
                for category, keywords in self.CATEGORY_KEYWORDS.items():
                    if any(keyword in label_lower for keyword in keywords):
                        scores[category] += 2
        
        # Get category with highest score
        max_score = max(scores.values())
        
        if max_score == 0:
            return IssueCategory.OTHER
        
        # Get all categories with max score
        max_categories = [cat for cat, score in scores.items() if score == max_score]
        
        # If tie, prefer BUG or FEATURE_REQUEST
        if IssueCategory.BUG in max_categories:
            return IssueCategory.BUG
        if IssueCategory.FEATURE_REQUEST in max_categories:
            return IssueCategory.FEATURE_REQUEST
        
        return max_categories[0]
    
    def _detect_priority(self, text: str, labels: Optional[list]) -> IssuePriority:
        """Detect issue priority."""
        scores = {priority: 0 for priority in IssuePriority}
        
        # Check keywords
        for priority, keywords in self.PRIORITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[priority] += 1
        
        # Check labels
        if labels:
            for label in labels:
                label_lower = label.lower()
                if label_lower in ["critical", "urgent", "blocker"]:
                    scores[IssuePriority.CRITICAL] += 3
                elif label_lower in ["high", "important"]:
                    scores[IssuePriority.HIGH] += 3
                elif label_lower in ["medium", "normal"]:
                    scores[IssuePriority.MEDIUM] += 3
                elif label_lower in ["low", "minor"]:
                    scores[IssuePriority.LOW] += 3
        
        # Get priority with highest score
        max_score = max(scores.values())
        
        if max_score == 0:
            return IssuePriority.MEDIUM  # Default
        
        return max(scores, key=scores.get)
    
    def _detect_severity(self, text: str, category: IssueCategory) -> IssueSeverity:
        """Detect issue severity."""
        scores = {severity: 0 for severity in IssueSeverity}
        
        # Check keywords
        for severity, keywords in self.SEVERITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[severity] += 1
        
        # Category-based defaults
        if category == IssueCategory.SECURITY:
            scores[IssueSeverity.CRITICAL] += 3
        elif category == IssueCategory.BUG:
            scores[IssueSeverity.HIGH] += 1
        elif category == IssueCategory.FEATURE_REQUEST:
            scores[IssueSeverity.LOW] += 1
        elif category == IssueCategory.DOCUMENTATION:
            scores[IssueSeverity.TRIVIAL] += 1
        
        # Get severity with highest score
        max_score = max(scores.values())
        
        if max_score == 0:
            return IssueSeverity.MEDIUM  # Default
        
        return max(scores, key=scores.get)
    
    def _calculate_confidence(
        self,
        category: IssueCategory,
        priority: IssuePriority,
        severity: IssueSeverity,
        text: str
    ) -> float:
        """Calculate classification confidence."""
        # Simple confidence based on keyword matches
        total_keywords = 0
        matched_keywords = 0
        
        for keywords in self.CATEGORY_KEYWORDS.values():
            total_keywords += len(keywords)
            for keyword in keywords:
                if keyword in text:
                    matched_keywords += 1
        
        if total_keywords == 0:
            return 0.5
        
        return min(matched_keywords / total_keywords * 2, 1.0)
    
    def _generate_reasoning(
        self,
        category: IssueCategory,
        priority: IssuePriority,
        severity: IssueSeverity,
        text: str
    ) -> str:
        """Generate classification reasoning."""
        reasoning_parts = []
        
        reasoning_parts.append(f"Category: {category.value}")
        reasoning_parts.append(f"Priority: {priority.value}")
        reasoning_parts.append(f"Severity: {severity.value}")
        
        return " | ".join(reasoning_parts)
