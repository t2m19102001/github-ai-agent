#!/usr/bin/env python3
"""
Tests for RAG integration with multi-agent workflow
"""

import pytest
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from src.rag.llamaindex_adapter import LlamaIndexRAG, initialize_rag, get_rag_instance, query_rag


class TestLlamaIndexRAG:
    """Test RAG functionality"""
    
    def setup_method(self):
        self.rag = LlamaIndexRAG("/tmp/test-index")
    
    def test_rag_initialization(self):
        """Test RAG initialization"""
        assert self.rag.index_path == Path("/tmp/test-index")
        assert self.rag.index is None
        assert self.rag.query_engine is None
        assert len(self.rag.query_times) == 0
        assert self.rag.total_queries == 0
    
    def test_build_simple_index_success(self):
        """Test building simple index"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def hello():\n    return 'world'")
            
            result = self.rag.build_index([temp_dir])
            
            assert result["backend"] == "simple"  # Fallback mode
            assert result["documents_count"] > 0
            assert "build_time" in result
            assert result["build_time"] > 0
    
    def test_build_index_empty_directory(self):
        """Test building index with empty directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.rag.build_index([temp_dir])
            
            assert result["documents_count"] == 0
            assert "build_time" in result
    
    def test_query_simple_rag_success(self):
        """Test querying simple RAG"""
        # First build index
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def hello():\n    return 'world'")
            
            self.rag.build_index([temp_dir])
            
            # Query
            result = self.rag.query("hello function")
            
            assert result is not None
            assert len(result) > 0
            assert "hello" in result.lower()
    
    def test_query_empty_rag(self):
        """Test querying RAG with no index"""
        result = self.rag.query("test query")
        
        assert "No documents available" in result
    
    def test_query_empty_string(self):
        """Test querying with empty string"""
        result = self.rag.query("")
        assert result == "Empty query provided"
    
    def test_performance_tracking(self):
        """Test performance tracking"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Build index
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("test content")
            
            self.rag.build_index([temp_dir])
            
            # Query multiple times
            for i in range(3):
                self.rag.query(f"query {i}")
            
            assert len(self.rag.query_times) == 3
            assert self.rag.total_queries == 3
            assert all(time > 0 for time in self.rag.query_times)
    
    def test_performance_metrics(self):
        """Test performance metrics calculation"""
        # Add some mock query times
        self.rag.query_times = [0.1, 0.2, 0.15]
        self.rag.total_queries = 3
        self.rag.relevant_results = 2
        
        metrics = self.rag.get_performance_metrics()
        
        assert metrics["avg_query_time"] == pytest.approx(0.15, rel=1e-2)
        assert metrics["total_queries"] == 3
        assert metrics["relevance_rate"] == pytest.approx(0.667, rel=1e-2)
        assert metrics["meets_time_target"] == True  # 0.15s < 0.8s
        assert metrics["meets_relevance_target"] == False  # 66.7% < 80%
    
    def test_performance_metrics_empty(self):
        """Test performance metrics with no data"""
        metrics = self.rag.get_performance_metrics()
        
        assert metrics["avg_query_time"] == 0
        assert metrics["total_queries"] == 0
        assert metrics["relevance_rate"] == 0
        assert metrics["meets_time_target"] == True
        assert metrics["meets_relevance_target"] == False
    
    def test_clear_cache(self):
        """Test cache clearing"""
        # Add some data
        self.rag.query_times = [0.1, 0.2]
        self.rag.total_queries = 2
        
        self.rag.clear_cache()
        
        assert len(self.rag.query_times) == 0
        assert self.rag.total_queries == 0
        assert self.rag.relevant_results == 0


class TestRAGGlobalFunctions:
    """Test global RAG functions"""
    
    def setup_method(self):
        # Clear global instance
        import src.rag.llamaindex_adapter
        src.rag.llamaindex_adapter.rag_instance = None
    
    def test_initialize_rag(self):
        """Test RAG initialization"""
        rag = initialize_rag("/tmp/test-global-rag")
        
        assert rag is not None
        assert isinstance(rag, LlamaIndexRAG)
        assert rag.index_path == Path("/tmp/test-global-rag")
    
    def test_get_rag_instance_none(self):
        """Test getting RAG instance when not initialized"""
        instance = get_rag_instance()
        assert instance is None
    
    def test_get_rag_instance_initialized(self):
        """Test getting RAG instance when initialized"""
        rag = initialize_rag("/tmp/test-global-rag")
        instance = get_rag_instance()
        
        assert instance is rag
        assert instance is not None
    
    def test_query_rag_not_initialized(self):
        """Test query_rag when RAG not initialized"""
        result = query_rag("test query")
        assert result == "RAG not initialized"
    
    def test_query_rag_initialized(self):
        """Test query_rag when RAG is initialized"""
        rag = initialize_rag("/tmp/test-global-rag")
        
        # Mock the query method
        rag.query = Mock(return_value="mock response")
        
        result = query_rag("test query")
        assert result == "mock response"
        rag.query.assert_called_once_with("test query", 8)


class TestRAGIntegrationWithAgents:
    """Test RAG integration with multi-agent workflow"""
    
    def test_planner_with_rag_context(self):
        """Test planner agent using RAG context"""
        from src.agents.orchestrator import PlannerAgent
        
        # Mock LLM and RAG
        mock_llm = Mock()
        mock_llm.call.return_value = "Plan created with RAG context"
        
        mock_rag = Mock()
        mock_rag.query.return_value = "Relevant code context for planning"
        
        with patch('src.agents.orchestrator.get_rag_instance', return_value=mock_rag):
            planner = PlannerAgent(mock_llm)
            
            # Create mock state
            from src.agents.orchestrator import AgentState
            state = AgentState(task_data={"issue": "test issue"})
            
            result = planner.process(state, "Implement feature X")
            
            assert "Plan created" in result
            mock_rag.query.assert_called_once_with("Planning for: Implement feature X")
    
    def test_coder_with_rag_context(self):
        """Test coder agent using RAG context"""
        from src.agents.orchestrator import CoderAgent
        
        # Mock LLM and RAG
        mock_llm = Mock()
        mock_llm.call.return_value = "Code generated with RAG context"
        
        mock_rag = Mock()
        mock_rag.query.return_value = "Relevant code examples"
        
        with patch('src.agents.orchestrator.get_rag_instance', return_value=mock_rag):
            coder = CoderAgent(mock_llm)
            
            # Create mock state with planner message
            from src.agents.orchestrator import AgentState, AgentMessage, AgentRole
            state = AgentState(task_data={"issue": "test issue"})
            state.messages = [
                AgentMessage(role=AgentRole.PLANNER, content="Plan: Implement feature")
            ]
            
            result = coder.process(state, "Implement feature X")
            
            assert "Code generated" in result
            mock_rag.query.assert_called_once_with("Code implementation for: Implement feature X")
    
    def test_reviewer_with_rag_context(self):
        """Test reviewer agent using RAG context"""
        from src.agents.orchestrator import ReviewerAgent
        
        # Mock LLM and RAG
        mock_llm = Mock()
        mock_llm.call.return_value = "Review completed with RAG context"
        
        mock_rag = Mock()
        mock_rag.query.return_value = "Relevant review guidelines"
        
        with patch('src.agents.orchestrator.get_rag_instance', return_value=mock_rag):
            reviewer = ReviewerAgent(mock_llm)
            
            # Create mock state with planner and coder messages
            from src.agents.orchestrator import AgentState, AgentMessage, AgentRole
            state = AgentState(task_data={"issue": "test issue"})
            state.messages = [
                AgentMessage(role=AgentRole.PLANNER, content="Plan: Implement feature"),
                AgentMessage(role=AgentRole.CODER, content="def feature(): pass")
            ]
            
            result = reviewer.process(state, "Review feature X")
            
            assert "Review completed" in result
            mock_rag.query.assert_called_once_with("Code review for: Review feature X")
    
    def test_rag_failure_handling(self):
        """Test agent behavior when RAG fails"""
        from src.agents.orchestrator import PlannerAgent
        
        # Mock LLM and failing RAG
        mock_llm = Mock()
        mock_llm.call.return_value = "Plan created without RAG"
        
        mock_rag = Mock()
        mock_rag.query.side_effect = Exception("RAG failed")
        
        with patch('src.agents.orchestrator.get_rag_instance', return_value=mock_rag):
            planner = PlannerAgent(mock_llm)
            
            from src.agents.orchestrator import AgentState
            state = AgentState(task_data={"issue": "test issue"})
            
            result = planner.process(state, "Implement feature X")
            
            assert "Plan created" in result
            # Should not have RAG context in prompt
            assert "Relevant Code Context:" not in result


class TestRAGPerformanceTargets:
    """Test RAG performance targets"""
    
    def test_query_time_target(self):
        """Test RAG query time target: <0.8s"""
        rag = LlamaIndexRAG()
        
        # Add query times under target
        rag.query_times = [0.1, 0.2, 0.3, 0.4]
        rag.total_queries = 4
        rag.relevant_results = 4
        
        metrics = rag.get_performance_metrics()
        
        assert metrics["meets_time_target"] == True
        assert metrics["avg_query_time"] == 0.25
        
        # Add query times over target
        rag.query_times = [0.5, 0.9, 1.2]
        rag.total_queries = 3
        
        metrics = rag.get_performance_metrics()
        
        assert metrics["meets_time_target"] == False
        assert metrics["avg_query_time"] == pytest.approx(0.867, rel=1e-2)
    
    def test_relevance_rate_target(self):
        """Test RAG relevance rate target: ≥80%"""
        rag = LlamaIndexRAG()
        
        # Test meeting target
        rag.total_queries = 10
        rag.relevant_results = 8
        
        metrics = rag.get_performance_metrics()
        
        assert metrics["relevance_rate"] == 0.8
        assert metrics["meets_relevance_target"] == True
        
        # Test below target
        rag.total_queries = 10
        rag.relevant_results = 7
        
        metrics = rag.get_performance_metrics()
        
        assert metrics["relevance_rate"] == 0.7
        assert metrics["meets_relevance_target"] == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
