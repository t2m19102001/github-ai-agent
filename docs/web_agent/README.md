# GitHub AI Agent — Web surface

Canonical entrypoint: `src.web.main:app`. `src.web.app_fastapi:app` is a
compatibility alias to the same application.

## Verified capabilities

- FastAPI chat UI with WebSocket transport.
- Mock, Ollama, Groq, and failover LLM providers.
- Issue-analysis orchestration with an explicit runtime dependency graph.
- OCR/diagram analysis when OpenCV and Tesseract are installed.
- Deterministic fallback vector search and SQLite memory/activity logs.
- GitHub issue and PR automation through GitHub Actions.

Slack/Discord bots and a bundled monitoring stack are **not implemented** in
the canonical surface. Performance and accuracy figures remain targets until a
versioned evaluation report records them.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/run_web.sh
```

The default is offline: `LLM_PROVIDER=mock`, SQLite, and no Redis/PostgreSQL.
Open <http://127.0.0.1:8000>, `/docs`, or `/health`.

Costly/stateful POST routes accept `Authorization: Bearer <API_TOKEN>` or
`X-API-Key: <API_TOKEN>`. Development allows an empty token for local UI use;
production fails closed. WebSocket clients can also use `?token=...`.

## Routes

| Route | Purpose |
|---|---|
| `/`, `/ws/chat` | Chat UI and WebSocket |
| `/issue`, `POST /analyze_issue` | Issue workflow |
| `/image-page`, `POST /analyze_image` | OCR/diagram analysis |
| `/dashboard`, `/logs-page`, `/logs` | Local activity views |
| `/memory/search`, `/vector_store/search` | Retrieval APIs |
| `/health`, `/docs` | Readiness details and OpenAPI |

## Production container

Create `.env` from `.env.example`, replace `API_TOKEN` and `JWT_SECRET`, then:

```bash
docker compose up --build -d
```

Canonical Compose runs one Web service with persistent data/log volumes.
External PostgreSQL is optional. Redis, Nginx, Grafana, and Prometheus are not
bundled.

## Verification

```bash
pytest tests/ src/local_agent/tests/
flake8 src/ tests/ --exclude=tests/verify_changes.py --count --select=E9,F63,F7,F82
```

CI runs the full regression gate; security/performance tests are not ignored.
Live GitHub/Ollama/Groq checks remain separate from hermetic regression tests.

## Current targets

- Golden sets for issue classification, PR relevance, and OCR.
- Versioned p50/p95 latency and quality reports.
- Optional Slack adapter after Web contracts stabilize.
- Production observability as a separate deployment profile.
