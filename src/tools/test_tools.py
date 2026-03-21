#!/usr/bin/env python3
"""
Test Generation Tools
Tools for generating tests, mocks, and fixtures
"""

from typing import Dict, Any, List
import re

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from src.agents.base import Tool

logger = get_logger(__name__)


class MockGeneratorTool(Tool):
    """Tool that generates mocks for external dependencies"""
    
    name = "MockGeneratorTool"
    description = "Generates mock objects and patch statements for testing"
    
    def execute(self, code: str, language: str = "python", **kwargs) -> Dict[str, Any]:
        """Generate mocks for imports in code"""
        imports = self._extract_imports(code, language)
        mocks = self._generate_mocks(imports, language)
        
        return {
            "imports_mocked": imports,
            "mock_code": mocks,
            "count": len(imports)
        }
    
    def _extract_imports(self, code: str, language: str) -> List[str]:
        """Extract importable modules from code"""
        imports = []
        
        if language == "python":
            patterns = [
                r'^import\s+(\w+)',
                r'^from\s+(\S+)\s+import',
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, code, re.MULTILINE):
                    module = match.group(1)
                    if module and module not in ("pytest", "unittest", "typing", "os", "sys"):
                        imports.append(module)
        
        return imports
    
    def _generate_mocks(self, imports: List[str], language: str) -> str:
        """Generate mock code"""
        if language == "python":
            code = "from unittest.mock import patch, Mock\n\n"
            for module in imports:
                code += f"@patch('{module}')\n"
                code += f"def mock_{module}(mock_obj):\n"
                code += f"    mock_obj.return_value = Mock()\n"
                code += "    yield mock_obj\n\n"
            return code
        
        return ""


class FixtureGeneratorTool(Tool):
    """Tool that generates test fixtures"""
    
    name = "FixtureGeneratorTool"
    description = "Generates pytest fixtures and test data"
    
    def execute(
        self,
        code: str,
        language: str = "python",
        framework: str = "pytest",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate fixtures for test classes/functions"""
        classes = self._extract_classes(code, language)
        fixtures = self._generate_fixtures(classes, framework)
        
        return {
            "fixtures": fixtures,
            "classes_found": classes,
            "framework": framework
        }
    
    def _extract_classes(self, code: str, language: str) -> List[str]:
        """Extract class names from code"""
        if language == "python":
            return re.findall(r'class\s+(\w+)', code)
        return []
    
    def _generate_fixtures(
        self,
        classes: List[str],
        framework: str
    ) -> Dict[str, str]:
        """Generate fixture code"""
        fixtures = {}
        
        if framework == "pytest":
            conftest = "import pytest\n\n\n"
            
            for cls in classes:
                conftest += f"@pytest.fixture\n"
                conftest += f"def {cls.lower()}_instance():\n"
                conftest += f"    return {cls}()\n\n"
            
            fixtures["conftest"] = conftest
        
        return fixtures


class EdgeCaseAnalyzerTool(Tool):
    """Tool that analyzes code for edge cases"""
    
    name = "EdgeCaseAnalyzerTool"
    description = "Finds potential edge cases in functions"
    
    def execute(self, code: str, language: str = "python", **kwargs) -> Dict[str, Any]:
        """Analyze code for edge cases"""
        functions = self._extract_functions(code, language)
        edge_cases = self._analyze_functions(functions)
        
        return edge_cases
    
    def _extract_functions(self, code: str, language: str) -> List[Dict[str, str]]:
        """Extract function details"""
        functions = []
        
        if language == "python":
            pattern = r'def\s+(\w+)\s*\(([^)]*)\):'
            for match in re.finditer(pattern, code):
                functions.append({
                    "name": match.group(1),
                    "params": match.group(2)
                })
        
        return functions
    
    def _analyze_functions(self, functions: List[Dict[str, str]]) -> Dict[str, List]:
        """Analyze functions for edge cases"""
        cases = {
            "null_empty": [],
            "boundary": [],
            "error": [],
            "special": []
        }
        
        for func in functions:
            params = func["params"]
            
            if any(p in params for p in ["list", "items", "arr", "array"]):
                cases["null_empty"].append({
                    "function": func["name"],
                    "case": "empty collection",
                    "input": "[] or None"
                })
            
            if "/" in params or "div" in func["name"].lower():
                cases["error"].append({
                    "function": func["name"],
                    "case": "division by zero",
                    "input": "0"
                })
            
            if any(t in params for t in ["str", "string", "text"]):
                cases["boundary"].append({
                    "function": func["name"],
                    "case": "empty string",
                    "input": '""'
                })
        
        if not any(cases.values()):
            cases["null_empty"].append({
                "function": "generic",
                "case": "null check",
                "input": "None"
            })
        
        return cases


class CoverageAnalyzerTool(Tool):
    """Tool that analyzes test coverage"""
    
    name = "CoverageAnalyzerTool"
    description = "Analyzes code coverage of tests"
    
    def execute(
        self,
        code: str,
        test_code: str,
        language: str = "python",
        **kwargs
    ) -> Dict[str, Any]:
        """Analyze coverage between code and tests"""
        code_functions = self._extract_code_functions(code, language)
        test_functions = self._extract_test_functions(test_code, language)
        
        normalized_test_funcs = {self._normalize_function_name(f) for f in test_functions}
        
        tested = set()
        for func in code_functions:
            normalized = self._normalize_function_name(func)
            if normalized in normalized_test_funcs or func in test_functions:
                tested.add(func)
        
        untested = set(code_functions) - tested
        
        coverage = len(tested) / len(code_functions) * 100 if code_functions else 0
        
        return {
            "coverage_percentage": coverage,
            "total_functions": len(code_functions),
            "tested_functions": len(tested),
            "tested": list(tested),
            "untested_functions": list(untested)
        }
    
    def _extract_code_functions(self, code: str, language: str) -> List[str]:
        """Extract function names from source code"""
        if language == "python":
            pattern = r'def\s+(\w+)\s*\('
            return re.findall(pattern, code)
        elif language in ["javascript", "typescript"]:
            patterns = [
                r'function\s+(\w+)\s*\(',
                r'const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>',
                r'let\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>',
                r'(?:async\s+)?function\s+(\w+)\s*\(',
            ]
            funcs = []
            for pattern in patterns:
                funcs.extend(re.findall(pattern, code))
            return funcs
        return []
    
    def _extract_test_functions(self, test_code: str, language: str) -> List[str]:
        """Extract function names from test code"""
        if language == "python":
            pattern = r'def\s+(\w+)\s*\('
            all_funcs = re.findall(pattern, test_code)
            return all_funcs
        elif language in ["javascript", "typescript"]:
            patterns = [
                r'(?:test|it|describe)\s*[\(\'"]\s*[\'"](?:[^\'"]+[\'"]\s*,\s*)?(?:async\s+)?(\w+)\s*\(',
                r'function\s+(\w+)\s*\(',
                r'const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>',
            ]
            funcs = []
            for pattern in patterns:
                funcs.extend(re.findall(pattern, test_code))
            return funcs
        return []
    
    def _normalize_function_name(self, name: str) -> str:
        """Normalize function name by removing common prefixes"""
        for prefix in ["test_", "Test", "test"]:
            if name.startswith(prefix) and len(name) > len(prefix):
                return name[len(prefix):]
        return name


class TestFrameworkDetectorTool(Tool):
    """Tool that detects test framework from code"""
    
    name = "TestFrameworkDetectorTool"
    description = "Detects which test framework is used"
    
    def execute(self, language: str = "python", **kwargs) -> Dict[str, Any]:
        """Detect test framework for language"""
        frameworks = self._get_frameworks(language)
        recommended = frameworks[0] if frameworks else None
        
        return {
            "language": language,
            "frameworks": frameworks,
            "recommended": recommended
        }
    
    def _get_frameworks(self, language: str) -> List[str]:
        """Get available frameworks for language"""
        mapping = {
            "python": ["pytest", "unittest", "doctest", "nose2"],
            "javascript": ["jest", "mocha", "vitest", "jasmine"],
            "typescript": ["jest", "vitest", "mocha"],
            "java": ["junit5", "junit4", "testng"],
            "go": ["testing", "ginkgo", "goconvey"],
            "rust": ["cargo test", "rstest"],
        }
        return mapping.get(language.lower(), ["unknown"])


__all__ = [
    "MockGeneratorTool",
    "FixtureGeneratorTool",
    "EdgeCaseAnalyzerTool",
    "CoverageAnalyzerTool",
    "TestFrameworkDetectorTool"
]
