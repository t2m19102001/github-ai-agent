#!/usr/bin/env bash
# Chạy Local AI Agent nhanh gọn để test thủ công.
#
# Cách dùng:
#   bash scripts/ask.sh "câu hỏi của bạn"
#   bash scripts/ask.sh -v "câu hỏi"                 # kèm step trace
#   MODEL=qwen2.5:0.5b bash scripts/ask.sh "..."     # đổi model (nhanh, ngố hơn)
#   SESSION=mychat bash scripts/ask.sh "..."         # bật memory nhớ nhiều lượt
#
# Memory lưu ở Postgres (database local_agent) nếu Postgres chạy; nếu không,
# tự fallback về SQLite. Đổi qua biến SESSION_DB nếu muốn.

cd "$(dirname "$0")/.." || exit 1

# Chống segfault OpenMP (faiss + torch) trên máy Intel + giới hạn 1 thread.
export KMP_DUPLICATE_LIB_OK=TRUE
export OMP_NUM_THREADS=1

MODEL="${MODEL:-llama3.2:3b}"
INDEX_DIR="data/local_agent/indices/code"
PY=".venv/bin/python"
SESSION_DB="${SESSION_DB:-postgresql://postgres@localhost/local_agent}"

# Kiểm tra Ollama đang chạy chưa (không để lỗi này làm script tắt âm thầm).
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "⚠️  Ollama chưa chạy. Mở terminal khác và chạy:  ollama serve" >&2
  exit 1
fi

# Ghép cờ session nếu có biến SESSION.
ARGS=(agent --model "$MODEL" --index-dir "$INDEX_DIR" --max-iters 3)
if [ -n "${SESSION:-}" ]; then
  ARGS+=(--session "$SESSION" --session-db "$SESSION_DB")
fi

"$PY" -m src.local_agent.cli "${ARGS[@]}" "$@"
