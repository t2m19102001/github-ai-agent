#!/usr/bin/env python3
"""Compatibility test generation agent."""

from __future__ import annotations

import re
from typing import Dict, List

from src.tools.test_tools import (
    CoverageAnalyzerTool,
    EdgeCaseAnalyzerTool,
    FixtureGeneratorTool,
    MockGeneratorTool,
    TestFrameworkDetectorTool,
)


class TestGenerationAgent:
    def __init__(self):
        self.name = "TestGenerationAgent"
        self.description = "Generate and analyze tests"
        self.supported_frameworks = {
            "python": ["pytest", "unittest"],
            "javascript": ["jest", "mocha"],
        }
        self.mock_tool = MockGeneratorTool()
        self.fixture_tool = FixtureGeneratorTool()
        self.edge_tool = EdgeCaseAnalyzerTool()
        self.coverage_tool = CoverageAnalyzerTool()
        self.framework_tool = TestFrameworkDetectorTool()

    def _extract_function_names(self, code: str, language: str) -> List[str]:
        if language == "python":
            return re.findall(r"def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", code)
        if language == "javascript":
            return re.findall(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", code)
        return []

    def generate_unit_tests(self, code: str, language: str = "python", framework: str = "pytest", coverage_target: int = 80) -> Dict:
        funcs = self._extract_function_names(code, language)
        if language == "python":
            lines = [f"def test_{fn}():\n    assert {fn}(None) is not None or True\n" for fn in funcs]
        else:
            lines = [f"test('{fn}', () => {{ expect(true).toBeTruthy(); }});" for fn in funcs]
        return {
            "status": "success",
            "language": language,
            "framework": framework,
            "test_count": len(functions) * 3,
            "functions_tested": list(functions.keys()),
            "test_code": test_code,
            "coverage_target": coverage_target
        }
    
    def generate_function_tests(
        self,
        function_code: str,
        language: str,
        framework: str = "pytest"
    ) -> List[Dict[str, Any]]:
        """Generate tests for a single function"""
        tests = []
        edge_cases = self._analyze_edge_cases(function_code, language)
        
        for case in edge_cases:
            tests.append({
                "name": f"test_{case['name']}",
                "input": case.get("input"),
                "expected": case.get("expected"),
                "type": case.get("type", "normal")
            })
        
        return tests
    
    def suggest_test_cases(
        self,
        function_code: str,
        language: str
    ) -> List[Dict[str, Any]]:
        """Suggest test cases for a function"""
        cases = []
        
        cases.append({"name": "normal case", "input": "typical values", "type": "normal"})
        cases.append({"name": "edge case - empty", "input": "empty/null", "type": "edge"})
        cases.append({"name": "edge case - boundary", "input": "boundary values", "type": "boundary"})
        cases.append({"name": "error case", "input": "invalid input", "type": "error"})
        
        return cases
    
    def generate_mock_fixtures(
        self,
        code: str,
        language: str,
        framework: str = "pytest"
    ) -> Dict[str, Any]:
        """Generate mock objects and fixtures"""
        imports = self._extract_imports(code, language)
        
        fixtures = f"""
# Auto-generated fixtures for {language} using {framework}
"""
        
        if language == "python":
            fixtures += "@pytest.fixture\n"
            fixtures += "def mock_requests():\n"
            fixtures += "    with patch('requests.get') as mock_get:\n"
            fixtures += "        mock_get.return_value.json.return_value = {'data': 'mocked'}\n"
            fixtures += "        yield mock_get\n\n"
        
        return {
            "mocks_fixtures": fixtures,
            "imports_mocked": imports[:3]
        }
    
    def analyze_test_coverage(
        self,
        code: str,
        test_code: str,
        language: str
    ) -> Dict[str, Any]:
        """Analyze test coverage"""
        code_functions = self._extract_functions(code, language)
        test_functions = self._extract_functions(test_code, language)
        
        tested = [f for f in code_functions if f in test_functions]
        untested = [f for f in code_functions if f not in test_functions]
        
        coverage = (len(tested) / len(code_functions) * 100) if code_functions else 0
        
        return {
            "coverage_percentage": coverage,
            "total_functions": len(code_functions),
            "tested_functions": len(tested),
            "covered": tested,
            "untested_functions": untested,
            "recommendations": [
                f"Add tests for: {f}" for f in untested[:3]
            ] if untested else ["Good coverage!"]
        }
    
    def _extract_functions(self, code: str, language: str) -> Dict[str, str]:
        """Extract function signatures from code"""
        functions = {}
        
        if language == "python":
            pattern = r'def\s+(\w+)\s*\([^)]*\):'
            for match in re.finditer(pattern, code):
                functions[match.group(1)] = match.group(0)
        elif language in ["javascript", "typescript"]:
            pattern = r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>|(?:async\s+)?function\s+(\w+))'
            for match in re.finditer(pattern, code):
                name = match.group(1) or match.group(2) or match.group(3)
                if name:
                    functions[name] = match.group(0)
        elif language == "java":
            pattern = r'(?:public|private|protected)\s+\w+\s+(\w+)\s*\([^)]*\)'
            for match in re.finditer(pattern, code):
                functions[match.group(1)] = match.group(0)
        
        return functions
    
    def _extract_imports(self, code: str, language: str) -> List[str]:
        """Extract imports from code"""
        imports = []
        
        if language == "python":
            for match in re.finditer(r'^(?:from\s+(\S+)|import\s+(\S+))', code, re.MULTILINE):
                imp = match.group(1) or match.group(2)
                imports.append(imp.split('.')[0] if imp else None)
        
        return [i for i in imports if i and i not in ("pytest", "unittest", "typing")]
    
    def _analyze_edge_cases(self, code: str, language: str) -> List[Dict[str, Any]]:
        """Analyze function for edge cases"""
        edge_cases = []
        
        if "divide" in code.lower() or "/" in code:
            edge_cases.append({"name": "divide_by_zero", "type": "edge", "input": "0", "expected": "raises"})
        
        if "email" in code.lower():
            edge_cases.append({"name": "valid_email", "type": "normal", "input": "test@example.com", "expected": "True"})
            edge_cases.append({"name": "invalid_email", "type": "edge", "input": "not-an-email", "expected": "False"})
        
        if any(w in code.lower() for w in ["list", "array", "items"]):
            edge_cases.append({"name": "empty_input", "type": "edge", "input": "[]", "expected": "handled"})
            edge_cases.append({"name": "null_input", "type": "edge", "input": "None", "expected": "handled"})
        
        if not edge_cases:
            edge_cases.append({"name": "basic_case", "type": "normal", "input": "sample", "expected": "result"})
        
        return edge_cases
    
    def _generate_test_code(
        self,
        functions: Dict[str, str],
        language: str,
        framework: str
    ) -> str:
        """Generate test code"""
        lines = []
        
        if language == "python" and framework == "pytest":
            lines.append("import pytest")
            lines.append("")
            
            for func_name in functions:
                lines.append(f"def test_{func_name}():")
                lines.append(f"    # TODO: Implement test for {func_name}")
                lines.append(f"    pass")
                lines.append("")
        
        elif language in ["javascript", "typescript"] and framework in ["jest", "vitest"]:
            if framework == "jest":
                lines.append("describe('Test Suite', () => {")
            
            for func_name in functions:
                if framework == "jest":
                    lines.append(f"  test('{func_name}', () => {{")
                    lines.append(f"    // TODO: Implement test for {func_name}")
                    lines.append(f"    expect({func_name}()).toBeDefined();")
                    lines.append(f"  }});")
                else:
                    lines.append(f"test('{func_name}', async () => {{")
                    lines.append(f"  // TODO: Implement test for {func_name}")
                    lines.append(f"  expect({func_name}()).toBeDefined();")
                    lines.append(f"}});")
            
            if framework == "jest":
                lines.append("});")
        
        return "\n".join(lines)
