"""
Ranker Module.

Purpose: Rank retrieval results using RRF.
"""

from typing import List


class Ranker:
    """Ranks retrieval results."""
    
    def rank(self, results: List) -> List:
        """
        Rank results by relevance.
        
        Args:
            results: List of results to rank
            
        Returns:
            Ranked list
        """
        raise NotImplementedError("Ranker not yet implemented")
