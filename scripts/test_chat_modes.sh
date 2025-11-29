#!/bin/bash

API_URL="http://localhost:5000"
PROJECT_DIR="/Users/minhman/Develop/github-ai-agent"
TEST_SAMPLES_DIR="$PROJECT_DIR/test_samples"

echo "🧪 Testing All Chat Modes with Workspace Files..."
echo ""

# Test 1: Ask Mode
echo "1️⃣ Testing ASK Mode..."
curl -s -X POST "$API_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Odoo là gì?",
    "mode": "ask"
  }' | python3 -m json.tool
echo ""
echo ""

# Test 2: Agent Mode (with file)
echo "2️⃣ Testing AGENT Mode (with file upload)..."
curl -s -X POST "$API_URL/api/chat" \
  -F "message=Phân tích file code này" \
  -F "mode=agent" \
  -F "file=@$TEST_SAMPLES_DIR/factorial.py" | python3 -m json.tool
echo ""
echo ""

# Test 3: Agent Mode (without file)
echo "3️⃣ Testing AGENT Mode (without file)..."
curl -s -X POST "$API_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Làm sao để build một Odoo module?",
    "mode": "agent"
  }' | python3 -m json.tool
echo ""
echo ""

# Test 4: Plan Mode
echo "4️⃣ Testing PLAN Mode..."
curl -s -X POST "$API_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Design a scalable Odoo implementation",
    "mode": "plan"
  }' | python3 -m json.tool
echo ""
echo ""

# Test 5: Agent Mode with JavaScript file
echo "5️⃣ Testing AGENT Mode (JavaScript file)..."
curl -s -X POST "$API_URL/api/chat" \
  -F "message=Phân tích và optimize code JavaScript này" \
  -F "mode=agent" \
  -F "file=@$TEST_SAMPLES_DIR/hello.js" | python3 -m json.tool
echo ""
echo ""

echo "✅ All tests completed!"
