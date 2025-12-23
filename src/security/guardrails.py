#!/usr/bin/env python3
"""
Security Guardrails for GitHub AI Agent
Implements file access control, command validation, and patch security
"""

import os
import re
from pathlib import Path
from typing import List, Set, Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SecurityGuardrails:
    """Security guardrails for autonomous operations"""
    
    def __init__(self):
        # Sensitive files and directories to protect
        self.sensitive_files = {
            '.env', '.git', 'node_modules', '__pycache__', 
            '.venv', 'venv', 'env', '.vscode', '.idea',
            'secrets', 'credentials', 'config', 'private',
            '.aws', '.ssh', 'docker-compose.yml', 'Dockerfile'
        }
        
        # Sensitive file extensions
        self.sensitive_extensions = {
            '.key', '.pem', '.crt', '.p12', '.pfx',
            '.env', '.secret', '.credentials'
        }
        
        # Whitelisted commands for execution
        self.whitelisted_commands = {
            'git', 'python', 'python3', 'pytest', 'pip', 'pip3',
            'node', 'npm', 'yarn', 'docker', 'curl', 'wget',
            'ls', 'cat', 'grep', 'find', 'head', 'tail'
        }
        
        # Blocked commands (dangerous)
        self.blocked_commands = {
            'rm', 'rmdir', 'sudo', 'su', 'chmod', 'chown',
            'dd', 'mkfs', 'fdisk', 'mount', 'umount',
            'systemctl', 'service', 'crontab', 'at'
        }
        
        # File size limits
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.max_patch_size = 1024 * 1024  # 1MB for patches
        
        # Path restrictions
        self.allowed_paths = {
            '/tmp', '/home', '/Users',  # User directories
            'src', 'tests', 'docs'      # Project directories
        }
        
        # Blocked patterns in code
        self.blocked_patterns = [
            r'eval\s*\(',
            r'exec\s*\(',
            r'subprocess\.call\s*\(',
            r'os\.system\s*\(',
            r'__import__\s*\(',
            r'open\s*\([\'"]\s*[\/]',  # Absolute file paths
            r'socket\.',
            r'urllib\.',
            r'requests\.',
            r'hashlib\.',
            r'base64\.',
            r'pickle\.',
            r'marshal\.'
        ]
        
        # Audit log
        self.audit_log: List[Dict[str, Any]] = []
    
    def validate_file_access(self, file_path: str, operation: str = "read") -> Dict[str, Any]:
        """
        Validate file access request
        
        Args:
            file_path: Path to file
            operation: Type of operation (read, write, delete)
            
        Returns:
            Dict with validation result
        """
        try:
            path = Path(file_path).resolve()
            
            # Check if path is within allowed directories
            if not self._is_path_allowed(path):
                return {
                    "valid": False,
                    "reason": f"Path {file_path} is outside allowed directories",
                    "risk_level": "high"
                }
            
            # Check for sensitive files/directories
            for part in path.parts:
                if part in self.sensitive_files:
                    return {
                        "valid": False,
                        "reason": f"Access to sensitive file/directory: {part}",
                        "risk_level": "high"
                    }
            
            # Check for sensitive extensions
            if path.suffix.lower() in self.sensitive_extensions:
                return {
                    "valid": False,
                    "reason": f"Access to sensitive file type: {path.suffix}",
                    "risk_level": "high"
                }
            
            # Check file size for existing files
            if path.exists() and operation in ["read", "write"]:
                size = path.stat().st_size
                if size > self.max_file_size:
                    return {
                        "valid": False,
                        "reason": f"File size {size} bytes exceeds limit {self.max_file_size}",
                        "risk_level": "medium"
                    }
            
            # Log successful validation
            self._log_audit("file_access", {
                "file_path": file_path,
                "operation": operation,
                "result": "allowed"
            })
            
            return {"valid": True, "reason": "File access allowed"}
            
        except Exception as e:
            logger.error(f"File access validation error: {e}")
            return {
                "valid": False,
                "reason": f"Validation error: {str(e)}",
                "risk_level": "medium"
            }
    
    def validate_command(self, command: str) -> Dict[str, Any]:
        """
        Validate command execution request
        
        Args:
            command: Command string to execute
            
        Returns:
            Dict with validation result
        """
        try:
            # Parse command
            parts = command.strip().split()
            if not parts:
                return {
                    "valid": False,
                    "reason": "Empty command",
                    "risk_level": "medium"
                }
            
            base_cmd = parts[0].lower()
            
            # Check for blocked commands
            if base_cmd in self.blocked_commands:
                return {
                    "valid": False,
                    "reason": f"Command '{base_cmd}' is blocked for security",
                    "risk_level": "high"
                }
            
            # Check if command is whitelisted
            if base_cmd not in self.whitelisted_commands:
                return {
                    "valid": False,
                    "reason": f"Command '{base_cmd}' is not in whitelist",
                    "risk_level": "medium"
                }
            
            # Check for dangerous arguments
            dangerous_args = [
                '--rm', '-rf', 'sudo', 'su', '&&', '||', ';', '|', '>',
                '<', '>>', '2>&1', '/dev/null', '/dev/zero', '/dev/random'
            ]
            
            for arg in parts[1:]:
                if any(dangerous in arg for dangerous in dangerous_args):
                    return {
                        "valid": False,
                        "reason": f"Dangerous argument detected: {arg}",
                        "risk_level": "high"
                    }
            
            # Log successful validation
            self._log_audit("command_execution", {
                "command": command,
                "result": "allowed"
            })
            
            return {"valid": True, "reason": "Command allowed"}
            
        except Exception as e:
            logger.error(f"Command validation error: {e}")
            return {
                "valid": False,
                "reason": f"Validation error: {str(e)}",
                "risk_level": "medium"
            }
    
    def validate_patch(self, patch: str) -> Dict[str, Any]:
        """
        Validate patch for security issues
        
        Args:
            patch: Patch content to validate
            
        Returns:
            Dict with validation result
        """
        try:
            issues = []
            risk_level = "low"
            
            # Check patch size
            if len(patch.encode('utf-8')) > self.max_patch_size:
                issues.append(f"Patch size {len(patch)} exceeds limit {self.max_patch_size}")
                risk_level = "medium"
            
            # Analyze patch line by line
            lines = patch.split('\n')
            for i, line in enumerate(lines, 1):
                line = line.strip()
                
                # Check for file modifications
                if line.startswith('+++') or line.startswith('---'):
                    file_path = line[4:].strip().replace('b/', '')
                    file_validation = self.validate_file_access(file_path, "write")
                    if not file_validation["valid"]:
                        issues.append(f"Line {i}: {file_validation['reason']}")
                        if file_validation["risk_level"] == "high":
                            risk_level = "high"
                
                # Check for dangerous code patterns
                for pattern in self.blocked_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append(f"Line {i}: Dangerous pattern detected: {pattern}")
                        risk_level = "high"
                
                # Check for hardcoded secrets
                secret_patterns = [
                    r'[\'"]\w*[pP]assword\w*[\'"]\s*:',
                    r'[\'"]\w*[sS]ecret\w*[\'"]\s*:',
                    r'[\'"]\w*[kK]ey\w*[\'"]\s*:',
                    r'[\'"]\w*[tT]oken\w*[\'"]\s*:',
                    r'[A-Z0-9]{20,}',  # Long alphanumeric strings (possible API keys)
                    r'sk-[a-zA-Z0-9]{20,}',  # OpenAI API key pattern
                    r'ghp_[a-zA-Z0-9]{36}',  # GitHub personal access token
                ]
                
                for pattern in secret_patterns:
                    if re.search(pattern, line):
                        issues.append(f"Line {i}: Potential secret detected")
                        risk_level = "high"
            
            # Log validation result
            self._log_audit("patch_validation", {
                "patch_size": len(patch),
                "issues_found": len(issues),
                "risk_level": risk_level,
                "result": "allowed" if len(issues) == 0 else "blocked"
            })
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "risk_level": risk_level
            }
            
        except Exception as e:
            logger.error(f"Patch validation error: {e}")
            return {
                "valid": False,
                "issues": [f"Validation error: {str(e)}"],
                "risk_level": "medium"
            }
    
    def validate_repository_access(self, repo_url: str, operation: str = "read") -> Dict[str, Any]:
        """
        Validate repository access
        
        Args:
            repo_url: Repository URL
            operation: Type of operation
            
        Returns:
            Dict with validation result
        """
        try:
            # Check URL format
            if not repo_url.startswith(('http://', 'https://')):
                return {
                    "valid": False,
                    "reason": "Invalid URL format",
                    "risk_level": "medium"
                }
            
            # Check for suspicious domains
            blocked_domains = [
                'malicious.com', 'evil.com', 'phishing.com'
            ]
            
            for domain in blocked_domains:
                if domain in repo_url:
                    return {
                        "valid": False,
                        "reason": f"Access to blocked domain: {domain}",
                        "risk_level": "high"
                    }
            
            # Only allow GitHub for now
            if 'github.com' not in repo_url:
                return {
                    "valid": False,
                    "reason": "Only GitHub repositories are allowed",
                    "risk_level": "medium"
                }
            
            # Log successful validation
            self._log_audit("repository_access", {
                "repo_url": repo_url,
                "operation": operation,
                "result": "allowed"
            })
            
            return {"valid": True, "reason": "Repository access allowed"}
            
        except Exception as e:
            logger.error(f"Repository access validation error: {e}")
            return {
                "valid": False,
                "reason": f"Validation error: {str(e)}",
                "risk_level": "medium"
            }
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit log entries"""
        return self.audit_log[-limit:]
    
    def clear_audit_log(self):
        """Clear audit log"""
        self.audit_log.clear()
        logger.info("Audit log cleared")
    
    def _is_path_allowed(self, path: Path) -> bool:
        """Check if path is within allowed directories"""
        if not any(allowed_path in str(path) for allowed_path in self.allowed_paths):
            return False
        
        return True
    
    def _log_audit(self, action: str, details: Dict[str, Any]):
        """Log audit entry"""
        import time
        
        entry = {
            "timestamp": time.time(),
            "action": action,
            "details": details
        }
        self.audit_log.append(entry)
        
        # Keep only last 1000 entries
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        total_actions = len(self.audit_log)
        if total_actions == 0:
            return {
                "total_actions": 0,
                "blocked_actions": 0,
                "success_rate": 1.0
            }
        
        blocked_actions = sum(
            1 for entry in self.audit_log
            if entry["details"].get("result") == "blocked"
        )
        
        success_rate = (total_actions - blocked_actions) / total_actions
        
        return {
            "total_actions": total_actions,
            "blocked_actions": blocked_actions,
            "success_rate": success_rate,
            "meets_security_target": success_rate >= 0.95  # 95% success rate target
        }


# Global instance for application use
security_guardrails = SecurityGuardrails()


# Decorator for automatic security validation
def validate_security(operation_type: str):
    """Decorator for automatic security validation"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract relevant data based on operation type
            if operation_type == "file_access":
                file_path = kwargs.get("file_path") or args[1] if len(args) > 1 else None
                if file_path:
                    validation = security_guardrails.validate_file_access(file_path)
                    if not validation["valid"]:
                        raise SecurityError(f"File access blocked: {validation['reason']}")
            
            elif operation_type == "command_execution":
                command = kwargs.get("command") or args[1] if len(args) > 1 else None
                if command:
                    validation = security_guardrails.validate_command(command)
                    if not validation["valid"]:
                        raise SecurityError(f"Command blocked: {validation['reason']}")
            
            elif operation_type == "patch_validation":
                patch = kwargs.get("patch") or args[1] if len(args) > 1 else None
                if patch:
                    validation = security_guardrails.validate_patch(patch)
                    if not validation["valid"]:
                        raise SecurityError(f"Patch blocked: {validation['reason']}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


class SecurityError(Exception):
    """Security validation error"""
    pass
