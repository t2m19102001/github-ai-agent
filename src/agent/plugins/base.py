#!/usr/bin/env python3
"""Simple plugin manager for API webhook/event hooks.

This module intentionally supports both legacy and current plugin contracts:
- `run(event, context)` (newer)
- `execute(event, context)` (legacy aliases found in older branches)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class PluginResult:
    plugin: str
    action: str
    comment: str

    def to_dict(self) -> Dict[str, str]:
        return {"plugin": self.plugin, "action": self.action, "comment": self.comment}


class PluginBase:
    name = "plugin_base"

    def should_run(self, event: Dict[str, Any]) -> bool:
        return True

    def run(self, event: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []

    # Legacy compatibility alias.
    def execute(self, event: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self.run(event, context or {})


class PluginManager:
    def __init__(self, plugins: Iterable[PluginBase] | None = None):
        self.plugins = list(plugins or [])

    def register(self, plugin: PluginBase) -> None:
        self.plugins.append(plugin)

    def run_plugins(self, event: Dict[str, Any], context: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        context = context or {}
        outputs: List[Dict[str, Any]] = []
        for plugin in self.plugins:
            if plugin.should_run(event):
                try:
                    outputs.extend(plugin.run(event, context))
                except Exception as exc:
                    outputs.append(
                        PluginResult(
                            plugin=getattr(plugin, "name", plugin.__class__.__name__),
                            action="error",
                            comment=f"Plugin error: {exc}",
                        ).to_dict()
                    )
        return outputs
