#!/usr/bin/env python3
import os
import httpx
import pytest

@pytest.mark.anyio
async def test_api_providers(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "t")
    from src.agent.api import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/providers", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    data = r.json()
    assert "ordered" in data


@pytest.mark.anyio
async def test_api_plugins(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "t")
    monkeypatch.setenv("AGENT_PLUGINS", "auto_comment_on_issue")
    from src.agent.api import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/plugins", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert "enabled" in r.json()


@pytest.mark.anyio
async def test_api_analyze_issue(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "t")
    from src.agent.api import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"title": "Bug report", "body": "App crashes", "labels": ["question"]}
        r = await client.post("/analyze-issue", json=payload, headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    data = r.json()
    assert "analysis" in data
    assert "plugins" in data


@pytest.mark.anyio
async def test_api_status(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "t")
    from src.agent.api import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/status", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    data = r.json()
    assert "ready" in data
    assert "providers" in data
