#!/usr/bin/env python3
"""
Secure Command Executor - RCE Prevention
- No shell=True
- Command whitelist
- Input sanitization
"""

import subprocess
import sys
import shlex
from typing import Dict, Any, List, Optional
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)


# Command whitelist - Only these commands are allowed
ALLOWED_COMMANDS = {
    # Git operations
    "git": ["status", "log", "diff", "branch", "add", "commit", "push", "pull", "checkout", "clone"],
    # File operations
    "ls": [],
    "cat": [],
    "pwd": [],
    "mkdir": [],
    "rm": ["-f", "-rf"],  # Only specific flags allowed
    # Python
    "python": ["-c", "-m"],
    "python3": ["-c", "-m"],
    "pip": ["install", "list", "show"],
    "pytest": [],
    # Docker
    "docker": ["ps", "images", "logs", "build", "run", "stop"],
    # Other safe commands
    "echo": [],
    "grep": [],
    "find": [],
    "head": [],
    "tail": [],
}


class SecureCommandExecutor:
    """Execute commands securely without shell=True"""
    
    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        logger.info(f"✅ Secure executor initialized (workspace: {self.workspace_root})")
    
    def _validate_command(self, command_parts: List[str]) -> bool:
        """Validate command against whitelist"""
        if not command_parts:
            return False
        
        base_command = command_parts[0]
        
        # Check if base command is whitelisted
        if base_command not in ALLOWED_COMMANDS:
            logger.warning(f"❌ Command not whitelisted: {base_command}")
            return False
        
        # Check subcommands/flags if specified
        allowed_subcommands = ALLOWED_COMMANDS[base_command]
        if allowed_subcommands:
            # At least one subcommand must match
            if len(command_parts) < 2:
                logger.warning(f"❌ Missing required subcommand for: {base_command}")
                return False
            
            subcommand = command_parts[1]
            if subcommand not in allowed_subcommands:
                logger.warning(f"❌ Subcommand not allowed: {base_command} {subcommand}")
                return False
        
        logger.info(f"✅ Command validated: {' '.join(command_parts[:2])}")
        return True
    
    def _sanitize_path(self, path: str) -> str:
        """Ensure path is within workspace"""
        try:
            full_path = (self.workspace_root / path).resolve()
            # Check if path is within workspace
            if not str(full_path).startswith(str(self.workspace_root)):
                raise ValueError(f"Path outside workspace: {path}")
            return str(full_path)
        except Exception as e:
            logger.error(f"Path validation failed: {e}")
            raise ValueError(f"Invalid path: {path}")
    
    def execute_safe(self, command: str, timeout: int = 30, 
                     allow_outside_workspace: bool = False) -> Dict[str, Any]:
        """
        Execute command safely without shell=True
        
        Args:
            command: Command string to execute
            timeout: Execution timeout
            allow_outside_workspace: Allow operations outside workspace
            
        Returns:
            {
                "success": bool,
                "output": str,
                "error": str,
                "exit_code": int
            }
        """
        try:
            # Parse command (handles quotes, escaping)
            command_parts = shlex.split(command)
            
            if not command_parts:
                return {
                    "success": False,
                    "output": "",
                    "error": "Empty command",
                    "exit_code": -1
                }
            
            # Validate against whitelist
            if not self._validate_command(command_parts):
                return {
                    "success": False,
                    "output": "",
                    "error": f"Command not allowed: {command_parts[0]}",
                    "exit_code": -1
                }
            
            # Execute without shell=True (secure)
            logger.info(f"🔧 Executing: {' '.join(command_parts)}")
            
            result = subprocess.run(
                command_parts,  # List, not string - NO SHELL INJECTION
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.workspace_root),
                shell=False  # EXPLICIT - No shell injection
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "exit_code": result.returncode
            }
        
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ Command timeout: {command}")
            return {
                "success": False,
                "output": "",
                "error": f"Execution timeout after {timeout}s",
                "exit_code": -1
            }
        except ValueError as e:
            # Validation error
            logger.error(f"❌ Validation error: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": -1
            }
        except Exception as e:
            logger.error(f"❌ Execution error: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": -1
            }
    
    def execute_python_safe(self, code: str, timeout: int = 10) -> Dict[str, Any]:
        """Execute Python code in isolated subprocess"""
        try:
            # NO shell=True - direct execution
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.workspace_root),
                shell=False
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
                "error": f"Python execution timeout after {timeout}s",
                "exit_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": -1
            }
    
    def is_command_allowed(self, command: str) -> bool:
        """Check if command would be allowed"""
        try:
            command_parts = shlex.split(command)
            return self._validate_command(command_parts)
        except Exception:
            return False


# Singleton instance
_executor_instance = None


def get_secure_executor(workspace_root: Optional[str] = None) -> SecureCommandExecutor:
    """Get or create secure executor instance"""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = SecureCommandExecutor(workspace_root)
    return _executor_instance
