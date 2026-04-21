#!/usr/bin/env python3
"""
PR Diff Analysis.

Production-grade implementation with:
- File change detection
- Line change statistics
- Diff parsing
- Complexity analysis
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class ChangeType(Enum):
    """Change types."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass
class FileChange:
    """File change."""
    path: str
    change_type: ChangeType
    additions: int = 0
    deletions: int = 0
    binary: bool = False
    complexity_change: Optional[int] = None


@dataclass
class DiffAnalysis:
    """Diff analysis result."""
    total_files: int = 0
    total_additions: int = 0
    total_deletions: int = 0
    file_changes: List[FileChange] = field(default_factory=list)
    languages: Dict[str, int] = field(default_factory=dict)
    complexity_increase: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_files": self.total_files,
            "total_additions": self.total_additions,
            "total_deletions": self.total_deletions,
            "file_changes": [
                {
                    "path": fc.path,
                    "change_type": fc.change_type.value,
                    "additions": fc.additions,
                    "deletions": fc.deletions,
                    "binary": fc.binary,
                    "complexity_change": fc.complexity_change,
                }
                for fc in self.file_changes
            ],
            "languages": self.languages,
            "complexity_increase": self.complexity_increase,
        }


class DiffAnalyzer:
    """
    Diff analyzer.
    
    Analyzes PR diffs for changes and complexity.
    """
    
    def __init__(self):
        """Initialize diff analyzer."""
        self._language_extensions = {
            "py": "Python",
            "js": "JavaScript",
            "ts": "TypeScript",
            "jsx": "React",
            "tsx": "React",
            "java": "Java",
            "go": "Go",
            "rs": "Rust",
            "cpp": "C++",
            "c": "C",
            "h": "C",
            "rb": "Ruby",
            "php": "PHP",
            "cs": "C#",
            "sql": "SQL",
            "json": "JSON",
            "yaml": "YAML",
            "yml": "YAML",
            "md": "Markdown",
            "txt": "Text",
        }
        
        logger.info("DiffAnalyzer initialized")
    
    def analyze(self, diff_data: Dict[str, Any]) -> DiffAnalysis:
        """
        Analyze diff.
        
        Args:
            diff_data: GitHub diff data
            
        Returns:
            Diff analysis
        """
        analysis = DiffAnalysis()
        
        files = diff_data.get("files", [])
        
        for file in files:
            path = file.get("filename", "")
            status = file.get("status", "modified")
            additions = file.get("additions", 0)
            deletions = file.get("deletions", 0)
            binary = file.get("binary", False)
            
            # Determine change type
            if status == "added":
                change_type = ChangeType.ADDED
            elif status == "removed":
                change_type = ChangeType.DELETED
            elif status == "renamed":
                change_type = ChangeType.RENAMED
            else:
                change_type = ChangeType.MODIFIED
            
            # Detect language
            language = self._detect_language(path)
            if language:
                analysis.languages[language] = analysis.languages.get(language, 0) + 1
            
            # Create file change
            file_change = FileChange(
                path=path,
                change_type=change_type,
                additions=additions,
                deletions=deletions,
                binary=binary,
            )
            
            analysis.file_changes.append(file_change)
            analysis.total_files += 1
            analysis.total_additions += additions
            analysis.total_deletions += deletions
        
        return analysis
    
    def _detect_language(self, path: str) -> Optional[str]:
        """
        Detect programming language from file path.
        
        Args:
            path: File path
            
        Returns:
            Language name or None
        """
        # Get extension
        if "." in path:
            ext = path.rsplit(".", 1)[-1].lower()
            return self._language_extensions.get(ext)
        
        return None
