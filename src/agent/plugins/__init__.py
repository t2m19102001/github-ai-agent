"""
Agent plugins package
Provides extensibility through plugin system
"""

from src.agent.plugins.base import BasePlugin, PluginConfig, PluginResult, PluginRegistry
from src.agent.plugins.manager import PluginManager, get_plugin_manager

__all__ = [
    "BasePlugin",
    "PluginConfig",
    "PluginResult", 
    "PluginRegistry",
    "PluginManager",
    "get_plugin_manager"
]
