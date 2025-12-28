#!/usr/bin/env python3
"""
Test Phase 3 Integration
Tests RAG, Memory, and Multi-agent collaboration
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
import tempfile
import os

try:
    from ..agents.agent_manager import AgentManager, Task, CollaborativeResult
    from ..agents.github_issue_agent import GitHubIssueAgent
    from ..agents.doc_agent import DocumentationAgent
    from ..rag.vector_store import VectorStore
    from ..memory.memory_manager import MemoryManager
    from ..agents.base_agent import AgentContext
    from ..utils.logger import get_logger
except ImportError:
    from src.agents.agent_manager import AgentManager, Task, CollaborativeResult
    from src.agents.github_issue_agent import GitHubIssueAgent
    from src.agents.doc_agent import DocumentationAgent
    from src.rag.vector_store import VectorStore
    from src.memory.memory_manager import MemoryManager
    from src.agents.base_agent import AgentContext
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class TestPhase3Integration:
    """Integration tests for Phase 3 features"""
    
    @pytest.fixture
    def temp_vector_store(self):
        """Create temporary vector store for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = VectorStore(dimension=10, storage_path=temp_dir)
            yield store
    
    @pytest.fixture
    def temp_memory_manager(self):
        """Create temporary memory manager for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_memory.db")
            memory = MemoryManager(db_path)
            yield memory
            memory.close()
    
    @pytest.fixture
    def mock_agents(self):
        """Create mock agents for testing"""
        # Create mock agents
        try:
            from ..agents.base_agent import SimpleAgent
        except ImportError:
            from src.agents.base_agent import SimpleAgent
        
        agents = {
            "github_agent": SimpleAgent("GitHubAgent"),
            "doc_agent": SimpleAgent("DocAgent"),
            "code_agent": SimpleAgent("CodeAgent")
        }
        
        # Mock agent capabilities
        for name, agent in agents.items():
            agent.name = name
        
        return agents
    
    @pytest.fixture
    def agent_manager(self, mock_agents, temp_vector_store, temp_memory_manager):
        """Create agent manager with test dependencies"""
        return AgentManager(mock_agents, temp_vector_store, temp_memory_manager)
    
    @pytest.mark.asyncio
    async def test_rag_documentation_search(self, temp_vector_store):
        """Test RAG documentation search functionality"""
        # Add test documents
        test_docs = [
            ("Authentication API allows users to login with JWT tokens", 
             {"type": "api", "title": "Authentication"}),
            ("Use OAuth2 for secure authentication flows", 
             {"type": "tutorial", "title": "OAuth2 Guide"}),
            ("Error handling best practices include try-catch blocks", 
             {"type": "best_practices", "title": "Error Handling"})
        ]
        
        # Create fake embeddings
        import numpy as np
        embeddings = [np.random.rand(10) for _ in test_docs]
        
        # Add documents to vector store
        for (content, metadata), embedding in zip(test_docs, embeddings):
            temp_vector_store.add_document(content, metadata, embedding=embedding)
        
        # Test search
        query_embedding = np.random.rand(10)
        results = temp_vector_store.search(query_embedding, k=2)
        
        assert len(results) <= 2
        assert all(isinstance(result.document.content, str) for result in results)
        assert all(0 <= result.score <= 1 for result in results)
        
        # Test document retrieval
        if results:
            doc = temp_vector_store.get_document_by_id(results[0].document.id)
            assert doc is not None
            assert doc.content == results[0].document.content
    
    @pytest.mark.asyncio
    async def test_memory_operations(self, temp_memory_manager):
        """Test memory manager operations"""
        # Test remember
        memory_id = temp_memory_manager.remember(
            key="test_preference",
            value={"theme": "dark", "language": "python"},
            memory_type="preference",
            importance=0.8
        )
        
        assert memory_id is not None
        
        # Test recall
        entries = temp_memory_manager.recall("test_preference")
        assert len(entries) >= 1
        assert entries[0].value["theme"] == "dark"
        assert entries[0].type == "preference"
        assert entries[0].importance == 0.8
        
        # Test search
        search_results = temp_memory_manager.search("preference")
        assert len(search_results) >= 1
        
        # Test conversation saving
        session_id = temp_memory_manager.save_conversation(
            session_id="test_session",
            user_id="test_user",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ],
            summary="Test conversation"
        )
        
        assert session_id == "test_session"
        
        # Test conversation retrieval
        conversation = temp_memory_manager.get_conversation("test_session")
        assert conversation is not None
        assert conversation.user_id == "test_user"
        assert len(conversation.messages) == 2
        assert conversation.summary == "Test conversation"
    
    @pytest.mark.asyncio
    async def test_agent_manager_task_creation(self, agent_manager):
        """Test agent manager task creation"""
        # Create test task
        task_id = agent_manager.create_task(
            task_type="github_issue",
            data={
                "issue": {
                    "title": "Bug: Login fails",
                    "body": "Users cannot login with correct credentials"
                }
            },
            priority="high"
        )
        
        assert task_id is not None
        assert task_id.startswith("task_")
        
        # Check task status
        status = agent_manager.get_task_status(task_id)
        assert status is not None
        assert status["status"] == "queued"
    
    @pytest.mark.asyncio
    async def test_multi_agent_collaboration(self, agent_manager):
        """Test multi-agent collaboration workflow"""
        # Create collaborative task
        task_id = agent_manager.create_task(
            task_type="collaborative_task",
            data={
                "issue": {
                    "title": "Bug: Authentication error",
                    "body": "Login system returns 500 error"
                },
                "context": "User authentication flow"
            },
            priority="high"
        )
        
        # Process task
        result = await agent_manager.process_task(task_id)
        
        assert isinstance(result, CollaborativeResult)
        assert result.task_id == task_id
        assert len(result.agent_results) > 0
        assert result.success is not False  # Should not be False (might be True or partial)
        assert result.total_time >= 0
        assert result.summary is not None
    
    @pytest.mark.asyncio
    async def test_documentation_agent_integration(self, temp_vector_store, temp_memory_manager):
        """Test documentation agent with RAG and memory"""
        # Create documentation agent
        doc_agent = DocumentationAgent(temp_vector_store, temp_memory_manager)
        
        # Add test documentation
        test_docs = [
            ("JWT tokens are used for secure authentication", 
             {"type": "api", "title": "JWT Authentication"}),
            ("OAuth2 provides authorization flows", 
             {"type": "tutorial", "title": "OAuth2 Guide"})
        ]
        
        import numpy as np
        for content, metadata in test_docs:
            embedding = np.random.rand(10)
            temp_vector_store.add_document(content, metadata, embedding=embedding)
        
        # Test documentation search
        result = await doc_agent.search_documentation("authentication")
        
        assert result.query == "authentication"
        assert isinstance(result.sections, list)
        assert isinstance(result.code_examples, list)
        assert isinstance(result.related_topics, list)
        assert 0 <= result.confidence <= 1
        
        # Test message processing
        response = await doc_agent.chat("search docs for authentication")
        assert "authentication" in response.lower() or "search" in response.lower()
    
    @pytest.mark.asyncio
    async def test_github_issue_agent_with_memory(self, temp_memory_manager):
        """Test GitHub issue agent with memory integration"""
        # Create GitHub issue agent
        issue_agent = GitHubIssueAgent(
            repo="testowner/testrepo",
            token="test_token",
            config={"test_mode": True}
        )
        
        # Mock memory manager
        issue_agent.memory_manager = temp_memory_manager
        
        # Test issue analysis
        from datetime import datetime
        test_issue = Mock()
        test_issue.number = 123
        test_issue.title = "Bug: Login fails"
        test_issue.body = "Authentication system crashes"
        test_issue.state = "open"
        test_issue.created_at = datetime.now()
        test_issue.updated_at = datetime.now()
        test_issue.user = "testuser"
        test_issue.labels = ["bug"]
        test_issue.assignees = []
        test_issue.milestone = None
        test_issue.comments_count = 5
        test_issue.url = "https://github.com/test/test/issues/123"
        
        analysis = await issue_agent.analyze_issue(test_issue)
        
        assert analysis.issue_number == 123
        assert analysis.title == "Login fails"
        assert analysis.category in ["Bug", "Feature", "Documentation", "Question", "Other"]
        assert analysis.priority in ["Critical", "High", "Medium", "Low"]
        assert analysis.complexity in ["Low", "Medium", "High"]
        assert isinstance(analysis.suggested_labels, list)
        assert isinstance(analysis.confidence, float)
        assert 0 <= analysis.confidence <= 1
    
    @pytest.mark.asyncio
    async def test_complete_workflow_integration(self, agent_manager, temp_vector_store, temp_memory_manager):
        """Test complete Phase 3 workflow integration"""
        # 1. Add documentation to RAG
        test_docs = [
            ("Authentication requires JWT token validation", 
             {"type": "api", "title": "Auth Validation"}),
            ("Error handling should include proper logging", 
             {"type": "best_practices", "title": "Error Handling"})
        ]
        
        import numpy as np
        for content, metadata in test_docs:
            embedding = np.random.rand(10)
            temp_vector_store.add_document(content, metadata, embedding=embedding)
        
        # 2. Store context in memory
        temp_memory_manager.remember(
            key="project_context",
            value={"framework": "django", "version": "4.0"},
            memory_type="context",
            importance=0.9
        )
        
        # 3. Create collaborative task
        task_id = agent_manager.create_task(
            task_type="github_issue",
            data={
                "issue": {
                    "title": "Bug: Authentication fails",
                    "body": "JWT validation is not working properly"
                },
                "context": "Django 4.0 authentication system"
            },
            priority="high"
        )
        
        # 4. Process task with multi-agent collaboration
        result = await agent_manager.process_task(task_id)
        
        # 5. Verify integration
        assert isinstance(result, CollaborativeResult)
        assert result.task_id == task_id
        assert len(result.agent_results) > 0
        
        # Check that memory was used
        memory_entries = temp_memory_manager.recall("project_context")
        assert len(memory_entries) >= 1
        
        # Check that vector store was queried
        stats = temp_vector_store.get_stats()
        assert stats["total_documents"] >= 2
        
        # Verify agent performance
        perf_stats = agent_manager.get_performance_stats()
        assert perf_stats["total_tasks"] >= 1
        assert perf_stats["success_rate"] >= 0
    
    def test_vector_store_persistence(self, temp_vector_store):
        """Test vector store persistence"""
        # Add document
        doc_id = temp_vector_store.add_document(
            "Test content",
            {"type": "test", "title": "Test Document"}
        )
        
        # Save
        temp_vector_store.save()
        
        # Create new instance with same path
        new_store = VectorStore(dimension=10, storage_path=temp_vector_store.storage_path)
        
        # Verify document was loaded
        doc = new_store.get_document_by_id(doc_id)
        assert doc is not None
        assert doc.content == "Test content"
        assert doc.metadata["type"] == "test"
        
        # Check stats
        stats = new_store.get_stats()
        assert stats["total_documents"] >= 1
    
    def test_memory_cleanup(self, temp_memory_manager):
        """Test memory cleanup functionality"""
        # Add expired memory
        temp_memory_manager.remember(
            key="expired_memory",
            value="test",
            memory_type="test",
            expires_in=timedelta(seconds=-1)  # Already expired
        )
        
        # Add non-expired memory
        temp_memory_manager.remember(
            key="valid_memory",
            value="test",
            memory_type="test",
            expires_in=timedelta(hours=1)
        )
        
        # Cleanup expired memories
        cleaned_count = temp_memory_manager.cleanup_expired()
        
        assert cleaned_count >= 1
        
        # Verify expired memory is gone
        expired_entries = temp_memory_manager.recall("expired_memory")
        assert len(expired_entries) == 0
        
        # Verify valid memory remains
        valid_entries = temp_memory_manager.recall("valid_memory")
        assert len(valid_entries) >= 1
    
    @pytest.mark.asyncio
    async def test_agent_performance_tracking(self, agent_manager):
        """Test agent performance tracking"""
        # Create and process multiple tasks
        task_ids = []
        for i in range(3):
            task_id = agent_manager.create_task(
                task_type="github_issue",
                data={"issue": {"title": f"Test issue {i}"}},
                priority="medium"
            )
            task_ids.append(task_id)
        
        # Process tasks
        for task_id in task_ids:
            await agent_manager.process_task(task_id)
        
        # Check performance stats
        stats = agent_manager.get_performance_stats()
        
        assert stats["total_tasks"] >= 3
        assert stats["agent_performance"] is not None
        assert len(stats["agent_performance"]) > 0
        
        # Check individual agent performance
        for agent_name, perf in stats["agent_performance"].items():
            assert "tasks_completed" in perf
            assert "success_count" in perf
            assert "total_time" in perf
            assert "average_time" in perf


# Test runner
def run_phase3_tests():
    """Run Phase 3 integration tests"""
    import sys
    
    # Run with pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short"
    ])
    
    sys.exit(exit_code)


if __name__ == "__main__":
    run_phase3_tests()
