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
        pending = list(changes)
        ordered = []
        completed = set()

        while pending:
            progressed = False
            for change in list(pending):
                dependencies = getattr(change, "dependencies", None)
                if dependencies is None and isinstance(change, dict):
                    dependencies = change.get("dependencies", [])
                dependencies = dependencies or []
                if all(dep in completed for dep in dependencies):
                    ordered.append(change)
                    completed.add(len(ordered))
                    pending.remove(change)
                    progressed = True
            if not progressed:
                raise ValueError("change dependencies contain a cycle or unknown step")

        return ordered
