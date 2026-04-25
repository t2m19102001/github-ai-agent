"""
Step Sequencer Module.

Purpose: Order implementation steps by dependency.
"""

from typing import List


class StepSequencer:
    """Sequences implementation steps."""
    
    def sequence(self, changes: List) -> List:
        """
        Sequence changes by dependency.
        
        Args:
            changes: List of changes to sequence
            
        Returns:
            Ordered list of steps
        """
        raise NotImplementedError("P1-5: Step sequencer not yet implemented")
