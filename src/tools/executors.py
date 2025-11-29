#!/usr/bin/env python3
"""
Code and command executors
Allows agents to execute Python code and shell commands safely
"""

import subprocess
import sys
from typing import Dict, Any
from src.agents.base import Executor
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PythonExecutor(Executor):
    """Execute Python code safely"""
    
    def __init__(self):
        super().__init__(name="python")
    
    def execute(self, code: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Execute Python code
        
        Returns:
            {
                "success": bool,
                "output": str,
                "error": str,
                "exit_code": int
            }
        """
        try:
            # Use subprocess to isolate execution
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": f"Execution timeout after {timeout}s",
                "exit_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": -1
            }


class ShellExecutor(Executor):
    """Execute shell commands"""
    
    def __init__(self):
        super().__init__(name="shell")
    
    def execute(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Execute shell command
        
        Returns:
            {
                "success": bool,
                "output": str,
                "error": str,
                "exit_code": int
            }
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=True
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": f"Execution timeout after {timeout}s",
                "exit_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": -1
            }
