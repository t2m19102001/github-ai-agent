"""
Planner Module.

Purpose: Create structured implementation plans.
Input: Goal + context window
Output: JSON plan with steps, risks, validation

Components:
    analyzer: Goal and impact analysis
    sequencer: Step ordering (dependency-based)
    risk_assessor: Risk identification
    output_schema: PlanOutput dataclasses
"""

from src.local_agent.planner.analyzer import GoalAnalyzer
from src.local_agent.planner.sequencer import StepSequencer
from src.local_agent.planner.risk_assessor import RiskAssessor
from src.local_agent.planner.output_schema import PlanOutput, PlanStep, RiskItem, FileChange

__all__ = [
    "GoalAnalyzer",
    "StepSequencer",
    "RiskAssessor",
    "PlanOutput",
    "PlanStep",
    "RiskItem",
    "FileChange",
]
