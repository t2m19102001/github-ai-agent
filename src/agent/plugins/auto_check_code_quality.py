#!/usr/bin/env python3
"""PR code quality check plugin."""

from __future__ import annotations

from typing import Any, Dict, List

from .base import PluginBase


class AutoCheckCodeQualityPlugin(PluginBase):
    name = "auto_check_code_quality"

    def should_run(self, event: Dict[str, Any]) -> bool:
        return event.get("type") == "pr"

    def run(self, event: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings: List[str] = []
        for file_data in event.get("files_data", []):
            patch = (file_data.get("patch") or "").lower()
            if "eval(" in patch:
                findings.append(f"{file_data.get('filename')}: avoid eval().")
            if "password" in patch or "api_key" in patch:
                findings.append(f"{file_data.get('filename')}: potential secret in diff.")

        if not findings:
            return []

        comment = "Auto Review Findings:\n- " + "\n- ".join(findings)
        return [{"plugin": self.name, "action": "comment", "comment": comment}]
