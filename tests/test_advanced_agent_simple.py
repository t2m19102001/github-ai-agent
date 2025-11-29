#!/usr/bin/env python3
"""
Simplified unit tests cho Advanced AI-Agent Framework
Focused on core functionality
"""

import pytest
from src.agents.advanced_agent import (
    AgentProfile, MemoryStore, CodeExecutorTool, FileOperationsTool,
    ToolKit, AdvancedAIAgent
)


class TestAgentProfileCore:
    """Test AgentProfile core functionality"""
    
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


class TestMemoryStoreCore:
    """Test MemoryStore core functionality"""
    
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


class TestToolsCore:
    """Test Tool implementations"""
    
    def test_code_executor_initialization(self):
        """Test init code executor"""
        tool = CodeExecutorTool()
        assert tool.name == "code_executor"
    
    def test_code_executor_valid_code(self):
        """Test execute valid Python code"""
        tool = CodeExecutorTool()
        result = tool.execute(code="x = 2 + 2\nprint(x)")
        
        assert result["status"] == "success"
        assert result["output"] == "4\n"
        assert result["return_code"] == 0
    
    def test_code_executor_error_handling(self):
        """Test execute code với error"""
        tool = CodeExecutorTool()
        result = tool.execute(code="print(undefined_variable)")
        
        # Should either have error or non-zero return code
        assert result["status"] == "error" or result["return_code"] != 0
    
    def test_file_operations_tool(self):
        """Test FileOperationsTool initialization"""
        tool = FileOperationsTool()
        assert tool.name == "file_operations"
    
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


class TestAdvancedAIAgentCore:
    """Test AdvancedAIAgent core functionality"""
    
    def test_agent_creation(self):
        """Test create agent"""
        profile = AgentProfile("Test", "Role", [], "", "")
        agent = AdvancedAIAgent(profile, "test_provider")
        
        assert agent.profile.name == "Test"
        assert agent.llm_provider == "test_provider"
    
    def test_agent_has_memory(self):
        """Test agent has memory system"""
        profile = AgentProfile("Test", "Role", [], "", "")
        agent = AdvancedAIAgent(profile, "test_provider")
        
        assert hasattr(agent, 'memory')
        assert isinstance(agent.memory, MemoryStore)
    
    def test_agent_has_tools(self):
        """Test agent has tools"""
        profile = AgentProfile("Test", "Role", [], "", "")
        agent = AdvancedAIAgent(profile, "test_provider")
        
        assert hasattr(agent, 'toolkit')
        assert isinstance(agent.toolkit, ToolKit)
    
    def test_agent_status_format(self):
        """Test get agent status format"""
        profile = AgentProfile("Test", "Role", ["Python"], "Helpful", "")
        agent = AdvancedAIAgent(profile, "test_provider")
        
        status = agent.get_agent_status()
        
        assert "agent_name" in status
        assert "agent_role" in status
        assert "expertise" in status
        assert status["agent_name"] == "Test"


class TestIntegration:
    """Integration tests for complete workflows"""
    
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
        
        assert stats2["short_term_messages"] == 0
    
    def test_toolkit_with_multiple_tools(self):
        """Test toolkit with multiple tools"""
        toolkit = ToolKit()
        toolkit.register_tool(CodeExecutorTool())
        toolkit.register_tool(FileOperationsTool())
        
        tools = toolkit.list_tools()
        
        # list_tools returns list of dict with name, description
        tool_names = [t["name"] for t in tools]
        assert "code_executor" in tool_names
        assert "file_operations" in tool_names
        assert len(tools) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
