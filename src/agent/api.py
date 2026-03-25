#!/usr/bin/env python3
"""
Agent API Module
Provides REST API endpoints for agent operations
"""

from fastapi import FastAPI, HTTPException, Header
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import os

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

try:
    from src.agent.ai_provider import get_default_provider
except ImportError:
    from src.llm.provider import get_llm_provider as get_default_provider

logger = get_logger(__name__)

app = FastAPI(title="GitHub AI Agent API", version="1.0")


class AnalyzeIssueRequest(BaseModel):
    title: str
    body: str
    labels: Optional[List[str]] = []
    priority: Optional[str] = "medium"


class IssueAnalysisResponse(BaseModel):
    analysis: Dict[str, Any]
    plugins: List[str]
    agents: List[str]


@app.get("/providers")
async def get_providers(authorization: str = Header(None)) -> Dict[str, Any]:
    """Get available LLM providers"""
    if not _verify_token(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        provider = get_default_provider()
        return {
            "ordered": ["groq", "huggingface", "mock"],
            "current": provider.name if hasattr(provider, 'name') else "mock",
            "status": "active"
        }
    except Exception as e:
        logger.error(f"Error getting providers: {e}")
        return {
            "ordered": ["mock"],
            "current": "mock",
            "status": "fallback"
        }


@app.get("/plugins")
async def get_plugins(authorization: str = Header(None)) -> Dict[str, Any]:
    """Get enabled plugins"""
    if not _verify_token(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    enabled_plugins_env = os.getenv("AGENT_PLUGINS", "")
    enabled_plugins = [p.strip() for p in enabled_plugins_env.split(",") if p.strip()]
    
    if not enabled_plugins:
        enabled_plugins = ["auto_comment_on_issue", "auto_check_code_quality"]
    
    return {
        "enabled": enabled_plugins,
        "available": [
            "auto_comment_on_issue",
            "auto_check_code_quality",
            "auto_label_issue",
            "auto_assign_reviewer"
        ]
    }


@app.post("/analyze-issue")
async def analyze_issue(
    request: AnalyzeIssueRequest,
    authorization: str = Header(None)
) -> IssueAnalysisResponse:
    """Analyze GitHub issue"""
    if not _verify_token(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        analysis = {
            "title": request.title,
            "summary": f"Analysis of issue: {request.title}",
            "suggestions": ["Review code related to the issue"],
            "priority_score": 5 if request.priority == "high" else 3,
            "labels_suggested": _suggest_labels(request.title, request.body)
        }
        
        plugins = os.getenv("AGENT_PLUGINS", "").split(",") if os.getenv("AGENT_PLUGINS") else []
        
        return IssueAnalysisResponse(
            analysis=analysis,
            plugins=[p.strip() for p in plugins if p.strip()] or ["auto_comment_on_issue"],
            agents=["github_issue"]
        )
    except Exception as e:
        logger.error(f"Error analyzing issue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status(authorization: str = Header(None)) -> Dict[str, Any]:
    """Get API status"""
    if not _verify_token(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return {
        "ready": True,
        "providers": {
            "groq": {"status": "active", "latency_ms": 150},
            "huggingface": {"status": "active", "latency_ms": 200}
        },
        "agents": ["github_issue", "code", "documentation", "image"],
        "version": "5.0.0"
    }


def _verify_token(authorization: Optional[str]) -> bool:
    """Verify authorization token"""
    if not authorization:
        return False
    
    expected_token = os.getenv("API_TOKEN", "test_token")
    
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization
    
    return token == expected_token


def _suggest_labels(title: str, body: str) -> List[str]:
    """Suggest labels based on issue content"""
    labels = []
    content = f"{title} {body}".lower()
    
    if any(w in content for w in ["bug", "error", "crash", "fail"]):
        labels.append("bug")
    if any(w in content for w in ["feature", "enhancement", "request"]):
        labels.append("enhancement")
    if any(w in content for w in ["security", "vulnerability"]):
        labels.append("security")
    
    return labels or ["question"]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
