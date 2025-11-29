# 🤖 GitHub AI Agent v2.0

**Production-ready AI Agent for GitHub with modular architecture, code execution, and Git integration.**

![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## 🚀 Quick Start (2 minutes)

```bash
# 1. Setup
cp .env.example .env
# Edit .env with your API keys

# 2. Run Web UI
python run_web.py
# Open http://localhost:5000

# 3. Or CLI
python main.py
```

## 📁 Clean Structure

```
src/                    # All production code
├── config.py          # Configuration
├── agents/            # AI agents
├── llm/               # LLM providers
├── tools/             # Tools & executors
├── utils/             # Utilities
├── web/               # Web interface
└── legacy/            # Old code (reference)

tests/                 # Unit tests
docs/                  # Documentation
main.py                # CLI entry point
run_web.py             # Web UI entry point
```

## ✨ Features

✅ **AI Code Assistant** - Chat, analyze, suggest  
✅ **Code Execution** - Safe, sandboxed Python execution  
✅ **File Operations** - Read, write, manage files  
✅ **Git Integration** - Commit, push, status  
✅ **Web UI** - Modern interactive interface  
✅ **CLI** - Terminal interface  
✅ **REST API** - Integration endpoints  
✅ **Professional Architecture** - Modular, extensible  

## 🌐 Use It

### Web UI
```bash
python run_web.py
# → http://localhost:5000
```

### CLI
```bash
python main.py
```

### Python Library
```python
from src.agents.code_agent import CodeChatAgent
from src.llm.groq import GroqProvider

llm = GroqProvider()
agent = CodeChatAgent(llm_provider=llm)
response = agent.chat("Explain my code")
```

## 📚 Documentation

All documentation in `docs/` folder:
- [NEW_README.md](docs/NEW_README.md) - Complete guide
- [PROJECT_STATUS.md](docs/PROJECT_STATUS.md) - Overview
- [RESTRUCTURE_SUMMARY.md](docs/RESTRUCTURE_SUMMARY.md) - Architecture
- [QUICK_START.py](docs/QUICK_START.py) - Quick reference

## 🔧 Configuration

Required:
```dotenv
GITHUB_TOKEN=your_github_token
REPO_FULL_NAME=username/repo
GROQ_API_KEY=your_groq_key
```

Optional:
```dotenv
DEBUG=false
CHAT_PORT=5000
ENABLE_CODE_EXECUTION=true
```

See `.env.example` for all options.

## 🧪 Testing

```bash
pytest tests/                    # All tests
pytest tests/test_basic.py -v   # Specific test
pytest --cov=src tests/         # With coverage
```

## 📦 Installation

```bash
pip install -r requirements.txt
```

## 🔒 Security

- ✅ Sandboxed code execution
- ✅ File operation restrictions  
- ✅ Input validation
- ✅ Timeout protection
- ✅ Configuration validation

## 🎯 Next Phase

**Phase 2: GitHub Agent**
- Auto-analyze issues
- Auto-commenting
- Issue categorization

## 🛠️ Development

### Create Custom Agent
```python
from src.agents.base import Agent

class MyAgent(Agent):
    def think(self, prompt: str) -> str:
        # Your logic
        pass
    
    def act(self, action: str) -> bool:
        # Your logic
        pass
```

### Add Custom Tool
```python
from src.agents.base import Tool

class MyTool(Tool):
    def execute(self, *args, **kwargs):
        # Your logic
        pass
```

## 📄 License

MIT License - See LICENSE file

## 📞 Support

- 📖 [Documentation](docs/)
- 🐛 [Report Issues](https://github.com/t2m19102001/github-ai-agent/issues)
- 💡 [Discussions](https://github.com/t2m19102001/github-ai-agent/discussions)

---

**Status:** ✅ Ready for production | 🚀 Ready for Phase 2 development

Made with ❤️ for developers
