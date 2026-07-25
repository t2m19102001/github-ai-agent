# Local Agent — Architecture

V1 spec, module-by-module. Đối tượng đọc: dev mới đụng `src/local_agent/` lần đầu.

---

## 1. Big picture

```
┌──────────────┐
│  Repository  │   (Python files on disk)
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│  Ingestion — src/local_agent/ingestion/    │
│   crawler → parser → symbols → chunker     │
│                                  → embedder │
└──────┬──────────────────────────────────────┘
       │ list[EmbeddedChunk]
       ▼
┌─────────────────────────────────────────────┐
│  Indexing — src/local_agent/indexing/      │
│   IndexBuilder.build → code.index +        │
│                         metadata.json       │
└──────┬──────────────────────────────────────┘
       │ FAISS IndexFlatL2 + sidecar
       ▼
┌─────────────────────────────────────────────┐
│  Retrieval — src/local_agent/retrieval/    │
│   BasicRetriever.retrieve → list[hit]      │
│   ContextBuilder.build → ContextWindow     │
└──────┬──────────────────────────────────────┘
       │ ContextWindow
       ▼
┌─────────────────────────────────────────────┐
│  Core — src/local_agent/core.py            │
│   LocalAgent.query → AgentResponse         │
│   (system prompt + LLM call + fallback)    │
└──────┬──────────────────────────────────────┘
       │ AgentResponse
       ▼
┌─────────────────────────────────────────────┐
│  CLI — src/local_agent/cli.py              │
│   `index` + `query` subcommands            │
└─────────────────────────────────────────────┘
```

Determinism được enforce ở mọi tầng (sort-stable). Cùng repo + cùng model → byte-identical index.

---

## 2. Layer-by-layer

### 2.1 Ingestion ([src/local_agent/ingestion/](../../src/local_agent/ingestion/))

| Module | Vai trò | Output type |
|---|---|---|
| [crawler.py](../../src/local_agent/ingestion/crawler.py) | Walk repo, respect `.gitignore`, filter Python files | `dict` (files + stats) |
| [parser.py](../../src/local_agent/ingestion/parser.py) | Python AST → ParsedFile + per-node docstrings | `ParsedFile` |
| [symbols.py](../../src/local_agent/ingestion/symbols.py) | ParsedFile → SymbolTable (classes/functions/imports) | `SymbolTable` |
| [chunker.py](../../src/local_agent/ingestion/chunker.py) | Hierarchical chunks: 4 levels (file/class/function/method) | `list[CodeChunk]` |
| [embedder.py](../../src/local_agent/ingestion/embedder.py) | sentence-transformers wrapper, lazy load | `list[EmbeddedChunk]` |

**Key contract** (P0-04): mỗi `CodeChunk` có `id` (deterministic hash), `level`, `content` (formatted text dùng cho embedding), line span, docstring, parent_name. Docstring được preserve qua mọi tầng (regression test khoá).

### 2.2 Indexing ([src/local_agent/indexing/](../../src/local_agent/indexing/))

| Module | Vai trò | Output |
|---|---|---|
| [index_builder.py](../../src/local_agent/indexing/index_builder.py) | Build FAISS `IndexFlatL2` + JSON metadata | `code.index` + `metadata.json` |
| [embedder.py](../../src/local_agent/indexing/embedder.py) | **Compat re-export** từ `ingestion.embedder` (zero logic) | — |

**Key contract** (P0-06): `metadata["chunks"][N]` ⇔ FAISS row `N`. Sort theo `chunk_id` ascending. Atomic write via `os.replace()`. Xem [INDEXING.md](INDEXING.md).

### 2.3 Retrieval ([src/local_agent/retrieval/](../../src/local_agent/retrieval/))

| Module | Vai trò | Output |
|---|---|---|
| [retriever.py](../../src/local_agent/retrieval/retriever.py) | Embed query + FAISS search + map IDs → metadata | `list[RetrievalResult]` |
| [context_builder.py](../../src/local_agent/retrieval/context_builder.py) | Dedupe + budget enforce + format | `ContextWindow` |

**Key contracts**:
- (P0-07) `BasicRetriever` raise `ValueError` khi model_name của index ≠ model_name của retriever (silent failure prevention).
- (P0-08) `ContextBuilder` luôn include first chunk dù vượt budget (tránh empty context). Heuristic token = `len(text)//4`.

### 2.4 Core ([src/local_agent/core.py](../../src/local_agent/core.py))

`LocalAgent.query(question)` = orchestration thuần. Pipeline:

1. Validate question (`ValueError` nếu rỗng/whitespace)
2. `retriever.retrieve()` → if empty → safe fallback "I do not have enough information"
3. `context_builder.build()` → `ContextWindow`
4. `llm_client.generate(system, user)` trong try/except → if fail → safe fallback + warning
5. Return `AgentResponse` với heuristic confidence

**Dependency injection**: `LLMClientProtocol` (structural typing) cho phép inject fake LLM trong tests, real `_OllamaAdapter` trong CLI production.

### 2.5 CLI ([src/local_agent/cli.py](../../src/local_agent/cli.py))

2 subcommand:

| Subcommand | Flow |
|---|---|
| `index <repo>` | Crawl + parse + chunk + embed + IndexBuilder.build |
| `query "?"` | Build LocalAgent (real adapter) + `query()` + format human/JSON |

Production wiring qua `_build_default_agent()` (lazy imports). Tests dùng `agent_factory` injection để hermetic.

---

## 3. Data shapes (V1)

### `EmbeddedChunk` ([ingestion/embedder.py](../../src/local_agent/ingestion/embedder.py))
```python
chunk_id: str       # = chunk.id, propagated explicitly
embedding: list[float]
model_name: str
embedding_dim: int
chunk: CodeChunk    # full reference for downstream
```

### `IndexMetadata` ([indexing/index_builder.py](../../src/local_agent/indexing/index_builder.py))
13 fields per chunk: `chunk_id, file_path, relative_path, name, qualified_name, level, start_line, end_line, docstring, symbols, parent_name, content, model_name`. **Lưu ý**: không lưu `imports` và `token_count` thật — gap đã document, defer P1.

### `RetrievalResult` ([retrieval/retriever.py](../../src/local_agent/retrieval/retriever.py))
15 fields = IndexMetadata 13 + `score: float` + `rank: int` + `source: RetrievalSource`. Score là raw L2 distance (lower = better).

### `ContextWindow` ([retrieval/context_builder.py](../../src/local_agent/retrieval/context_builder.py))
```python
query: str
chunks: list[RetrievalResult]   # post-dedupe, post-budget
formatted_context: str           # ready for prompt injection
total_tokens: int
metadata: ContextMetadata        # 7 fields
```

### `AgentResponse` ([core.py](../../src/local_agent/core.py))
10 fields: `question, answer, retrieved_chunks (ids), total_retrieved, total_context_tokens, confidence, model_name, latency_ms, timestamp, warnings`.

---

## 4. Determinism guarantees

| Layer | Sort key |
|---|---|
| Crawler | `relative_path` ASC |
| Parser batch | posix path |
| Symbol batch | `(relative_path, file_path)` |
| Chunker | `(line_start, line_end, name)` |
| IndexBuilder | `chunk_id` ASC |

→ Cùng repo + cùng model = same `code.index` byte-for-byte. Verified bằng integration tests.

---

## 5. Module status

| Module | LOC | Status |
|---|---|---|
| ingestion/ | ~1.5K | ✅ V1 done, tests xanh |
| indexing/ | ~270 | ✅ V1 done |
| retrieval/ | ~320 | ✅ V1 dense retrieval; hybrid + RRF ở backlog |
| core.py | 221 | ✅ V1 done |
| cli.py | 403 | ✅ V1 done (index + query) |
| explainer/ | ~200 | 🟢 citation + formatter wired vào core/cli, tests xanh; confidence scoring ở backlog |
| memory/ | ~100 | 🟡 partial — session.py, không persist |
| planner/ | ~200 | ✅ deterministic analyzer/sequencer/risk assessor + SWE handoff |
| guardrails/ | ~250 | 🟢 file guardrails wired vào planning handoff |
| integration/swe16_interface.py | ~300 | 🟢 `PlanRequestBuilder` tạo handoff grounded |

`LocalAgent.plan(goal)` tạo `PlanRequest` grounded từ retrieval, chạy file guardrails, luôn `auto_execute=False` và `require_approval=True`. Memory + read-only tools vẫn thuộc roadmap.

---

## 6. Testing

| Layer | Test file | Count |
|---|---|---|
| Ingestion | [tests/local_agent/test_ingestion/](../../tests/local_agent/test_ingestion/) | 50 |
| Indexing | [tests/local_agent/test_indexing/](../../tests/local_agent/test_indexing/) | 14 |
| Retrieval | [tests/local_agent/test_retrieval/](../../tests/local_agent/test_retrieval/) | 40 |
| Core | [tests/local_agent/test_core/](../../tests/local_agent/test_core/) | 22 |
| CLI | [tests/local_agent/test_cli/](../../tests/local_agent/test_cli/) | 27 |
| Other (legacy) | `src/local_agent/tests/` | 51 |

Xác minh Python 3.10 tháng 7/2026: **254 passed, 6 skipped**, bao gồm planner và guarded SWE handoff.

---

## 7. Configuration

| File | Status |
|---|---|
| [configs/localagent.yaml](../../configs/localagent.yaml) | ✅ runtime defaults được CLI đọc |

Environment variables vẫn có precedence cao hơn file config. Hai config reference-only cũ đã được bỏ để tránh mô tả hybrid search/tree-sitter không tồn tại.

Env var override: `LOCAL_AGENT_INDEX_PATH`, `LOCAL_AGENT_MODEL`, `LOCAL_AGENT_DEBUG=1`.

---

## 8. Non-goals (V1)

Liệt kê rõ để tránh scope creep:

- ❌ Multi-language (chỉ Python)
- ❌ Code modification (read-only)
- ❌ Web UI (CLI-only — Web surface là `src/web/`, sản phẩm khác)
- ❌ LLM API calls (Ollama local only)
- ❌ Streaming responses
- ❌ Multi-turn conversation state
- ❌ Hybrid retrieval (BM25 + dense → P1)
- ❌ Reranker
- ❌ Incremental index (full rebuild only)

V2/V3 ý tưởng được track ở từng module section "Status" bên trên.
