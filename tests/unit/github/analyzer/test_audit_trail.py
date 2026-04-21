#!/usr/bin/env python3
"""
Unit tests for Audit Trail.
"""

import pytest

from src.github.analyzer.audit_trail import (
    AuditTrail,
    AnalysisDecision,
    DecisionType,
)


class TestAuditTrail:
    """Test AuditTrail."""
    
    def test_audit_trail_initialization(self):
        """Test audit trail initialization."""
        trail = AuditTrail()
        
        assert trail is not None
        assert len(trail._analyses) == 0
    
    def test_start_analysis(self):
        """Test starting analysis."""
        trail = AuditTrail()
        
        analysis_id = trail.start_analysis("Test issue", "Test body")
        
        assert analysis_id in trail._analyses
        assert analysis_id in trail._analysis_metadata
    
    def test_record_decision(self):
        """Test recording decision."""
        trail = AuditTrail()
        
        analysis_id = trail.start_analysis("Test issue", "Test body")
        
        trail.record_decision(
            analysis_id,
            "classification",
            {"category": "bug"},
            "Issue is a bug"
        )
        
        decisions = trail._analyses[analysis_id]
        assert len(decisions) == 1
        assert decisions[0].decision_type == DecisionType.CLASSIFICATION
    
    def test_record_error(self):
        """Test recording error."""
        trail = AuditTrail()
        
        analysis_id = trail.start_analysis("Test issue", "Test body")
        
        trail.record_error(analysis_id, "Analysis failed")
        
        decisions = trail._analyses[analysis_id]
        assert len(decisions) == 1
        assert decisions[0].decision_type == DecisionType.ERROR
    
    def test_complete_analysis(self):
        """Test completing analysis."""
        trail = AuditTrail()
        
        analysis_id = trail.start_analysis("Test issue", "Test body")
        trail.complete_analysis(analysis_id)
        
        metadata = trail._analysis_metadata[analysis_id]
        assert metadata["completed_at"] is not None
    
    def test_get_trail(self):
        """Test getting audit trail."""
        trail = AuditTrail()
        
        analysis_id = trail.start_analysis("Test issue", "Test body")
        trail.record_decision(analysis_id, "classification", {"category": "bug"})
        trail.complete_analysis(analysis_id)
        
        trail_data = trail.get_trail(analysis_id)
        
        assert trail_data["analysis_id"] == analysis_id
        assert trail_data["decision_count"] == 1
    
    def test_get_all_analyses(self):
        """Test getting all analyses."""
        trail = AuditTrail()
        
        trail.start_analysis("Issue 1", "Body 1")
        trail.start_analysis("Issue 2", "Body 2")
        
        all_analyses = trail.get_all_analyses()
        
        assert len(all_analyses) == 2
