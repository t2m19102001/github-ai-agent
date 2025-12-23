#!/usr/bin/env python3
from src.agent.plugins.base import PluginManager
from src.agent.plugins.auto_check_code_quality import AutoCheckCodeQualityPlugin
from src.agent.plugins.auto_comment_on_issue import AutoCommentOnIssuePlugin


def test_quality_plugin_comment_generated():
    mgr = PluginManager([AutoCheckCodeQualityPlugin()])
    event = {
        "type": "pr",
        "labels": ["bug"],
        "files_data": [
            {
                "filename": "app.py",
                "patch": "+ print('hello')\n+ eval('x')\n+ def a():\n+    pass\n",
            }
        ],
    }
    res = mgr.run_plugins(event, {})
    assert len(res) >= 1
    assert any(r.get("action") == "comment" for r in res)


def test_issue_auto_comment():
    mgr = PluginManager([AutoCommentOnIssuePlugin()])
    event = {"type": "issue", "labels": ["question"], "title": "How to run?"}
    res = mgr.run_plugins(event, {})
    assert len(res) == 1
    assert res[0]["plugin"] == "auto_comment_on_issue"
    assert "Auto Reply" in res[0]["comment"]

