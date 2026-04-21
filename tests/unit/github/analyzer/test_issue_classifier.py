#!/usr/bin/env python3
"""
Unit tests for Issue Classifier.
"""

import pytest

from src.github.analyzer.issue_classifier import (
    IssueClassifier,
    IssueCategory,
    IssuePriority,
    IssueSeverity,
    ClassificationResult,
)


class TestIssueClassifier:
    """Test IssueClassifier."""
    
    def test_classifier_initialization(self):
        """Test classifier initialization."""
        classifier = IssueClassifier()
        
        assert classifier is not None
    
    def test_classify_bug(self):
        """Test bug classification."""
        classifier = IssueClassifier()
        
        result = classifier.classify(
            title="Application crashes on startup",
            body="The app crashes when I start it with error code 500",
        )
        
        assert result.category == IssueCategory.BUG
        assert isinstance(result, ClassificationResult)
    
    def test_classify_feature_request(self):
        """Test feature request classification."""
        classifier = IssueClassifier()
        
        result = classifier.classify(
            title="Add dark mode support",
            body="It would be great to have dark mode in the application",
        )
        
        assert result.category == IssueCategory.FEATURE_REQUEST
    
    def test_classify_security(self):
        """Test security classification."""
        classifier = IssueClassifier()
        
        result = classifier.classify(
            title="Security vulnerability in auth",
            body="There's a potential XSS vulnerability in the login form",
        )
        
        assert result.category == IssueCategory.SECURITY
        assert result.severity == IssueSeverity.CRITICAL
    
    def test_detect_priority_critical(self):
        """Test critical priority detection."""
        classifier = IssueClassifier()
        
        result = classifier.classify(
            title="CRITICAL: Production down",
            body="The production server is down, urgent fix needed",
        )
        
        assert result.priority == IssuePriority.CRITICAL
    
    def test_detect_priority_low(self):
        """Test low priority detection."""
        classifier = IssueClassifier()
        
        result = classifier.classify(
            title="Minor typo in documentation",
            body="There's a small typo in the README file",
        )
        
        assert result.priority == IssuePriority.LOW
    
    def test_detect_severity(self):
        """Test severity detection."""
        classifier = IssueClassifier()
        
        result = classifier.classify(
            title="Data corruption bug",
            body="Users are experiencing data corruption when saving files",
        )
        
        assert result.severity == IssueSeverity.CRITICAL
    
    def test_classify_with_labels(self):
        """Test classification with labels."""
        classifier = IssueClassifier()
        
        result = classifier.classify(
            title="Fix login issue",
            body="Users cannot login to the application",
            labels=["bug", "high-priority"],
        )
        
        assert result.category == IssueCategory.BUG
        assert result.priority == IssuePriority.HIGH
    
    def test_confidence_calculation(self):
        """Test confidence calculation."""
        classifier = IssueClassifier()
        
        result = classifier.classify(
            title="Bug: Application crashes",
            body="The application crashes with error",
        )
        
        assert 0.0 <= result.confidence <= 1.0
