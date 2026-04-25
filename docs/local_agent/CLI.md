# Local Agent CLI

## Overview

Local Agent CLI cho phép bạn hỏi đáp về codebase trực tiếp từ terminal.
Nó wrap pipeline:

`câu hỏi → retrieval → context builder → local LLM → câu trả lời`

CLI được thiết kế:
- 100% local (Ollama / model local khác)
- Read-only với repo
- Grounded trên code, tránh đoán mò
- Dễ tích hợp vào workflow existing (shell, editor, scripts)

CLI có 2 subcommand:

| Command | Mục đích |
|---|---|
| `index <repo_path>` | Crawl + parse + chunk + embed → ghi FAISS index xuống đĩa |
| `query "câu hỏi"` | Retrieve + build context + gọi LLM trả lời câu hỏi |

---

## Quick start

### 1. Chuẩn bị môi trường

- Python 3.10+
- Các dependency đã cài (tree-sitter, sentence-transformers, faiss-cpu, v.v.)
- Ollama đang chạy với model đã pull (chỉ cần cho `query`):

```bash
ollama pull llama3:8b
ollama serve
```

> Nếu bạn dùng backend LLM khác, xem docs cấu hình LLM tương ứng.

### 2. Build index lần đầu

Từ root project (hoặc bất kỳ đâu, miễn `repo_path` đúng):

```bash
python -m src.local_agent.cli index .
```

Xem chi tiết hơn về indexing pipeline tại [INDEXING.md](INDEXING.md).

### 3. Chạy câu hỏi đầu tiên

```bash
python -m src.local_agent.cli query "What does AuthService.login do?"
```

CLI sẽ:
- Tìm các đoạn code liên quan đến câu hỏi
- Assemble context window trong giới hạn token
- Gọi model local với context đó
- In câu trả lời và một ít metadata (confidence, model, latency)

---

## Usage

### `index` — Build FAISS index

```bash
python -m src.local_agent.cli index <REPO_PATH> [OPTIONS]
```

Tuỳ chọn:

- `REPO_PATH` (positional, required) — đường dẫn tới repo cần index.
- `--index-dir DIR` — thư mục output cho index (mặc định: `data/local_agent/indices/code`).
- `--model MODEL` — embedding model (mặc định: `llama3:8b`). Lưu ý: đây là tên model
  phục vụ cả embedding lẫn query — đổi model nghĩa là phải re-index.
- `--batch-size N` — batch size cho embedding (mặc định: 32).
- `-v, --verbose` — in tiến độ từng bước (crawl / parse / embed / write).

Ví dụ:

```bash
python -m src.local_agent.cli index . \
  --index-dir data/local_agent/indices/code \
  --model all-MiniLM-L6-v2 \
  --batch-size 64 \
  --verbose
```

Output (rút gọn, verbose):

```text
Crawling Python files under /path/to/repo...
  found 142 files
Parsing AST...
Extracting symbols...
Chunking...
  produced 873 chunks
Embedding with all-MiniLM-L6-v2 (batch_size=64)...
Writing FAISS index to /path/to/index...
Indexed 873 chunks from 142 files in 12345 ms.
Index written to: /path/to/index
```

### `query` — Hỏi đáp

```bash
python -m src.local_agent.cli query "YOUR_QUESTION_HERE" [OPTIONS]
```

Tuỳ chọn:

- `QUESTION` (positional, required) — câu hỏi tự nhiên về codebase.
- `-k, --top-k N` — số chunk retrieve (mặc định: 8).
- `--max-context-tokens N` — giới hạn token cho context window (mặc định: 32000).
- `--model MODEL` — LLM model name (mặc định: `llama3:8b`).
- `--index-dir DIR` — thư mục index (mặc định: `data/local_agent/indices/code`).
- `--json` — output JSON machine-readable.
- `-v, --verbose` — in thêm context info, chunks, warnings.

Ví dụ đầy đủ:

```bash
python -m src.local_agent.cli query \
  -k 8 \
  --max-context-tokens 32000 \
  --model llama3:8b \
  --verbose \
  "Explain the auth flow when a user logs in"
```

### Top-level flags

```bash
python -m src.local_agent.cli --help      # show usage + list of subcommands
python -m src.local_agent.cli --version   # print version
```

### Output

#### Mặc định (human-readable)

```text
Question:
  What does AuthService.login do?

Answer:
  AuthService.login validates the user's credentials against the repository,
  creates a session token, and records an audit log entry when login succeeds.

Confidence: 0.87
Model: llama3:8b
Latency: 1234 ms

Context:
  Retrieved chunks: 7 (used in context: 5)
  Files:
    - src/auth/service.py
    - src/auth/repository.py
```

#### JSON mode

```bash
python -m src.local_agent.cli query --json "Where is the scheduler?"
```

Ví dụ output (rút gọn):

```json
{
  "question": "Where is the scheduler?",
  "answer": "The scheduler is implemented in ...",
  "retrieved_chunks": ["chunk_123", "chunk_456"],
  "total_retrieved": 7,
  "total_context_tokens": 5240,
  "confidence": 0.81,
  "model_name": "llama3:8b",
  "latency_ms": 987,
  "timestamp": "2026-04-25T10:15:00Z",
  "warnings": []
}
```

JSON mode hữu ích khi bạn:
- Gọi Local Agent từ script/batch khác
- Tích hợp vào editor, CI hoặc tool automation

---

## Environment variables

- `LOCAL_AGENT_INDEX_PATH` — override default `--index-dir`.
- `LOCAL_AGENT_MODEL` — override default `--model`.
- `LOCAL_AGENT_DEBUG=1` — in stack trace đầy đủ khi có lỗi (cùng tác dụng `--verbose` cho debug output).

---

## Exit codes

| Code | Ý nghĩa |
|------|---------|
| 0 | Thành công |
| 1 | Lỗi runtime (LLM không kết nối, index hỏng, indexing pipeline fail, v.v.) |
| 2 | Lỗi input (question rỗng, repo_path không tồn tại) |

---

## Troubleshooting

### `query failed: Index not found at …`

**Nguyên nhân**: index chưa được build, hoặc `--index-dir` trỏ sai chỗ.

**Cách xử lý**:
1. Build index trước: `python -m src.local_agent.cli index .`
2. Kiểm tra path trùng nhau giữa lệnh `index` và `query`.
3. Xem [INDEXING.md](INDEXING.md) cho chi tiết flow indexing.

### Ollama connection failed / CLI treo khi gọi model

**Nguyên nhân**: `ollama serve` chưa chạy, model chưa pull, hoặc timeout.

**Cách xử lý**:

```bash
ps aux | grep ollama          # kiểm tra Ollama đang chạy
ollama list                    # xem model đã có
ollama pull llama3:8b          # pull model nếu thiếu
```

Nếu bạn đổi tên model, cập nhật `--model` ở cả `index` và `query` (model embedding
phải khớp với model đã build index — xem M-2 trong INDEXING.md).

### "I do not have enough information…" / answer chung chung

**Nguyên nhân**: query mơ hồ, index thiếu file liên quan, hoặc retrieval `-k` quá nhỏ.

**Cách xử lý**:
- Hỏi cụ thể hơn (kèm tên module/class/function): `"What does AuthService.login do in src/auth/service.py?"`
- Re-index sau khi commit code mới.
- Tăng `-k` (vd `-k 16`).

### CLI chạy chậm

**Nguyên nhân**: model lớn chạy CPU, index lớn, machine hạn chế.

**Cách xử lý**:
- Dùng model nhẹ hơn (vd `llama3:8b` thay vì 70B).
- Giảm `--max-context-tokens` hoặc `-k`.
- Chạy trên máy có GPU.

### Cần debug thêm

- Chạy với `--verbose` để xem retrieved chunks, token counts.
- Set `LOCAL_AGENT_DEBUG=1` để thấy stack trace đầy đủ khi có exception.

---

Nếu bạn gặp vấn đề khác với CLI, hãy đính kèm:
- Câu lệnh CLI đầy đủ (ẩn thông tin nhạy cảm)
- Output (stdout/stderr)
- Thông tin hệ thống (OS, Python, Ollama/model version)
khi mở issue hoặc hỏi trong kênh nội bộ.
