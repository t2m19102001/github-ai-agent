#!/usr/bin/env python3
"""
Unit tests for Diff Analyzer.
"""

import pytest

from src.github.review.diff_analyzer import DiffAnalyzer, DiffAnalysis, FileChange, ChangeType


class TestDiffAnalyzer:
    """Test DiffAnalyzer."""
    
    def test_diff_analyzer_initialization(self):
        """Test diff analyzer initialization."""
        analyzer = DiffAnalyzer()
        
        assert analyzer is not None
    
    def test_analyze_empty_diff(self):
        """Test analyzing empty diff."""
        analyzer = DiffAnalyzer()
        
        diff_data = {"files": []}
        analysis = analyzer.analyze(diff_data)
        
        assert analysis.total_files == 0
        assert analysis.total_additions == 0
        assert analysis.total_deletions == 0
    
    def test_analyze_simple_diff(self):
        """Test analyzing simple diff."""
        analyzer = DiffAnalyzer()
        
        diff_data = {
            "files": [
                {
                    "filename": "src/main.py",
                    "status": "modified",
                    "additions": 10,
                    "deletions": 5,
                    "binary": False,
                }
            ]
        }
        
        analysis = analyzer.analyze(diff_data)
        
        assert analysis.total_files == 1
        assert analysis.total_additions == 10
        assert analysis.total_deletions == 5
        assert len(analysis.file_changes) == 1
    
    def test_detect_language(self):
        """Test language detection."""
        analyzer = DiffAnalyzer()
        
        assert analyzer._detect_language("src/main.py") == "Python"
        assert analyzer._detect_language("src/app.js") == "JavaScript"
        assert analyzer._detect_language("src/main.go") == "Go"
        assert analyzer._detect_language("README.md") == "Markdown"
        assert analyzer._detect_language("src/unknown.xyz") is None
