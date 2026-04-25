# Local Agent — Indexing

Tài liệu này mô tả pipeline indexing mà CLI subcommand `index` thực hiện
khi bạn gõ `python -m src.local_agent.cli index <repo_path>`.

> Đối tượng đọc: developer cần build index trước khi `query`, hoặc
> debug khi index không trả về kết quả mong muốn.

---

## Pipeline tổng quan

```
repo_path
   │
   ▼
crawl_python_files       (crawler)        — list .py files, respect .gitignore
   │
   ▼
parse_files              (parser)         — Python AST → ParsedFile
   │
   ▼
extract_symbols_batch    (symbols)        — ParsedFile → SymbolTable
   │
   ▼
chunk_files              (chunker)        — 4 chunk levels: file/class/function/method
   │
   ▼
embed_chunks             (embedder)       — sentence-transformers → list[float]
   │
   ▼
IndexBuilder.build       (index_builder)  — FAISS IndexFlatL2 + metadata.json
   │
   ▼
{index_dir}/
  ├── code.index
  └── metadata.json
```

Mỗi bước là 1 module độc lập trong [`src/local_agent/ingestion/`](../../src/local_agent/ingestion/)
+ [`src/local_agent/indexing/`](../../src/local_agent/indexing/).

---

## Cách chạy

### Lệnh cơ bản

```bash
python -m src.local_agent.cli index .
```

### Verbose (khuyến nghị lần đầu)

```bash
python -m src.local_agent.cli index . --verbose
```

Output mẫu:

```text
Crawling Python files under /repo...
  found 142 files
Parsing AST...
Extracting symbols...
Chunking...
  produced 873 chunks
Embedding with llama3:8b (batch_size=32)...
Writing FAISS index to /repo/data/local_agent/indices/code...
Indexed 873 chunks from 142 files in 12345 ms.
Index written to: /repo/data/local_agent/indices/code
```

### Tuỳ chọn

| Flag | Mặc định | Ý nghĩa |
|---|---|---|
| `repo_path` (positional) | — | Repo cần index |
| `--index-dir` | `data/local_agent/indices/code` | Output dir cho FAISS index |
| `--model` | `llama3:8b` | Model name (cần khớp với `query --model`) |
| `--batch-size` | `32` | Batch size khi embed |
| `-v, --verbose` | off | Hiện tiến độ từng bước |

---

## Output trên đĩa

```
{index_dir}/
├── code.index          # FAISS binary (IndexFlatL2)
└── metadata.json       # 1-1 với FAISS row IDs
```

`metadata.json` shape:

```json
{
  "chunks": [
    {
      "chunk_id": "...",
      "file_path": "/repo/src/foo.py",
      "relative_path": "src/foo.py",
      "name": "fn",
      "qualified_name": "Module.fn",
      "level": "function",
      "start_line": 10,
      "end_line": 25,
      "docstring": "...",
      "symbols": ["fn"],
      "parent_name": null,
      "content": "def fn(): ...",
      "model_name": "llama3:8b"
    }
  ],
  "model_name": "llama3:8b",
  "embedding_dim": 384
}
```

**Quy tắc mapping** (do P0-06 enforce): `metadata["chunks"][N]` ⇔ FAISS row ID `N`.
Thứ tự sort theo `chunk_id` ascending — không phụ thuộc input order từ embedder.
Retriever (`BasicRetriever`) đọc trực tiếp metadata theo FAISS ID, không assume gì khác.

---

## Khi nào cần re-index

Re-index toàn bộ khi:

1. **Code thay đổi** — chunk mới / xoá / sửa nội dung.
2. **Đổi `--model`** — embedding khác model = vector space khác. Mismatch sẽ bị
   `BasicRetriever._load()` raise `ValueError: Model mismatch` (M-2 fix from P0-07).
3. **Đổi chunking config** — vd thay đổi `chunking.yaml` (Milestone 1 wiring).
4. **Index file hỏng / mất** — `code.index` hoặc `metadata.json` mất một trong hai.

V1 chưa hỗ trợ incremental update — mỗi lần index là full rebuild. Defer P1.

---

## Determinism guarantee

Các tầng đều enforce deterministic ordering:

- **Crawler**: sort by `relative_path` ascending
- **Parser batch**: sort by posix path
- **Symbol batch**: sort by `(relative_path, file_path)`
- **Chunker**: sort by `(line_start, line_end, name)`
- **IndexBuilder**: sort by `chunk_id` (= input to FAISS)

→ Cùng repo + cùng model = cùng `code.index` byte-for-byte (modulo `assembly_time_ms`
metadata field). Verify bằng:

```bash
python -m src.local_agent.cli index . --index-dir /tmp/idx-a
python -m src.local_agent.cli index . --index-dir /tmp/idx-b
diff /tmp/idx-a/code.index /tmp/idx-b/code.index   # → no difference
```

---

## Troubleshooting

### `Error: repo_path is not a directory: ...`

Path bạn pass không tồn tại hoặc không phải directory. Exit code 2.

### `Error: indexing failed: no Python files found under ...`

Repo không có file `.py` (hoặc tất cả bị `.gitignore` exclude). Exit code 1.

Cách xử lý:
- Kiểm tra repo có file Python.
- Kiểm tra `.gitignore` không ignore quá rộng.
- Crawler hiện chỉ index `.py`. Multi-language defer V2.

### `Error: indexing failed: ImportError: faiss-cpu is required ...`

```bash
pip install faiss-cpu
```

### `Error: indexing failed: sentence-transformers is required ...`

```bash
pip install sentence-transformers
```

Lần đầu chạy sẽ download model weights (~80MB cho `all-MiniLM-L6-v2`,
hoặc lớn hơn cho model khác).

### Indexing rất chậm

- Embedding là bottleneck — repo lớn (>10K files) có thể mất hàng phút trên CPU.
- Tăng `--batch-size` (32 → 64 hoặc 128) nếu RAM cho phép.
- Dùng model nhỏ hơn (`all-MiniLM-L6-v2` ~22MB, nhanh hơn LLM-class embedding).
- GPU acceleration: nếu sentence-transformers detect được CUDA / MPS, tự dùng.

### Index xong nhưng `query` trả "I do not have enough information"

Khả năng cao là model name mismatch. Verify:

```bash
cat data/local_agent/indices/code/metadata.json | python -c \
  "import json,sys; print(json.load(sys.stdin)['model_name'])"
```

Compare với `query --model ...`. Phải khớp.

---

## Programmatic API

Pipeline có thể chạy lập trình mà không qua CLI:

```python
from pathlib import Path
from src.local_agent.indexing.index_builder import IndexBuilder
from src.local_agent.ingestion import (
    chunk_files, crawl_python_files, embed_chunks,
    extract_symbols_batch, parse_files,
)

repo = Path(".")
crawl = crawl_python_files(repo)
paths = [Path(r["path"]) for r in crawl["files"]]

parsed = parse_files(paths, repo_root=repo)
symbols = extract_symbols_batch(parsed)
chunks = chunk_files(parsed, {s.file_path: s for s in symbols})
embedded = embed_chunks(chunks, model_name="all-MiniLM-L6-v2")

result = IndexBuilder("./my_index").build(embedded)
print(f"{result.total_chunks} chunks → {result.index_path}")
```

Dùng pattern này khi bạn cần custom step (vd filter chunks trước khi embed,
hoặc chạy trong notebook).

---

## Future work

- **Incremental update**: chỉ re-index file thay đổi (P1).
- **Multi-language**: hiện chỉ Python; JS/TS/Go defer V2.
- **Index types**: `IndexIVFFlat` / `IndexHNSWFlat` cho repo > 100K chunks (P1).
- **Config wiring**: `configs/chunking.yaml` + `configs/localagent.yaml` chưa được
  CLI đọc. Defer Milestone 1.
- **Metadata sidecar mở rộng**: thêm `imports`, `token_count` thật (BPE) — hiện
  bị strip khi vào IndexMetadata. Cần khi P0-09+ muốn citation chi tiết.
