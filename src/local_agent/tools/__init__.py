"""
Tools Module.

Purpose: Read-only file and git operations.
Input: File paths, git commands
Output: File contents, git info

Components:
    file_reader: File operations (read-only)
    git_reader: Git operations (log, diff, blame)
    code_query: Code analysis queries

NOTE: All tools are read-only - no write operations in V1.
"""

from src.local_agent.tools.file_reader import FileReader
from src.local_agent.tools.git_reader import GitReader
from src.local_agent.tools.code_query import CodeQuery

__all__ = ["FileReader", "GitReader", "CodeQuery"]
