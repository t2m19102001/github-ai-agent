"""
Risk Assessor Module.

Purpose: Identify and assess risks in plans.
"""

from typing import List

from src.local_agent.planner.output_schema import RiskItem, Severity


class RiskAssessor:
    """Assesses risks in implementation plans."""
    
    def assess(self, changes: List, steps: List) -> List:
        """
        Assess risks for changes and steps.
        
        Args:
            changes: List of changes
            steps: List of steps
            
        Returns:
            List of risk items
        """
        risks = []
        if len(changes) > 3:
            risks.append(RiskItem(
                description="Plan spans multiple files",
                severity=Severity.MEDIUM,
                probability=min(1.0, len(changes) / 10),
                mitigation="Split the handoff into small, independently validated changes.",
                contingency="Revert the failing change and execute remaining steps separately.",
            ))

        if any("test" not in str(getattr(step, "validation", "")).lower() for step in steps):
            risks.append(RiskItem(
                description="Validation may not cover behavioral regressions",
                severity=Severity.MEDIUM,
                probability=0.5,
                mitigation="Require targeted tests before approving execution.",
                contingency="Stop execution when validation is incomplete.",
            ))
        return risks
