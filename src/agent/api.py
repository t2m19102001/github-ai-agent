#!/usr/bin/env python3
from typing import Dict, Any, List
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

from src.agent.ai_provider import get_default_provider, ProviderAdapter, CompositeAIProvider, ProviderBase
from src.agent.plugins.base import PluginManager
from src.agent.plugins.auto_comment_on_issue import AutoCommentOnIssuePlugin
from src.agent.plugins.auto_check_code_quality import AutoCheckCodeQualityPlugin
from src.core.config import API_TOKEN, API_ALLOWLIST, DEBUG, AGENT_PLUGINS, GITHUB_WEBHOOK_SECRET
from src.agents.orchestrator import Orchestrator
import hmac
import hashlib

app = FastAPI(title="AI Agent REST API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"]
    ,allow_headers=["*"]
)

security = HTTPBearer(auto_error=False)


def _auth(credentials: HTTPAuthorizationCredentials = Depends(security), request: Request = None):
    # IP allowlist
    if API_ALLOWLIST:
        ip = request.client.host if request and request.client else ""
        if ip not in API_ALLOWLIST:
            raise HTTPException(status_code=403, detail="IP not allowed")
    # Token check
    if API_TOKEN:
        if not credentials or credentials.scheme.lower() != "bearer" or credentials.credentials != API_TOKEN:
            raise HTTPException(status_code=401, detail="Invalid token")
    return True


base_provider: ProviderBase = get_default_provider()
adapter = ProviderAdapter(base_provider)
orchestrator = Orchestrator(adapter)

plugins = PluginManager()
enabled = set(AGENT_PLUGINS or [])
if not enabled or "auto_check_code_quality" in enabled:
    plugins.register(AutoCheckCodeQualityPlugin())
if "auto_comment_on_issue" in enabled:
    plugins.register(AutoCommentOnIssuePlugin())


@app.get("/providers")
def get_providers(_: bool = Depends(_auth)):
    # If composite, show ordered providers and availability
    def info(p: ProviderBase):
        try:
            avail = p.is_available()
        except Exception:
            avail = False
        return {"name": getattr(p, "name", p.__class__.__name__), "available": avail}

    if isinstance(base_provider, CompositeAIProvider):
        ordered = [info(p) for p in base_provider.providers]
        ready = any(i["available"] for i in ordered)
        return {"ordered": ordered, "ready": ready}
    else:
        return {"ordered": [info(base_provider)], "ready": base_provider.is_available()}


@app.get("/plugins")
def get_plugins(_: bool = Depends(_auth)):
    return {"enabled": [getattr(p, "name", p.__class__.__name__) for p in plugins.plugins]}


@app.post("/analyze-issue")
def analyze_issue(payload: Dict[str, Any], _: bool = Depends(_auth)):
    title = payload.get("title", "")
    body = payload.get("body", "")
    labels: List[str] = payload.get("labels", [])
    event = {"type": "issue", "labels": labels, "title": title}

    # Plugin pass
    plugin_results = plugins.run_plugins(event, {"title": title})

    # LLM analysis
    prompt = f"Issue: {title}\n\n{body}\n\nProvide summary and recommended next actions."
    resp = adapter.call([
        {"role": "system", "content": "You are a helpful triage assistant."},
        {"role": "user", "content": prompt}
    ])
    analysis = resp or "Unable to generate analysis"
    return {"analysis": analysis, "plugins": plugin_results}


@app.get("/api/status")
def api_status(_: bool = Depends(_auth)):
    def info(p: ProviderBase):
        try:
            avail = p.is_available()
        except Exception:
            avail = False
        return {"name": getattr(p, "name", p.__class__.__name__), "available": avail}

    if isinstance(base_provider, CompositeAIProvider):
        ordered = [info(p) for p in base_provider.providers]
        ready = any(i["available"] for i in ordered)
        return {"ready": ready, "providers": ordered, "debug": DEBUG}
    else:
        ordered = [info(base_provider)]
        ready = base_provider.is_available()
        return {"ready": ready, "providers": ordered, "debug": DEBUG}


@app.post("/api/github/webhook")
async def github_webhook(request: Request, _: bool = Depends(_auth)):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if GITHUB_WEBHOOK_SECRET:
        digest = hmac.new(GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        expected = f"sha256={digest}"
        if signature != expected:
            raise HTTPException(status_code=401, detail="Invalid signature")
    event = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()
    plugins_result: List[Dict[str, Any]] = []
    if event == "issues":
        labels = [l.get("name") for l in (payload.get("issue", {}).get("labels") or [])]
        local_plugins = PluginManager([AutoCheckCodeQualityPlugin(), AutoCommentOnIssuePlugin()])
        plugins_result = local_plugins.run_plugins({"type": "issue", "labels": labels, "title": payload.get("issue", {}).get("title")}, {"title": payload.get("issue", {}).get("title")})
        result = orchestrator.handle_issue_event({"issue": payload.get("issue", {})})
        return {"status": "ok", "event": event, "result": result, "plugins": plugins_result}
    if event == "pull_request":
        pr = payload.get("pull_request", {})
        labels = [l.get("name") for l in (pr.get("labels") or [])]
        files_data = payload.get("files", [])
        local_plugins = PluginManager([AutoCheckCodeQualityPlugin()])
        plugins_result = local_plugins.run_plugins({"type": "pr", "labels": labels, "files_data": files_data}, {"files_count": len(files_data)})
        result = orchestrator.handle_pull_request_event({"pull_request": pr, "title": pr.get("title")})
        return {"status": "ok", "event": event, "result": result, "plugins": plugins_result}
    return {"status": "ignored", "event": event}
