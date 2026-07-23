"""Read-only tools the local agent can call during a tool-calling loop."""

from src.local_agent.tools.base import Tool, ToolRegistry, ToolResult
from src.local_agent.tools.file_reader import FileReaderTool

__all__ = ["FileReaderTool", "Tool", "ToolRegistry", "ToolResult"]
