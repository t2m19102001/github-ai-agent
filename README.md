# 🤖 GitHub AI Agent

[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)

> Repo này ship **2 surface AI agent** chia theo run mode: **local CLI** cho dev cá nhân, **web/API** cho team workflow.

| | Surface | Run mode | Mục đích chính | Docs |
|---|---|---|---|---|
| 🖥️ | **Local AI Agent (CLI)** | 100% local, Ollama, read-only | Hỏi-đáp về codebase ngay từ terminal, có citations | [docs/local_agent/](docs/local_agent/) |
| 🌐 | **GitHub AI Agent (Web)** | FastAPI + Slack + CI/CD | Multi-agent issue / image / PR review qua Web/Slack | [docs/web_agent/README.md](docs/web_agent/README.md) |

→ Mới đến repo? Hầu hết dev cần **Local AI Agent (CLI)** trước. Đọc tiếp phần dưới. Đang tìm Web/Slack/CI? Sang [docs/web_agent/README.md](docs/web_agent/README.md).

→ Là AI coding agent? Đọc [AGENTS.md](AGENTS.md) cho boundaries + module status.

---

## 🖥️ Local AI Agent (CLI)

Read-only, suggest-only AI agent chạy 100% local. Pipeline:

`câu hỏi → retrieval (FAISS) → context builder → local LLM (Ollama) → answer (with citations)`

### Quick start

```bash
# 1. Cài deps + kích hoạt venv
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Pull model + chạy Ollama
ollama pull llama3:8b
ollama serve

# 3. Build index cho repo này (1 lần / lần code đổi)
python -m src.local_agent.cli index .

# 4. Hỏi
python -m src.local_agent.cli query "What does LocalAgent.query do?"
python -m src.local_agent.cli query --json "Where is the scheduler?"
```

### Docs

- [docs/local_agent/CLI.md](docs/local_agent/CLI.md) — usage, flags, troubleshooting
- [docs/local_agent/INDEXING.md](docs/local_agent/INDEXING.md) — indexing pipeline chi tiết
- [docs/local_agent/ARCHITECTURE.md](docs/local_agent/ARCHITECTURE.md) — kiến trúc V1 module-by-module

### Status

- **V1 (P0-01 → P0-10) hoàn thành**: ingestion → indexing → retrieval → context → LLM → CLI + citations.
- **Test suite**: `pytest tests/local_agent/` — green except one known pre-existing
  parser failure (`test_method_decorators_captured`). The hermetic E2E smoke test
  (`test_e2e_smoke.py`) is skipped unless `faiss-cpu` is installed.
- **Code path**: [src/local_agent/](src/local_agent/) (~3.5K LOC, độc lập với FastAPI surface).

---

## 🌐 GitHub AI Agent (Web / Slack / CI)

Multi-agent system với FastAPI backend, Slack bot, GitHub Actions integration, Docker deployment, OCR / diagram analysis.

→ Toàn bộ docs gồm Features, API endpoints, Configuration, Deployment, Use cases: **[docs/web_agent/README.md](docs/web_agent/README.md)**.

Quick smoke:
```bash
# FastAPI dev server
uvicorn src.web.main:app --host 0.0.0.0 --port 8000 --reload

# Hoặc Docker
docker-compose -f docker-compose.dev.yml up --build
```

---

## 🤝 Contributing

```bash
# Fork + branch
git clone https://github.com/your-username/github-ai-agent.git
cd github-ai-agent && git checkout -b feature/your-feature

# Dev deps
pip install -r requirements.txt && pip install -e .

# Run tests
pytest tests/local_agent/    # local agent
pytest tests/                # everything

# Lint (CI uses E9,F63,F7,F82 strict)
flake8 src/ tests/ --select=E9,F63,F7,F82
```

PRs welcome. Tests + lint phải xanh trước khi review.

## 📄 License

MIT — see [LICENSE](LICENSE).

## 🙏 Acknowledgments

- [Ollama](https://ollama.com) — local LLM runtime
- [sentence-transformers](https://www.sbert.net) — embedding models
- [FAISS](https://github.com/facebookresearch/faiss) — vector similarity search
- [FastAPI](https://fastapi.tiangolo.com) — web framework (web surface)
- [Tesseract](https://github.com/tesseract-ocr/tesseract) — OCR (web surface)

## 📞 Support

- Issues: [GitHub Issues](https://github.com/minhman20/github-ai-agent/issues)
- Discussions: [GitHub Discussions](https://github.com/minhman20/github-ai-agent/discussions)
