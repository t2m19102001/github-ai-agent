#!/usr/bin/env python3
"""Compatibility API for legacy `src.agent.api` imports in tests."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException, Request

from src.agent.plugins import (
    AutoCheckCodeQualityPlugin,
    AutoCommentOnIssuePlugin,
    PluginManager,
)

app = FastAPI(title="Agent Compatibility API", version="1.0.0")


def _authorized(authorization: Optional[str]) -> bool:
    expected = os.getenv("API_TOKEN", "")
    if not expected:
        return True
    return authorization == f"Bearer {expected}"


def _plugin_manager_from_env() -> PluginManager:
    enabled = [item.strip() for item in os.getenv("AGENT_PLUGINS", "").split(",") if item.strip()]
    plugins = []
    if "auto_check_code_quality" in enabled:
        plugins.append(AutoCheckCodeQualityPlugin())
    if "auto_comment_on_issue" in enabled:
        plugins.append(AutoCommentOnIssuePlugin())
    return PluginManager(plugins)


def _verify_signature(secret: str, body: bytes, signature: Optional[str]) -> bool:
    if not secret:
        return True
    if not signature:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.get("/providers")
async def providers(authorization: Optional[str] = Header(default=None)):
    if not _authorized(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    ordered = ["mock", "groq", "ollama", "huggingface"]
    return {"ordered": ordered}


@app.get("/plugins")
async def plugins(authorization: Optional[str] = Header(default=None)):
    if not _authorized(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    enabled = [item.strip() for item in os.getenv("AGENT_PLUGINS", "").split(",") if item.strip()]
    return {"enabled": enabled}


@app.post("/analyze-issue")
async def analyze_issue(payload: Dict[str, Any], authorization: Optional[str] = Header(default=None)):
    if not _authorized(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    labels = payload.get("labels") or []
    event = {"type": "issue", "labels": labels, "title": payload.get("title", "")}
    plugin_outputs = _plugin_manager_from_env().run_plugins(event, {})
    return {
        "analysis": {
            "category": "question" if "question" in labels else "general",
            "title": payload.get("title", ""),
        },
        "plugins": plugin_outputs,
    }


@app.get("/api/status")
async def status(authorization: Optional[str] = Header(default=None)):
    if not _authorized(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"ready": True, "providers": ["mock"]}


@app.post("/api/github/webhook")
async def github_webhook(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_github_event: Optional[str] = Header(default=None),
    x_hub_signature_256: Optional[str] = Header(default=None),
):
    if not _authorized(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")

    body = await request.body()
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if not _verify_signature(secret, body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body.decode("utf-8") or "{}")
    event_type = x_github_event or "unknown"

    plugin_event: Dict[str, Any]
    result = {}
    if event_type == "issues":
        issue = payload.get("issue", {})
        labels = [x.get("name", "") for x in issue.get("labels", [])]
        plugin_event = {"type": "issue", "labels": labels, "title": issue.get("title", "")}
    elif event_type == "pull_request":
        pr = payload.get("pull_request", {})
        labels = [x.get("name", "") for x in pr.get("labels", [])]
        files_data = payload.get("files") or []
        plugin_event = {"type": "pr", "labels": labels, "title": pr.get("title", ""), "files_data": files_data}
        result = {"review": "Pull request analyzed"}
    else:
        plugin_event = {"type": "unknown"}

    plugin_outputs = _plugin_manager_from_env().run_plugins(plugin_event, {})
    return {"status": "ok", "event": event_type, "plugins": plugin_outputs, "result": result}
