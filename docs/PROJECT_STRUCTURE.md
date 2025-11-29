# 📁 Project Structure - New Organization

```
github-ai-agent/
├── README.md                          # Main entry point
├── requirements.txt                   # Dependencies
├── .env                              # Config (local)
├── .env.example                      # Config template
├── .gitignore                        # Git ignore rules
│
├── src/                              # ✨ NEW - Source code
│   ├── __init__.py
│   ├── config.py                     # Configuration management
│   │
│   ├── core/                         # Core AI functionality
│   │   ├── __init__.py
│   │   ├── llm.py                    # LLM interface (GROQ, HF)
│   │   ├── agent.py                  # AI Agent base class
│   │   └── tools.py                  # Tool definitions
│   │
│   ├── agents/                       # Specific agents
│   │   ├── __init__.py
│   │   ├── github_agent.py           # GitHub issue analyzer
│   │   └── code_agent.py             # Code chat & analysis
│   │
│   ├── tools/                        # Tool implementations
│   │   ├── __init__.py
│   │   ├── file_tools.py             # File operations
│   │   ├── code_tools.py             # Code execution & analysis
│   │   ├── git_tools.py              # Git operations
│   │   ├── test_tools.py             # Test running
│   │   └── shell_tools.py            # Shell commands
│   │
│   └── utils/                        # Utilities
│       ├── __init__.py
│       ├── logging.py                # Logging setup
│       ├── validation.py             # Input validation
│       └── formatting.py             # Output formatting
│
├── web/                              # ✨ NEW - Web interface
│   ├── app.py                        # Flask app
│   ├── routes.py                     # API routes
│   ├── templates/
│   │   └── chat.html                 # Chat UI
│   └── static/
│       ├── css/
│       │   └── style.css             # Styles
│       └── js/
│           └── chat.js               # Chat logic
│
├── cli/                              # ✨ NEW - CLI interface
│   ├── __init__.py
│   └── main.py                       # Terminal chat
│
├── tests/                            # ✨ NEW - Test suite
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_tools.py
│   └── test_llm.py
│
├── docs/                             # Documentation
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── API.md                        # ✨ NEW - API docs
│   ├── TOOLS.md                      # ✨ NEW - Tools reference
│   └── DEPLOYMENT.md
│
├── scripts/                          # ✨ NEW - Helper scripts
│   ├── setup.sh                      # Setup script
│   ├── run_web.sh                    # Run web server
│   ├── run_cli.sh                    # Run CLI
│   └── deploy.sh                     # Deployment
│
└── .github/
    └── workflows/
        └── ai-agent.yml              # GitHub Actions
```

## 📊 Benefits

✅ **Modular**: Mỗi component độc lập, dễ test  
✅ **Scalable**: Dễ thêm agents/tools mới  
✅ **Maintainable**: Code organization rõ ràng  
✅ **Testable**: Dedicated test folder  
✅ **Professional**: Enterprise-grade structure  

