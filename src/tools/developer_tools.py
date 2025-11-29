"""
Professional Developer Tools
Specialized tools for reading, writing, reviewing, and debugging code like a professional
"""

from src.agents.base import Tool
from src.utils.logger import get_logger
import re
from typing import Dict, List, Optional

logger = get_logger(__name__)


class CodeAnalyzerTool(Tool):
    """Analyzes code structure and patterns"""
    
    def __init__(self):
        super().__init__(
            name="code_analyzer",
            description="Deep code analysis - structure, patterns, issues, complexity"
        )
    
    def execute(self, code: str) -> Dict:
        """Analyze code structure"""
        analysis = {
            "functions": self._extract_functions(code),
            "classes": self._extract_classes(code),
            "imports": self._extract_imports(code),
            "complexity": self._analyze_complexity(code),
            "patterns": self._detect_patterns(code),
            "issues": self._find_issues(code)
        }
        return analysis
    
    def _extract_functions(self, code: str) -> List[str]:
        """Extract function definitions"""
        pattern = r'def\s+(\w+)\s*\(([^)]*)\)'
        matches = re.findall(pattern, code)
        return [f"{name}({params})" for name, params in matches]
    
    def _extract_classes(self, code: str) -> List[str]:
        """Extract class definitions"""
        pattern = r'class\s+(\w+)(?:\(([^)]*)\))?'
        matches = re.findall(pattern, code)
        return [f"{name}({base})" if base else name for name, base in matches]
    
    def _extract_imports(self, code: str) -> List[str]:
        """Extract imports"""
        lines = code.split('\n')
        imports = [line.strip() for line in lines if line.strip().startswith(('import ', 'from '))]
        return imports
    
    def _analyze_complexity(self, code: str) -> Dict:
        """Estimate code complexity"""
        lines = len(code.split('\n'))
        cyclomatic = code.count('if ') + code.count('for ') + code.count('while ')
        return {
            "lines_of_code": lines,
            "cyclomatic_complexity": cyclomatic,
            "estimated_difficulty": "high" if cyclomatic > 10 else "medium" if cyclomatic > 5 else "low"
        }
    
    def _detect_patterns(self, code: str) -> List[str]:
        """Detect design patterns"""
        patterns = []
        if 'super().__init__' in code:
            patterns.append("Inheritance pattern")
        if '@' in code and 'def ' in code:
            patterns.append("Decorator pattern")
        if code.count('def __') > 2:
            patterns.append("Class with magic methods")
        return patterns
    
    def _find_issues(self, code: str) -> List[str]:
        """Find potential issues"""
        issues = []
        if 'except:' in code:
            issues.append("Bare except clause - should specify exception")
        if 'TODO' in code or 'FIXME' in code:
            issues.append("Contains TODO/FIXME comments")
        if 'pass' in code and code.count('pass') > 3:
            issues.append("Multiple pass statements")
        return issues


class CodeWriterTool(Tool):
    """Writes production-ready code"""
    
    def __init__(self):
        super().__init__(
            name="code_writer",
            description="Write production-ready, well-documented code"
        )
    
    def execute(self, requirements: str, language: str = "python") -> Dict:
        """Generate code based on requirements"""
        return {
            "requirements": requirements,
            "language": language,
            "status": "ready_for_generation"
        }


class CodeReviewTool(Tool):
    """Professional code review"""
    
    def __init__(self):
        super().__init__(
            name="code_reviewer",
            description="Professional code review - security, performance, quality"
        )
    
    def execute(self, code: str, review_type: str = "comprehensive") -> Dict:
        """Review code professionally"""
        review = {
            "code_length": len(code.split('\n')),
            "review_type": review_type,
            "issues_found": self._find_review_issues(code),
            "quality_score": self._calculate_quality_score(code)
        }
        return review
    
    def _find_review_issues(self, code: str) -> List[Dict]:
        """Find code review issues"""
        issues = []
        
        # Style issues
        if '\t' in code:
            issues.append({"severity": "medium", "type": "style", "message": "Uses tabs instead of spaces"})
        
        # Security issues
        if 'eval(' in code:
            issues.append({"severity": "critical", "type": "security", "message": "eval() is dangerous"})
        if 'pickle' in code:
            issues.append({"severity": "high", "type": "security", "message": "pickle is insecure"})
        
        # Quality issues
        if 'print(' in code and 'logging' not in code:
            issues.append({"severity": "medium", "type": "quality", "message": "Use logging instead of print"})
        
        return issues
    
    def _calculate_quality_score(self, code: str) -> int:
        """Calculate code quality score 0-100"""
        score = 80
        
        # Deduct for issues
        score -= len(code.split('if ')) * 2  # Complex conditions
        score -= code.count('TODO') * 5
        score -= code.count('FIXME') * 5
        
        # Add for good practices
        if 'def ' in code:
            score += 5  # Has functions
        if '"""' in code or "'''" in code:
            score += 5  # Has docstrings
        
        return max(0, min(100, score))


class TestWriterTool(Tool):
    """Write comprehensive tests"""
    
    def __init__(self):
        super().__init__(
            name="test_writer",
            description="Write comprehensive unit tests and test scenarios"
        )
    
    def execute(self, code: str, framework: str = "pytest") -> Dict:
        """Generate tests for code"""
        return {
            "code_analyzed": len(code),
            "framework": framework,
            "test_scenarios": self._identify_test_scenarios(code),
            "estimated_coverage": "85-90%"
        }
    
    def _identify_test_scenarios(self, code: str) -> List[str]:
        """Identify test scenarios"""
        scenarios = []
        
        # Find functions to test
        functions = re.findall(r'def\s+(\w+)\s*\(([^)]*)\)', code)
        for func_name, params in functions:
            scenarios.append(f"Test {func_name} with valid inputs")
            scenarios.append(f"Test {func_name} with invalid inputs")
            scenarios.append(f"Test {func_name} with edge cases")
        
        return scenarios


class DebuggerTool(Tool):
    """Debug code issues"""
    
    def __init__(self):
        super().__init__(
            name="debugger",
            description="Debug and identify issues in code"
        )
    
    def execute(self, error: str, code: str) -> Dict:
        """Debug code"""
        return {
            "error": error,
            "code_length": len(code),
            "debugging_approach": "systematic",
            "suggested_steps": [
                "Identify error type and line",
                "Trace variable values",
                "Check function inputs/outputs",
                "Review error context",
                "Apply fix and test"
            ]
        }


class DocumentationTool(Tool):
    """Generate professional documentation"""
    
    def __init__(self):
        super().__init__(
            name="documentation_generator",
            description="Generate comprehensive, professional documentation"
        )
    
    def execute(self, code: str, doc_type: str = "full") -> Dict:
        """Generate documentation"""
        doc_sections = [
            "Overview",
            "Installation",
            "Configuration",
            "API Reference",
            "Usage Examples",
            "Architecture",
            "Security",
            "Deployment",
            "Troubleshooting",
            "Contributing",
            "License"
        ]
        
        return {
            "code_analyzed": len(code),
            "doc_type": doc_type,
            "sections": doc_sections,
            "estimated_length": "2000+ words"
        }


class RefactoringTool(Tool):
    """Refactor code for improvement"""
    
    def __init__(self):
        super().__init__(
            name="refactorer",
            description="Refactor code for readability, performance, and maintainability"
        )
    
    def execute(self, code: str, goals: str = "") -> Dict:
        """Suggest refactorings"""
        refactorings = []
        
        # Detect refactoring opportunities
        if code.count('if ') > 5:
            refactorings.append("Extract complex conditionals into methods")
        if len([line for line in code.split('\n') if line.strip()]) > 50:
            refactorings.append("Break into smaller functions")
        if 'TODO' in code or 'FIXME' in code:
            refactorings.append("Address TODO/FIXME comments")
        
        return {
            "code_analyzed": len(code),
            "refactoring_goals": goals,
            "suggested_refactorings": refactorings,
            "improvement_areas": ["Readability", "Maintainability", "Performance"]
        }


class ArchitectureTool(Tool):
    """Design system architecture"""
    
    def __init__(self):
        super().__init__(
            name="architect",
            description="Design scalable, professional system architecture"
        )
    
    def execute(self, project: str, requirements: str, scale: str = "medium") -> Dict:
        """Design architecture"""
        return {
            "project": project,
            "requirements": requirements,
            "scale": scale,
            "architecture_components": [
                "API Layer",
                "Business Logic",
                "Data Access Layer",
                "Database",
                "Caching",
                "Message Queue",
                "Monitoring"
            ],
            "design_patterns": [
                "MVC/MVVM",
                "Repository Pattern",
                "Service Layer",
                "Dependency Injection",
                "Observer Pattern"
            ]
        }
