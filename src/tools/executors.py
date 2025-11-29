#!/usr/bin/env python3
"""
Code and command executors - SECURE VERSION
No shell=True - RCE Prevention
"""

import subprocess
import sys
from typing import Dict, Any
from src.agents.base import Executor
from src.tools.secure_executor import get_secure_executor
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PythonExecutor(Executor):
    """Execute Python code safely"""
    
    def __init__(self):
        super().__init__(name="python")
        self.secure_executor = get_secure_executor()
    
    def execute(self, code: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Execute Python code securely (no shell=True)
        
        Returns:
            {
                "success": bool,
                "output": str,
                "error": str,
                "exit_code": int
            }
        """
        return self.secure_executor.execute_python_safe(code, timeout=timeout)


class ShellExecutor(Executor):
    """Execute shell commands - SECURE with whitelist"""
    
    def __init__(self):
        super().__init__(name="shell")
        self.secure_executor = get_secure_executor()
    
    def execute(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Execute shell command SECURELY
        - No shell=True
        - Command whitelist validation
        - Input sanitization
        
        Returns:
            {
                "success": bool,
                "output": str,
                "error": str,
                "exit_code": int
            }
        """
        return self.secure_executor.execute_safe(command, timeout=timeout)

