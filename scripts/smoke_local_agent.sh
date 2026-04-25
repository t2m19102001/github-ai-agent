#!/usr/bin/env bash
# Manual end-to-end smoke test for the Local Agent CLI.
#
# Steps:
#   1. Build a FAISS index for THIS repository.
#   2. Run a query that should hit known code (LocalAgent.query).
#
# Prerequisites:
#   - .venv activated, dependencies installed.
#   - Ollama running locally with the chosen model pulled.
#       ollama serve
#       ollama pull "$MODEL"
#
# Usage:
#   bash scripts/smoke_local_agent.sh                    # default model
#   MODEL=all-MiniLM-L6-v2 bash scripts/smoke_local_agent.sh
#
# Exit codes:
#   0  smoke passed
#   1  index step failed
#   2  query step failed (LLM unreachable, index missing, etc.)

set -euo pipefail

MODEL="${MODEL:-llama3:8b}"
INDEX_DIR="${INDEX_DIR:-data/local_agent/indices/code}"
QUESTION="${QUESTION:-What does LocalAgent.query do?}"

echo "==> Local Agent smoke test"
echo "    Model:      $MODEL"
echo "    Index dir:  $INDEX_DIR"
echo "    Question:   $QUESTION"
echo

echo "==> Step 1: build index"
if ! python -m src.local_agent.cli index . \
    --index-dir "$INDEX_DIR" \
    --model "$MODEL" \
    --verbose; then
  echo "FAIL: indexing step failed" >&2
  exit 1
fi

echo
echo "==> Step 2: run query"
if ! python -m src.local_agent.cli query \
    --index-dir "$INDEX_DIR" \
    --model "$MODEL" \
    --verbose \
    "$QUESTION"; then
  echo "FAIL: query step failed (Ollama unreachable? model not pulled?)" >&2
  exit 2
fi

echo
echo "==> Smoke OK"
