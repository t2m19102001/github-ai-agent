#!/usr/bin/env python3
"""
Test script for auto-fix functionality
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.autofix_tool import run_pytest, auto_fix
from src.llm.groq import GroqProvider
from src.agents.code_agent import CodeChatAgent

def test_pytest():
    """Test pytest runner"""
    print("🧪 Testing pytest runner...\n")
    print("-" * 60)
    
    result = run_pytest("-q")
    
    if result["success"]:
        print("✅ All tests passed!")
    else:
        print("❌ Tests failed!")
    
    print("\nOutput:")
    print(result["output"])
    print("-" * 60)


def test_autofix_simple():
    """Test auto-fix with a simple broken code"""
    print("\n🔧 Testing auto-fix with simple code...\n")
    print("-" * 60)
    
    # Broken code example
    broken_code = """
def add(a, b):
    return a - b  # Bug: should be +

def test_add():
    assert add(2, 3) == 5
"""
    
    print("Broken code:")
    print(broken_code)
    print("\n🔄 Running auto-fix...\n")
    
    # Create agent
    llm = GroqProvider()
    agent = CodeChatAgent(llm_provider=llm)
    
    # Run auto-fix
    result = auto_fix(broken_code, agent=agent, max_iterations=3)
    
    print("-" * 60)
    if result["success"]:
        print(f"✅ {result['message']}")
        print(f"\nFixed in {result['fixed_on_iteration']} iteration(s)")
        print("\nFixed code:")
        print(result['code'])
    else:
        print(f"❌ {result['message']}")
        if result.get('final_error'):
            print(f"\nLast error:\n{result['final_error']}")
    
    print("\nIteration details:")
    for it in result['iterations']:
        print(f"  Iteration {it['iteration']}: {'✅ Passed' if it['success'] else '❌ Failed'}")
    
    print("-" * 60)


def test_slash_command_demo():
    """Demo of slash command usage"""
    print("\n💡 Slash Command Usage Examples:\n")
    print("-" * 60)
    print("In the chat interface, use these commands:\n")
    print("1. Auto-fix with code:")
    print("   /autofix def test(): assert 1 == 2\n")
    print("2. The system will:")
    print("   - Run tests on the code")
    print("   - If tests fail, ask AI to fix")
    print("   - Apply fix and retry")
    print("   - Repeat up to 5 times")
    print("   - Return fixed code or error\n")
    print("3. API endpoint:")
    print("   POST /api/autofix")
    print('   {"code": "def test(): assert 1==2", "max_iterations": 5}')
    print("-" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("AUTO-FIX SYSTEM TEST")
    print("=" * 60)
    
    # Test 1: Basic pytest
    test_pytest()
    
    # Test 2: Simple auto-fix (requires LLM)
    try:
        print("\n⚠️  Note: Auto-fix test requires GROQ_API_KEY")
        print("Skipping auto-fix test. Use manually if needed.\n")
        # test_autofix_simple()  # Uncomment to test with real LLM
    except Exception as e:
        print(f"❌ Auto-fix test failed: {e}")
    
    # Test 3: Show usage examples
    test_slash_command_demo()
    
    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60)
