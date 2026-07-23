"""Authentication dependencies shared by the canonical FastAPI surface."""

from __future__ import annotations

import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException, WebSocket


def _extract_token(authorization: Optional[str], api_key: Optional[str]) -> str:
    if api_key:
        return api_key
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return ""


async def require_api_token(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> None:
    """Protect costly or state-changing routes.

    Local development remains zero-config. Production fails closed when an API
    token has not been configured.
    """
    expected = os.getenv("API_TOKEN", "")
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if not expected:
        if environment == "production":
            raise HTTPException(status_code=503, detail="API_TOKEN is not configured")
        return

    supplied = _extract_token(authorization, x_api_key)
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


async def authorize_websocket(websocket: WebSocket) -> bool:
    """Validate a WebSocket using Bearer, X-API-Key, or ``token`` query param."""
    expected = os.getenv("API_TOKEN", "")
    if not expected:
        return os.getenv("ENVIRONMENT", "development").lower() != "production"
    supplied = _extract_token(
        websocket.headers.get("authorization"),
        websocket.headers.get("x-api-key") or websocket.query_params.get("token"),
    )
    return bool(supplied and hmac.compare_digest(supplied, expected))
