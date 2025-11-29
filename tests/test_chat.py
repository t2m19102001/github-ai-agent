#!/usr/bin/env python3
"""
Quick verification script to test if the chat interface is working
"""
import requests
import json
import sys
import time

def test_api():
    """Test the chat API endpoint"""
    
    print("🔍 Testing GitHub AI Agent Chat Interface...")
    print("=" * 60)
    
    # Test API endpoint
    api_url = "http://localhost:5000/api/chat"
    
    test_cases = [
        {"message": "Hello, how are you?", "mode": "ask", "name": "Ask Mode - Simple"},
        {"message": "What is Python?", "mode": "ask", "name": "Ask Mode - Question"},
        {"message": "Review my code", "mode": "agent", "name": "Agent Mode"},
        {"message": "Design a web app", "mode": "plan", "name": "Plan Mode"},
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n[Test {i}/{len(test_cases)}] {test['name']}")
        print(f"  Mode: {test['mode']}")
        print(f"  Message: {test['message']}")
        
        try:
            response = requests.post(
                api_url,
                json={"message": test["message"], "mode": test["mode"]},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Status: Success")
                print(f"  Response length: {len(data.get('response', ''))} characters")
                print(f"  Response preview: {data.get('response', '')[:100]}...")
            else:
                print(f"  ❌ Status: {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                
        except requests.exceptions.ConnectionError:
            print(f"  ❌ Error: Cannot connect to server at {api_url}")
            print(f"  Make sure the server is running: python run_web.py")
            sys.exit(1)
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            
        time.sleep(1)  # Rate limiting
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("\n🌐 Open chat interface at: http://localhost:5000")
    print("📝 For testing guide, see: TESTING_CHAT.md")

if __name__ == "__main__":
    try:
        test_api()
    except KeyboardInterrupt:
        print("\n\n⏹ Testing interrupted by user")
        sys.exit(0)
