"""Read-only tools the local agent can call during a tool-calling loop."""

from src.local_agent.tools.base import Tool, ToolRegistry, ToolResult, is_within
from src.local_agent.tools.code_query import CodeQueryTool
from src.local_agent.tools.file_reader import FileReaderTool
from src.local_agent.tools.git_reader import GitReaderTool
from src.local_agent.tools.list_files import ListFilesTool

__all__ = [
    "CodeQueryTool",
    "FileReaderTool",
    "GitReaderTool",
    "ListFilesTool",
    "Tool",
    "ToolRegistry",
    "ToolResult",
    "is_within",
]
