# GitHub AI Agent

[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)

Repo này ship **hai surface AI agent** chia theo run mode: một **local CLI** cho dev cá nhân và một **web/API** cho team workflow. Hai surface độc lập về code path.

| Surface | Run mode | Mục đích chính | Docs |
|---|---|---|---|
| **Local AI Agent (CLI)** | 100% local, Ollama, read-only | Hỏi-đáp về codebase ngay từ terminal, kèm citations | [docs/local_agent/](docs/local_agent/) |
| **GitHub AI Agent (Web)** | FastAPI + GitHub Actions | Chat, issue/image analysis, PR automation | [docs/web_agent/README.md](docs/web_agent/README.md) |

Mới đến repo? Hầu hết dev cần **Local AI Agent (CLI)** trước — đọc tiếp phần dưới. Đang tìm Web/GitHub Actions? Sang [docs/web_agent/README.md](docs/web_agent/README.md). Là AI coding agent? Đọc [AGENTS.md](AGENTS.md) cho boundaries và module status.

---

## Local AI Agent (CLI)

Read-only, suggest-only agent chạy hoàn toàn local. Pipeline:

```
câu hỏi -> retrieval (FAISS) -> context builder -> local LLM (Ollama) -> answer (with citations)
```

### Quick start

```bash
# 1. Tạo venv + cài deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Pull model + chạy Ollama
ollama pull llama3.2:3b
ollama serve

# 3. Build index cho repo (chạy lại mỗi khi code đổi nhiều)
python -m src.local_agent.cli index .

# 4. Hỏi
python -m src.local_agent.cli query "What does LocalAgent.query do?"
python -m src.local_agent.cli query --json "Where is the scheduler?"
```

Model mặc định lấy từ `configs/localagent.yaml` (`llama3.2:3b`), rồi có thể override bằng `LOCAL_AGENT_MODEL` hoặc `--model`.

### Docs

- [docs/local_agent/CLI.md](docs/local_agent/CLI.md) — usage, flags, troubleshooting
- [docs/local_agent/INDEXING.md](docs/local_agent/INDEXING.md) — chi tiết indexing pipeline
- [docs/local_agent/ARCHITECTURE.md](docs/local_agent/ARCHITECTURE.md) — kiến trúc module-by-module

### Status

- **V1 hoàn thành**: ingestion → indexing → retrieval → context → LLM → CLI, kèm citations + Markdown report.
- **Test suite**: 254 passed, 6 skipped trên Python 3.10 (xác minh tháng 7/2026).
- **Code path**: [src/local_agent/](src/local_agent/) — độc lập với web surface.
- **Roadmap còn lại**: confidence scorer, read-only tools và hybrid retrieval — xem [GitHub Issues](https://github.com/t2m19102001/github-ai-agent/issues) (label `local-agent`).

---

## GitHub AI Agent (Web / GitHub Actions)

FastAPI backend, GitHub Actions integration, Docker deployment, và phân tích OCR / diagram. Slack chưa nằm trong source canonical.

Toàn bộ docs (Features, API endpoints, Configuration, Deployment, Use cases): **[docs/web_agent/README.md](docs/web_agent/README.md)**.

LLM layer (`src/llm/`) gồm `OllamaProvider`, `GroqProvider`, `FailoverProvider`; mặc định dùng `mock` cho test/CI không cần network.

Quick smoke:

Chạy ổn định trên localhost với defaults an toàn (mock LLM, SQLite — **không cần Postgres/Redis**):

```bash
# 1. (tuỳ chọn) tạo .env localhost từ template
cp .env.example .env   # mock LLM + SQLite; thay secrets trước production

# 2. Boot web surface bằng 1 lệnh (có pre-flight check venv + port)
bash scripts/run_web.sh                       # http://127.0.0.1:8000
HOST=0.0.0.0 PORT=9000 bash scripts/run_web.sh

# Kiểm tra: http://127.0.0.1:8000/health · API docs: /docs
```

Hoặc chạy uvicorn / Docker trực tiếp:

```bash
uvicorn src.web.main:app --host 127.0.0.1 --port 8000 --reload
docker-compose -f docker-compose.dev.yml up --build
```

### Web UI

| Route | Mô tả |
|---|---|
| `/` | **Chat** kiểu Claude Code — streaming qua WebSocket (`/ws/chat`), model selector, mặc định mock (offline) |
| `/issue` | Form phân tích GitHub issue (trang chủ cũ) |
| `/dashboard` · `/logs-page` · `/image-page` | Dashboard, logs, phân tích ảnh |
| `/docs` · `/health` · `/api/models` | API docs (Swagger) · health check · danh sách provider |

**LLM provider cho chat** (`LLM_PROVIDER` trong `.env`, hoặc chọn ở model selector):

| Provider | Cần gì | Ghi chú |
|---|---|---|
| `mock` | không | Mặc định an toàn, offline, trả lời giả lập (để demo UI) |
| `groq` | `GROQ_API_KEY` (free tại [console.groq.com](https://console.groq.com)) | **Câu trả lời AI thật**, nhanh, model `llama-3.3-70b-versatile` |
| `ollama` | `ollama serve` + model đã pull | AI thật, 100% local |
| `failover` | (ưu tiên ollama → groq → mock) | Tự fallback khi provider lỗi |

Để chat trả lời thật: đặt `LLM_PROVIDER=groq` + dán `GROQ_API_KEY=gsk_...` vào `.env`, rồi khởi động lại server.

---

## Contributing

```bash
# Fork + branch
git clone https://github.com/t2m19102001/github-ai-agent.git
cd github-ai-agent && git checkout -b feature/your-feature

# Dev deps
pip install -r requirements.txt && pip install -e .

# Run tests
pytest tests/local_agent/    # local agent
pytest tests/                # everything

# Lint (CI strict set)
flake8 src/ tests/ --select=E9,F63,F7,F82
```

PRs welcome. Tests và lint phải xanh trước khi review. Roadmap mở nằm ở [GitHub Issues](https://github.com/t2m19102001/github-ai-agent/issues) (label `roadmap`).

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- [Ollama](https://ollama.com) — local LLM runtime
- [sentence-transformers](https://www.sbert.net) — embedding models
- [FAISS](https://github.com/facebookresearch/faiss) — vector similarity search
- [FastAPI](https://fastapi.tiangolo.com) — web framework (web surface)
- [Tesseract](https://github.com/tesseract-ocr/tesseract) — OCR (web surface)

## Support

- Issues: [GitHub Issues](https://github.com/t2m19102001/github-ai-agent/issues)
- Discussions: [GitHub Discussions](https://github.com/t2m19102001/github-ai-agent/discussions)
