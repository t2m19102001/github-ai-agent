#!/usr/bin/env python3
"""
Plugin Manager
Manages plugin lifecycle and integration with agents
"""

import os
from typing import Dict, Any, List, Optional
from src.plugins.plugins import BasePlugin, PluginRegistry, PluginResult

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class PluginManager:
    """Manages plugin lifecycle and integration"""
    
    def __init__(self):
        self._enabled_plugins: List[str] = []
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}
        self._load_configs()
        self._initialize_plugins()
    
    def _load_configs(self) -> None:
        """Load plugin configurations from environment"""
        plugins_env = os.getenv("AGENT_PLUGINS", "")
        if plugins_env:
            self._enabled_plugins = [p.strip() for p in plugins_env.split(",") if p.strip()]
        
        if not self._enabled_plugins:
            self._enabled_plugins = [
                "auto_comment_on_issue",
                "auto_check_code_quality",
                "auto_label_issue",
                "auto_assign_reviewer"
            ]
        
        logger.info(f"PluginManager loaded {len(self._enabled_plugins)} enabled plugins")
    
    def _initialize_plugins(self) -> None:
        """Initialize all plugins"""
        PluginRegistry.clear()
        
        plugin_classes = {
            "auto_comment_on_issue": "src.agent.plugins.auto_comment_on_issue",
            "auto_check_code_quality": "src.agent.plugins.auto_check_code_quality",
            "auto_label_issue": "src.agent.plugins.auto_label_issue",
            "auto_assign_reviewer": "src.agent.plugins.auto_assign_reviewer",
        }
        
        for plugin_name in self._enabled_plugins:
            if plugin_name in plugin_classes:
                try:
                    module_path = plugin_classes[plugin_name]
                    from importlib import import_module
                    module = import_module(module_path)
                    
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr != BasePlugin:
                            plugin = attr()
                            PluginRegistry.register(plugin)
                            logger.info(f"Initialized plugin: {plugin_name}")
                except Exception as e:
                    logger.error(f"Failed to initialize plugin {plugin_name}: {e}")
    
    async def handle_event(self, event_type: str, event_data: Dict[str, Any]) -> List[PluginResult]:
        """Handle an event and execute relevant plugins"""
        logger.info(f"Handling event: {event_type}")
        results = await PluginRegistry.execute_for_event(event_type, event_data)
        
        for result in results:
            if result.success:
                logger.info(f"Plugin {result.action} succeeded: {result.message}")
            else:
                logger.warning(f"Plugin {result.action} failed: {result.message}")
        
        return results
    
    async def on_issue_opened(self, issue: Dict[str, Any], github_client=None) -> List[PluginResult]:
        """Handle issue opened event"""
        context = {
            "issue": issue,
            "github_client": github_client,
            "event": "issue.opened"
        }
        return await self.handle_event("issue.opened", context)
    
    async def on_pr_opened(self, pr: Dict[str, Any], files: List[str] = None, github_client=None) -> List[PluginResult]:
        """Handle PR opened event"""
        context = {
            "pull_request": pr,
            "files_changed": files or [],
            "github_client": github_client,
            "event": "pull_request.opened"
        }
        return await self.handle_event("pull_request.opened", context)
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all available plugins"""
        return PluginRegistry.list_plugins()
    
    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin"""
        return PluginRegistry.enable(name)
    
    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin"""
        return PluginRegistry.disable(name)
    
    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Get a plugin by name"""
        return PluginRegistry.get(name)


_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get global plugin manager instance"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


__all__ = [
    "PluginManager",
    "get_plugin_manager",
    "BasePlugin",
    "PluginRegistry",
    "PluginResult"
]
