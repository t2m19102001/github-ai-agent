# Lộ trình phát triển — Local AI Agent

> Tài liệu này mô tả **con đường hoàn thiện** cho local agent: đã làm gì, đang ở
> đâu, và các bước tiếp theo. Cập nhật lần cuối sau khi hoàn thành tool-calling
> loop (commit `ea4333c`).

---

## 1. Bối cảnh & mục tiêu

**Mục tiêu của người xây (đã làm rõ):** HỌC kiến trúc AI Agent bằng cách xây một
trợ lý chạy **100% local** (offline, không API/key bên ngoài) trên chính máy dev.

**Phân biệt cốt lõi (chỗ 99% người nhầm):**
- **AI Model (LLM)** = "bộ não". KHÔNG train ở đây (tốn hàng trăm triệu USD). Ta
  *chạy* model open-weight có sẵn (Llama/Qwen) qua **Ollama**.
- **AI Agent** = phần mềm điều phối quanh model: RAG, tool-calling, memory,
  planning. **Đây là thứ ta xây và học.**

**Ràng buộc phần cứng:** máy dev là Intel i5 2 nhân, 16GB RAM, không GPU → chỉ
chạy được model nhỏ (0.5b–3b), chậm. Bài học đã kiểm chứng: `llama3.2:3b` đủ
thông minh để dùng tool; `qwen2.5:0.5b` thì bỏ qua tool và bịa. Kiến trúc không
đổi dù phần cứng nào — nâng cấp máy (Apple Silicon / GPU NVIDIA ≥12GB) chỉ làm
model to hơn chạy mượt hơn.

**Nguyên tắc phát triển:** mỗi bước là 1 slice nhỏ (≤5 files, ≤300 LOC, có test),
verify bằng `flake8 strict + mypy + pytest` và **chạy thật trên Ollama**.

---

## 2. Kiến trúc hiện tại

Repo có **2 surface độc lập** (code path tách biệt):

- **Local Agent** (`src/local_agent/`) — trọng tâm của lộ trình này. RAG Q&A +
  tool-calling, 100% offline qua Ollama.
- **Web Surface** (`src/web/`) — FastAPI + chat UI, nhiều provider (mock/groq/
  ollama/failover). Không phải trọng tâm học kiến trúc, nhưng đã chạy được.

### Hai luồng trong Local Agent

```
Luồng 1 — RAG một chiều (LocalAgent.query, core.py):
  câu hỏi → retriever (FAISS) → context_builder → LLM → answer + citations

Luồng 2 — Tool-calling loop (ToolCallingAgent, agent_loop.py):
  câu hỏi → LLM quyết định → {tool,args} → chạy tool → observation → lặp
          → {final} → answer   (cap max_iters đảm bảo dừng)
```

Hai luồng **độc lập**, chưa gộp. Luồng 1 trả lời từ code đã index; luồng 2 cho
LLM chủ động đọc thêm (read_file) khi context chưa đủ.

---

## 3. Trạng thái từng module (đã verify)

| Module | Trạng thái | Ghi chú |
|---|---|---|
| `ingestion/` | ✅ Xong | crawl → parse → symbols → chunk → embed (sentence-transformers) |
| `indexing/` | ✅ Xong | FAISS IndexFlatL2 + metadata sidecar |
| `retrieval/` | ✅ Xong | dense retrieval + context_builder + ranker |
| `explainer/` | ✅ Citation | citation + formatter hoạt động; confidence là heuristic đơn giản |
| `core.py` (RAG) | ✅ Xong | `LocalAgent.query` chạy end-to-end |
| `cli.py` | ✅ Xong | `index` / `query`; đã tách `--embed-model` vs `--model` + `--timeout` |
| `tools/` + `agent_loop.py` | ✅ MỚI | tool-calling loop + tool `read_file` (read-only, chặn traversal) |
| `memory/` | ✅ Persist | `storage.py` (SQLite) lưu turns; `agent` CLI có `--session` nhớ multi-turn |
| `guardrails/validators.py` | 🟡 Chưa wire | code thật nhưng **chưa gắn** vào core/loop |
| `planner/` + `integration/` | 🟡 Có wire | `LocalAgent.plan()` build PlanRequest (handoff SWE), chưa dùng thực tế |

Cấu hình tập trung: `configs/localagent.yaml` (model, timeout, embedding, paths).

---

## 4. Đã hoàn thành

- **Giai đoạn 0** — Chạy được & hiểu luồng RAG. Fix môi trường (numpy<2,
  sentence-transformers), build index, query end-to-end qua Ollama.
- **Fix bug CLI** — tách `--embed-model` (embedding) vs `--model` (LLM) + thêm
  `--timeout`; đọc default từ config. (commit `aee18b2`)
- **Web security** — `src/web/security.py` timing-safe, fail-closed. (commit `aee18b2`)
- **Giai đoạn 1 — Tool-calling** — `agent_loop.py` + `tools/` build mới, 14 test,
  chạy thật thành công với llama3.2:3b. (commit `ea4333c`)

---

## 5. Các bước tiếp theo (lộ trình còn lại)

### Bước A — Mở rộng tool (kế tiếp ngay)
Thêm tool read-only theo khuôn `file_reader.py`:
- `list_files` — liệt kê file trong 1 thư mục (repo-relative, an toàn).
- `git_reader` — `git log` / `git diff` cho 1 file (chỉ đọc).
- `code_query` — tìm định nghĩa/usages (tận dụng symbols đã có ở ingestion).

*Lý do:* nhiều tool hơn → agent giải được nhiều loại câu hỏi hơn. Đây là chỗ học
cách thiết kế tool interface nhất quán.

### Bước B — Wire tool-calling vào CLI
Thêm subcommand `agent` bên cạnh `index`/`query`:
```
python -m src.local_agent.cli agent "câu hỏi cần đọc file/git"
```
*Lý do:* biến loop từ module thành tính năng dùng được từ terminal.

### Bước C — Giai đoạn 2: Memory / multi-turn ✅ XONG
- `memory/storage.py` (SQLite): bảng `sessions` + `turns`, lưu/nạp hội thoại.
- `ToolCallingAgent.run(question, history)`: nạp lượt trước vào prompt.
- CLI: `agent --session <id>` nhớ qua nhiều lần chạy (`--session-db`,
  `--history-turns`).

### Bước D — Guardrails wiring
Gắn `guardrails/validators.py` vào output của loop/planner (chặn câu trả lời
không có citation, chặn action nguy hiểm).
*Lý do:* an toàn & tin cậy — thứ phân biệt agent đồ chơi với agent dùng được.

### Bước E — Hybrid retrieval (tùy chọn, nâng cao)
Thêm BM25 (sparse) vào retrieval (hiện chỉ dense) như config đã khai báo.
*Lý do:* cải thiện chất lượng tìm kiếm — nơi 90% chất lượng agent nằm ở đó, và
KHÔNG cần GPU.

### Bước F — Gộp RAG + tool-calling (tầm nhìn)
Cho `ToolCallingAgent` truy cập cả retriever (như một "tool" search) để agent tự
chọn giữa "tìm trong index" và "đọc nguyên file". Đây là kiến trúc agent trưởng
thành.

---

## 6. Cách chạy & kiểm chứng

**Prerequisites:** `ollama serve` + `ollama pull llama3.2:3b` (hoặc qwen2.5:0.5b
cho nhanh nhưng "ngố").

```bash
# Luôn cần trên máy Intel này (tránh segfault OpenMP faiss+torch):
export KMP_DUPLICATE_LIB_OK=TRUE
export OMP_NUM_THREADS=1

# RAG một chiều:
.venv/bin/python -m src.local_agent.cli index .
.venv/bin/python -m src.local_agent.cli query --model llama3.2:3b \
  -k 3 --max-context-tokens 1500 "What does LocalAgent.query do?"
```

**Verify mỗi slice:**
- `flake8 <paths> --select=E9,F63,F7,F82` (bộ chặn CI)
- `mypy <paths> --ignore-missing-imports`
- `pytest tests/local_agent/`
- Chạy thật trên Ollama (bằng chứng > giả định)

---

## 7. Non-goals (không làm)

- KHÔNG train/fine-tune model từ đầu.
- KHÔNG gọi API LLM bên ngoài trong local agent (Ollama là local).
- KHÔNG sửa file repo lúc runtime (mọi tool read-only).
- KHÔNG chạy model lớn (>7B) trên máy dev hiện tại — quá chậm.
