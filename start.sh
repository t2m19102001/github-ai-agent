#!/bin/bash

# GitHub Copilot Alternative - Quick Start Script
# This script activates the virtual environment and starts the web server

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "🚀 GitHub Copilot Alternative - Starting..."
echo ""

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Virtual environment not found at $VENV_DIR"
    echo "Please create it with: python3 -m venv .venv"
    exit 1
fi

# Check Python in venv
if [ ! -f "$VENV_DIR/bin/python" ]; then
    echo "❌ Python not found in virtual environment"
    exit 1
fi

echo "✅ Virtual environment found"
echo "✅ Python version: $($VENV_DIR/bin/python --version)"
echo ""

# Kill any existing process on port 5000
echo "🔍 Checking port 5000..."
if lsof -i :5000 >/dev/null 2>&1; then
    echo "⚠️  Port 5000 is in use. Killing existing process..."
    lsof -i :5000 | grep -v COMMAND | awk '{print $2}' | xargs kill -9 2>/dev/null
    sleep 1
    echo "✅ Port cleared"
fi

echo ""
echo "📂 Project directory: $PROJECT_DIR"
echo "🌐 Starting web server on http://localhost:5000"
echo "📊 Dashboard: http://localhost:5000/dashboard"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""

# Start the server
cd "$PROJECT_DIR"
exec "$VENV_DIR/bin/python" run_web.py
