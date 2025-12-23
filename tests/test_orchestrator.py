#!/usr/bin/env python3
"""
Unit tests for Multi-Agent Orchestrator with performance metrics
"""

import pytest
import time
from unittest.mock import Mock, patch
from src.agents.orchestrator import (
    MultiAgentOrchestrator, 
    AgentRole, 
    AgentMessage, 
    AgentState,
    PerformanceTracker
)
from src.agents.base import LLMProvider


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing"""
    
    def __init__(self, response_delay=0.1):
        self.response_delay = response_delay
        self.call_count = 0
    
    def call(self, messages, **kwargs):
        """Mock LLM call with configurable delay"""
        self.call_count += 1
        time.sleep(self.response_delay)  # Simulate processing time
        
        role_responses = {
            "planner": "Plan: Analyze requirements, implement solution, test thoroughly",
            "coder": "Code: def solution():\n    # Implementation here\n    pass",
            "reviewer": "Review: Code looks good, approved for merge"
        }
        
        # Determine role from context (simplified)
        content = messages[0]["content"] if messages else ""
        if "Planner Agent" in content:
            return role_responses["planner"]
        elif "Coder Agent" in content:
            return role_responses["coder"]
        elif "Reviewer Agent" in content:
            return role_responses["reviewer"]
        
        return "Default response"
    
    def get_available_models(self):
        """Mock method to satisfy abstract base class"""
        return ["mock-model-1", "mock-model-2"]


class TestPerformanceTracker:
    """Test performance tracking functionality"""
    
    def setup_method(self):
        self.tracker = PerformanceTracker()
    
    def test_record_loop_time(self):
        """Test loop time recording"""
        self.tracker.record_loop_time(AgentRole.PLANNER, 2.5)
        self.tracker.record_loop_time(AgentRole.CODER, 3.0)
        self.tracker.record_loop_time(AgentRole.REVIEWER, 1.8)
        
        assert len(self.tracker.loop_times) == 3
        assert self.tracker.loop_times[0] == 2.5
        assert self.tracker.loop_times[1] == 3.0
        assert self.tracker.loop_times[2] == 1.8
    
    def test_record_task_success(self):
        """Test task success recording"""
        # Record successful tasks
        self.tracker.record_task_success(True)
        self.tracker.record_task_success(True)
        self.tracker.record_task_success(True)
        
        # Record failed task
        self.tracker.record_task_success(False)
        
        assert self.tracker.total_tasks == 4
        assert self.tracker.successful_tasks == 3
    
    def test_metrics_calculation(self):
        """Test metrics calculation"""
        # Add test data
        self.tracker.record_loop_time(AgentRole.PLANNER, 2.0)
        self.tracker.record_loop_time(AgentRole.CODER, 3.0)
        self.tracker.record_loop_time(AgentRole.REVIEWER, 1.5)
        self.tracker.record_task_success(True)
        self.tracker.record_task_success(False)
        
        metrics = self.tracker.get_metrics()
        
        assert metrics["success_rate"] == 0.5  # 1 success / 2 total
        assert metrics["avg_loop_time"] == 2.1666666666666665  # (2+3+1.5)/3
        assert metrics["total_tasks"] == 2
        assert metrics["meets_success_target"] == False  # 50% < 90%
        assert metrics["meets_time_target"] == True  # 2.17s < 5s
    
    def test_empty_metrics(self):
        """Test metrics with no data"""
        metrics = self.tracker.get_metrics()
        
        assert metrics["success_rate"] == 0
        assert metrics["avg_loop_time"] == 0
        assert metrics["total_tasks"] == 0
        assert metrics["meets_success_target"] == False
        assert metrics["meets_time_target"] == True


class TestMultiAgentOrchestrator:
    """Test multi-agent orchestrator functionality"""
    
    def setup_method(self):
        self.mock_llm = MockLLMProvider(response_delay=0.1)
        self.orchestrator = MultiAgentOrchestrator(self.mock_llm)
    
    def test_task_execution_success(self):
        """Test successful task execution"""
        task = "Implement a new feature for authentication"
        task_data = {"repository": "test-repo", "issue_number": 123}
        
        result = self.orchestrator.execute_task(task, task_data)
        
        # Verify structure
        assert "task_id" in result
        assert "success" in result
        assert "total_time" in result
        assert "messages" in result
        assert "performance" in result
        
        # Verify success
        assert result["success"] == True
        assert len(result["messages"]) == 3  # Planner, Coder, Reviewer
        
        # Verify message roles
        roles = [msg["role"] for msg in result["messages"]]
        assert "planner" in roles
        assert "coder" in roles
        assert "reviewer" in roles
        
        # Verify performance metrics
        perf = result["performance"]
        assert perf["success_rate"] == 1.0  # 100% success
        assert perf["total_tasks"] == 1
        assert perf["meets_success_target"] == True
    
    def test_task_execution_under_5s_per_role(self):
        """Test that each agent completes under 5 seconds"""
        task = "Quick task for performance testing"
        
        result = self.orchestrator.execute_task(task)
        
        # Check loop times for each agent
        loop_times = self.orchestrator.performance_tracker.loop_times
        assert len(loop_times) == 3
        
        # Each loop should be under 5s (our mock uses 0.1s delay)
        for loop_time in loop_times:
            assert loop_time < 5.0, f"Loop time {loop_time}s exceeded 5s limit"
        
        # Average should also be under 5s
        avg_time = result["performance"]["avg_loop_time"]
        assert avg_time < 5.0, f"Average loop time {avg_time}s exceeded 5s limit"
    
    def test_task_completion_success_rate(self):
        """Test task completion success rate >90%"""
        tasks = [
            "Fix authentication bug",
            "Add new API endpoint", 
            "Optimize database query",
            "Update documentation",
            "Implement caching"
        ]
        
        success_count = 0
        results = []
        
        for task in tasks:
            try:
                result = self.orchestrator.execute_task(task)
                results.append(result)
                if result["success"] and len(result["messages"]) == 3:
                    success_count += 1
            except Exception as e:
                print(f"Task failed: {task}, Error: {e}")
        
        success_rate = success_count / len(tasks)
        assert success_rate >= 0.9, f"Success rate {success_rate:.2%} below 90%"
        
        # Verify overall performance metrics
        overall_metrics = self.orchestrator.performance_tracker.get_metrics()
        assert overall_metrics["success_rate"] >= 0.9
    
    def test_task_execution_with_llm_failure(self):
        """Test task execution when LLM fails"""
        # Create failing mock LLM
        failing_llm = Mock()
        failing_llm.call.side_effect = Exception("LLM API failed")
        
        orchestrator = MultiAgentOrchestrator(failing_llm)
        
        result = orchestrator.execute_task("Test task")
        
        # Should handle failure gracefully
        assert result["success"] == False
        assert "error" in result
        assert result["performance"]["success_rate"] == 0.0
    
    def test_message_flow_between_agents(self):
        """Test that messages flow correctly between agents"""
        task = "Implement user authentication system"
        
        result = self.orchestrator.execute_task(task)
        
        messages = result["messages"]
        assert len(messages) == 3
        
        # Verify planner message
        planner_msg = next(msg for msg in messages if msg["role"] == "planner")
        assert "Plan:" in planner_msg["content"]
        assert "loop_time" in planner_msg["metadata"]
        
        # Verify coder message
        coder_msg = next(msg for msg in messages if msg["role"] == "coder")
        assert "Code:" in coder_msg["content"]
        assert "loop_time" in coder_msg["metadata"]
        
        # Verify reviewer message
        reviewer_msg = next(msg for msg in messages if msg["role"] == "reviewer")
        assert "Review:" in reviewer_msg["content"]
        assert "loop_time" in reviewer_msg["metadata"]
    
    def test_performance_threshold_warnings(self):
        """Test that warnings are logged for slow agents"""
        # Create slow mock LLM
        slow_llm = MockLLMProvider(response_delay=6.0)  # Exceeds 5s threshold
        
        with patch('src.agents.orchestrator.logger') as mock_logger:
            orchestrator = MultiAgentOrchestrator(slow_llm)
            orchestrator.execute_task("Test task")
            
            # Should log warning for slow agents
            warning_calls = mock_logger.warning.call_args_list
            assert len(warning_calls) >= 3  # Should warn for each agent
            
            # Verify warning content
            for call in warning_calls:
                warning_msg = call[0][0]  # First argument of warning call
                assert "exceeded 5s" in warning_msg
    
    def test_backward_compatibility(self):
        """Test backward compatibility with legacy orchestrator"""
        from src.agents.orchestrator import Orchestrator
        
        # Create legacy orchestrator directly with multi-agent
        legacy_orchestrator = Orchestrator.__new__(Orchestrator)
        legacy_orchestrator.multi_agent = MultiAgentOrchestrator(self.mock_llm)
        
        # Test issue event handling
        issue_payload = {
            "issue": {
                "title": "Bug in authentication",
                "body": "Users cannot login with valid credentials"
            }
        }
        
        result = legacy_orchestrator.handle_issue_event(issue_payload)
        
        assert "task_id" in result
        assert "success" in result
        assert "messages" in result
        assert len(result["messages"]) == 3
        
        # Test PR event handling
        pr_payload = {
            "pull_request": {
                "title": "Add user registration",
                "body": "Implements user registration flow"
            }
        }
        
        result = legacy_orchestrator.handle_pull_request_event(pr_payload)
        
        assert "task_id" in result
        assert "success" in result
        assert "messages" in result
        assert len(result["messages"]) == 3


class TestAgentState:
    """Test agent state management"""
    
    def test_agent_state_initialization(self):
        """Test agent state initialization"""
        state = AgentState()
        
        assert state.current_role == AgentRole.PLANNER
        assert len(state.messages) == 0
        assert state.task_id is not None
        assert state.start_time > 0
        assert state.task_data == {}
    
    def test_agent_state_with_data(self):
        """Test agent state with custom data"""
        task_data = {"repo": "test-repo", "issue": 123}
        state = AgentState(task_data=task_data)
        
        assert state.task_data == task_data
        assert state.current_role == AgentRole.PLANNER


class TestAgentMessage:
    """Test agent message structure"""
    
    def test_agent_message_creation(self):
        """Test agent message creation"""
        message = AgentMessage(
            role=AgentRole.PLANNER,
            content="Test plan",
            metadata={"priority": "high"}
        )
        
        assert message.role == AgentRole.PLANNER
        assert message.content == "Test plan"
        assert message.metadata["priority"] == "high"
        assert message.timestamp > 0
    
    def test_agent_message_defaults(self):
        """Test agent message with defaults"""
        message = AgentMessage(
            role=AgentRole.CODER,
            content="Test code"
        )
        
        assert message.role == AgentRole.CODER
        assert message.content == "Test code"
        assert message.metadata == {}
        assert message.timestamp > 0


class TestIntegrationScenarios:
    """Integration test scenarios"""
    
    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow"""
        mock_llm = MockLLMProvider(response_delay=0.05)
        orchestrator = MultiAgentOrchestrator(mock_llm)
        
        # Simulate realistic GitHub issue
        task = "Fix authentication bug where users cannot reset password"
        task_data = {
            "repository": "my-app",
            "issue_number": 456,
            "issue": {
                "title": "Password reset not working",
                "body": "Users report that password reset emails are not being sent"
            }
        }
        
        start_time = time.time()
        result = orchestrator.execute_task(task, task_data)
        execution_time = time.time() - start_time
        
        # Verify successful execution
        assert result["success"] == True
        assert len(result["messages"]) == 3
        
        # Verify performance targets
        assert execution_time < 15.0  # 3 agents × 5s max
        assert result["performance"]["avg_loop_time"] < 5.0
        assert result["performance"]["success_rate"] == 1.0
        
        # Verify message quality
        messages = result["messages"]
        planner_content = messages[0]["content"]
        coder_content = messages[1]["content"] 
        reviewer_content = messages[2]["content"]
        
        assert "Plan:" in planner_content
        assert "Code:" in coder_content
        assert "Review:" in reviewer_content
    
    def test_concurrent_task_execution(self):
        """Test handling multiple tasks"""
        mock_llm = MockLLMProvider(response_delay=0.1)
        orchestrator = MultiAgentOrchestrator(mock_llm)
        
        tasks = [
            ("Task 1", {"priority": "high"}),
            ("Task 2", {"priority": "medium"}),
            ("Task 3", {"priority": "low"})
        ]
        
        results = []
        for task, data in tasks:
            result = orchestrator.execute_task(task, data)
            results.append(result)
        
        # All tasks should succeed
        assert all(r["success"] for r in results)
        
        # Verify unique task IDs
        task_ids = [r["task_id"] for r in results]
        assert len(set(task_ids)) == 3  # All unique
        
        # Verify overall performance
        final_metrics = orchestrator.performance_tracker.get_metrics()
        assert final_metrics["success_rate"] == 1.0
        assert final_metrics["total_tasks"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
