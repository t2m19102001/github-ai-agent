"""Backward-compatible import for the canonical FastAPI application.

Historically this module exposed a second web application with unauthenticated
Git, test execution, and autofix endpoints.  Keeping two independently wired
applications made the documented run command determine the security model.

All callers now receive the single canonical application from
``src.web.main``.  The module remains importable so old deployment commands do
not fail, but it no longer defines a separate route surface.
"""

from src.web.main import app

__all__ = ["app"]
