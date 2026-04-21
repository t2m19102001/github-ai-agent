#!/usr/bin/env python3
"""Basic smoke tests for GitHub AI Agent."""

import sys
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestConfig:
    """Test configuration imports and basic shape."""

    def test_config_loads(self):
        from src.core.config import DEBUG, GITHUB_TOKEN, REPO_FULL_NAME

        assert isinstance(DEBUG, bool)
        assert GITHUB_TOKEN is None or isinstance(GITHUB_TOKEN, str)
        assert REPO_FULL_NAME is None or isinstance(REPO_FULL_NAME, str)

    def test_groq_configured_shape(self):
        from src.core.config import GROQ_API_KEY

        assert GROQ_API_KEY is None or isinstance(GROQ_API_KEY, str)


class TestLLM:
    """Test LLM providers."""

    def test_mock_provider_creates(self):
        from src.llm.provider import get_llm_provider

        provider = get_llm_provider("mock")
        status = provider.get_status()
        assert status["name"] == "mock"

    def test_groq_provider_import_optional(self):
        requests = pytest.importorskip("requests")
        assert requests is not None
        from src.llm.groq import GroqProvider

        provider = GroqProvider()
        assert provider.name == "GROQ"


class TestAgents:
    """Test agent implementations."""

    def test_code_agent_creates(self):
        from src.plugins.code_agent import CodeChatAgent
        from src.llm.provider import get_llm_provider

        llm = get_llm_provider("mock")
        agent = CodeChatAgent(llm_provider=llm)

        assert agent.name == "CodeChat"
        assert len(agent.tools) > 0


class TestTools:
    """Test file tools."""

    def test_file_list_tool(self):
        from src.tools.file_tools import ListFilesTool

        tool = ListFilesTool()
        files = tool.execute("src", "*.py")
        assert isinstance(files, list)

    def test_file_read_tool(self):
        from src.tools.file_tools import FileReadTool

        tool = FileReadTool()
        content = tool.execute("src/core/config.py")
        assert content is not None
        assert len(content) > 0


class TestExecutors:
    """Test code executors."""

    def test_python_executor(self):
        from src.tools.executors import PythonExecutor

        executor = PythonExecutor()
        result = executor.execute("print('Hello')")
        assert result["success"] is True
        assert "Hello" in result["output"]

    def test_python_executor_error(self):
        from src.tools.executors import PythonExecutor

        executor = PythonExecutor()
        result = executor.execute("raise ValueError('Test error')")
        assert result["success"] is False
        assert len(result["error"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
