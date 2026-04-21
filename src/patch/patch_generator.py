#!/usr/bin/env python3
"""
Patch Generation Engine.

Production-grade implementation with:
- Patch generation from changes
- Diff format support
- Patch size limits
- Metadata tracking
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class PatchFormat(Enum):
    """Patch format types."""
    UNIFIED = "unified"
    CONTEXT = "context"


@dataclass
class Patch:
    """Patch entity."""
    id: str
    file_path: str
    old_content: str
    new_content: str
    format: PatchFormat = PatchFormat.UNIFIED
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_size(self) -> int:
        """Get patch size in bytes."""
        return len(self.new_content.encode()) + len(self.old_content.encode())
    
    def get_line_count(self) -> int:
        """Get line count of patch."""
        return len(self.new_content.splitlines())


class PatchGenerator:
    """
    Patch generator.
    
    Generates patches from code changes.
    """
    
    def __init__(self, max_patch_size: int = 1024 * 1024):  # 1MB default
        """
        Initialize patch generator.
        
        Args:
            max_patch_size: Maximum patch size in bytes
        """
        self.max_patch_size = max_patch_size
        
        logger.info(f"PatchGenerator initialized (max_size: {max_patch_size} bytes)")
    
    def generate(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Patch:
        """
        Generate patch from changes.
        
        Args:
            file_path: File path
            old_content: Original content
            new_content: New content
            metadata: Additional metadata
            
        Returns:
            Patch
            
        Raises:
            ValueError: If patch size exceeds limit
        """
        # Create patch
        patch = Patch(
            id=self._generate_patch_id(),
            file_path=file_path,
            old_content=old_content,
            new_content=new_content,
            metadata=metadata or {},
        )
        
        # Validate patch size
        if patch.get_size() > self.max_patch_size:
            raise ValueError(
                f"Patch size ({patch.get_size()} bytes) exceeds limit ({self.max_patch_size} bytes)"
            )
        
        logger.info(f"Generated patch: {file_path} (size: {patch.get_size()} bytes)")
        
        return patch
    
    def generate_unified_diff(
        self,
        file_path: str,
        old_content: str,
        new_content: str
    ) -> str:
        """
        Generate unified diff format.
        
        Args:
            file_path: File path
            old_content: Original content
            new_content: New content
            
        Returns:
            Unified diff string
        """
        import difflib
        
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=""
        )
        
        return "".join(diff)
    
    def _generate_patch_id(self) -> str:
        """Generate unique patch ID."""
        import uuid
        return str(uuid.uuid4())
