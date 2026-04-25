#!/usr/bin/env python3
"""PR code quality check plugin."""

from __future__ import annotations

from typing import Any, Dict, List

from .base import BasePlugin, PluginResult


class AutoCheckCodeQualityPlugin(BasePlugin):
    name = "auto_check_code_quality"
    version = "1.0.0"
    triggers = ["pr.opened", "pr.updated"]

    def should_run(self, event: Dict[str, Any]) -> bool:
        event_type = (event.get("type") or "").lower()
        return event_type in {"pr", "pull_request"}

    def validate(self, context: Dict[str, Any]) -> bool:
        return "pull_request" in context or "code_diff" in context

    def run(
        self,
        event: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        findings: List[str] = []
        files_data = context.get("code_diff", [])

        for file_data in files_data:
            patch = (file_data.get("patch") or "").lower()
            filename = file_data.get("filename", "unknown")

            if "eval(" in patch:
                findings.append(f"{filename}: avoid eval().")

            if "password" in patch or "api_key" in patch:
                findings.append(f"{filename}: potential secret in diff.")

            if "console.log" in patch:
                findings.append(
                    f"{filename}: remove console.log before production."
                )

        if not findings:
            return []

        comment = "Auto Review Findings:\n- " + "\n- ".join(findings)

        return [
            {
                "plugin": self.name,
                "action": "comment",
                "comment": comment,
            }
        ]

    async def execute(self, context: Dict[str, Any]) -> PluginResult:
        """Async execution for new plugin system."""
        if not self.validate(context):
            return PluginResult(
                success=False,
                action="validate",
                message="Invalid context for code quality check",
                plugin=self.name,
            )

        findings: List[str] = []
        files_data = context.get("code_diff", [])

        for file_data in files_data:
            patch = (file_data.get("patch") or "").lower()
            filename = file_data.get("filename", "unknown")

            if "eval(" in patch:
                findings.append(f"{filename}: avoid eval()")

            if "password" in patch or "api_key" in patch:
                findings.append(f"{filename}: potential secret in code")

            if "console.log" in patch:
                findings.append(
                    f"{filename}: remove console.log before production"
                )

        return PluginResult(
            success=True,
            action="code_review",
            message=(
                f"Found {len(findings)} issues"
                if findings
                else "No issues found"
            ),
            data={"findings": findings},
            plugin=self.name,
        )