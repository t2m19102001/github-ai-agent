#!/usr/bin/env python3
"""
Base Plugin Classes
Provides abstract base classes for agent plugins
"""

import os
import importlib
import pkgutil
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PluginConfig:
    """Plugin configuration"""
    name: str
    enabled: bool = True
    priority: int = 100
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginResult:
    """Result from plugin execution"""
    success: bool
    action: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class BasePlugin(ABC):
    """Abstract base class for all plugins"""
    
    name: str = "BasePlugin"
    version: str = "1.0.0"
    description: str = "Base plugin"
    triggers: List[str] = field(default_factory=list)
    
    def __init__(self, config: Optional[PluginConfig] = None):
        self.config = config or PluginConfig(name=self.name)
        self.name = self.config.name
        self.enabled = self.config.enabled
        self._initialized = False
        logger.info(f"Plugin initialized: {self.name}")
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> PluginResult:
        """Execute the plugin logic"""
        pass
    
    @abstractmethod
    def validate(self, context: Dict[str, Any]) -> bool:
        """Validate if plugin should run for given context"""
        pass
    
    def on_enable(self) -> None:
        """Called when plugin is enabled"""
        self._initialized = True
        logger.info(f"Plugin enabled: {self.name}")
    
    def on_disable(self) -> None:
        """Called when plugin is disabled"""
        self._initialized = False
        logger.info(f"Plugin disabled: {self.name}")
    
    def get_info(self) -> Dict[str, Any]:
        """Get plugin information"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "enabled": self.enabled,
            "priority": self.config.priority,
            "initialized": self._initialized,
            "class": self.__class__.__name__,
            "triggers": self.triggers
        }
    
    def matches_trigger(self, event_type: str) -> bool:
        """Check if event matches plugin triggers"""
        if not self.triggers:
            return True
        return event_type in self.triggers


class PluginRegistry:
    """Registry for managing plugins"""
    
    _plugins: Dict[str, BasePlugin] = {}
    _execution_order: List[str] = []
    
    @classmethod
    def register(cls, plugin: BasePlugin) -> None:
        """Register a plugin"""
        cls._plugins[plugin.name] = plugin
        if plugin.name not in cls._execution_order:
            cls._execution_order.append(plugin.name)
            cls._execution_order.sort(key=lambda p: cls._plugins[p].config.priority)
        logger.info(f"Registered plugin: {plugin.name}")
    
    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister a plugin"""
        if name in cls._plugins:
            del cls._plugins[name]
            if name in cls._execution_order:
                cls._execution_order.remove(name)
            logger.info(f"Unregistered plugin: {name}")
    
    @classmethod
    def get(cls, name: str) -> Optional[BasePlugin]:
        """Get a plugin by name"""
        return cls._plugins.get(name)
    
    @classmethod
    def get_all(cls) -> List[BasePlugin]:
        """Get all registered plugins"""
        return [cls._plugins[name] for name in cls._execution_order if name in cls._plugins]
    
    @classmethod
    def get_enabled(cls) -> List[BasePlugin]:
        """Get all enabled plugins"""
        return [p for p in cls.get_all() if p.enabled]
    
    @classmethod
    async def execute_all(cls, context: Dict[str, Any]) -> List[PluginResult]:
        """Execute all enabled plugins in order"""
        results = []
        for name in cls._execution_order:
            plugin = cls._plugins.get(name)
            if plugin and plugin.enabled and plugin.validate(context):
                try:
                    result = await plugin.execute(context)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Plugin {name} execution failed: {e}")
                    results.append(PluginResult(
                        success=False,
                        action=name,
                        message=str(e)
                    ))
        return results
    
    @classmethod
    async def execute_for_event(cls, event_type: str, context: Dict[str, Any]) -> List[PluginResult]:
        """Execute plugins matching the event type"""
        results = []
        for name in cls._execution_order:
            plugin = cls._plugins.get(name)
            if plugin and plugin.enabled and plugin.matches_trigger(event_type):
                if plugin.validate(context):
                    try:
                        result = await plugin.execute(context)
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Plugin {name} execution failed: {e}")
                        results.append(PluginResult(
                            success=False,
                            action=name,
                            message=str(e)
                        ))
        return results
    
    @classmethod
    def list_plugins(cls) -> List[Dict[str, Any]]:
        """List all registered plugins"""
        return [p.get_info() for p in cls.get_all()]
    
    @classmethod
    def enable(cls, name: str) -> bool:
        """Enable a plugin"""
        plugin = cls._plugins.get(name)
        if plugin:
            plugin.enabled = True
            plugin.on_enable()
            return True
        return False
    
    @classmethod
    def disable(cls, name: str) -> bool:
        """Disable a plugin"""
        plugin = cls._plugins.get(name)
        if plugin:
            plugin.enabled = False
            plugin.on_disable()
            return True
        return False
    
    @classmethod
    def load_from_package(cls, package_path: str) -> int:
        """Auto-discover and load plugins from a package"""
        loaded = 0
        try:
            package = importlib.import_module(package_path)
            for _, name, _ in pkgutil.iter_modules(package.__path__):
                if name.startswith("_"):
                    continue
                try:
                    module = importlib.import_module(f"{package_path}.{name}")
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr != BasePlugin:
                            cls.register(attr())
                            loaded += 1
                            logger.info(f"Auto-loaded plugin: {name}")
                except Exception as e:
                    logger.warning(f"Failed to load plugin {name}: {e}")
        except Exception as e:
            logger.error(f"Failed to load plugins from {package_path}: {e}")
        return loaded
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered plugins"""
        cls._plugins.clear()
        cls._execution_order.clear()
        logger.info("Cleared all plugins from registry")
