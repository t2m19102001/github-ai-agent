#!/usr/bin/env python3
"""
Quick Reference for GitHub AI Agent v2.0
"""

QUICK_START = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🤖 GitHub AI Agent v2.0 - Quick Start                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

1️⃣  SETUP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  cp .env.example .env
  # Edit .env with your API keys
  pip install -r requirements.txt

2️⃣  RUN WEB UI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  python run_web.py
  # Open http://localhost:5000

3️⃣  RUN CLI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  python main.py

4️⃣  USE AS LIBRARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  from src.agents.code_agent import CodeChatAgent
  from src.llm.groq import GroqProvider
  
  llm = GroqProvider()
  agent = CodeChatAgent(llm_provider=llm)
  response = agent.chat("Your question")

5️⃣  RUN TESTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  pytest tests/
  pytest tests/test_basic.py -v
  pytest --cov=src tests/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 PROJECT STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  src/
  ├── __init__.py
  ├── config.py                 # Configuration management
  ├── agents/
  │   ├── base.py              # Base classes
  │   └── code_agent.py        # Code Chat Agent
  ├── llm/
  │   └── groq.py              # GROQ provider
  ├── tools/
  │   ├── executors.py         # Python/Shell execution
  │   └── tools.py             # File/Git tools
  ├── utils/
  │   ├── logger.py            # Logging
  │   └── text.py              # Text utilities
  └── web/
      └── app.py               # Flask web app

  tests/
  └── test_basic.py            # Unit tests

  main.py                       # CLI entry point
  run_web.py                    # Web UI entry point

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 KEY COMPONENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  • GroqProvider       - LLM integration
  • CodeChatAgent      - AI agent for code analysis
  • PythonExecutor     - Execute Python code safely
  • FileReadTool       - Read files from project
  • FileWriteTool      - Create/modify files
  • GitTool            - Git operations

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 API ENDPOINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  GET  /                       - Web UI
  POST /api/chat               - Send message to AI
  GET  /api/files              - List project files
  POST /api/read               - Read file content
  GET  /api/history            - Conversation history
  POST /api/clear-history      - Clear history
  GET  /api/status             - Application status

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 DOCUMENTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  • NEW_README.md              - Complete user guide
  • PROJECT_STATUS.md          - Project overview
  • RESTRUCTURE_SUMMARY.md     - Architecture details
  • docs/ARCHITECTURE.md       - Technical architecture
  • CODE_CHAT_GUIDE.md         - Chat interface guide

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 CONFIGURATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Required (.env):
  ✓ GITHUB_TOKEN                 # GitHub API token
  ✓ REPO_FULL_NAME              # username/repository
  ✓ GROQ_API_KEY                # GROQ API key

  Optional:
  - HUGGINGFACE_TOKEN           # Fallback LLM
  - DEBUG                        # true/false
  - CHAT_PORT                    # Web server port
  - ENABLE_CODE_EXECUTION       # true/false
  - ENABLE_GIT_OPERATIONS       # true/false

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ FEATURES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✅ Code analysis and chat
  ✅ Python code execution (sandboxed)
  ✅ File reading and modification
  ✅ Git operations (commit, push, status)
  ✅ Web UI interface
  ✅ CLI interface
  ✅ REST API
  ✅ Comprehensive logging
  ✅ Error handling and recovery
  ✅ Input validation and security

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 Ready to develop! Start with: python run_web.py
"""

if __name__ == "__main__":
    print(QUICK_START)
