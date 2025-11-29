#!/usr/bin/env python3
"""
Tests for Test Generation Agent
"""

import pytest
from src.agents.test_agent import TestGenerationAgent
from src.tools.test_tools import (
    MockGeneratorTool,
    FixtureGeneratorTool,
    EdgeCaseAnalyzerTool,
    CoverageAnalyzerTool,
    TestFrameworkDetectorTool
)


class TestTestGenerationAgent:
    """Test suite for TestGenerationAgent"""
    
    @pytest.fixture
    def agent(self):
        """Create test agent"""
        return TestGenerationAgent()
    
    @pytest.fixture
    def sample_python_code(self):
        """Sample Python code for testing"""
        return """
def calculate_total(items):
    '''Calculate total price of items'''
    if not items:
        return 0
    return sum(item['price'] for item in items)

def apply_discount(total, discount_percent):
    '''Apply discount to total'''
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Invalid discount percentage")
    return total * (1 - discount_percent / 100)

class OrderCalculator:
    def __init__(self):
        self.tax_rate = 0.1
    
    def calculate_with_tax(self, subtotal):
        return subtotal * (1 + self.tax_rate)
"""
    
    def test_agent_initialization(self, agent):
        """Test agent initializes correctly"""
        assert agent.name == "TestGenerationAgent"
        assert "test" in agent.description.lower()
        assert agent.supported_frameworks['python'] == ['pytest', 'unittest']
        print("✅ Agent initialized")
    
    def test_generate_unit_tests_python(self, agent, sample_python_code):
        """Test Python unit test generation"""
        result = agent.generate_unit_tests(
            code=sample_python_code,
            language="python",
            framework="pytest",
            coverage_target=80
        )
        
        assert result['status'] == 'success'
        assert result['language'] == 'python'
        assert result['framework'] == 'pytest'
        assert result['test_count'] > 0
        assert 'calculate_total' in result['functions_tested']
        assert 'apply_discount' in result['functions_tested']
        assert len(result['test_code']) > 0
        
        print(f"✅ Generated {result['test_count']} tests")
        print(f"   Functions tested: {result['functions_tested']}")
    
    def test_generate_unit_tests_javascript(self, agent):
        """Test JavaScript unit test generation"""
        js_code = """
function calculateTotal(items) {
    if (!items || items.length === 0) return 0;
    return items.reduce((sum, item) => sum + item.price, 0);
}

function applyDiscount(total, discountPercent) {
    if (discountPercent < 0 || discountPercent > 100) {
        throw new Error("Invalid discount");
    }
    return total * (1 - discountPercent / 100);
}
"""
        result = agent.generate_unit_tests(
            code=js_code,
            language="javascript",
            framework="jest"
        )
        
        assert result['status'] == 'success'
        assert result['language'] == 'javascript'
        assert result['framework'] == 'jest'
        assert result['test_count'] > 0
        assert len(result['test_code']) > 0
        
        print(f"✅ Generated {result['test_count']} JavaScript tests")
    
    def test_generate_function_tests(self, agent):
        """Test single function test generation"""
        function_code = """
def validate_email(email):
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
"""
        
        tests = agent.generate_function_tests(
            function_code=function_code,
            language="python",
            framework="pytest"
        )
        
        assert isinstance(tests, list)
        assert len(tests) > 0
        
        print(f"✅ Generated {len(tests)} tests for email validation")
    
    def test_suggest_test_cases(self, agent):
        """Test test case suggestions"""
        function_code = """
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""
        
        cases = agent.suggest_test_cases(
            function_code=function_code,
            language="python"
        )
        
        assert isinstance(cases, list)
        assert len(cases) > 0
        assert all('name' in case or 'input' in case for case in cases)
        
        print(f"✅ Suggested {len(cases)} test cases")
        for case in cases[:3]:
            print(f"   - {case.get('name', case.get('input', 'Test'))}")
    
    def test_generate_mock_fixtures(self, agent):
        """Test mock and fixture generation"""
        code = """
import requests
from datetime import datetime

def fetch_user_data(user_id):
    response = requests.get(f'https://api.example.com/users/{user_id}')
    return response.json()
"""
        
        result = agent.generate_mock_fixtures(
            code=code,
            language="python",
            framework="pytest"
        )
        
        assert 'mocks_fixtures' in result
        assert len(result['mocks_fixtures']) > 0
        assert 'pytest' in result['mocks_fixtures'].lower() or '@' in result['mocks_fixtures']
        
        print(f"✅ Generated mocks and fixtures")
    
    def test_analyze_test_coverage(self, agent):
        """Test coverage analysis"""
        code = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b
"""
        
        test_code = """
def test_add():
    assert add(2, 3) == 5

def test_subtract():
    assert subtract(5, 3) == 2

# multiply not tested
"""
        
        analysis = agent.analyze_test_coverage(
            code=code,
            test_code=test_code,
            language="python"
        )
        
        assert 'coverage_percentage' in analysis
        assert 'covered' in analysis or analysis.get('coverage_percentage', 0) >= 0
        assert 'recommendations' in analysis
        
        print(f"✅ Coverage analysis: {analysis.get('coverage_percentage', 'N/A')}%")


class TestMockGeneratorTool:
    """Test suite for MockGeneratorTool"""
    
    @pytest.fixture
    def tool(self):
        """Create mock generator tool"""
        return MockGeneratorTool()
    
    def test_tool_initialization(self, tool):
        """Test tool initializes"""
        assert tool.name == "MockGeneratorTool"
        print("✅ MockGeneratorTool initialized")
    
    def test_extract_imports_python(self, tool):
        """Test Python import extraction"""
        code = """
import os
import sys
from datetime import datetime
from requests import get
"""
        
        result = tool.execute(code, language="python")
        
        assert len(result['imports_mocked']) >= 2
        assert 'requests' in result['imports_mocked'] or 'get' in result['imports_mocked']
        
        print(f"✅ Extracted {len(result['imports_mocked'])} imports")


class TestFixtureGeneratorTool:
    """Test suite for FixtureGeneratorTool"""
    
    @pytest.fixture
    def tool(self):
        """Create fixture generator tool"""
        return FixtureGeneratorTool()
    
    def test_tool_initialization(self, tool):
        """Test tool initializes"""
        assert tool.name == "FixtureGeneratorTool"
        print("✅ FixtureGeneratorTool initialized")
    
    def test_generate_pytest_fixtures(self, tool):
        """Test pytest fixture generation"""
        code = """
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
"""
        
        result = tool.execute(code, language="python", framework="pytest")
        
        assert 'fixtures' in result
        assert len(result['fixtures']) > 0
        assert '@pytest.fixture' in result['fixtures']['conftest']
        
        print(f"✅ Generated pytest fixtures")


class TestEdgeCaseAnalyzerTool:
    """Test suite for EdgeCaseAnalyzerTool"""
    
    @pytest.fixture
    def tool(self):
        """Create edge case analyzer"""
        return EdgeCaseAnalyzerTool()
    
    def test_tool_initialization(self, tool):
        """Test tool initializes"""
        assert tool.name == "EdgeCaseAnalyzerTool"
        print("✅ EdgeCaseAnalyzerTool initialized")
    
    def test_find_edge_cases(self, tool):
        """Test edge case detection"""
        code = """
def process_list(items):
    if not items:
        return []
    result = []
    for item in items:
        result.append(item * 2)
    return result
"""
        
        result = tool.execute(code)
        
        assert 'null_empty' in result
        assert 'boundary' in result
        
        total_cases = sum(len(v) for v in result.values())
        assert total_cases > 0
        
        print(f"✅ Found {total_cases} edge cases")


class TestCoverageAnalyzerTool:
    """Test suite for CoverageAnalyzerTool"""
    
    @pytest.fixture
    def tool(self):
        """Create coverage analyzer"""
        return CoverageAnalyzerTool()
    
    def test_tool_initialization(self, tool):
        """Test tool initializes"""
        assert tool.name == "CoverageAnalyzerTool"
        print("✅ CoverageAnalyzerTool initialized")
    
    def test_analyze_coverage(self, tool):
        """Test coverage analysis"""
        code = """
def func1():
    pass

def func2():
    pass

def func3():
    pass
"""
        
        test_code = """
def test_func1():
    assert func1() is None

def test_func2():
    assert func2() is None
"""
        
        result = tool.execute(code, test_code)
        
        assert 'coverage_percentage' in result
        assert result['total_functions'] == 3
        assert result['tested_functions'] == 2
        assert 'func3' in result['untested_functions']
        assert result['coverage_percentage'] > 0
        
        print(f"✅ Coverage: {result['coverage_percentage']:.0f}%")


class TestTestFrameworkDetectorTool:
    """Test suite for TestFrameworkDetectorTool"""
    
    @pytest.fixture
    def tool(self):
        """Create framework detector"""
        return TestFrameworkDetectorTool()
    
    def test_tool_initialization(self, tool):
        """Test tool initializes"""
        assert tool.name == "TestFrameworkDetectorTool"
        print("✅ TestFrameworkDetectorTool initialized")
    
    def test_detect_python_frameworks(self, tool):
        """Test Python framework detection"""
        result = tool.execute('python')
        
        assert result['language'] == 'python'
        assert 'pytest' in result['frameworks']
        assert 'unittest' in result['frameworks']
        assert result['recommended'] is not None
        
        print(f"✅ Python frameworks: {result['frameworks']}")
    
    def test_detect_javascript_frameworks(self, tool):
        """Test JavaScript framework detection"""
        result = tool.execute('javascript')
        
        assert result['language'] == 'javascript'
        assert 'jest' in result['frameworks']
        assert len(result['frameworks']) > 0
        
        print(f"✅ JavaScript frameworks: {result['frameworks']}")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🧪 Running Test Generation Test Suite")
    print("="*70 + "\n")
    
    pytest.main([__file__, "-v", "-s"])
    
    print("\n" + "="*70)
    print("✅ All tests completed!")
    print("="*70)
