#!/usr/bin/env python3
"""
Multi-Agent Orchestrator for GitHub AI Agent
Implements Planner -> Coder -> Reviewer workflow with performance tracking
"""

import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
from src.agents.base import LLMProvider
from src.utils.logger import get_logger
from src.rag.llamaindex_adapter import get_rag_instance

logger = get_logger(__name__)


class AgentRole(Enum):
    PLANNER = "planner"
    CODER = "coder" 
    REVIEWER = "reviewer"


@dataclass
class AgentMessage:
    role: AgentRole
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentState:
    messages: List[AgentMessage] = field(default_factory=list)
    current_role: AgentRole = AgentRole.PLANNER
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: float = field(default_factory=time.time)
    task_data: Dict[str, Any] = field(default_factory=dict)


class PerformanceTracker:
    def __init__(self):
        self.loop_times: List[float] = []
        self.success_rates: Dict[str, float] = {}
        self.total_tasks = 0
        self.successful_tasks = 0
    
    def record_loop_time(self, role: AgentRole, duration: float):
        self.loop_times.append(duration)
        
        # Success metric: <5s per role
        if duration > 5.0:
            logger.warning(f"Agent {role.value} exceeded 5s: {duration:.2f}s")
    
    def record_task_success(self, success: bool):
        self.total_tasks += 1
        if success:
            self.successful_tasks += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        success_rate = self.successful_tasks / self.total_tasks if self.total_tasks > 0 else 0
        avg_loop_time = sum(self.loop_times) / len(self.loop_times) if self.loop_times else 0
        
        return {
            "success_rate": success_rate,
            "avg_loop_time": avg_loop_time,
            "total_tasks": self.total_tasks,
            "meets_success_target": success_rate >= 0.9,
            "meets_time_target": avg_loop_time < 5.0
        }


class PlannerAgent:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def process(self, state: AgentState, task: str) -> str:
        """Process task and create execution plan"""
        # Get RAG context if available
        rag = get_rag_instance()
        rag_context = ""
        if rag:
            try:
                rag_context = rag.query(f"Planning for: {task}")
                logger.info(f"RAG context retrieved for planner")
            except Exception as e:
                logger.warning(f"RAG query failed: {e}")
        
        prompt = f"""
You are a Planner Agent. Analyze the task and create a detailed execution plan.

Task: {task}
Context: {state.task_data}
{f"Relevant Code Context:\n{rag_context}" if rag_context else ""}

Provide:
1. Task breakdown into specific steps
2. Required files and dependencies
3. Implementation approach
4. Testing requirements
5. Potential risks and mitigations

Be specific and actionable.
"""
        
        try:
            response = self.llm.call([{"role": "user", "content": prompt}])
            return response or "Unable to generate plan"
        except Exception as e:
            logger.error(f"Planner agent failed: {e}")
            return f"Planning failed: {str(e)}"

    def plan(self, payload: Dict[str, Any]) -> str:
        """Legacy method for backward compatibility"""
        title = str(payload.get("title") or payload.get("issue", {}).get("title") or "")
        return f"Plan: analyze '{title}' and propose changes"


class CoderAgent:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def process(self, state: AgentState, task: str) -> str:
        """Process task and generate code"""
        plan_message = self._get_latest_message_by_role(state, AgentRole.PLANNER)
        plan = plan_message.content if plan_message else "No plan available"
        
        # Get RAG context if available
        rag = get_rag_instance()
        rag_context = ""
        if rag:
            try:
                rag_context = rag.query(f"Code implementation for: {task}")
                logger.info(f"RAG context retrieved for coder")
            except Exception as e:
                logger.warning(f"RAG query failed: {e}")
        
        prompt = f"""
You are a Coder Agent. Implement code based on the plan and task.

Task: {task}
Plan: {plan}
Context: {state.task_data}
{f"Relevant Code Context:\n{rag_context}" if rag_context else ""}

Requirements:
1. Write clean, production-ready code
2. Follow best practices and conventions
3. Include error handling
4. Add necessary imports
5. Provide complete implementation

Generate the complete code solution.
"""
        
        try:
            response = self.llm.call([{"role": "user", "content": prompt}])
            return response or "Unable to generate code"
        except Exception as e:
            logger.error(f"Coder agent failed: {e}")
            return f"Coding failed: {str(e)}"

    def code(self, payload: Dict[str, Any]) -> str:
        """Legacy method for backward compatibility"""
        return "CodeChanges: placeholder"
    
    def _get_latest_message_by_role(self, state: AgentState, role: AgentRole) -> Optional[AgentMessage]:
        """Get the latest message from a specific role"""
        for message in reversed(state.messages):
            if message.role == role:
                return message
        return None


class ReviewerAgent:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def process(self, state: AgentState, task: str) -> str:
        """Review code and provide feedback"""
        plan_message = self._get_latest_message_by_role(state, AgentRole.PLANNER)
        code_message = self._get_latest_message_by_role(state, AgentRole.CODER)
        
        plan = plan_message.content if plan_message else "No plan available"
        code = code_message.content if code_message else "No code available"
        
        # Get RAG context if available
        rag = get_rag_instance()
        rag_context = ""
        if rag:
            try:
                rag_context = rag.query(f"Code review for: {task}")
                logger.info(f"RAG context retrieved for reviewer")
            except Exception as e:
                logger.warning(f"RAG query failed: {e}")
        
        prompt = f"""
You are a Reviewer Agent. Review the implementation against the plan and requirements.

Task: {task}
Plan: {plan}
Code: {code}
{f"Relevant Code Context:\n{rag_context}" if rag_context else ""}

Review for:
1. Correctness and functionality
2. Security vulnerabilities
3. Code quality and best practices
4. Performance considerations
5. Test coverage requirements
6. Documentation completeness

Provide detailed review with specific feedback and approval/rejection recommendation.
"""
        
        try:
            response = self.llm.call([{"role": "user", "content": prompt}])
            return response or "Unable to review code"
        except Exception as e:
            logger.error(f"Reviewer agent failed: {e}")
            return f"Review failed: {str(e)}"

    def review(self, payload: Dict[str, Any]) -> str:
        """Legacy method for backward compatibility"""
        title = str(payload.get("title") or payload.get("pull_request", {}).get("title") or "")
        return f"Review: '{title}' looks acceptable"
    
    def _get_latest_message_by_role(self, state: AgentState, role: AgentRole) -> Optional[AgentMessage]:
        """Get the latest message from a specific role"""
        for message in reversed(state.messages):
            if message.role == role:
                return message
        return None


class MultiAgentOrchestrator:
    def __init__(self, llm_provider: LLMProvider):
        self.planner = PlannerAgent(llm_provider)
        self.coder = CoderAgent(llm_provider)
        self.reviewer = ReviewerAgent(llm_provider)
        self.performance_tracker = PerformanceTracker()
    
    def execute_task(self, task: str, task_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute task through multi-agent workflow"""
        state = AgentState(
            task_data=task_data or {},
            task_id=str(uuid.uuid4()),
            start_time=time.time()
        )
        
        logger.info(f"Starting task execution: {state.task_id}")
        
        try:
            # Execute agent pipeline
            for role in [AgentRole.PLANNER, AgentRole.CODER, AgentRole.REVIEWER]:
                loop_start = time.time()
                
                agent = self._get_agent(role)
                response = agent.process(state, task)
                
                loop_time = time.time() - loop_start
                self.performance_tracker.record_loop_time(role, loop_time)
                
                message = AgentMessage(
                    role=role,
                    content=response,
                    metadata={"loop_time": loop_time},
                    timestamp=time.time()
                )
                state.messages.append(message)
                
                logger.info(f"Agent {role.value} completed in {loop_time:.2f}s")
            
            total_time = time.time() - state.start_time
            success = len(state.messages) == 3  # All agents completed
            
            self.performance_tracker.record_task_success(success)
            
            result = {
                "task_id": state.task_id,
                "success": success,
                "total_time": total_time,
                "messages": [
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                        "metadata": msg.metadata
                    } for msg in state.messages
                ],
                "performance": self.performance_tracker.get_metrics()
            }
            
            logger.info(f"Task {state.task_id} completed in {total_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            self.performance_tracker.record_task_success(False)
            
            return {
                "task_id": state.task_id,
                "success": False,
                "error": str(e),
                "messages": [
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                        "metadata": msg.metadata
                    } for msg in state.messages
                ],
                "performance": self.performance_tracker.get_metrics()
            }
    
    def _get_agent(self, role: AgentRole):
        """Get agent instance by role"""
        agents = {
            AgentRole.PLANNER: self.planner,
            AgentRole.CODER: self.coder,
            AgentRole.REVIEWER: self.reviewer
        }
        return agents[role]


class Orchestrator:
    """Legacy orchestrator for backward compatibility"""
    def __init__(self, llm_provider: LLMProvider):
        self.multi_agent = MultiAgentOrchestrator(llm_provider)

    def handle_issue_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle issue event using multi-agent orchestrator"""
        title = payload.get("issue", {}).get("title", "")
        body = payload.get("issue", {}).get("body", "")
        task = f"Handle GitHub issue: {title}\n\n{body}"
        
        return self.multi_agent.execute_task(task, payload)

    def handle_pull_request_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle PR event using multi-agent orchestrator"""
        title = payload.get("pull_request", {}).get("title", "")
        body = payload.get("pull_request", {}).get("body", "")
        task = f"Review and improve GitHub PR: {title}\n\n{body}"
        
        return self.multi_agent.execute_task(task, payload)
