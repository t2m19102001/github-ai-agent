#!/usr/bin/env python3
"""Pytest collection guards for optional dependency test modules.

This repository contains a mix of smoke tests and integration tests that rely on
optional runtime dependencies (FastAPI, NumPy, httpx, requests, python-dotenv).
In lightweight environments where these packages are not installed, importing
those test modules fails during collection. We skip only the affected modules so
the rest of the suite can still run.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Dict, Set


MODULE_DEPENDENCIES: Dict[str, Set[str]] = {
    "scripts/test_autofix.py": {"requests"},
    "tests/test_api_basic.py": {"httpx"},
    "tests/test_chat.py": {"requests"},
    "tests/test_completion.py": {"dotenv"},
    "tests/test_github_issue_agent.py": {"requests"},
    "tests/test_image_agent.py": {"numpy"},
    "tests/test_orchestrator.py": {"numpy"},
    "tests/test_phase3_integration.py": {"numpy"},
    "tests/test_pr_agent.py": {"dotenv"},
    "tests/test_rag_integration.py": {"numpy"},
    "tests/test_webhook.py": {"httpx"},
    "tests/test_webhook_quality.py": {"httpx"},
    "tests/test_webhooks.py": {"fastapi"},
}


def _missing_dependencies(dependencies: Set[str]) -> Set[str]:
    return {dep for dep in dependencies if importlib.util.find_spec(dep) is None}


def pytest_ignore_collect(collection_path, config) -> bool:
    path = Path(str(collection_path)).as_posix()
    for module_path, dependencies in MODULE_DEPENDENCIES.items():
        if path.endswith(module_path):
            missing = _missing_dependencies(dependencies)
            if missing:
                return True
            return False
    return False
