#!/usr/bin/env python3
"""Plugin system for API webhook/event hooks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Iterable, Callable
import asyncio


@dataclass
class PluginResult:
    """Result from plugin execution."""
    success: bool
    action: str
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    plugin: str = ""


class BasePlugin:
    """Base class for all plugins."""
    
    name: str = "base_plugin"
    version: str = "1.0.0"
    triggers: List[str] = []
    enabled: bool = True
    
    def should_run(self, event: Dict[str, Any]) -> bool:
        """Check if plugin should run for this event."""
        return True
    
    def validate(self, context: Dict[str, Any]) -> bool:
        """Validate context before running."""
        return True
    
    def run(self, event: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Synchronous run method."""
        return []
    
    async def execute(self, context: Dict[str, Any]) -> PluginResult:
        """Async execution method."""
        return PluginResult(
            success=True,
            action="execute",
            message="Executed",
            plugin=self.name
        )
    
    def get_info(self) -> Dict[str, Any]:
        """Get plugin info."""
        return {
            "name": self.name,
            "version": self.version,
            "enabled": self.enabled,
            "triggers": self.triggers
        }
    
    def matches_trigger(self, trigger: str) -> bool:
        """Check if trigger matches."""
        if not self.triggers:
            return True
        return trigger in self.triggers


class PluginRegistry:
    """Global registry for managing plugins."""
    
    _plugins: Dict[str, BasePlugin] = {}
    _enabled: Dict[str, bool] = {}
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered plugins."""
        cls._plugins.clear()
        cls._enabled.clear()
    
    @classmethod
    def register(cls, plugin: BasePlugin, name: Optional[str] = None) -> None:
        """Register a plugin."""
        plugin_name = name or plugin.name
        cls._plugins[plugin_name] = plugin
        cls._enabled[plugin_name] = plugin.enabled
    
    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister a plugin."""
        if name in cls._plugins:
            del cls._plugins[name]
        if name in cls._enabled:
            del cls._enabled[name]
    
    @classmethod
    def get(cls, name: str) -> Optional[BasePlugin]:
        """Get a plugin by name."""
        return cls._plugins.get(name)
    
    @classmethod
    def enable(cls, name: str) -> None:
        """Enable a plugin."""
        cls._enabled[name] = True
        if name in cls._plugins:
            cls._plugins[name].enabled = True
    
    @classmethod
    def disable(cls, name: str) -> None:
        """Disable a plugin."""
        cls._enabled[name] = False
        if name in cls._plugins:
            cls._plugins[name].enabled = False
    
    @classmethod
    def is_enabled(cls, name: str) -> bool:
        """Check if plugin is enabled."""
        return cls._enabled.get(name, False)
    
    @classmethod
    def list_plugins(cls) -> List[str]:
        """List all registered plugins."""
        return list(cls._plugins.keys())
    
    @classmethod
    async def execute_all(cls, context: Dict[str, Any]) -> List[PluginResult]:
        """Execute all enabled plugins."""
        results = []
        for name, plugin in cls._plugins.items():
            if cls._enabled.get(name, False) and plugin.should_run(context):
                try:
                    result = await plugin.execute(context)
                    results.append(result)
                except Exception as e:
                    results.append(PluginResult(
                        success=False,
                        action="execute",
                        message=str(e),
                        plugin=name
                    ))
        return results


class PluginManager:
    """Simple plugin manager for running plugins."""
    
    def __init__(self, plugins: Iterable[BasePlugin] | None = None):
        self.plugins = list(plugins or [])
    
    def add_plugin(self, plugin: BasePlugin) -> None:
        """Add a plugin."""
        self.plugins.append(plugin)
    
    def remove_plugin(self, name: str) -> None:
        """Remove a plugin by name."""
        self.plugins = [p for p in self.plugins if p.name != name]
    
    def run_plugins(self, event: Dict[str, Any], context: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """Run all plugins."""
        context = context or {}
        outputs: List[Dict[str, Any]] = []
        for plugin in self.plugins:
            if plugin.enabled and plugin.should_run(event):
                outputs.extend(plugin.run(event, context))
        return outputs


# Alias for backward compatibility
PluginBase = BasePlugin
