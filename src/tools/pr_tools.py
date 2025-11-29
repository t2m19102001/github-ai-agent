#!/usr/bin/env python3
"""
Tools for PR analysis
Security checks, performance analysis, code quality
"""

import re
from typing import List, Dict, Any
from src.agents.base import Tool
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SecurityCheckTool(Tool):
    """Detect security issues in code changes"""
    
    def __init__(self):
        super().__init__(
            name="security_check",
            description="Detects potential security vulnerabilities"
        )
        
        # Security patterns to detect
        self.patterns = {
            'hardcoded_secret': [
                r'(?i)(password|passwd|pwd|secret|token|api_key|apikey)\s*=\s*["\'][^"\']+["\']',
                r'(?i)(api|secret|token)[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']',
            ],
            'sql_injection': [
                r'execute\s*\(\s*["\'].*%s.*["\']',
                r'\.raw\s*\(',
                r'query\s*\(\s*["\'].*\+.*["\']',
            ],
            'xss_vulnerability': [
                r'innerHTML\s*=',
                r'dangerouslySetInnerHTML',
                r'eval\s*\(',
            ],
            'unsafe_deserialization': [
                r'pickle\.loads',
                r'yaml\.load\(',
                r'eval\s*\(',
            ],
            'weak_crypto': [
                r'md5\s*\(',
                r'sha1\s*\(',
                r'Random\s*\(',
            ],
        }
    
    def execute(self, code: str, filename: str = '') -> List[Dict[str, Any]]:
        """
        Check code for security issues
        
        Args:
            code: Code to analyze
            filename: File name for context
            
        Returns:
            List of security issues found
        """
        issues = []
        
        for issue_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, code, re.MULTILINE)
                for match in matches:
                    line_num = code[:match.start()].count('\n') + 1
                    issues.append({
                        'type': issue_type,
                        'severity': 'high',
                        'line': line_num,
                        'code': match.group(0),
                        'file': filename,
                        'message': self._get_issue_message(issue_type)
                    })
        
        return issues
    
    def _get_issue_message(self, issue_type: str) -> str:
        """Get human-readable message for issue type"""
        messages = {
            'hardcoded_secret': 'Hardcoded secret detected. Use environment variables instead.',
            'sql_injection': 'Potential SQL injection vulnerability. Use parameterized queries.',
            'xss_vulnerability': 'Potential XSS vulnerability. Sanitize user input.',
            'unsafe_deserialization': 'Unsafe deserialization detected. Validate input.',
            'weak_crypto': 'Weak cryptographic algorithm. Use SHA-256 or better.',
        }
        return messages.get(issue_type, 'Security issue detected')


class PerformanceCheckTool(Tool):
    """Detect performance issues"""
    
    def __init__(self):
        super().__init__(
            name="performance_check",
            description="Detects potential performance issues"
        )
        
        self.patterns = {
            'n_plus_one_query': [
                r'for\s+\w+\s+in\s+.*:\s*\n\s*.*\.get\(',
                r'for\s+\w+\s+in\s+.*:\s*\n\s*.*\.filter\(',
            ],
            'inefficient_loop': [
                r'\+\=\s*\[.*\]',  # List concatenation in loop
                r'\.append\(.*\)\s+for.*in',  # Could use list comprehension
            ],
            'missing_index': [
                r'\.filter\(.*\)\.all\(\)',
                r'WHERE.*LIKE',
            ],
            'large_file_load': [
                r'\.read\(\)',
                r'\.readlines\(\)',
            ],
        }
    
    def execute(self, code: str, filename: str = '') -> List[Dict[str, Any]]:
        """Check code for performance issues"""
        issues = []
        
        for issue_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, code, re.MULTILINE)
                for match in matches:
                    line_num = code[:match.start()].count('\n') + 1
                    issues.append({
                        'type': issue_type,
                        'severity': 'medium',
                        'line': line_num,
                        'code': match.group(0),
                        'file': filename,
                        'message': self._get_issue_message(issue_type)
                    })
        
        return issues
    
    def _get_issue_message(self, issue_type: str) -> str:
        """Get human-readable message"""
        messages = {
            'n_plus_one_query': 'Potential N+1 query. Consider using select_related or prefetch_related.',
            'inefficient_loop': 'Inefficient loop operation. Consider list comprehension or generators.',
            'missing_index': 'Query may need database index for better performance.',
            'large_file_load': 'Loading entire file into memory. Consider streaming for large files.',
        }
        return messages.get(issue_type, 'Performance issue detected')


class CodeQualityTool(Tool):
    """Check code quality and best practices"""
    
    def __init__(self):
        super().__init__(
            name="code_quality",
            description="Checks code quality and best practices"
        )
        
        self.patterns = {
            'long_function': None,  # Check by line count
            'too_many_parameters': None,  # Check parameter count
            'missing_docstring': None,  # Check for docstrings
            'unused_import': r'import\s+\w+(?!\s+as)',
            'bare_except': r'except\s*:',
            'print_statement': r'\bprint\s*\(',
            'todo_comment': r'#\s*TODO',
            'magic_number': r'(?<!["\'])\b\d{3,}\b(?!["\'])',
        }
    
    def execute(self, code: str, filename: str = '') -> List[Dict[str, Any]]:
        """Check code quality"""
        issues = []
        
        # Pattern-based checks
        for issue_type, pattern in self.patterns.items():
            if pattern:
                matches = re.finditer(pattern, code, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    line_num = code[:match.start()].count('\n') + 1
                    issues.append({
                        'type': issue_type,
                        'severity': 'low',
                        'line': line_num,
                        'code': match.group(0),
                        'file': filename,
                        'message': self._get_issue_message(issue_type)
                    })
        
        # Check function length
        functions = re.finditer(r'def\s+\w+\s*\([^)]*\):', code)
        for func in functions:
            func_start = func.start()
            func_line = code[:func_start].count('\n') + 1
            
            # Find function end (next def or class)
            remaining = code[func_start:]
            next_def = re.search(r'\n(?:def|class)\s+', remaining)
            func_end = func_start + next_def.start() if next_def else len(code)
            
            func_lines = code[func_start:func_end].count('\n')
            
            if func_lines > 50:
                issues.append({
                    'type': 'long_function',
                    'severity': 'medium',
                    'line': func_line,
                    'code': func.group(0),
                    'file': filename,
                    'message': f'Function is {func_lines} lines long. Consider breaking into smaller functions.'
                })
        
        return issues
    
    def _get_issue_message(self, issue_type: str) -> str:
        """Get human-readable message"""
        messages = {
            'unused_import': 'Unused import detected. Remove to keep code clean.',
            'bare_except': 'Bare except clause. Specify exception type.',
            'print_statement': 'Print statement found. Use logging instead.',
            'todo_comment': 'TODO comment found. Create an issue to track this.',
            'magic_number': 'Magic number detected. Use named constant.',
        }
        return messages.get(issue_type, 'Code quality issue detected')


class DiffAnalysisTool(Tool):
    """Analyze git diffs"""
    
    def __init__(self):
        super().__init__(
            name="diff_analysis",
            description="Analyzes git diff patches"
        )
    
    def execute(self, patch: str) -> Dict[str, Any]:
        """
        Analyze a git diff patch
        
        Args:
            patch: Git diff patch text
            
        Returns:
            Analysis with additions, deletions, and context
        """
        if not patch:
            return {
                'additions': [],
                'deletions': [],
                'context': [],
                'stats': {'added': 0, 'removed': 0}
            }
        
        additions = []
        deletions = []
        context = []
        
        added_count = 0
        removed_count = 0
        
        for line in patch.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                additions.append(line[1:])
                added_count += 1
            elif line.startswith('-') and not line.startswith('---'):
                deletions.append(line[1:])
                removed_count += 1
            elif line.startswith(' '):
                context.append(line[1:])
        
        return {
            'additions': additions,
            'deletions': deletions,
            'context': context,
            'stats': {
                'added': added_count,
                'removed': removed_count,
                'total': added_count + removed_count
            }
        }


def analyze_pr_files(files_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Analyze all files in a PR
    
    Args:
        files_data: List of file data from PR
        
    Returns:
        Dictionary with security, performance, and quality issues
    """
    security_tool = SecurityCheckTool()
    performance_tool = PerformanceCheckTool()
    quality_tool = CodeQualityTool()
    
    all_issues = {
        'security': [],
        'performance': [],
        'quality': []
    }
    
    for file_data in files_data:
        filename = file_data.get('filename', '')
        patch = file_data.get('patch', '')
        
        if not patch:
            continue
        
        # Extract added lines from patch
        added_lines = []
        for line in patch.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line[1:])
        
        added_code = '\n'.join(added_lines)
        
        # Run checks
        all_issues['security'].extend(security_tool.execute(added_code, filename))
        all_issues['performance'].extend(performance_tool.execute(added_code, filename))
        all_issues['quality'].extend(quality_tool.execute(added_code, filename))
    
    logger.info(f"Found {len(all_issues['security'])} security, "
                f"{len(all_issues['performance'])} performance, "
                f"{len(all_issues['quality'])} quality issues")
    
    return all_issues


if __name__ == "__main__":
    # Test the tools
    test_code = """
password = "hardcoded123"

def long_function():
    for user in users:
        data = User.get(user.id)
        print(data)
    
    execute("SELECT * FROM users WHERE name = '%s'" % name)
"""
    
    print("🧪 Testing Security Check...")
    sec_tool = SecurityCheckTool()
    issues = sec_tool.execute(test_code)
    print(f"Found {len(issues)} security issues:")
    for issue in issues:
        print(f"  - Line {issue['line']}: {issue['message']}")
    
    print("\n🧪 Testing Performance Check...")
    perf_tool = PerformanceCheckTool()
    issues = perf_tool.execute(test_code)
    print(f"Found {len(issues)} performance issues:")
    for issue in issues:
        print(f"  - Line {issue['line']}: {issue['message']}")
    
    print("\n🧪 Testing Code Quality...")
    quality_tool = CodeQualityTool()
    issues = quality_tool.execute(test_code)
    print(f"Found {len(issues)} quality issues:")
    for issue in issues:
        print(f"  - Line {issue['line']}: {issue['message']}")
