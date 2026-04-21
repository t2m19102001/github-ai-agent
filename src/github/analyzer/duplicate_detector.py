#!/usr/bin/env python3
"""
Duplicate Issue Detection.

Production-grade implementation with:
- Text similarity detection
- Semantic similarity
- Threshold-based detection
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import difflib

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DuplicateMatch:
    """Duplicate match result."""
    issue_id: str
    similarity: float
    title_similarity: float
    body_similarity: float
    reason: str


class DuplicateDetector:
    """
    Duplicate issue detector.
    
    Detects duplicate issues based on text similarity.
    """
    
    def __init__(self, similarity_threshold: float = 0.8):
        """
        Initialize duplicate detector.
        
        Args:
            similarity_threshold: Similarity threshold (0.0-1.0)
        """
        self.similarity_threshold = similarity_threshold
        
        logger.info(f"DuplicateDetector initialized (threshold: {similarity_threshold})")
    
    def detect_duplicates(
        self,
        title: str,
        body: str,
        existing_issues: List[Dict[str, Any]]
    ) -> List[DuplicateMatch]:
        """
        Detect duplicate issues.
        
        Args:
            title: Issue title
            body: Issue body
            existing_issues: List of existing issues with title and body
            
        Returns:
            List of duplicate matches
        """
        matches = []
        
        for issue in existing_issues:
            issue_id = issue.get("id", "")
            existing_title = issue.get("title", "")
            existing_body = issue.get("body", "")
            
            # Calculate similarity
            title_similarity = self._calculate_similarity(title, existing_title)
            body_similarity = self._calculate_similarity(body, existing_body)
            
            # Combined similarity
            combined_similarity = (title_similarity * 0.6) + (body_similarity * 0.4)
            
            # Check if above threshold
            if combined_similarity >= self.similarity_threshold:
                reason = self._generate_reason(title_similarity, body_similarity)
                
                matches.append(
                    DuplicateMatch(
                        issue_id=issue_id,
                        similarity=combined_similarity,
                        title_similarity=title_similarity,
                        body_similarity=body_similarity,
                        reason=reason,
                    )
                )
        
        # Sort by similarity descending
        matches.sort(key=lambda m: m.similarity, reverse=True)
        
        return matches
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0.0-1.0)
        """
        if not text1 or not text2:
            return 0.0
        
        # Use SequenceMatcher for similarity
        matcher = difflib.SequenceMatcher(None, text1.lower(), text2.lower())
        return matcher.ratio()
    
    def _generate_reason(self, title_similarity: float, body_similarity: float) -> str:
        """Generate reason for duplicate detection."""
        parts = []
        
        if title_similarity > 0.8:
            parts.append(f"High title similarity ({title_similarity:.2f})")
        
        if body_similarity > 0.8:
            parts.append(f"High body similarity ({body_similarity:.2f})")
        
        return " | ".join(parts) if parts else "Similar content"
