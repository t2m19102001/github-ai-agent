#!/usr/bin/env python3
"""
Unit tests for Security Reviewer.
"""

import pytest

from src.github.review.security_reviewer import SecurityReviewer, SecurityAnalysis, SecurityIssue, SecurityIssueType, Severity


class TestSecurityReviewer:
    """Test SecurityReviewer."""
    
    def test_reviewer_initialization(self):
        """Test reviewer initialization."""
        reviewer = SecurityReviewer()
        
        assert reviewer is not None
    
    def test_analyze_empty_diff(self):
        """Test analyzing empty diff."""
        reviewer = SecurityReviewer()
        
        diff_data = {"files": []}
        analysis = reviewer.analyze(diff_data)
        
        assert analysis.total_issues == 0
    
    def test_detect_hardcoded_password(self):
        """Test detecting hardcoded password."""
        reviewer = SecurityReviewer()
        
        diff_data = {
            "files": [
                {
                    "filename": "src/config.py",
                    "patch": "@@ -1,1 +1,1 @@\n+password = 'secret123'",
                }
            ]
        }
        
        analysis = reviewer.analyze(diff_data)
        
        assert analysis.total_issues > 0
        assert any(i.type == SecurityIssueType.SECRET_LEAK for i in analysis.issues)
    
    def test_detect_sql_injection(self):
        """Test detecting SQL injection patterns."""
        reviewer = SecurityReviewer()
        
        diff_data = {
            "files": [
                {
                    "filename": "src/database.py",
                    "patch": "@@ -1,1 +1,1 @@\n+query.execute('SELECT * FROM users WHERE id = ' + user_id)",
                }
            ]
        }
        
        analysis = reviewer.analyze(diff_data)
        
        assert analysis.total_issues > 0
        assert any(i.type == SecurityIssueType.SQL_INJECTION for i in analysis.issues)
    
    def test_detect_xss(self):
        """Test detecting XSS patterns."""
        reviewer = SecurityReviewer()
        
        diff_data = {
            "files": [
                {
                    "filename": "src/web.py",
                    "patch": "@@ -1,1 +1,1 @@\n+element.innerHTML = user_input",
                }
            ]
        }
        
        analysis = reviewer.analyze(diff_data)
        
        assert analysis.total_issues > 0
        assert any(i.type == SecurityIssueType.XSS for i in analysis.issues)
