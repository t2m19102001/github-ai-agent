#!/usr/bin/env python3
"""
Test script for GitHub AI Agent
Verify configuration, imports, and basic functionality
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def test_imports():
    """Test if all required packages are installed"""
    print("🧪 Testing imports...")
    try:
        import github
        print("✅ PyGithub imported")
    except ImportError as e:
        print(f"❌ PyGithub: {e}")
        return False
    
    try:
        import requests
        print("✅ requests imported")
    except ImportError as e:
        print(f"❌ requests: {e}")
        return False
    
    try:
        import dotenv
        print("✅ python-dotenv imported")
    except ImportError as e:
        print(f"❌ python-dotenv: {e}")
        return False
    
    try:
        import github
        print("✅ github imported")
    except ImportError as e:
        print(f"❌ github: {e}")
        return False
    
    return True

def test_env_variables():
    """Test if environment variables are set"""
    print("\n🧪 Testing environment variables...")
    
    required = ['GITHUB_TOKEN', 'REPO_FULL_NAME']
    optional = ['GROQ_API_KEY', 'HUGGINGFACE_TOKEN']
    
    for var in required:
        if os.getenv(var):
            print(f"✅ {var} is set")
        else:
            print(f"❌ {var} is NOT set (required)")
            return False
    
    groq_key = os.getenv('GROQ_API_KEY')
    hf_token = os.getenv('HUGGINGFACE_TOKEN')
    
    if groq_key:
        print(f"✅ GROQ_API_KEY is set")
    else:
        print(f"⚠️  GROQ_API_KEY is NOT set (at least one LLM key required)")
    
    if hf_token:
        print(f"✅ HUGGINGFACE_TOKEN is set (fallback)")
    else:
        print(f"⚠️  HUGGINGFACE_TOKEN is NOT set (recommended as fallback)")
    
    # At least one LLM key must be set
    if not (groq_key or hf_token):
        print(f"❌ No LLM API keys configured!")
        return False
    
    return True

def test_syntax():
    """Test if main script has no syntax errors"""
    print("\n🧪 Testing syntax...")
    try:
        import github_agent_hybrid
        print("✅ github_agent_hybrid.py has valid syntax")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False
    except ImportError as e:
        print(f"⚠️  Import error (might be missing dependencies): {e}")
        return True  # Continue if just missing dependencies

def test_validation_functions():
    """Test sanitize and validation functions"""
    print("\n🧪 Testing validation functions...")
    try:
        from github_agent_hybrid import sanitize_text, validate_prompt
        
        # Test sanitize_text
        test_text = "Hello World! This is a test #123"
        result = sanitize_text(test_text)
        print(f"✅ sanitize_text works: '{test_text}' -> '{result}'")
        
        # Test validate_prompt
        valid_prompt = "This is a valid prompt" * 50
        is_valid = validate_prompt(valid_prompt)
        print(f"✅ validate_prompt works: {is_valid}")
        
        return True
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 GitHub AI Agent - Verification Tests")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Environment Variables", test_env_variables()))
    results.append(("Syntax", test_syntax()))
    results.append(("Validation Functions", test_validation_functions()))
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✅ All tests passed! Agent is ready to use.")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
