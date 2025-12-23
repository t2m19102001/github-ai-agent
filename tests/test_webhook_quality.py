#!/usr/bin/env python3
import os
import json
import hmac
import hashlib
import httpx
import pytest


def _sig(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.anyio
async def test_webhook_pull_request_quality(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "t")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "s")
    from src.agent.api import app
    transport = httpx.ASGITransport(app=app)

    patch = """
diff --git a/app.py b/app.py
index 000000..111111 100644
--- a/app.py
+++ b/app.py
@@
+password = "hardcoded123"
+print("debug")
    """

    payload = {
        "pull_request": {"title": "Fix bug", "labels": [{"name": "bug"}]},
        "files": [{"filename": "app.py", "patch": patch}]
    }

    body = json.dumps(payload).encode()
    headers = {
        "Authorization": "Bearer t",
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": _sig("s", body),
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/github/webhook", content=body, headers=headers)

    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert data.get("event") == "pull_request"
    plugins = data.get("plugins") or []
    # Expect at least one plugin output when label 'bug' and issues in patch
    assert len(plugins) >= 1
    assert any(p.get("action") == "comment" for p in plugins)
