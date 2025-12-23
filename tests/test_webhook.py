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
async def test_webhook_issue_comment(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "t")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "s")
    monkeypatch.setenv("AGENT_PLUGINS", "auto_comment_on_issue")
    from src.agent.api import app
    transport = httpx.ASGITransport(app=app)
    payload = {
        "issue": {"title": "Help needed", "labels": [{"name": "question"}]}
    }
    body = json.dumps(payload).encode()
    headers = {
        "Authorization": "Bearer t",
        "X-GitHub-Event": "issues",
        "X-Hub-Signature-256": _sig("s", body),
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/github/webhook", content=body, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert data.get("event") == "issues"
    assert isinstance(data.get("plugins"), list)
    assert any(p.get("action") == "comment" for p in data.get("plugins") or [])


@pytest.mark.anyio
async def test_webhook_pull_request(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "t")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "s")
    from src.agent.api import app
    transport = httpx.ASGITransport(app=app)
    payload = {
        "pull_request": {"title": "Feature X"}
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
    assert isinstance(data.get("result"), dict)
    assert "review" in data.get("result")
