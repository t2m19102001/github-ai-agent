#!/usr/bin/env python3
"""
File Tools Module
Basic file operations for agents
"""

import os
import glob
from typing import List, Optional, Dict, Any

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class FileReadTool:
    """Tool for reading files"""
    
    def __init__(self):
        self.name = "file_read"
        self.description = "Read file contents"
    
    def execute(self, file_path: str) -> str:
        """Read file contents"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Read file: {file_path}")
            return content
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return f"Error reading file: {e}"


class FileWriteTool:
    """Tool for writing files"""
    
    def __init__(self):
        self.name = "file_write"
        self.description = "Write content to file"
    
    def execute(self, file_path: str, content: str) -> bool:
        """Write content to file"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Wrote file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return False


class ListFilesTool:
    """Tool for listing files"""
    
    def __init__(self):
        self.name = "list_files"
        self.description = "List files in directory"
    
    def execute(self, directory: str, pattern: str = "*") -> List[str]:
        """List files in directory"""
        try:
            files = glob.glob(os.path.join(directory, pattern))
            files = [f for f in files if os.path.isfile(f)]
            logger.info(f"Listed {len(files)} files in {directory}")
            return files
        except Exception as e:
            logger.error(f"Error listing files in {directory}: {e}")
            return []
