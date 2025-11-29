#!/usr/bin/env python3
"""
Unit tests for GitHub AI Agent
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestConfig:
    """Test configuration"""
    
    def test_config_loads(self):
        """Test that config loads without error"""
        from src.core.config import DEBUG, GITHUB_TOKEN, REPO_FULL_NAME
        assert GITHUB_TOKEN is not None
        assert REPO_FULL_NAME is not None
    
    def test_groq_configured(self):
        """Test GROQ API key is configured"""
        from src.core.config import GROQ_API_KEY
        assert GROQ_API_KEY is not None


class TestLLM:
    """Test LLM providers"""
    
    def test_groq_provider_creates(self):
        """Test GROQ provider initializes"""
        from src.llm.groq import GroqProvider
        provider = GroqProvider()
        assert provider.name == "GROQ"
        assert provider.model is not None
    
    def test_groq_has_api_key(self):
        """Test GROQ has API key"""
        from src.llm.groq import GroqProvider
        provider = GroqProvider()
        assert provider.api_key is not None


class TestAgents:
    """Test agent implementations"""
    
    def test_code_agent_creates(self):
        """Test CodeChatAgent initializes"""
        from src.agents.code_agent import CodeChatAgent
        from src.llm.groq import GroqProvider
        
        llm = GroqProvider()
        agent = CodeChatAgent(llm_provider=llm)
        
        assert agent.name == "CodeChat"
        assert len(agent.tools) > 0
        assert len(agent.project_files) > 0


class TestTools:
    """Test tools"""
    
    def test_file_list_tool(self):
        """Test file listing tool"""
        from src.tools.tools import ListFilesTool
        tool = ListFilesTool()
        files = tool.execute()
        assert isinstance(files, list)
        assert len(files) > 0
    
    def test_file_read_tool(self):
        """Test file reading tool"""
        from src.tools.tools import FileReadTool
        tool = FileReadTool()
        content = tool.execute("src/core/config.py")
        assert content is not None
        assert len(content) > 0


class TestExecutors:
    """Test code executors"""
    
    def test_python_executor(self):
        """Test Python code executor"""
        from src.tools.executors import PythonExecutor
        executor = PythonExecutor()
        
        result = executor.execute("print('Hello')")
        assert result['success'] == True
        assert "Hello" in result['output']
    
    def test_python_executor_error(self):
        """Test Python executor error handling"""
        from src.tools.executors import PythonExecutor
        executor = PythonExecutor()
        
        result = executor.execute("raise ValueError('Test error')")
        assert result['success'] == False
        assert len(result['error']) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
