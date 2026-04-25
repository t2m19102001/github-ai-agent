"""
Git Reader Module.

Purpose: Git operations (log, diff, blame).
"""

class GitReader:
    """Reads git information."""
    
    def log(self, repo_path: str, file_path: str) -> list:
        """Get git log for a file."""
        raise NotImplementedError("Git reader not yet implemented")
    
    def diff(self, repo_path: str, commit: str) -> str:
        """Get git diff."""
        raise NotImplementedError("Git reader not yet implemented")
    
    def blame(self, repo_path: str, file_path: str, line: int) -> dict:
        """Get git blame for a line."""
        raise NotImplementedError("Git reader not yet implemented")
