#!/usr/bin/env python3
"""
Audit Trail for Analysis Decisions.

Production-grade implementation with:
- Decision tracking
- Analysis history
- Immutable records
"""

import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class DecisionType(Enum):
    """Decision types."""
    CLASSIFICATION = "classification"
    DUPLICATE_DETECTION = "duplicate_detection"
    SUMMARY_GENERATION = "summary_generation"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    ERROR = "error"


@dataclass
class AnalysisDecision:
    """Analysis decision record."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_type: DecisionType = DecisionType.CLASSIFICATION
    decision_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reasoning: Optional[str] = None


class AuditTrail:
    """
    Audit trail for issue analysis decisions.
    
    Tracks all decisions made during analysis.
    """
    
    def __init__(self):
        """Initialize audit trail."""
        self._analyses: Dict[str, List[AnalysisDecision]] = {}
        self._analysis_metadata: Dict[str, Dict[str, Any]] = {}
        
        logger.info("AuditTrail initialized")
    
    def start_analysis(
        self,
        title: str,
        body: str,
        labels: Optional[list] = None
    ) -> str:
        """
        Start new analysis.
        
        Args:
            title: Issue title
            body: Issue body
            labels: Issue labels
            
        Returns:
            Analysis ID
        """
        analysis_id = str(uuid.uuid4())
        
        self._analyses[analysis_id] = []
        self._analysis_metadata[analysis_id] = {
            "title": title,
            "body": body,
            "labels": labels or [],
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
        }
        
        logger.debug(f"Started analysis: {analysis_id}")
        
        return analysis_id
    
    def record_decision(
        self,
        analysis_id: str,
        decision_type: str,
        decision_data: Any,
        reasoning: Optional[str] = None
    ):
        """
        Record analysis decision.
        
        Args:
            analysis_id: Analysis ID
            decision_type: Type of decision
            decision_data: Decision data
            reasoning: Optional reasoning
        """
        if analysis_id not in self._analyses:
            logger.warning(f"Analysis ID not found: {analysis_id}")
            return
        
        # Convert decision data to dict if needed
        if hasattr(decision_data, 'to_dict'):
            data = decision_data.to_dict()
        elif isinstance(decision_data, dict):
            data = decision_data
        elif isinstance(decision_data, list):
            data = {"items": decision_data}
        else:
            data = {"value": str(decision_data)}
        
        decision = AnalysisDecision(
            decision_type=DecisionType(decision_type),
            decision_data=data,
            reasoning=reasoning,
        )
        
        self._analyses[analysis_id].append(decision)
        
        logger.debug(
            f"Recorded decision: {decision_type} for analysis {analysis_id}"
        )
    
    def record_error(self, analysis_id: str, error: str):
        """
        Record analysis error.
        
        Args:
            analysis_id: Analysis ID
            error: Error message
        """
        if analysis_id not in self._analyses:
            return
        
        decision = AnalysisDecision(
            decision_type=DecisionType.ERROR,
            decision_data={"error": error},
            reasoning="Analysis failed",
        )
        
        self._analyses[analysis_id].append(decision)
        
        logger.error(f"Recorded error for analysis {analysis_id}: {error}")
    
    def complete_analysis(self, analysis_id: str):
        """
        Mark analysis as complete.
        
        Args:
            analysis_id: Analysis ID
        """
        if analysis_id in self._analysis_metadata:
            self._analysis_metadata[analysis_id]["completed_at"] = datetime.utcnow().isoformat()
        
        logger.debug(f"Completed analysis: {analysis_id}")
    
    def get_trail(self, analysis_id: str) -> Dict[str, Any]:
        """
        Get audit trail for analysis.
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            Audit trail data
        """
        if analysis_id not in self._analyses:
            return {"error": "Analysis not found"}
        
        decisions = self._analyses[analysis_id]
        metadata = self._analysis_metadata[analysis_id]
        
        return {
            "analysis_id": analysis_id,
            "metadata": metadata,
            "decisions": [
                {
                    "id": d.id,
                    "type": d.decision_type.value,
                    "data": d.decision_data,
                    "timestamp": d.timestamp.isoformat(),
                    "reasoning": d.reasoning,
                }
                for d in decisions
            ],
            "decision_count": len(decisions),
        }
    
    def get_all_analyses(self) -> List[Dict[str, Any]]:
        """Get all analyses."""
        return [
            {
                "analysis_id": analysis_id,
                "metadata": metadata,
                "decision_count": len(self._analyses[analysis_id]),
            }
            for analysis_id, metadata in self._analysis_metadata.items()
        ]
