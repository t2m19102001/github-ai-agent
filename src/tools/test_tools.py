#!/usr/bin/env python3
"""
Test Generation Tools
Tools for test creation, mocking, and coverage analysis
"""

from src.agents.base import Tool
from src.utils.logger import get_logger
import re
from typing import Dict, List, Any, Optional

logger = get_logger(__name__)


class MockGeneratorTool(Tool):
    """Generate mock objects and fixtures from code"""
    
    def __init__(self):
        super().__init__(
            name="MockGeneratorTool",
            description="Generate mock objects and fixtures for testing"
        )
    
    def execute(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Generate mocks for external dependencies
        
        Args:
            code: Source code to analyze
            language: Programming language
            
        Returns:
            Dictionary with mock definitions
        """
        logger.info(f"Generating mocks for {language}")
        
        # Extract imports and external dependencies
        imports = self._extract_imports(code, language)
        
        # Generate mocks for each import
        mocks = {}
        for imp in imports:
            if not self._is_builtin(imp, language):
                mocks[imp] = self._generate_mock_for_import(imp, language)
        
        logger.info(f"Generated {len(mocks)} mocks")
        
        return {
            'mocks': mocks,
            'language': language,
            'imports_mocked': list(mocks.keys())
        }
    
    def _extract_imports(self, code: str, language: str) -> List[str]:
        """Extract imported modules"""
        imports = []
        
        if language == 'python':
            # import X or from X import Y
            patterns = [
                r'import\s+(\w+)',
                r'from\s+(\w+)\s+import'
            ]
        elif language in ['javascript', 'typescript']:
            # import X from 'Y' or require('Y')
            patterns = [
                r"import\s+.*?from\s+['\"]([^'\"]+)['\"]",
                r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
            ]
        else:
            return imports
        
        for pattern in patterns:
            for match in re.finditer(pattern, code):
                imports.append(match.group(1))
        
        return list(set(imports))
    
    def _is_builtin(self, module: str, language: str) -> bool:
        """Check if module is builtin"""
        builtins = {
            'python': ['os', 'sys', 'json', 're', 'math', 'datetime', 'collections', 'itertools'],
            'javascript': ['fs', 'path', 'http', 'events', 'stream'],
            'typescript': ['fs', 'path', 'http', 'events', 'stream']
        }
        return module in builtins.get(language, [])
    
    def _generate_mock_for_import(self, module: str, language: str) -> str:
        """Generate mock code for an import"""
        if language == 'python':
            return f"""
# Mock for {module}
{module}_mock = MagicMock()
# Configure mock methods as needed
"""
        elif language in ['javascript', 'typescript']:
            return f"""
// Mock for {module}
jest.mock('{module}');
const {module} = require('{module}');
"""
        return ""


class FixtureGeneratorTool(Tool):
    """Generate test fixtures and setup/teardown code"""
    
    def __init__(self):
        super().__init__(
            name="FixtureGeneratorTool",
            description="Generate test fixtures and test data"
        )
    
    def execute(self, code: str, language: str = "python",
               framework: str = "pytest") -> Dict[str, Any]:
        """
        Generate test fixtures
        
        Args:
            code: Source code
            language: Programming language
            framework: Test framework
            
        Returns:
            Fixture code
        """
        logger.info(f"Generating fixtures for {framework}")
        
        # Analyze data structures
        data_types = self._extract_data_types(code, language)
        
        # Generate fixtures
        fixtures = self._generate_fixtures(data_types, language, framework)
        
        logger.info(f"Generated {len(fixtures)} fixtures")
        
        return {
            'fixtures': fixtures,
            'language': language,
            'framework': framework
        }
    
    def _extract_data_types(self, code: str, language: str) -> List[Dict[str, str]]:
        """Extract data types and structures"""
        types = []
        
        if language == 'python':
            # Find class definitions
            pattern = r'class\s+(\w+).*?:'
            for match in re.finditer(pattern, code):
                types.append({
                    'name': match.group(1),
                    'type': 'class',
                    'language': language
                })
        
        elif language in ['javascript', 'typescript']:
            # Find class/interface definitions
            pattern = r'class\s+(\w+)'
            for match in re.finditer(pattern, code):
                types.append({
                    'name': match.group(1),
                    'type': 'class',
                    'language': language
                })
        
        return types
    
    def _generate_fixtures(self, types: List[Dict[str, str]], 
                          language: str, framework: str) -> Dict[str, str]:
        """Generate fixture code"""
        fixtures = {}
        
        if framework == 'pytest':
            fixtures['conftest'] = """
import pytest

@pytest.fixture
def sample_data():
    '''Sample test data'''
    return {
        'id': 1,
        'name': 'Test Item',
        'value': 100
    }

@pytest.fixture
def empty_data():
    '''Empty test data'''
    return {}
"""
        
        elif framework in ['jest', 'vitest']:
            fixtures['setup'] = """
beforeEach(() => {
    // Setup before each test
    jest.clearAllMocks();
});

afterEach(() => {
    // Cleanup after each test
});

beforeAll(() => {
    // Setup for all tests
});

afterAll(() => {
    // Cleanup for all tests
});
"""
        
        return fixtures


class EdgeCaseAnalyzerTool(Tool):
    """Identify edge cases and boundary conditions"""
    
    def __init__(self):
        super().__init__(
            name="EdgeCaseAnalyzerTool",
            description="Analyze code for edge cases and boundary conditions"
        )
    
    def execute(self, code: str) -> Dict[str, List[str]]:
        """
        Analyze code for potential edge cases
        
        Args:
            code: Source code to analyze
            
        Returns:
            Dictionary of identified edge cases by category
        """
        logger.info("Analyzing edge cases")
        
        edge_cases = {
            'null_empty': self._find_null_empty_cases(code),
            'boundary': self._find_boundary_cases(code),
            'type_errors': self._find_type_errors(code),
            'overflow': self._find_overflow_cases(code)
        }
        
        total = sum(len(v) for v in edge_cases.values())
        logger.info(f"Found {total} potential edge cases")
        
        return edge_cases
    
    def _find_null_empty_cases(self, code: str) -> List[str]:
        """Find null/empty handling cases"""
        cases = []
        
        # Look for null checks
        if re.search(r'if\s+.*?==\s*None|if\s+not\s+\w+', code):
            cases.append("Handle None/empty input")
        
        # Look for list operations
        if re.search(r'len\(|\.append\(|\.pop\(', code):
            cases.append("Test with empty list")
            cases.append("Test with single item")
            cases.append("Test with multiple items")
        
        # Look for string operations
        if re.search(r'\.split\(|\.strip\(|\.replace\(', code):
            cases.append("Test with empty string")
            cases.append("Test with whitespace")
        
        return cases
    
    def _find_boundary_cases(self, code: str) -> List[str]:
        """Find boundary conditions"""
        cases = []
        
        # Look for comparisons
        if re.search(r'[<>]=?|==|!=', code):
            cases.append("Test boundary values")
            cases.append("Test values just inside boundary")
            cases.append("Test values just outside boundary")
        
        # Look for ranges
        if re.search(r'range\(|for.*in', code):
            cases.append("Test at range start")
            cases.append("Test at range end")
        
        return cases
    
    def _find_type_errors(self, code: str) -> List[str]:
        """Find potential type errors"""
        cases = []
        
        # Look for type-sensitive operations
        if re.search(r'\.split\(|int\(|float\(|str\(', code):
            cases.append("Test with wrong type")
            cases.append("Test type conversion")
        
        return cases
    
    def _find_overflow_cases(self, code: str) -> List[str]:
        """Find potential overflow/underflow"""
        cases = []
        
        # Look for arithmetic
        if re.search(r'[+\-*/]|sum\(', code):
            cases.append("Test with very large numbers")
            cases.append("Test with very small numbers")
            cases.append("Test with negative numbers")
        
        return cases


class CoverageAnalyzerTool(Tool):
    """Analyze test coverage and provide recommendations"""
    
    def __init__(self):
        super().__init__(
            name="CoverageAnalyzerTool",
            description="Analyze code coverage and suggest improvements"
        )
    
    def execute(self, code: str, test_code: str) -> Dict[str, Any]:
        """
        Analyze test coverage
        
        Args:
            code: Source code
            test_code: Test code
            
        Returns:
            Coverage analysis
        """
        logger.info("Analyzing coverage")
        
        # Extract functions from source code
        source_functions = self._extract_functions(code)
        
        # Extract tested functions from test code
        tested_functions = self._extract_tested_functions(test_code, source_functions)
        
        # Calculate coverage
        if source_functions:
            coverage = (len(tested_functions) / len(source_functions)) * 100
        else:
            coverage = 0
        
        untested = [f for f in source_functions if f not in tested_functions]
        
        logger.info(f"Coverage: {coverage:.1f}%")
        
        return {
            'coverage_percentage': coverage,
            'total_functions': len(source_functions),
            'tested_functions': len(tested_functions),
            'untested_functions': untested,
            'recommendations': self._generate_recommendations(untested, coverage)
        }
    
    def _extract_functions(self, code: str) -> List[str]:
        """Extract function names from code"""
        functions = []
        
        # Python functions
        pattern = r'def\s+(\w+)\s*\('
        for match in re.finditer(pattern, code):
            functions.append(match.group(1))
        
        return functions
    
    def _extract_tested_functions(self, test_code: str, source_functions: List[str]) -> List[str]:
        """Identify which functions are tested"""
        tested = []
        
        for func in source_functions:
            if func in test_code:
                tested.append(func)
        
        return tested
    
    def _generate_recommendations(self, untested: List[str], coverage: float) -> List[str]:
        """Generate coverage improvement recommendations"""
        recommendations = []
        
        if coverage < 50:
            recommendations.append("⚠️  Critical: Less than 50% coverage. Add tests for core functions.")
        elif coverage < 80:
            recommendations.append("⚠️  Important: Coverage below 80%. Add tests for edge cases.")
        
        if untested:
            recommendations.append(f"Add tests for untested functions: {', '.join(untested[:3])}")
        
        if coverage < 100:
            recommendations.append("Consider adding integration tests for better coverage.")
        
        return recommendations


class TestFrameworkDetectorTool(Tool):
    """Detect and validate test framework compatibility"""
    
    def __init__(self):
        super().__init__(
            name="TestFrameworkDetectorTool",
            description="Detect and validate test frameworks"
        )
    
    def execute(self, language: str) -> Dict[str, List[str]]:
        """
        Get compatible test frameworks for a language
        
        Args:
            language: Programming language
            
        Returns:
            Available test frameworks
        """
        frameworks = {
            'python': ['pytest', 'unittest', 'nose2', 'testng'],
            'javascript': ['jest', 'vitest', 'mocha', 'jasmine'],
            'typescript': ['jest', 'vitest', 'mocha'],
            'java': ['junit', 'testng'],
            'csharp': ['nunit', 'xunit', 'mstest'],
            'go': ['testing', 'testify'],
            'rust': ['cargo test']
        }
        
        available = frameworks.get(language, [])
        logger.info(f"Detected {len(available)} frameworks for {language}")
        
        return {
            'language': language,
            'frameworks': available,
            'recommended': available[0] if available else None
        }


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🔧 Testing Test Tools")
    print("="*70 + "\n")
    
    # Test code
    test_code = """
import requests
import json

def calculate_total(items):
    return sum(item['price'] for item in items) if items else 0

def apply_discount(total, discount):
    if discount < 0 or discount > 100:
        raise ValueError("Invalid discount")
    return total * (1 - discount / 100)
"""
    
    # Test 1: Mock Generator
    print("📝 Test 1: Mock Generator")
    mock_tool = MockGeneratorTool()
    result = mock_tool.execute(test_code, 'python')
    print(f"✅ Generated {len(result['imports_mocked'])} mocks")
    print(f"   Imports: {result['imports_mocked']}")
    
    # Test 2: Fixture Generator
    print("\n📝 Test 2: Fixture Generator")
    fixture_tool = FixtureGeneratorTool()
    result = fixture_tool.execute(test_code, 'python', 'pytest')
    print(f"✅ Generated fixtures")
    
    # Test 3: Edge Case Analyzer
    print("\n📝 Test 3: Edge Case Analyzer")
    edge_tool = EdgeCaseAnalyzerTool()
    result = edge_tool.execute(test_code)
    print(f"✅ Found edge cases:")
    for category, cases in result.items():
        if cases:
            print(f"   {category}: {cases[0]}")
    
    # Test 4: Test Framework Detector
    print("\n📝 Test 4: Framework Detector")
    framework_tool = TestFrameworkDetectorTool()
    result = framework_tool.execute('python')
    print(f"✅ Available frameworks: {result['frameworks']}")
    
    print("\n" + "="*70)
    print("✅ All tool tests completed!")
    print("="*70)
