# Plugin Guide

## Overview
Plugins extend AI Agent workflows (PR review, issues, commands) without touching core logic. Each plugin implements `AgentPluginBase` with `matches(event)` and `run(event, context)`.

## Base Interface
`src/agent/plugins/base.py`
- `matches(event) -> bool`: decide if plugin should run for the event.
- `run(event, context) -> Dict`: perform action; return structured result like `{ action: "comment", comment: "..." }`.

## Examples
- `auto_check_code_quality`: analyzes added code in PR labeled `bug` and returns a comment report.
- `auto_comment_on_issue`: auto-replies on issues labeled `question` or `discussion`.
- `auto_create_pr`: scaffolds branch/commit on `command` event.

## Enabling Plugins
Set env `AGENT_PLUGINS` to comma-separated list:
```
AGENT_PLUGINS=auto_check_code_quality,auto_comment_on_issue
```
If unset, `auto_check_code_quality` is enabled by default in PR Agent.

## Event Schema
Common fields:
- `type`: `pr` | `issue` | `command`
- `labels`: list of strings
- `files_data`: PR files with `filename`, `patch`
- `command`: for command events

## Integration
PR Agent calls plugins after analysis and posts any `comment` results.

## Write Your Plugin
1. Create file in `src/agent/plugins/your_plugin.py`.
2. Implement class extending `AgentPluginBase`.
3. Add to registry (via env `AGENT_PLUGINS`).
4. Write tests under `tests/`.

## Testing
Use `PluginManager` to run plugins on synthetic events:
```python
mgr = PluginManager([YourPlugin()])
res = mgr.run_plugins({"type":"pr","labels":["bug"],"files_data":[]}, {})
```

