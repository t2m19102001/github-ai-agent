#!/usr/bin/env python3
"""Simple plugin manager for API webhook/event hooks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List


@dataclass
class PluginResult:
    plugin: str
    action: str
    comment: str


class PluginBase:
    name = "plugin_base"

    def should_run(self, event: Dict[str, Any]) -> bool:
        return True

    def run(self, event: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []


class PluginManager:
    def __init__(self, plugins: Iterable[PluginBase] | None = None):
        self.plugins = list(plugins or [])

    def run_plugins(self, event: Dict[str, Any], context: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        context = context or {}
        outputs: List[Dict[str, Any]] = []
        for plugin in self.plugins:
            if plugin.should_run(event):
                outputs.extend(plugin.run(event, context))
        return outputs
