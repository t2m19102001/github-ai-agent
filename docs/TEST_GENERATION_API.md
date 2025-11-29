# Test Generation API Documentation

## Overview

The Test Generation Agent automatically generates unit tests for source code with multi-framework support, mock/fixture generation, and coverage analysis.

**Status**: ✅ Phase 2.3 - Complete

## Features

### 1. Intelligent Unit Test Generation
- **Multi-language support**: Python, JavaScript, TypeScript, Java, C#
- **Multi-framework support**: pytest, unittest, jest, vitest, mocha
- **Automatic test case creation** from function signatures
- **Edge case detection** and comprehensive test coverage
- **Mock/fixture generation** for external dependencies
- **Coverage target setting** (default: 80%)

### 2. Function-Level Test Generation
- Single function test generation
- 5-7 test cases per function covering:
  - Happy path scenarios
  - Edge cases
  - Error/exception scenarios
  - Boundary conditions
- Independent, isolated test functions

### 3. Test Case Suggestions
- Suggests test cases without generating full tests
- Specifies inputs and expected outputs
- Categorizes tests (happy path, edge case, error)
- Helps developers understand test requirements

### 4. Mock & Fixture Generation
- Automatically identifies external dependencies
- Generates realistic mock objects
- Creates reusable fixtures
- Framework-specific implementation (pytest fixtures, jest mocks)

### 5. Coverage Analysis
- Analyzes which functions/methods are tested
- Calculates coverage percentage
- Identifies untested functions
- Provides improvement recommendations

## API Endpoints

### 1. Generate Unit Tests

**POST** `/api/generate-tests`

Generate complete test file for given code.

**Request:**
```json
{
  "code": "def calculate_total(items):\n    return sum(item['price'] for item in items) if items else 0",
  "language": "python",
  "framework": "pytest",
  "coverage_target": 80
}
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| code | string | Yes | - | Source code to generate tests for |
| language | string | No | python | Programming language (python, javascript, typescript, java, csharp) |
| framework | string | No | pytest | Test framework |
| coverage_target | integer | No | 80 | Target code coverage percentage |

**Response (Success - 200):**
```json
{
  "status": "success",
  "test_code": "import pytest\nfrom module import calculate_total\n\ndef test_calculate_total_with_items():\n    items = [{'price': 10}, {'price': 20}]\n    assert calculate_total(items) == 30\n\ndef test_calculate_total_empty():\n    assert calculate_total([]) == 0\n\ndef test_calculate_total_single_item():\n    assert calculate_total([{'price': 50}]) == 50",
  "test_count": 3,
  "language": "python",
  "framework": "pytest",
  "coverage_target": 80,
  "functions_tested": ["calculate_total"],
  "classes_tested": []
}
```

**Response (Error - 400/500):**
```json
{
  "status": "error",
  "error": "code required"
}
```

---

### 2. Generate Function Tests

**POST** `/api/generate-tests/function`

Generate tests for a single function with detailed test cases.

**Request:**
```json
{
  "function_code": "def validate_email(email):\n    import re\n    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'\n    return bool(re.match(pattern, email))",
  "language": "python",
  "framework": "pytest"
}
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| function_code | string | Yes | - | Complete function code |
| language | string | No | python | Programming language |
| framework | string | No | pytest | Test framework |

**Response (Success - 200):**
```json
{
  "status": "success",
  "tests": [
    "def test_validate_email_valid():\n    assert validate_email('user@example.com') == True",
    "def test_validate_email_invalid_no_at():\n    assert validate_email('userexample.com') == False",
    "def test_validate_email_invalid_no_domain():\n    assert validate_email('user@.com') == False",
    "def test_validate_email_empty():\n    assert validate_email('') == False"
  ],
  "test_count": 4,
  "language": "python",
  "framework": "pytest"
}
```

---

### 3. Suggest Test Cases

**POST** `/api/generate-tests/suggest`

Get suggestions for test cases without generating full tests.

**Request:**
```json
{
  "function_code": "def divide(a, b):\n    if b == 0:\n        raise ValueError('Cannot divide by zero')\n    return a / b",
  "language": "python"
}
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| function_code | string | Yes | - | Function code to analyze |
| language | string | No | python | Programming language |

**Response (Success - 200):**
```json
{
  "status": "success",
  "test_cases": [
    {
      "name": "Normal division",
      "input": "divide(10, 2)",
      "output": "5.0",
      "type": "happy path"
    },
    {
      "name": "Division by zero",
      "input": "divide(10, 0)",
      "output": "ValueError: Cannot divide by zero",
      "type": "error"
    },
    {
      "name": "Negative numbers",
      "input": "divide(-10, 2)",
      "output": "-5.0",
      "type": "edge case"
    },
    {
      "name": "Decimal division",
      "input": "divide(10, 3)",
      "output": "3.333...",
      "type": "edge case"
    }
  ],
  "count": 4,
  "language": "python"
}
```

---

### 4. Analyze Test Coverage

**POST** `/api/generate-tests/coverage`

Analyze coverage of existing tests and provide recommendations.

**Request:**
```json
{
  "code": "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n\ndef multiply(a, b):\n    return a * b",
  "test_code": "def test_add():\n    assert add(2, 3) == 5\n\ndef test_subtract():\n    assert subtract(5, 3) == 2",
  "language": "python"
}
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| code | string | Yes | - | Source code |
| test_code | string | Yes | - | Test code |
| language | string | No | python | Programming language |

**Response (Success - 200):**
```json
{
  "status": "success",
  "analysis": {
    "coverage_percentage": 66.7,
    "total_functions": 3,
    "tested_functions": 2,
    "untested_functions": ["multiply"],
    "recommendations": [
      "⚠️ Important: Coverage below 80%. Add tests for edge cases.",
      "Add tests for untested functions: multiply",
      "Consider adding integration tests for better coverage."
    ]
  },
  "language": "python"
}
```

---

## Supported Languages & Frameworks

### Python
- **Frameworks**: pytest, unittest, nose2
- **Test patterns**: def test_*, assert statements
- **Mocking**: unittest.mock.MagicMock, pytest fixtures

### JavaScript/TypeScript
- **Frameworks**: jest, vitest, mocha, jasmine
- **Test patterns**: test(), it(), describe()
- **Mocking**: jest.mock(), sinon mocks

### Java
- **Frameworks**: junit, testng
- **Test patterns**: @Test annotations
- **Mocking**: Mockito mocks

### C#
- **Frameworks**: nunit, xunit, mstest
- **Test patterns**: [Test] attributes
- **Mocking**: Moq mocks

## Usage Examples

### Example 1: Generate Tests for Python Code

**Python Code:**
```python
def calculate_discount(price, discount_percent):
    """Calculate discounted price"""
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0 and 100")
    return price * (1 - discount_percent / 100)
```

**cURL Request:**
```bash
curl -X POST http://localhost:5000/api/generate-tests \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def calculate_discount(price, discount_percent):\n    if discount_percent < 0 or discount_percent > 100:\n        raise ValueError(\"Discount must be between 0 and 100\")\n    return price * (1 - discount_percent / 100)",
    "language": "python",
    "framework": "pytest"
  }'
```

**Generated Tests:**
```python
import pytest
from module import calculate_discount

def test_calculate_discount_valid():
    result = calculate_discount(100, 10)
    assert result == 90.0

def test_calculate_discount_zero_percent():
    result = calculate_discount(100, 0)
    assert result == 100.0

def test_calculate_discount_hundred_percent():
    result = calculate_discount(100, 100)
    assert result == 0.0

def test_calculate_discount_invalid_negative():
    with pytest.raises(ValueError):
        calculate_discount(100, -10)

def test_calculate_discount_invalid_above_hundred():
    with pytest.raises(ValueError):
        calculate_discount(100, 101)

def test_calculate_discount_decimal_values():
    result = calculate_discount(99.99, 15.5)
    assert result == pytest.approx(84.49, rel=0.01)
```

### Example 2: Generate Jest Tests for JavaScript

**JavaScript Code:**
```javascript
function authenticateUser(email, password) {
  if (!email || !password) {
    throw new Error("Email and password required");
  }
  if (!email.includes("@")) {
    throw new Error("Invalid email format");
  }
  return { email, token: "jwt_token_123" };
}
```

**cURL Request:**
```bash
curl -X POST http://localhost:5000/api/generate-tests \
  -H "Content-Type: application/json" \
  -d '{
    "code": "function authenticateUser(email, password) { ... }",
    "language": "javascript",
    "framework": "jest"
  }'
```

**Generated Tests:**
```javascript
const { authenticateUser } = require("./auth");

describe("authenticateUser", () => {
  test("authenticates user with valid credentials", () => {
    const result = authenticateUser("user@example.com", "password123");
    expect(result.email).toBe("user@example.com");
    expect(result.token).toBeDefined();
  });

  test("throws error when email is missing", () => {
    expect(() => authenticateUser("", "password123")).toThrow("Email and password required");
  });

  test("throws error when password is missing", () => {
    expect(() => authenticateUser("user@example.com", "")).toThrow("Email and password required");
  });

  test("throws error for invalid email format", () => {
    expect(() => authenticateUser("user", "password123")).toThrow("Invalid email format");
  });
});
```

### Example 3: Get Test Case Suggestions

**Request:**
```bash
curl -X POST http://localhost:5000/api/generate-tests/suggest \
  -H "Content-Type: application/json" \
  -d '{
    "function_code": "def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n ** 0.5) + 1):\n        if n % i == 0:\n            return False\n    return True",
    "language": "python"
  }'
```

**Response:**
```json
{
  "status": "success",
  "test_cases": [
    {
      "name": "Prime number",
      "input": "is_prime(7)",
      "output": "True",
      "type": "happy path"
    },
    {
      "name": "Non-prime number",
      "input": "is_prime(4)",
      "output": "False",
      "type": "happy path"
    },
    {
      "name": "Number less than 2",
      "input": "is_prime(-5)",
      "output": "False",
      "type": "boundary"
    },
    {
      "name": "Number 2 (smallest prime)",
      "input": "is_prime(2)",
      "output": "True",
      "type": "boundary"
    },
    {
      "name": "Large prime",
      "input": "is_prime(97)",
      "output": "True",
      "type": "edge case"
    }
  ],
  "count": 5
}
```

### Example 4: Analyze Test Coverage

**Request:**
```bash
curl -X POST http://localhost:5000/api/generate-tests/coverage \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n\ndef multiply(a, b):\n    return a * b\n\ndef divide(a, b):\n    if b == 0:\n        raise ValueError()\n    return a / b",
    "test_code": "def test_add():\n    assert add(2, 3) == 5\n\ndef test_multiply():\n    assert multiply(2, 3) == 6",
    "language": "python"
  }'
```

**Response:**
```json
{
  "status": "success",
  "analysis": {
    "coverage_percentage": 50.0,
    "total_functions": 4,
    "tested_functions": 2,
    "untested_functions": ["subtract", "divide"],
    "recommendations": [
      "⚠️ Critical: Less than 50% coverage. Add tests for core functions.",
      "Add tests for untested functions: subtract, divide",
      "Consider adding integration tests for better coverage."
    ]
  },
  "language": "python"
}
```

## Error Handling

### Common Errors

| Status | Error | Solution |
|--------|-------|----------|
| 400 | "code required" | Provide non-empty code parameter |
| 400 | "function_code required" | Provide non-empty function_code parameter |
| 400 | "code and test_code required" | Provide both code and test_code |
| 500 | "Invalid language" | Use supported language (python, javascript, etc.) |
| 500 | "LLM API error" | Check GROQ API key and internet connection |

## Performance

- **Test Generation**: 5-10 seconds (depends on code size)
- **Single Function Tests**: 3-5 seconds
- **Test Case Suggestions**: 2-4 seconds
- **Coverage Analysis**: 1-2 seconds

## Best Practices

### 1. Code Quality
- Provide well-structured, clean code
- Include docstrings/comments
- Follow language conventions

### 2. Test Framework Selection
- Use pytest for Python (most popular)
- Use jest for JavaScript/TypeScript
- Use unittest for legacy Python projects

### 3. Coverage Targets
- Aim for 80%+ coverage
- Focus on critical paths
- Test edge cases thoroughly

### 4. Integration with CI/CD
```yaml
# GitHub Actions example
- name: Generate Tests
  run: |
    curl -X POST http://api.example.com/api/generate-tests \
      -H "Content-Type: application/json" \
      -d '{"code": "...", "language": "python"}'

- name: Run Tests
  run: pytest --cov=src
```

## Tools Overview

### MockGeneratorTool
Generates mock objects and fixtures for external dependencies.

### FixtureGeneratorTool
Creates reusable test data and setup/teardown code.

### EdgeCaseAnalyzerTool
Identifies potential edge cases and boundary conditions.

### CoverageAnalyzerTool
Analyzes test coverage and provides recommendations.

### TestFrameworkDetectorTool
Detects compatible test frameworks for given language.

## Integration Example

### Python Integration
```python
import requests

def generate_tests(code, language="python"):
    response = requests.post(
        "http://localhost:5000/api/generate-tests",
        json={
            "code": code,
            "language": language,
            "framework": "pytest"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(result['test_code'])
        return result['test_code']
    else:
        print(f"Error: {response.json()}")
        return None

# Use it
source_code = """
def greet(name):
    return f"Hello, {name}!"
"""

test_code = generate_tests(source_code)
```

### JavaScript Integration
```javascript
async function generateTests(code, language = "python") {
  const response = await fetch("http://localhost:5000/api/generate-tests", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, language, framework: "pytest" })
  });
  
  if (response.ok) {
    const result = await response.json();
    console.log(result.test_code);
    return result.test_code;
  } else {
    const error = await response.json();
    console.error("Error:", error);
    return null;
  }
}

// Use it
const sourceCode = `
def greet(name):
    return f"Hello, {name}!"
`;

const testCode = await generateTests(sourceCode);
```

## Limitations

1. **LLM Limitations**: Generated tests are LLM-based suggestions, not perfect
2. **Complex Logic**: Highly complex algorithms may need manual review
3. **Framework Specific**: Some framework-specific features may not be fully supported
4. **Context Window**: Very large code files may exceed LLM context limits
5. **Rate Limiting**: GROQ API has rate limits

## Future Enhancements

- [ ] Property-based testing (hypothesis, QuickCheck)
- [ ] Performance benchmarking tests
- [ ] API contract testing
- [ ] Mutation testing support
- [ ] Test report generation
- [ ] Integration with test runners
- [ ] VSCode extension integration

## Support

For issues or questions:
1. Check the error message and troubleshooting guide
2. Review API documentation
3. Check GROQ API status
4. Open an issue on GitHub

---

**Last Updated**: 2024
**Version**: 1.0.0
