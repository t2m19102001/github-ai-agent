#!/usr/bin/env python3
"""
PR Tools Module
Tools for analyzing pull requests and code changes
"""

import re
from typing import Dict, Any, List

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from src.agents.base import Tool

logger = get_logger(__name__)


class SecurityCheckTool(Tool):
    """Tool for checking security issues in code"""
    
    name = "security_check"
    description = "Checks code for security vulnerabilities"
    
    security_patterns = [
        {"pattern": r'password\s*=\s*["\'][^"\']+["\']', "type": "hardcoded_password", "severity": "high"},
        {"pattern": r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "type": "hardcoded_api_key", "severity": "high"},
        {"pattern": r'secret\s*=\s*["\'][^"\']+["\']', "type": "hardcoded_secret", "severity": "high"},
        {"pattern": r'token\s*=\s*["\'][^"\']+["\']', "type": "hardcoded_token", "severity": "high"},
        {"pattern": r'SQL\s*\([^)]*\+[^)]*\)', "type": "sql_injection", "severity": "high"},
        {"pattern": r'execute\s*\([^)]*%[^)]*\)', "type": "sql_injection_format", "severity": "high"},
        {"pattern": r'eval\s*\(', "type": "code_injection", "severity": "high"},
        {"pattern": r'exec\s*\(', "type": "code_injection", "severity": "high"},
        {"pattern": r'os\.system\s*\(', "type": "command_injection", "severity": "high"},
        {"pattern": r'subprocess\.call\s*\([^)]*shell\s*=\s*True', "type": "command_injection", "severity": "high"},
        {"pattern": r'requests\.get\s*\([^)]*\+', "type": "ssrf", "severity": "medium"},
    ]
    
    def execute(self, code: str, filename: str = "unknown", **kwargs) -> List[Dict[str, Any]]:
        """Check code for security issues"""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            for rule in self.security_patterns:
                if re.search(rule["pattern"], line, re.IGNORECASE):
                    issues.append({
                        "line": i,
                        "type": rule["type"],
                        "message": self._get_message(rule["type"]),
                        "severity": rule["severity"],
                        "file": filename,
                        "code": line.strip()[:100]
                    })
        
        logger.info(f"Security check found {len(issues)} issues in {filename}")
        return issues
    
    def _get_message(self, issue_type: str) -> str:
        messages = {
            "hardcoded_password": "Hardcoded password detected",
            "hardcoded_api_key": "Hardcoded API key detected",
            "hardcoded_secret": "Hardcoded secret detected",
            "hardcoded_token": "Hardcoded token detected",
            "sql_injection": "Potential SQL injection vulnerability",
            "sql_injection_format": "Potential SQL injection via string formatting",
            "code_injection": "Use of eval() or exec() can lead to code injection",
            "command_injection": "Potential command injection vulnerability",
            "ssrf": "Potential Server-Side Request Forgery (SSRF)",
        }
        return messages.get(issue_type, "Security issue detected")


class PerformanceCheckTool(Tool):
    """Tool for checking performance issues in code"""
    
    name = "performance_check"
    description = "Checks code for performance problems"
    
    performance_patterns = [
        {"pattern": r'for\s+\w+\s+in\s+\w+:[\s\S]*?\.get\s*\(', "type": "n_plus_one_query", "severity": "medium"},
        {"pattern": r'for\s+\w+\s+in\s+\w+:\s*\n\s*\w+\.\w+\s*\(', "type": "n_plus_one_pattern", "severity": "medium"},
        {"pattern": r'\.read\(\)', "type": "full_file_read", "severity": "low"},
        {"pattern": r'\.readlines\(\)', "type": "full_file_read", "severity": "low"},
        {"pattern": r'json\.loads\s*\(\s*open\s*\(', "type": "loading_entire_file", "severity": "low"},
        {"pattern": r'open\([^)]+\)\.read\(\)', "type": "full_file_read", "severity": "low"},
        {"pattern": r'import\s+\w+\s+#\s*$', "type": "unused_import", "severity": "low"},
        {"pattern": r'threading\.Lock\(\)', "type": "lock_usage", "severity": "info"},
    ]
    
    def execute(self, code: str, filename: str = "unknown", **kwargs) -> List[Dict[str, Any]]:
        """Check code for performance issues"""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            for rule in self.performance_patterns:
                if re.search(rule["pattern"], line):
                    issues.append({
                        "line": i,
                        "type": rule["type"],
                        "message": self._get_message(rule["type"]),
                        "severity": rule["severity"],
                        "file": filename,
                        "code": line.strip()[:100]
                    })
        
        logger.info(f"Performance check found {len(issues)} issues in {filename}")
        return issues
    
    def _get_message(self, issue_type: str) -> str:
        messages = {
            "n_plus_one_query": "N+1 query pattern detected - may cause performance issues",
            "n_plus_one_pattern": "Loop with database call pattern detected",
            "full_file_read": "Reading entire file into memory - consider streaming",
            "loading_entire_file": "Loading entire file for JSON parsing - consider streaming",
            "unused_import": "Possibly unused import statement",
            "lock_usage": "Threading lock usage - consider async alternatives",
        }
        return messages.get(issue_type, "Performance issue detected")


class CodeQualityTool(Tool):
    """Tool for checking code quality issues"""
    
    name = "code_quality_check"
    description = "Checks code for quality and style issues"
    
    quality_patterns = [
        {"pattern": r'TODO(?!:)', "type": "incomplete_todo", "severity": "low"},
        {"pattern": r'FIXME(?!:)', "type": "unresolved_fixme", "severity": "medium"},
        {"pattern": r'except\s*:', "type": "bare_except", "severity": "medium"},
        {"pattern": r'except\s*,', "type": "bare_except_python2", "severity": "medium"},
        {"pattern": r'print\s*\(', "type": "debug_print", "severity": "low"},
        {"pattern": r'#\s*$', "type": "empty_comment", "severity": "info"},
        {"pattern": r'def\s+\w+\s*\(\s*\):', "type": "missing_docstring", "severity": "info"},
        {"pattern": r'class\s+\w+[^:]*:', "type": "missing_docstring", "severity": "info"},
        {"pattern": r'\s{2,}[\w#]', "type": "inconsistent_indentation", "severity": "low"},
        {"pattern": r'if\s+\w+\s+==\s+True:', "type": "redundant_boolean_comparison", "severity": "low"},
        {"pattern": r'if\s+\w+\s+==\s+False:', "type": "redundant_boolean_comparison", "severity": "low"},
    ]
    
    def execute(self, code: str, filename: str = "unknown", **kwargs) -> List[Dict[str, Any]]:
        """Check code for quality issues"""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            for rule in self.quality_patterns:
                if re.search(rule["pattern"], stripped):
                    issues.append({
                        "line": i,
                        "type": rule["type"],
                        "message": self._get_message(rule["type"]),
                        "severity": rule["severity"],
                        "file": filename,
                        "code": stripped[:100]
                    })
        
        logger.info(f"Code quality check found {len(issues)} issues in {filename}")
        return issues
    
    def _get_message(self, issue_type: str) -> str:
        messages = {
            "incomplete_todo": "TODO comment without description",
            "unresolved_fixme": "FIXME comment found - should be resolved",
            "bare_except": "Bare except clause - catches all exceptions including KeyboardInterrupt",
            "bare_except_python2": "Bare except clause (Python 2 style)",
            "debug_print": "Debug print statement - should be removed or logged",
            "empty_comment": "Empty comment line",
            "missing_docstring": "Missing docstring for function/class",
            "inconsistent_indentation": "Inconsistent indentation detected",
            "redundant_boolean_comparison": "Redundant boolean comparison",
        }
        return messages.get(issue_type, "Code quality issue detected")


class DiffAnalysisTool(Tool):
    """Tool for analyzing code diffs"""
    
    name = "diff_analysis"
    description = "Analyzes code changes in diff format"
    
    def execute(self, diff: str, **kwargs) -> Dict[str, Any]:
        """Analyze a diff and return statistics"""
        if isinstance(diff, list):
            diff = "\n".join(diff)
        
        stats = {
            "files_changed": 0,
            "additions": 0,
            "deletions": 0,
            "files": []
        }
        
        current_file = None
        file_stats = {"additions": 0, "deletions": 0}
        
        for line in diff.split('\n'):
            if line.startswith('diff --git'):
                if current_file:
                    stats["files"].append({**file_stats, "file": current_file})
                current_file = line.split(' b/')[-1] if ' b/' in line else "unknown"
                file_stats = {"additions": 0, "deletions": 0}
                stats["files_changed"] += 1
            elif line.startswith('+') and not line.startswith('+++'):
                stats["additions"] += 1
                if current_file:
                    file_stats["additions"] += 1
            elif line.startswith('-') and not line.startswith('---'):
                stats["deletions"] += 1
                if current_file:
                    file_stats["deletions"] += 1
        
        if current_file:
            stats["files"].append({**file_stats, "file": current_file})
        
        return stats


class CoverageAnalysisTool(Tool):
    """Tool for analyzing test coverage"""
    
    name = "coverage_analysis"
    description = "Analyzes test coverage from code changes"
    
    def execute(self, code: str, test_code: str = "", language: str = "python", **kwargs) -> Dict[str, Any]:
        """Analyze coverage of tests on code"""
        if not test_code:
            return {
                "coverage_percentage": 0,
                "message": "No test code provided for analysis"
            }
        
        code_functions = self._extract_functions(code, language)
        test_functions = self._extract_functions(test_code, language)
        
        tested = set(code_functions) & set(test_functions)
        coverage = (len(tested) / len(code_functions) * 100) if code_functions else 0
        
        return {
            "coverage_percentage": round(coverage, 2),
            "total_functions": len(code_functions),
            "tested_functions": len(tested),
            "untested_functions": list(set(code_functions) - tested)
        }
    
    def _extract_functions(self, code: str, language: str) -> List[str]:
        """Extract function names from code"""
        if language == "python":
            return re.findall(r'def\s+(\w+)\s*\(', code)
        elif language in ["javascript", "typescript"]:
            patterns = [
                r'function\s+(\w+)\s*\(',
                r'const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>',
            ]
            funcs = []
            for pattern in patterns:
                funcs.extend(re.findall(pattern, code))
            return funcs
        return []


__all__ = [
    "SecurityCheckTool",
    "PerformanceCheckTool",
    "CodeQualityTool",
    "DiffAnalysisTool",
    "CoverageAnalysisTool"
]
