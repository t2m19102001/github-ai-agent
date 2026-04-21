#!/usr/bin/env python3
"""
Unit tests for Code Quality Analyzer.
"""

import pytest

from src.github.review.code_quality import CodeQualityAnalyzer, QualityAnalysis, QualityIssue, QualityIssueType, Severity


class TestCodeQualityAnalyzer:
    """Test CodeQualityAnalyzer."""
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        analyzer = CodeQualityAnalyzer()
        
        assert analyzer is not None
    
    def test_analyze_empty_diff(self):
        """Test analyzing empty diff."""
        analyzer = CodeQualityAnalyzer()
        
        diff_data = {"files": []}
        analysis = analyzer.analyze(diff_data)
        
        assert analysis.total_issues == 0
        assert analysis.score == 100.0
    
    def test_detect_hardcoded_secret(self):
        """Test detecting hardcoded secrets."""
        analyzer = CodeQualityAnalyzer()
        
        diff_data = {
            "files": [
                {
                    "filename": "src/config.py",
                    "patch": "@@ -1,1 +1,1 @@\n+password = 'secret123'",
                }
            ]
        }
        
        analysis = analyzer.analyze(diff_data)
        
        assert analysis.total_issues > 0
        assert any(i.type == QualityIssueType.SECURITY for i in analysis.issues)
    
    def test_detect_print_statement(self):
        """Test detecting debug print statements."""
        analyzer = CodeQualityAnalyzer()
        
        diff_data = {
            "files": [
                {
                    "filename": "src/main.py",
                    "patch": "@@ -1,1 +1,1 @@\n+print('debug info')",
                }
            ]
        }
        
        analysis = analyzer.analyze(diff_data)
        
        assert analysis.total_issues > 0
    
    def test_score_calculation(self):
        """Test quality score calculation."""
        analyzer = CodeQualityAnalyzer()
        
        diff_data = {
            "files": [
                {
                    "filename": "src/main.py",
                    "patch": "@@ -1,2 +1,2 @@\n+password = 'secret'\n+print('debug')",
                }
            ]
        }
        
        analysis = analyzer.analyze(diff_data)
        
        # Score should be less than 100 due to issues
        assert analysis.score < 100.0
        assert analysis.score >= 0.0
