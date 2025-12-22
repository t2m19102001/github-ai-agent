
import sys
import os
import unittest
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.code_agent import CodeChatAgent
from src.config.settings import LLMProvider
from src.utils.token_manager import TokenManager

class TestChanges(unittest.TestCase):
    def test_token_manager(self):
        tm = TokenManager()
        text = "Hello world"
        tokens = tm.count_tokens(text)
        self.assertTrue(tokens > 0)
        
        long_text = "a " * 100
        truncated = tm.truncate_text(long_text, 10)
        self.assertTrue(len(tm.encoding.encode(truncated)) <= 15) # approximate check due to "..."
        
    def test_code_agent_init(self):
        mock_llm = MagicMock()
        mock_llm.call.return_value = "Mock response"
        
        agent = CodeChatAgent(llm_provider=mock_llm)
        self.assertIsInstance(agent.token_manager, TokenManager)
        
        # Test chat flow (mocked)
        response = agent.chat("Hello")
        self.assertEqual(response, "Mock response")
        
if __name__ == "__main__":
    unittest.main()
