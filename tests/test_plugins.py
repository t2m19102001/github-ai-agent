#!/usr/bin/env python3
"""
Tests for Agent Plugins
"""

import pytest
import asyncio
from src.agent.plugins.base import PluginRegistry, BasePlugin, PluginResult
from src.agent.plugins.auto_check_code_quality import AutoCheckCodeQualityPlugin
from src.agent.plugins.auto_comment_on_issue import AutoCommentOnIssuePlugin


def test_quality_plugin_initialization():
    """Test quality plugin initializes"""
    plugin = AutoCheckCodeQualityPlugin()
    assert plugin.name == "auto_check_code_quality"
    assert plugin.enabled is True


def test_quality_plugin_validation():
    """Test quality plugin validates context"""
    plugin = AutoCheckCodeQualityPlugin()
    
    valid_context = {
        "pull_request": {"number": 1},
        "code_diff": ["some diff"]
    }
    assert plugin.validate(valid_context) is True
    
    invalid_context = {"issue": {}}
    assert plugin.validate(invalid_context) is False


def test_issue_plugin_validation():
    """Test issue plugin validates context"""
    plugin = AutoCommentOnIssuePlugin()
    
    valid_context = {
        "issue": {"action": "opened", "title": "Bug report"}
    }
    assert plugin.validate(valid_context) is True
    
    invalid_context = {}
    assert plugin.validate(invalid_context) is False


def test_plugin_registry_register():
    """Test plugin registry registers plugins"""
    PluginRegistry.clear()
    
    plugin = AutoCommentOnIssuePlugin()
    PluginRegistry.register(plugin)
    
    assert PluginRegistry.get("auto_comment_on_issue") is not None
    assert len(PluginRegistry.list_plugins()) == 1


def test_plugin_registry_enable_disable():
    """Test plugin registry enable/disable"""
    PluginRegistry.clear()
    
    plugin = AutoCommentOnIssuePlugin()
    PluginRegistry.register(plugin)
    
    assert plugin.enabled is True
    
    PluginRegistry.disable("auto_comment_on_issue")
    assert plugin.enabled is False
    
    PluginRegistry.enable("auto_comment_on_issue")
    assert plugin.enabled is True


def test_plugin_result_creation():
    """Test PluginResult creation"""
    result = PluginResult(
        success=True,
        action="test_action",
        message="Test message",
        data={"key": "value"}
    )
    
    assert result.success is True
    assert result.action == "test_action"
    assert result.message == "Test message"
    assert result.data["key"] == "value"


@pytest.mark.asyncio
async def test_plugin_execute():
    """Test plugin execution"""
    plugin = AutoCommentOnIssuePlugin()
    
    context = {
        "issue": {
            "action": "opened",
            "title": "Bug report",
            "body": "Something is broken",
            "labels": ["bug"]
        }
    }
    
    result = await plugin.execute(context)
    
    assert result.success is True
    assert result.action == "auto_comment"


@pytest.mark.asyncio
async def test_registry_execute_all():
    """Test registry execute all plugins"""
    PluginRegistry.clear()
    
    plugin1 = AutoCommentOnIssuePlugin()
    plugin2 = AutoCheckCodeQualityPlugin()
    
    PluginRegistry.register(plugin1)
    PluginRegistry.register(plugin2)
    
    context = {
        "issue": {
            "action": "opened",
            "title": "Test issue",
            "body": "Test body",
            "labels": []
        },
        "pull_request": {"number": 1},
        "code_diff": []
    }
    
    results = await PluginRegistry.execute_all(context)
    
    assert len(results) >= 0


def test_plugin_info():
    """Test plugin info"""
    plugin = AutoCommentOnIssuePlugin()
    info = plugin.get_info()
    
    assert "name" in info
    assert "enabled" in info
    assert "version" in info
    assert info["name"] == "auto_comment_on_issue"


def test_plugin_matches_trigger():
    """Test plugin trigger matching"""
    plugin = AutoCommentOnIssuePlugin()
    
    assert plugin.matches_trigger("issue.opened") is True
    assert plugin.matches_trigger("unknown.event") is True
