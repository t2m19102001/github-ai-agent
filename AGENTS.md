# AGENTS.md

Entry point cho **AI coding agents** (Claude Code, Cursor, Copilot, Aider, ...) và dev mới đụng repo. Đọc file này trước khi làm bất kỳ thay đổi nào.

---

## Repo này là gì

Một repository **2 sản phẩm song song**, không phải 1 monolith:

| | Surface | Run mode | Code path | Docs |
|---|---|---|---|---|
| 🖥️ | Local AI Agent (CLI) | local-only, Ollama, read-only | [src/local_agent/](src/local_agent/) | [docs/local_agent/](docs/local_agent/) |
| 🌐 | GitHub AI Agent (Web) | FastAPI + GitHub Actions | [src/agents/](src/agents/), [src/web/](src/web/), [src/github/](src/github/) | [docs/web_agent/](docs/web_agent/) |

Hai surface chia sẻ một số infrastructure (`src/llm/`, `src/rag/`, `src/utils/`) nhưng module logic **độc lập**. Đừng giả định 1 thay đổi ở local_agent là an toàn cho web_agent (và ngược lại) — chạy test riêng cho từng path.

---

## Khi sửa code: hỏi cái này trước

1. **Sửa cho surface nào?** Local CLI hay Web/GitHub Actions? Nếu không chắc → hỏi user, đừng đoán.
2. **Có test ở đâu?**
   - Local: [tests/local_agent/](tests/local_agent/) + [src/local_agent/tests/](src/local_agent/tests/) (legacy)
   - Web: `tests/test_*` ở root tests dir
3. **Có vi phạm boundary?** Local agent **read-only, suggest-only**. Không được tự sửa file repo, không gọi API ngoài, không web request.

---

## Local AI Agent — module status (V1 stable, V2 stubs)

| Module | LOC | Status |
|---|---|---|
| [ingestion/](src/local_agent/ingestion/) | ~1.5K | ✅ V1 done — crawler, parser, symbols, chunker, embedder |
| [indexing/](src/local_agent/indexing/) | ~270 | ✅ V1 done — IndexBuilder + FAISS + JSON metadata |
| [retrieval/](src/local_agent/retrieval/) | ~320 | ✅ V1 done — BasicRetriever + ContextBuilder; hybrid + RRF ở backlog |
| [core.py](src/local_agent/core.py) | 221 | ✅ V1 done — LocalAgent.query(), AgentResponse, citations |
| [cli.py](src/local_agent/cli.py) | 403 | ✅ V1 done — `index` + `query` subcommands |
| [explainer/](src/local_agent/explainer/) | ~130 | ✅ citation + formatter wired; confidence scoring ở backlog |
| [memory/](src/local_agent/memory/) | ~100 | 🟡 partial — `session.py` 68 LOC, không persist. Defer Memory milestone |
| [planner/](src/local_agent/planner/) | ~200 | ✅ deterministic planner + guarded SWE handoff |
| [guardrails/](src/local_agent/guardrails/) | ~250 | 🟢 file guardrails wired vào planning handoff |
| [integration/](src/local_agent/integration/) | ~300 | 🟢 grounded `PlanRequestBuilder` cho SWE handoff |

Full kiến trúc: [docs/local_agent/ARCHITECTURE.md](docs/local_agent/ARCHITECTURE.md).

---

## Quick start (cho agent đụng code lần đầu)

```bash
# 1. venv + deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Test toàn bộ local_agent (hermetic, no Ollama)
pytest tests/local_agent/ src/local_agent/tests/ -q
# Verified baseline: 254 passed, 6 environment-dependent tests skipped

# 3. CI lint check (strict — phải pass trước khi commit)
flake8 src/ tests/ --select=E9,F63,F7,F82
# Expected: 0 issues

# 4. Smoke E2E (no Ollama)
pytest tests/local_agent/test_e2e_smoke.py -v

# 5. Full smoke với Ollama thật (manual)
bash scripts/smoke_local_agent.sh
```

---

## Hard rules (không được vi phạm)

### Local AI Agent surface
- ❌ Không gọi API ngoài (Ollama là local).
- ❌ Không sửa file repo trong runtime — chỉ retrieve + suggest.
- ❌ Không thêm dependency nặng vào ingestion/indexing path (giữ FAISS-cpu + sentence-transformers, đủ rồi).
- ❌ Không reorder retrieval results ngoài việc dedupe — preserve rank.
- ❌ Không invent file/function names trong LLM answer (system prompt đã ép).
- ✅ Mọi tầng phải deterministic (same input → same output, except wall-clock fields).
- ✅ Lazy-load nặng (sentence-transformers, faiss) — không import top-level.

### Web AI Agent surface
- ❌ Không trộn dependencies vào local_agent (FastAPI, Tesseract, OCR là local-CLI cấm).
- ✅ Pydantic models cho mọi API contract.
- ✅ Tests cho từng agent.

### Cả 2
- ✅ Test phải pass trước khi commit (`pytest tests/` + `flake8 ... --select=E9,F63,F7,F82`).
- ✅ Không skip pre-commit hooks (`--no-verify`).
- ❌ Không hardcode credentials.

---

## Khi merge code: phải làm gì

1. Run lint:
   ```bash
   flake8 src/ tests/ --exclude=tests/verify_changes.py --count --select=E9,F63,F7,F82
   ```
2. Run regression cho surface đã đụng:
   ```bash
   pytest tests/local_agent/ src/local_agent/tests/ -q   # local
   pytest tests/                                          # everything
   ```
3. Update doc nếu đã đổi public API:
   - Local CLI flags → [docs/local_agent/CLI.md](docs/local_agent/CLI.md)
   - Indexing pipeline → [docs/local_agent/INDEXING.md](docs/local_agent/INDEXING.md)
   - Architecture → [docs/local_agent/ARCHITECTURE.md](docs/local_agent/ARCHITECTURE.md)
4. Update [README.md](README.md) chỉ khi đổi quick-start commands hoặc thêm surface mới.

---

## Backlog đáng làm tiếp (priority order)

1. **Eval framework**: bộ câu hỏi vàng + answer quality measurement cho retrieval.
2. **Hybrid retrieval**: BM25 + dense fusion (P1).
3. **Confidence scoring** cho câu trả lời có citation.
4. **Read-only tools wiring** cho local surface.
5. **Web eval**: thêm golden sets cho issue analysis, PR review và OCR trước khi công bố metric.

---

## Tài liệu nên đọc theo thứ tự

1. **README.md** (root) — overview 2 surfaces
2. **docs/local_agent/ARCHITECTURE.md** — pipeline V1 module-by-module
3. **docs/local_agent/CLI.md** — usage CLI
4. **docs/local_agent/INDEXING.md** — indexing pipeline detail
5. **docs/web_agent/README.md** — Web/GitHub Actions surface (nếu cần)

---

## Khi không chắc

Đừng đoán. Hỏi user (qua tool nếu là agent có khả năng). Đặc biệt khi:
- Đụng cross-surface code (local ↔ web).
- Đổi public API hoặc dataclass shape.
- Thêm dependency mới.
- Refactor lớn ảnh hưởng > 3 file.
- Sửa CI workflow hoặc test contracts.
