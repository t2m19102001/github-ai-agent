#!/usr/bin/env python3
"""
Unit tests cho Advanced AI-Agent Framework
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from src.agents.advanced_agent import (
    AgentProfile, MemoryStore, PlanningEngine, Tool, CodeExecutorTool,
    FileOperationsTool, APICallTool, ToolKit, AdvancedAIAgent
)


# ============================================================================
# Tests cho AgentProfile
# ============================================================================

class TestAgentProfile:
    """Test các chức năng của AgentProfile"""
    
    def test_profile_creation(self):
        """Test tạo AgentProfile"""
        profile = AgentProfile(
            name="TestAgent",
            role="Test Role",
            expertise=["Python", "Testing"],
            personality="Thorough",
            system_prompt=""
        )
        
        assert profile.name == "TestAgent"
        assert profile.role == "Test Role"
        assert "Python" in profile.expertise
        assert profile.personality == "Thorough"
    
    def test_system_instruction_generation(self):
        """Test tạo system instruction"""
        profile = AgentProfile(
            name="PyMaster",
            role="Python Developer",
            expertise=["Python", "Django"],
            personality="Helpful",
            system_prompt=""
        )
        
        instruction = profile.get_system_instruction()
        
        assert isinstance(instruction, str)
        assert len(instruction) > 0
        assert "PyMaster" in instruction or "Python" in instruction
    
    def test_profile_with_custom_prompt(self):
        """Test profile với custom system prompt"""
        custom_prompt = "You are a custom agent"
        profile = AgentProfile(
            name="Custom",
            role="Role",
            expertise=[],
            personality="",
            system_prompt=custom_prompt
        )
        
        instruction = profile.get_system_instruction()
        assert custom_prompt in instruction


# ============================================================================
# Tests cho MemoryStore
# ============================================================================

class TestMemoryStore:
    """Test chức năng Memory Store"""
    
    def test_short_term_memory_add(self):
        """Test thêm vào short-term memory"""
        memory = MemoryStore()
        memory.add_to_short_term("user", "Hello agent")
        
        assert len(memory.short_term_memory) == 1
        assert memory.short_term_memory[0]["role"] == "user"
        assert memory.short_term_memory[0]["content"] == "Hello agent"
    
    def test_short_term_memory_auto_trim(self):
        """Test auto-trim short-term memory"""
        memory = MemoryStore(max_context_messages=5)
        
        # Thêm 10 messages
        for i in range(10):
            memory.add_to_short_term("user", f"Message {i}")
        
        # Chỉ giữ 5 messages mới nhất
        assert len(memory.short_term_memory) <= 5
    
    def test_long_term_memory_add(self):
        """Test thêm vào long-term memory"""
        memory = MemoryStore()
        memory.add_to_long_term("Python tips", {"topic": "strings"})
        
        assert len(memory.long_term_memory) == 1
        assert memory.long_term_memory[0]["knowledge"] == "Python tips"
    
    def test_retrieve_context(self):
        """Test retrieve conversation context"""
        memory = MemoryStore()
        memory.add_to_short_term("user", "What is Python?")
        memory.add_to_short_term("assistant", "Python is...")
        
        context = memory.retrieve_context()
        
        assert len(context) > 0
        assert isinstance(context, str)
        assert "Python" in context
    
    def test_search_knowledge(self):
        """Test search long-term knowledge"""
        memory = MemoryStore()
        memory.add_to_long_term("Python is a programming language")
        memory.add_to_long_term("Django is a web framework")
        
        results = memory.search_knowledge("Python", top_k=1)
        
        assert len(results) > 0
        assert "Python" in results[0]
    
    def test_memory_stats(self):
        """Test lấy statistics"""
        memory = MemoryStore()
        memory.add_to_short_term("user", "Hello")
        memory.add_to_long_term("Knowledge item")
        
        stats = memory.get_memory_stats()
        
        assert "short_term_messages" in stats
        assert "long_term_knowledge" in stats
        assert stats["short_term_messages"] == 1
        assert stats["long_term_knowledge"] == 1


# ============================================================================
# Tests cho PlanningEngine
# ============================================================================

class TestPlanningEngine:
    """Test chức năng Planning Engine"""
    
    def test_engine_creation(self):
        """Test tạo PlanningEngine"""
        engine = PlanningEngine()
        assert engine is not None
    
    @patch('src.agents.advanced_agent.call_llm')
    def test_decompose_goal(self, mock_llm):
        """Test decompose goal"""
        mock_llm.return_value = """
        1. Analyze requirements
        2. Design architecture
        3. Implement features
        4. Test thoroughly
        """
        
        engine = PlanningEngine()
        steps = engine.decompose_goal("Build a web app", "test_provider")
        
        assert len(steps) > 0
        assert all(isinstance(step, str) for step in steps)
    
    @patch('src.agents.advanced_agent.call_llm')
    def test_chain_of_thought(self, mock_llm):
        """Test chain of thought reasoning"""
        mock_llm.return_value = "Step 1: ...\nStep 2: ...\nConclusion: ..."
        
        engine = PlanningEngine()
        reasoning = engine.chain_of_thought("How to optimize code?", "test_provider")
        
        assert len(reasoning) > 0
        assert isinstance(reasoning, str)
    
    @patch('src.agents.advanced_agent.call_llm')
    def test_self_reflection(self, mock_llm):
        """Test self reflection"""
        mock_llm.return_value = "Improvements: ...\nStrengths: ...\nWeaknesses: ..."
        
        engine = PlanningEngine()
        reflection = engine.self_reflection(
            "My solution is X",
            "Problem Y",
            "test_provider"
        )
        
        assert len(reflection) > 0


# ============================================================================
# Tests cho Tools
# ============================================================================

class TestCodeExecutorTool:
    """Test CodeExecutorTool"""
    
    def test_tool_initialization(self):
        """Test init code executor"""
        tool = CodeExecutorTool()
        assert tool.name == "code_executor"
    
    def test_execute_valid_code(self):
        """Test execute valid Python code"""
        tool = CodeExecutorTool()
        result = tool.execute(code="x = 2 + 2\nprint(x)")
        
        assert result["status"] == "success"
        assert result["output"] == "4\n"
        assert result["return_code"] == 0
    
    def test_execute_code_with_error(self):
        """Test execute code với error"""
        tool = CodeExecutorTool()
        result = tool.execute(code="print(undefined_variable)")
        
        assert result["status"] == "error" or result["return_code"] != 0
        assert len(result.get("error", "")) > 0 or result["status"] == "error"


class TestFileOperationsTool:
    """Test FileOperationsTool"""
    
    def test_tool_initialization(self):
        """Test init file operations tool"""
        tool = FileOperationsTool()
        assert tool.name == "file_operations"
    
    @patch('builtins.open', create=True)
    def test_read_file(self, mock_open):
        """Test read file operation"""
        mock_open.return_value.__enter__.return_value.read.return_value = "content"
        
        tool = FileOperationsTool()
        result = tool.execute(operation="read", path="/test.txt")
        
        assert "content" in result["result"] or len(result) > 0


class TestToolKit:
    """Test ToolKit manager"""
    
    def test_toolkit_register_tool(self):
        """Test register tool"""
        toolkit = ToolKit()
        tool = CodeExecutorTool()
        
        toolkit.register_tool(tool)
        assert "code_executor" in toolkit.tools
    
    def test_toolkit_get_tool(self):
        """Test get registered tool"""
        toolkit = ToolKit()
        tool = CodeExecutorTool()
        toolkit.register_tool(tool)
        
        retrieved = toolkit.get_tool("code_executor")
        assert retrieved is not None
        assert retrieved.name == "code_executor"
    
    def test_toolkit_list_tools(self):
        """Test list available tools"""
        toolkit = ToolKit()
        toolkit.register_tool(CodeExecutorTool())
        toolkit.register_tool(FileOperationsTool())
        
        tools = toolkit.list_tools()
        assert "code_executor" in tools
        assert "file_operations" in tools


# ============================================================================
# Tests cho AdvancedAIAgent
# ============================================================================

class TestAdvancedAIAgent:
    """Test AdvancedAIAgent integration"""
    
    def test_agent_creation(self):
        """Test create agent"""
        profile = AgentProfile("Test", "Role", [], "", "")
        agent = AdvancedAIAgent(profile, "test_provider")
        
        assert agent.profile.name == "Test"
        assert agent.llm_provider == "test_provider"
    
    @patch('src.agents.advanced_agent.call_llm')
    def test_chat_with_message(self, mock_llm):
        """Test chat method"""
        mock_llm.return_value = "Response from LLM"
        
        profile = AgentProfile("Test", "Role", [], "", "")
        agent = AdvancedAIAgent(profile, "test_provider")
        
        response = agent.chat("Hello agent", "test_provider")
        
        assert len(response) > 0
    
    def test_get_agent_status(self):
        """Test get agent status"""
        profile = AgentProfile("Test", "Role", ["Python"], "Helpful", "")
        agent = AdvancedAIAgent(profile, "test_provider")
        
        status = agent.get_agent_status()
        
        assert "name" in status
        assert "role" in status
        assert "expertise" in status
        assert status["name"] == "Test"
    
    @patch('src.agents.advanced_agent.call_llm')
    def test_execute_with_planning(self, mock_llm):
        """Test execute with planning"""
        mock_llm.return_value = "1. Step 1\n2. Step 2"
        
        profile = AgentProfile("Test", "Role", [], "", "")
        agent = AdvancedAIAgent(profile, "test_provider")
        
        result = agent.execute_with_planning("Complex task", "test_provider")
        
        assert len(result) > 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for full workflows"""
    
    @patch('src.agents.advanced_agent.call_llm')
    def test_complete_agent_workflow(self, mock_llm):
        """Test complete agent workflow"""
        mock_llm.return_value = "Agent response"
        
        # Create agent
        profile = AgentProfile(
            name="IntegrationTest",
            role="Test Role",
            expertise=["Testing"],
            personality="Thorough",
            system_prompt=""
        )
        agent = AdvancedAIAgent(profile, "test_provider")
        
        # Chat
        response = agent.chat("Test message", "test_provider")
        
        # Check memory
        stats = agent.memory.get_memory_stats()
        
        assert len(response) > 0
        assert stats["short_term_count"] > 0
    
    def test_multiple_agents_independent_memory(self):
        """Test multiple agents have independent memory"""
        profile1 = AgentProfile("Agent1", "Role1", [], "", "")
        profile2 = AgentProfile("Agent2", "Role2", [], "", "")
        
        agent1 = AdvancedAIAgent(profile1, "test_provider")
        agent2 = AdvancedAIAgent(profile2, "test_provider")
        
        # Add to agent1 memory
        agent1.memory.add_to_short_term("user", "Message for agent1")
        
        # Check agent2 memory is empty
        stats2 = agent2.memory.get_memory_stats()
        
        assert stats2["short_term_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
