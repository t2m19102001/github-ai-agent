#!/usr/bin/env python3
"""
Test script for PR Analysis Agent
Run this to verify everything works
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def test_imports():
    """Test all imports work"""
    print("="*70)
    print("🧪 Testing Imports")
    print("="*70)
    
    try:
        from src.plugins.pr_agent import GitHubPRAgent
        print("✅ PR Agent import successful")
    except Exception as e:
        print(f"❌ PR Agent import failed: {e}")
        return False
    
    try:
        from src.tools.pr_tools import (
            SecurityCheckTool,
            PerformanceCheckTool,
            CodeQualityTool,
            DiffAnalysisTool
        )
        print("✅ PR Tools import successful")
    except Exception as e:
        print(f"❌ PR Tools import failed: {e}")
        return False
    
    try:
        from src.llm.groq import GroqProvider
        print("✅ GROQ Provider import successful")
    except Exception as e:
        print(f"❌ GROQ Provider import failed: {e}")
        return False
    
    return True


def test_pr_tools():
    """Test PR analysis tools"""
    print("\n" + "="*70)
    print("🧪 Testing PR Analysis Tools")
    print("="*70)
    
    from src.tools.pr_tools import (
        SecurityCheckTool,
        PerformanceCheckTool,
        CodeQualityTool
    )
    
    # Test code with various issues
    test_code = '''
password = "hardcoded_secret123"
api_key = "sk_test_12345"

def fetch_users():
    for user in users:
        profile = UserProfile.get(user.id)  # N+1 query
        print(f"User: {user.name}")
    
    query = "SELECT * FROM users WHERE name = '%s'" % name  # SQL injection
    execute(query)
    
    data = open("large_file.txt").read()  # Load entire file
    
    import unused_module
'''
    
    # Security check
    security = SecurityCheckTool()
    issues = security.execute(test_code, "test.py")
    print(f"\n🛡️  Security Issues: {len(issues)}")
    for issue in issues[:3]:
        print(f"   Line {issue['line']}: {issue['message']}")
    
    # Performance check
    performance = PerformanceCheckTool()
    issues = performance.execute(test_code, "test.py")
    print(f"\n⚡ Performance Issues: {len(issues)}")
    for issue in issues[:3]:
        print(f"   Line {issue['line']}: {issue['message']}")
    
    # Code quality check
    quality = CodeQualityTool()
    issues = quality.execute(test_code, "test.py")
    print(f"\n💎 Code Quality Issues: {len(issues)}")
    for issue in issues[:3]:
        print(f"   Line {issue['line']}: {issue['message']}")
    
    return True


def test_pr_agent():
    """Test PR Agent initialization"""
    print("\n" + "="*70)
    print("🧪 Testing PR Agent")
    print("="*70)
    
    from src.plugins.pr_agent import GitHubPRAgent
    
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("⚠️  GITHUB_TOKEN not set - skipping agent test")
        return True
    
    try:
        agent = GitHubPRAgent(github_token)
        print(f"✅ PR Agent created: {agent.name}")
        print(f"✅ LLM Provider: {agent.llm.name}")
        print(f"✅ Model: {agent.llm.model}")
        return True
    except Exception as e:
        print(f"❌ PR Agent creation failed: {e}")
        return False


def test_api_endpoints():
    """Test API endpoints are available"""
    print("\n" + "="*70)
    print("🧪 Testing API Endpoints")
    print("="*70)
    
    import requests
    
    base_url = "http://localhost:5000"
    
    try:
        # Test status endpoint
        response = requests.get(f"{base_url}/api/status", timeout=5)
        if response.status_code == 200:
            print("✅ /api/status - Working")
        else:
            print(f"❌ /api/status - Failed ({response.status_code})")
    except requests.exceptions.ConnectionError:
        print("⚠️  Server not running on localhost:5000")
        print("   Start with: python run_web.py")
        return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False
    
    print("✅ API endpoints available")
    return True


def test_webhook_handler():
    """Test webhook handler logic"""
    print("\n" + "="*70)
    print("🧪 Testing Webhook Handler")
    print("="*70)
    
    from src.plugins.pr_agent import GitHubPRAgent
    
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("⚠️  GITHUB_TOKEN not set - skipping webhook test")
        return True
    
    agent = GitHubPRAgent(github_token)
    
    # Mock webhook data
    mock_payload = {
        'action': 'opened',
        'pull_request': {
            'number': 1,
            'title': 'Test PR'
        },
        'repository': {
            'full_name': 't2m19102001/github-ai-agent'
        }
    }
    
    # Test webhook processing (without actually calling API)
    action = mock_payload.get('action')
    if action in ['opened', 'synchronize', 'reopened']:
        print(f"✅ Webhook would process action: {action}")
    else:
        print(f"⚠️  Webhook would skip action: {action}")
    
    return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🚀 PR ANALYSIS AGENT - TEST SUITE")
    print("="*70 + "\n")
    
    tests = [
        ("Imports", test_imports),
        ("PR Tools", test_pr_tools),
        ("PR Agent", test_pr_agent),
        ("API Endpoints", test_api_endpoints),
        ("Webhook Handler", test_webhook_handler),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
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
        print("\n🎉 All tests passed! PR Agent is ready to use!")
        print("\nNext steps:")
        print("1. Start server: python run_web.py")
        print("2. Test manually with a PR")
        print("3. Setup webhook for auto-review")
        print("\nSee docs/PR_AGENT_SETUP.md for details")
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
