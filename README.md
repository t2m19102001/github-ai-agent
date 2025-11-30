# 🤖 GitHub AI Agent v2.0

**Production-ready AI Agent with multi-provider LLM support, RAG, long-term memory, and Git automation.**

![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## 🚀 Quick Start (3 Steps)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Choose LLM Provider
```bash
# Option A: Groq (Recommended - Fast & Free)
export LLM_PROVIDER=groq
export GROQ_API_KEY=gsk_your_key_here

# Option B: Ollama (Local)
export LLM_PROVIDER=ollama

# Option C: OpenAI (Most Powerful)
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk_your_key_here
```

### 3. Run Server
```bash
uvicorn src.web.app:app --reload --port=5000
# Open http://127.0.0.1:5000
```

**📚 Docs:** [`QUICK_START.md`](QUICK_START.md) | [`MULTI_PROVIDER_SETUP.md`](MULTI_PROVIDER_SETUP.md) | [`FIX_SUMMARY.md`](FIX_SUMMARY.md)

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
