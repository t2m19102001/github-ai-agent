#!/usr/bin/env python3
"""Repository-wide pytest guards."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import pytest


def pytest_ignore_collect(collection_path, config) -> bool:
    path = Path(str(collection_path)).as_posix()
    if path.endswith("scripts/test_autofix.py"):
        return importlib.util.find_spec("requests") is None
    return False


def pytest_collection_modifyitems(config, items):
    """Skip asyncio-marked tests when pytest-asyncio is unavailable."""
    has_asyncio_plugin = importlib.util.find_spec("pytest_asyncio") is not None
    if has_asyncio_plugin:
        return

    skip_async = pytest.mark.skip(reason="pytest-asyncio is not installed in this environment")
    for item in items:
        if item.get_closest_marker("asyncio"):
            item.add_marker(skip_async)
