"""Security contract for costly/stateful Web routes."""

import pytest
from fastapi import HTTPException

from src.web.security import require_api_token


@pytest.mark.asyncio
async def test_development_allows_zero_config(monkeypatch):
    monkeypatch.delenv("API_TOKEN", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert await require_api_token(None, None) is None


@pytest.mark.asyncio
async def test_production_fails_closed_without_token(monkeypatch):
    monkeypatch.delenv("API_TOKEN", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(HTTPException) as exc:
        await require_api_token(None, None)
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_production_requires_matching_token(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "expected")
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(HTTPException) as exc:
        await require_api_token("Bearer wrong", None)
    assert exc.value.status_code == 401
    assert await require_api_token("Bearer expected", None) is None
