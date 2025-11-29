#!/usr/bin/env python3
"""
Tool implementations for agents
File operations, Git operations, etc.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from src.agents.base import Tool
from src.utils.logger import get_logger
from src.core.config import PROJECT_ROOT, ALLOWED_FILE_EXTENSIONS, MAX_FILE_SIZE

logger = get_logger(__name__)


class FileReadTool(Tool):
    """Tool to read files"""
    
    def __init__(self):
        super().__init__(
            name="read_file",
            description="Read content of a file in the project"
        )
    
    def execute(self, file_path: str) -> Optional[str]:
        """Read a file and return its content"""
        try:
            full_path = PROJECT_ROOT / file_path
            
            # Security check
            if not full_path.exists():
                logger.warning(f"File not found: {file_path}")
                return None
            
            if full_path.stat().st_size > MAX_FILE_SIZE:
                logger.warning(f"File too large: {file_path}")
                return None
            
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return None


class FileWriteTool(Tool):
    """Tool to write files"""
    
    def __init__(self):
        super().__init__(
            name="write_file",
            description="Write or create a file in the project"
        )
    
    def execute(self, file_path: str, content: str) -> bool:
        """Write content to a file"""
        try:
            full_path = PROJECT_ROOT / file_path
            
            # Security check - only allowed extensions
            if full_path.suffix not in ALLOWED_FILE_EXTENSIONS:
                logger.warning(f"File extension not allowed: {full_path.suffix}")
                return False
            
            # Create parent directories
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"✅ File written: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing file: {e}")
            return False


class ListFilesTool(Tool):
    """Tool to list files in project"""
    
    def __init__(self):
        super().__init__(
            name="list_files",
            description="List all code files in the project"
        )
    
    def execute(self, pattern: str = "**/*.py") -> list:
        """List files matching pattern"""
        try:
            files = list(PROJECT_ROOT.glob(pattern))
            # Filter out venv and cache
            files = [
                f for f in files 
                if '.venv' not in str(f) and '__pycache__' not in str(f)
            ]
            return [str(f.relative_to(PROJECT_ROOT)) for f in sorted(files)]
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []


class GitTool(Tool):
    """Tool for Git operations"""
    
    def __init__(self):
        super().__init__(
            name="git_operation",
            description="Perform Git operations (commit, push, etc.)"
        )
    
    def execute(self, operation: str, **kwargs) -> Dict[str, Any]:
        """
        Execute Git operation
        
        Operations:
            - commit: {"message": "commit message", "files": ["file1", "file2"]}
            - push: {"branch": "main"}
            - status: {}
            - log: {"limit": 5}
        """
        import subprocess
        
        try:
            if operation == "commit":
                message = kwargs.get("message")
                files = kwargs.get("files", [])
                
                # Add files
                for f in files:
                    subprocess.run(["git", "add", f], cwd=PROJECT_ROOT, check=True)
                
                # Commit
                result = subprocess.run(
                    ["git", "commit", "-m", message],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True
                )
                
                return {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr
                }
            
            elif operation == "push":
                branch = kwargs.get("branch", "main")
                result = subprocess.run(
                    ["git", "push", "origin", branch],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True
                )
                
                return {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr
                }
            
            elif operation == "status":
                result = subprocess.run(
                    ["git", "status", "-s"],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True
                )
                
                return {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr
                }
            
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
        
        except Exception as e:
            logger.error(f"Git error: {e}")
            return {"success": False, "error": str(e)}
