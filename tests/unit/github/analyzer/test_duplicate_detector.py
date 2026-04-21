#!/usr/bin/env python3
"""
Unit tests for Duplicate Detector.
"""

import pytest

from src.github.analyzer.duplicate_detector import DuplicateDetector, DuplicateMatch


class TestDuplicateDetector:
    """Test DuplicateDetector."""
    
    def test_detector_initialization(self):
        """Test detector initialization."""
        detector = DuplicateDetector(similarity_threshold=0.8)
        
        assert detector.similarity_threshold == 0.8
    
    def test_detect_duplicates_high_similarity(self):
        """Test detecting duplicates with high similarity."""
        detector = DuplicateDetector(similarity_threshold=0.8)
        
        title = "Application crashes on startup"
        body = "The app crashes when I start it"
        
        existing_issues = [
            {
                "id": "1",
                "title": "Application crashes on startup",
                "body": "The app crashes when I start it with error",
            }
        ]
        
        matches = detector.detect_duplicates(title, body, existing_issues)
        
        assert len(matches) > 0
        assert matches[0].similarity >= 0.8
    
    def test_detect_duplicates_low_similarity(self):
        """Test detecting duplicates with low similarity."""
        detector = DuplicateDetector(similarity_threshold=0.9)
        
        title = "Application crashes on startup"
        body = "The app crashes when I start it"
        
        existing_issues = [
            {
                "id": "1",
                "title": "Feature request: Add dark mode",
                "body": "It would be great to have dark mode",
            }
        ]
        
        matches = detector.detect_duplicates(title, body, existing_issues)
        
        assert len(matches) == 0
    
    def test_detect_duplicates_multiple_matches(self):
        """Test detecting multiple duplicate matches."""
        detector = DuplicateDetector(similarity_threshold=0.7)
        
        title = "Application crashes on startup"
        body = "The app crashes when I start it"
        
        existing_issues = [
            {
                "id": "1",
                "title": "Application crashes on startup",
                "body": "The app crashes when I start it",
            },
            {
                "id": "2",
                "title": "App crashes on startup",
                "body": "App crashes when I start it",
            },
        ]
        
        matches = detector.detect_duplicates(title, body, existing_issues)
        
        assert len(matches) >= 2
    
    def test_matches_sorted_by_similarity(self):
        """Test matches are sorted by similarity."""
        detector = DuplicateDetector(similarity_threshold=0.7)
        
        title = "Application crashes on startup"
        body = "The app crashes when I start it"
        
        existing_issues = [
            {
                "id": "1",
                "title": "App crashes",
                "body": "App crashes",
            },
            {
                "id": "2",
                "title": "Application crashes on startup",
                "body": "The app crashes when I start it",
            },
        ]
        
        matches = detector.detect_duplicates(title, body, existing_issues)
        
        # First match should have highest similarity
        if len(matches) > 1:
            assert matches[0].similarity >= matches[1].similarity
