#!/usr/bin/env python3
"""Plugin system for API webhook/event hooks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Iterable


@dataclass
class PluginResult:
    """Result from plugin execution."""
    success: bool
    action: str
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    plugin: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin": self.plugin,
            "action": self.action,
            "message": self.message,
            "data": self.data,
        }


class BasePlugin:
    """Base class for all plugins."""

    name: str = "base_plugin"
    version: str = "1.0.0"
    triggers: List[str] = []
    enabled: bool = True

    def should_run(self, event: Dict[str, Any]) -> bool:
        return True

    def validate(self, context: Dict[str, Any]) -> bool:
        return True

    def run(
        self,
        event: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        return []

    async def execute(self, context: Dict[str, Any]) -> PluginResult:
        return PluginResult(
            success=True,
            action="execute",
            message="Executed",
            plugin=self.name,
        )

    def matches_trigger(self, trigger: str) -> bool:
        if not self.triggers:
            return True
        return trigger in self.triggers

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "enabled": self.enabled,
            "triggers": self.triggers,
        }

    # Legacy compatibility alias
    def execute_legacy(
        self,
        event: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return self.run(event, context or {})


class PluginRegistry:
    """Global registry for managing plugins."""

    _plugins: Dict[str, BasePlugin] = {}
    _enabled: Dict[str, bool] = {}

    @classmethod
    def clear(cls) -> None:
        cls._plugins.clear()
        cls._enabled.clear()

    @classmethod
    def register(
        cls,
        plugin: BasePlugin,
        name: Optional[str] = None,
    ) -> None:
        plugin_name = name or plugin.name
        cls._plugins[plugin_name] = plugin
        cls._enabled[plugin_name] = plugin.enabled

    @classmethod
    def get(cls, name: str) -> Optional[BasePlugin]:
        return cls._plugins.get(name)

    @classmethod
    def enable(cls, name: str) -> None:
        cls._enabled[name] = True
        if name in cls._plugins:
            cls._plugins[name].enabled = True

    @classmethod
    def disable(cls, name: str) -> None:
        cls._enabled[name] = False
        if name in cls._plugins:
            cls._plugins[name].enabled = False

    @classmethod
    async def execute_all(
        cls,
        context: Dict[str, Any],
    ) -> List[PluginResult]:
        results = []

        for name, plugin in cls._plugins.items():
            if not cls._enabled.get(name, False):
                continue

            if not plugin.should_run(context):
                continue

            try:
                result = await plugin.execute(context)
                results.append(result)
            except Exception as exc:
                results.append(
                    PluginResult(
                        success=False,
                        action="execute",
                        message=str(exc),
                        plugin=name,
                    )
                )

        return results


class PluginManager:
    """Simple plugin manager for running plugins."""

    def __init__(
        self,
        plugins: Optional[Iterable[BasePlugin]] = None,
    ):
        self.plugins = list(plugins or [])

    def register(self, plugin: BasePlugin) -> None:
        self.plugins.append(plugin)

    def remove_plugin(self, name: str) -> None:
        self.plugins = [
            p for p in self.plugins
            if p.name != name
        ]

    def run_plugins(
        self,
        event: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        context = context or {}
        outputs: List[Dict[str, Any]] = []

        for plugin in self.plugins:
            if not plugin.enabled:
                continue

            if not plugin.should_run(event):
                continue

            try:
                outputs.extend(plugin.run(event, context))
            except Exception as exc:
                outputs.append(
                    PluginResult(
                        success=False,
                        action="error",
                        message=str(exc),
                        plugin=plugin.name,
                    ).to_dict()
                )

        return outputs


PluginBase = BasePlugin