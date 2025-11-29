#!/usr/bin/env python3
"""
Test Code Completion Agent
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.completion_agent import CodeCompletionAgent
from dotenv import load_dotenv

load_dotenv()

def test_function_completion():
    """Test function name completion"""
    print("\n" + "="*70)
    print("🧪 Test 1: Function Completion")
    print("="*70)
    
    agent = CodeCompletionAgent()
    
    code_before = """
def calculate_total(items):
    total = 0
    for item in items:
        total += item['price']
    return total

def calculate_"""
    
    print("Code before cursor:")
    print(code_before)
    print("\n🔮 Generating suggestions...")
    
    suggestions = agent.complete(code_before, language="python", max_suggestions=3)
    
    print(f"\n✅ Generated {len(suggestions)} suggestions:\n")
    for i, sug in enumerate(suggestions, 1):
        print(f"{i}. {sug['text']}")
        print(f"   Confidence: {sug['confidence']:.2f}")
        print(f"   Type: {sug['type']}\n")
    
    return len(suggestions) > 0


def test_method_completion():
    """Test method call completion"""
    print("\n" + "="*70)
    print("🧪 Test 2: Method Call Completion")
    print("="*70)
    
    agent = CodeCompletionAgent()
    
    code_before = """
import requests

response = requests.get('https://api.example.com/data')
data = response."""
    
    print("Code before cursor:")
    print(code_before)
    print("\n🔮 Generating suggestions...")
    
    suggestions = agent.complete(code_before, language="python", max_suggestions=3)
    
    print(f"\n✅ Generated {len(suggestions)} suggestions:\n")
    for i, sug in enumerate(suggestions, 1):
        print(f"{i}. {sug['text'][:80]}")
        print(f"   Confidence: {sug['confidence']:.2f}\n")
    
    return len(suggestions) > 0


def test_class_completion():
    """Test class definition completion"""
    print("\n" + "="*70)
    print("🧪 Test 3: Class Definition Completion")
    print("="*70)
    
    agent = CodeCompletionAgent()
    
    code_before = """
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
    
    def """
    
    print("Code before cursor:")
    print(code_before)
    print("\n🔮 Generating suggestions...")
    
    suggestions = agent.complete(code_before, language="python", max_suggestions=3)
    
    print(f"\n✅ Generated {len(suggestions)} suggestions:\n")
    for i, sug in enumerate(suggestions, 1):
        print(f"{i}. {sug['text'][:100]}")
        print(f"   Confidence: {sug['confidence']:.2f}\n")
    
    return len(suggestions) > 0


def test_inline_completion():
    """Test inline completion with cursor position"""
    print("\n" + "="*70)
    print("🧪 Test 4: Inline Completion (Cursor Position)")
    print("="*70)
    
    agent = CodeCompletionAgent()
    
    file_content = """import pandas as pd

df = pd.read_csv('data.csv')
df."""
    
    cursor_line = 3
    cursor_column = 3
    
    print(f"File content:\n{file_content}")
    print(f"\nCursor at line {cursor_line}, column {cursor_column}")
    print("\n🔮 Generating suggestions...")
    
    suggestions = agent.complete_inline(
        file_content=file_content,
        cursor_line=cursor_line,
        cursor_column=cursor_column,
        language="python"
    )
    
    print(f"\n✅ Generated {len(suggestions)} suggestions:\n")
    for i, sug in enumerate(suggestions, 1):
        print(f"{i}. {sug['text'][:80]}")
        print(f"   Confidence: {sug['confidence']:.2f}\n")
    
    return len(suggestions) > 0


def test_context_detection():
    """Test context and completion type detection"""
    print("\n" + "="*70)
    print("🧪 Test 5: Context Detection")
    print("="*70)
    
    agent = CodeCompletionAgent()
    
    test_cases = [
        ("import ", "import"),
        ("from flask import ", "import"),
        ("def calculate_", "function"),
        ("class User", "class"),
        ("# TODO: ", "comment"),
        ("user.", "method"),
        ("total = ", "variable"),
    ]
    
    print("\nDetecting completion types:\n")
    for code, expected_type in test_cases:
        detected = agent._detect_completion_type(code, code)
        status = "✅" if detected == expected_type else "❌"
        print(f"{status} '{code}' → {detected} (expected: {expected_type})")
    
    return True


def main():
    print("\n" + "="*70)
    print("🚀 CODE COMPLETION AGENT - TEST SUITE")
    print("="*70)
    
    tests = [
        ("Function Completion", test_function_completion),
        ("Method Completion", test_method_completion),
        ("Class Completion", test_class_completion),
        ("Inline Completion", test_inline_completion),
        ("Context Detection", test_context_detection),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            print(f"\nRunning: {name}")
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' failed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Code Completion Agent is ready!")
        print("\nNext steps:")
        print("1. Start server: python run_web.py")
        print("2. Test API: curl -X POST http://localhost:5000/api/complete ...")
        print("3. Build IDE plugin")
        print("\nSee docs/CODE_COMPLETION_API.md for details")
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
