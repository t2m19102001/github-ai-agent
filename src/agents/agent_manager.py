#!/usr/bin/env python3
"""
Agent Manager Module
Coordinates multiple agents for collaborative task processing
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import json

try:
    from ..rag.vector_store import VectorStore, SearchResult
    from ..memory.memory_manager import MemoryManager, MemoryEntry
    from .base_agent import BaseAgent, AgentContext
except ImportError:
    from src.rag.vector_store import VectorStore, SearchResult
    from src.memory.memory_manager import MemoryManager, MemoryEntry
    from src.agents.base_agent import BaseAgent, AgentContext

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Task:
    """Task structure for agent processing"""
    id: str
    type: str
    data: Dict[str, Any]
    priority: str  # high, medium, low
    created_at: datetime
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class AgentResult:
    """Result from individual agent processing"""
    agent_name: str
    task_id: str
    success: bool
    result: Any
    error: Optional[str] = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class CollaborativeResult:
    """Combined result from multiple agents"""
    task_id: str
    agent_results: List[AgentResult]
    combined_result: Any
    success: bool
    total_time: float
    summary: str
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


class AgentManager:
    """Multi-agent coordination and management system"""
    
    def __init__(self, agents: Dict[str, BaseAgent] = None, 
                 vector_store: VectorStore = None, 
                 memory_manager: MemoryManager = None):
        self.agents = agents or {}
        self.vector_store = vector_store
        self.memory_manager = memory_manager
        self.task_queue = []
        self.active_tasks = {}
        self.completed_tasks = {}
        
        # Agent capabilities registry
        self.agent_capabilities = {}
        self._register_agent_capabilities()
        
        logger.info(f"Initialized AgentManager with {len(self.agents)} agents")
    
    def _register_agent_capabilities(self):
        """Register agent capabilities"""
        for name, agent in self.agents.items():
            capabilities = {
                "can_analyze_issues": hasattr(agent, 'analyze_issue'),
                "can_generate_code": hasattr(agent, 'generate_code'),
                "can_search_docs": hasattr(agent, 'search_documentation'),
                "can_manage_git": hasattr(agent, 'git_operations'),
                "can_rag": hasattr(agent, 'rag_query')
            }
            self.agent_capabilities[name] = capabilities
    
    def register_agent(self, name: str, agent: BaseAgent):
        """Register a new agent"""
        self.agents[name] = agent
        self._register_agent_capabilities()
        logger.info(f"Registered agent: {name}")
    
    def unregister_agent(self, name: str):
        """Unregister an agent"""
        if name in self.agents:
            del self.agents[name]
            if name in self.agent_capabilities:
                del self.agent_capabilities[name]
            logger.info(f"Unregistered agent: {name}")
    
    def create_task(self, task_type: str, data: Dict[str, Any], 
                  priority: str = "medium", deadline: datetime = None,
                  metadata: Dict[str, Any] = None) -> str:
        """Create a new task for processing"""
        task_id = f"task_{int(datetime.now().timestamp() * 1000)}"
        
        task = Task(
            id=task_id,
            type=task_type,
            data=data,
            priority=priority,
            created_at=datetime.now(),
            deadline=deadline,
            metadata=metadata or {}
        )
        
        self.task_queue.append(task)
        
        # Store in memory
        if self.memory_manager:
            self.memory_manager.remember(
                key=f"task_{task_id}",
                value=task.__dict__,
                memory_type="task",
                importance={"high": 1.0, "medium": 0.7, "low": 0.4}.get(priority, 0.5)
            )
        
        logger.info(f"Created task {task_id} of type {task_type}")
        return task_id
    
    async def process_task(self, task_id: str) -> CollaborativeResult:
        """Process task using appropriate agents"""
        try:
            # Get task from queue or active tasks
            task = self._get_task(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            # Move to active tasks
            self.active_tasks[task_id] = task
            start_time = datetime.now()
            
            # Determine which agents should process this task
            selected_agents = self._select_agents_for_task(task)
            
            # Process task with selected agents
            agent_results = []
            for agent_name in selected_agents:
                if agent_name in self.agents:
                    result = await self._process_with_agent(
                        self.agents[agent_name], task
                    )
                    agent_results.append(result)
            
            # Combine results
            combined_result = await self._combine_agent_results(
                agent_results, task
            )
            
            # Create collaborative result
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            collaborative_result = CollaborativeResult(
                task_id=task_id,
                agent_results=agent_results,
                combined_result=combined_result,
                success=any(r.success for r in agent_results),
                total_time=processing_time,
                summary=await self._generate_task_summary(task, agent_results),
                recommendations=await self._generate_recommendations(task, agent_results)
            )
            
            # Move to completed tasks
            self.completed_tasks[task_id] = collaborative_result
            
            # Store result in memory
            if self.memory_manager:
                self.memory_manager.remember(
                    key=f"result_{task_id}",
                    value=collaborative_result.__dict__,
                    memory_type="result",
                    importance=0.8
                )
            
            # Remove from active tasks
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            
            logger.info(f"Completed task {task_id} with {len(agent_results)} agent results")
            return collaborative_result
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            
            # Create error result
            error_result = CollaborativeResult(
                task_id=task_id,
                agent_results=[],
                combined_result=None,
                success=False,
                total_time=0,
                summary=f"Error processing task: {str(e)}",
                recommendations=[]
            )
            
            return error_result
    
    def _get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        # Check active tasks first
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        
        # Check task queue
        for task in self.task_queue:
            if task.id == task_id:
                return task
        
        # Check completed tasks
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id].combined_result.get('task') if self.completed_tasks[task_id].combined_result else None
        
        return None
    
    def _select_agents_for_task(self, task: Task) -> List[str]:
        """Select appropriate agents for task processing"""
        selected_agents = []
        
        # Task type to agent mapping
        task_agent_mapping = {
            "github_issue": ["github_issue"],
            "github_issue_analysis": ["github_issue", "documentation"],
            "code_analysis": ["code_agent"],
            "documentation_search": ["documentation"],
            "git_operations": ["git_agent"],
            "general_query": ["general_agent"],
            "collaborative_task": ["github_issue", "code_agent", "documentation"]
        }
        
        # Get agents for task type
        agents_for_task = task_agent_mapping.get(task.type, ["general_agent"])
        
        # Filter by available agents and capabilities
        for agent_name in agents_for_task:
            if agent_name in self.agents:
                if self._agent_can_handle_task(self.agents[agent_name], task):
                    selected_agents.append(agent_name)
        
        # Sort by priority and capabilities
        selected_agents = self._prioritize_agents(selected_agents, task.priority)
        
        return selected_agents
    
    def _agent_can_handle_task(self, agent: BaseAgent, task: Task) -> bool:
        """Check if agent can handle the task"""
        agent_name = agent.name.lower()
        
        # Check based on task type and agent capabilities
        if task.type == "github_issue" and "issue" in agent_name:
            return True
        elif task.type == "github_issue_analysis" and ("issue" in agent_name or "doc" in agent_name):
            return True
        elif task.type == "code_analysis" and "code" in agent_name:
            return True
        elif task.type == "documentation_search" and "doc" in agent_name:
            return True
        elif task.type == "git_operations" and "git" in agent_name:
            return True
        else:
            # Default - general agent can handle most tasks
            return "general" in agent_name or agent_name == "baseagent"
    
    def _prioritize_agents(self, agents: List[str], task_priority: str) -> List[str]:
        """Prioritize agents based on task priority"""
        # Priority weights
        priority_weights = {
            "high": {"github_issue_agent": 1.0, "code_agent": 0.9, "doc_agent": 0.7},
            "medium": {"github_issue_agent": 0.8, "code_agent": 0.8, "doc_agent": 0.8},
            "low": {"github_issue_agent": 0.6, "code_agent": 0.7, "doc_agent": 0.9}
        }
        
        # Get weights for task priority
        weights = priority_weights.get(task_priority, {})
        
        # Sort agents by weight
        weighted_agents = []
        for agent_name in agents:
            weight = weights.get(agent_name, 0.5)
            weighted_agents.append((agent_name, weight))
        
        weighted_agents.sort(key=lambda x: x[1], reverse=True)
        
        return [agent[0] for agent in weighted_agents]
    
    async def _process_with_agent(self, agent: BaseAgent, task: Task) -> AgentResult:
        """Process task with a specific agent"""
        start_time = datetime.now()
        
        try:
            # Create context for agent
            context = AgentContext(
                session_id=f"task_{task.id}",
                user_id="agent_manager",
                conversation_history=[],
                tools_available=agent.list_tools(),
                environment={"task": task.__dict__}
            )
            
            # Prepare task-specific prompt
            prompt = await self._prepare_agent_prompt(agent, task)
            
            # Process with agent
            result = await agent.chat(prompt, context)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return AgentResult(
                agent_name=agent.name,
                task_id=task.id,
                success=True,
                result=result,
                processing_time=processing_time,
                metadata={"agent_type": type(agent).__name__}
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return AgentResult(
                agent_name=agent.name,
                task_id=task.id,
                success=False,
                error=str(e),
                processing_time=processing_time,
                metadata={"error_type": type(e).__name__}
            )
    
    async def _prepare_agent_prompt(self, agent: BaseAgent, task: Task) -> str:
        """Prepare task-specific prompt for agent"""
        task_prompts = {
            "github_issue": f"""
            Analyze this GitHub issue and provide insights:
            
            Issue Data: {json.dumps(task.data, indent=2)}
            
            Please analyze:
            1. Issue category and priority
            2. Root cause analysis
            3. Suggested solutions
            4. Required code changes
            """,
            
            "code_analysis": f"""
            Analyze this code and provide feedback:
            
            Code Data: {json.dumps(task.data, indent=2)}
            
            Please analyze:
            1. Code quality issues
            2. Security vulnerabilities
            3. Performance optimizations
            4. Best practices recommendations
            """,
            
            "documentation_search": f"""
            Search for relevant documentation for:
            
            Query: {task.data.get('query', '')}
            Context: {task.data.get('context', '')}
            
            Please find:
            1. Relevant documentation sections
            2. Code examples
            3. Best practices
            4. Related resources
            """
        }
        
        return task_prompts.get(task.type, f"Process this task: {json.dumps(task.data, indent=2)}")
    
    async def _combine_agent_results(self, agent_results: List[AgentResult], 
                                 task: Task) -> Any:
        """Combine results from multiple agents"""
        if not agent_results:
            return {"error": "No agent results available"}
        
        # Filter successful results
        successful_results = [r for r in agent_results if r.success]
        
        if not successful_results:
            return {"error": "No successful agent results"}
        
        # Combine based on task type
        if task.type == "github_issue":
            return await self._combine_issue_analysis_results(successful_results)
        elif task.type == "code_analysis":
            return await self._combine_code_analysis_results(successful_results)
        elif task.type == "documentation_search":
            return await self._combine_documentation_results(successful_results)
        else:
            # Default combination
            return {
                "combined_results": [r.result for r in successful_results],
                "agent_contributions": {r.agent_name: r.result for r in successful_results}
            }
    
    async def _combine_issue_analysis_results(self, results: List[AgentResult]) -> Dict[str, Any]:
        """Combine GitHub issue analysis results"""
        combined = {
            "analysis": {},
            "suggestions": [],
            "confidence": 0,
            "agent_insights": {}
        }
        
        # Extract analysis from each agent
        for result in results:
            if isinstance(result.result, dict):
                combined["analysis"][result.agent_name] = result.result
                combined["agent_insights"][result.agent_name] = {
                    "processing_time": result.processing_time,
                    "confidence": result.result.get("confidence", 0.5)
                }
                
                # Add suggestions
                if "suggestions" in result.result:
                    combined["suggestions"].extend(result.result["suggestions"])
                
                # Update confidence
                if "confidence" in result.result:
                    combined["confidence"] += result.result["confidence"]
        
        # Average confidence
        if results:
            combined["confidence"] /= len(results)
        
        return combined
    
    async def _combine_code_analysis_results(self, results: List[AgentResult]) -> Dict[str, Any]:
        """Combine code analysis results"""
        combined = {
            "issues": [],
            "suggestions": [],
            "security_issues": [],
            "performance_issues": [],
            "agent_insights": {}
        }
        
        for result in results:
            if isinstance(result.result, dict):
                combined["agent_insights"][result.agent_name] = {
                    "processing_time": result.processing_time,
                    "issues_found": len(result.result.get("issues", []))
                }
                
                # Collect issues by category
                if "issues" in result.result:
                    combined["issues"].extend(result.result["issues"])
                
                if "security_issues" in result.result:
                    combined["security_issues"].extend(result.result["security_issues"])
                
                if "performance_issues" in result.result:
                    combined["performance_issues"].extend(result.result["performance_issues"])
                
                if "suggestions" in result.result:
                    combined["suggestions"].extend(result.result["suggestions"])
        
        return combined
    
    async def _combine_documentation_results(self, results: List[AgentResult]) -> Dict[str, Any]:
        """Combine documentation search results"""
        combined = {
            "documents": [],
            "relevant_sections": [],
            "code_examples": [],
            "agent_insights": {}
        }
        
        for result in results:
            if isinstance(result.result, dict):
                combined["agent_insights"][result.agent_name] = {
                    "processing_time": result.processing_time,
                    "documents_found": len(result.result.get("documents", []))
                }
                
                # Collect documentation
                if "documents" in result.result:
                    combined["documents"].extend(result.result["documents"])
                
                if "relevant_sections" in result.result:
                    combined["relevant_sections"].extend(result.result["relevant_sections"])
                
                if "code_examples" in result.result:
                    combined["code_examples"].extend(result.result["code_examples"])
        
        return combined
    
    async def _generate_task_summary(self, task: Task, 
                                  agent_results: List[AgentResult]) -> str:
        """Generate summary of task processing"""
        successful_agents = [r for r in agent_results if r.success]
        failed_agents = [r for r in agent_results if not r.success]
        
        summary = f"""Task {task.id} ({task.type}) Processing Summary

**Agents Involved**: {len(agent_results)} total
**Successful**: {len(successful_agents)} agents
**Failed**: {len(failed_agents)} agents

**Successful Agents**:
"""
        
        for result in successful_agents:
            summary += f"- {result.agent_name}: Success ({result.processing_time:.2f}s)\n"
        
        for result in failed_agents:
            summary += f"- {result.agent_name}: Failed - {result.error}\n"
        
        return summary
    
    async def _generate_recommendations(self, task: Task, 
                                   agent_results: List[AgentResult]) -> List[str]:
        """Generate recommendations based on agent results"""
        recommendations = []
        
        successful_results = [r for r in agent_results if r.success]
        
        if not successful_results:
            recommendations.append("Consider retrying the task with different agents")
            return recommendations
        
        # Task-specific recommendations
        if task.type == "github_issue":
            recommendations.extend([
                "Review all agent suggestions before implementing",
                "Test changes in a separate branch",
                "Update documentation based on findings"
            ])
        elif task.type == "code_analysis":
            recommendations.extend([
                "Address security issues first",
                "Implement performance optimizations gradually",
                "Add unit tests for fixed issues"
            ])
        elif task.type == "documentation_search":
            recommendations.extend([
                "Cross-reference multiple documentation sources",
                "Check for latest API changes",
                "Consider code examples in context"
            ])
        
        # Performance-based recommendations
        slow_agents = [r for r in successful_results if r.processing_time > 5.0]
        if slow_agents:
            recommendations.append(f"Consider optimizing {', '.join([a.agent_name for a in slow_agents])} performance")
        
        return recommendations
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            return {
                "status": "active",
                "task": task.__dict__,
                "started_at": task.created_at.isoformat()
            }
        elif task_id in self.completed_tasks:
            result = self.completed_tasks[task_id]
            return {
                "status": "completed",
                "task_id": task_id,
                "success": result.success,
                "total_time": result.total_time,
                "summary": result.summary,
                "agent_count": len(result.agent_results)
            }
        elif any(t.id == task_id for t in self.task_queue):
            return {
                "status": "queued",
                "task_id": task_id,
                "queue_position": next(i for i, t in enumerate(self.task_queue) if t.id == task_id)
            }
        else:
            return None
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        return {
            "total_agents": len(self.agents),
            "agent_capabilities": self.agent_capabilities,
            "agent_details": {
                name: agent.get_status() 
                for name, agent in self.agents.items()
            },
            "task_queue_size": len(self.task_queue),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks)
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.completed_tasks:
            return {
                "total_tasks": 0,
                "average_processing_time": 0,
                "success_rate": 0,
                "agent_performance": {}
            }
        
        # Calculate statistics
        total_tasks = len(self.completed_tasks)
        successful_tasks = sum(1 for t in self.completed_tasks.values() if t.success)
        total_time = sum(t.total_time for t in self.completed_tasks.values())
        
        # Agent performance
        agent_performance = {}
        for result in self.completed_tasks.values():
            for agent_result in result.agent_results:
                agent_name = agent_result.agent_name
                if agent_name not in agent_performance:
                    agent_performance[agent_name] = {
                        "tasks_completed": 0,
                        "success_count": 0,
                        "total_time": 0,
                        "average_time": 0
                    }
                
                perf = agent_performance[agent_name]
                perf["tasks_completed"] += 1
                perf["total_time"] += agent_result.processing_time
                if agent_result.success:
                    perf["success_count"] += 1
                
                perf["average_time"] = perf["total_time"] / perf["tasks_completed"]
        
        return {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "success_rate": (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "average_processing_time": total_time / total_tasks if total_tasks > 0 else 0,
            "agent_performance": agent_performance
        }


# Global instance
_agent_manager: Optional[AgentManager] = None


def get_agent_manager(agents: Dict[str, BaseAgent] = None,
                   vector_store: VectorStore = None,
                   memory_manager: MemoryManager = None) -> AgentManager:
    """Get global agent manager instance"""
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager(agents, vector_store, memory_manager)
    return _agent_manager


# Test function
async def test_agent_manager():
    """Test agent manager functionality"""
    try:
        from src.agents.base_agent import SimpleAgent
        
        # Create test agents
        agents = {
            "github_agent": SimpleAgent("GitHubAgent"),
            "code_agent": SimpleAgent("CodeAgent"),
            "doc_agent": SimpleAgent("DocAgent")
        }
        
        # Create agent manager
        manager = AgentManager(agents)
        
        # Create test task
        task_id = manager.create_task(
            task_type="github_issue",
            data={
                "issue": {
                    "title": "Bug: Login fails",
                    "body": "Users cannot login with correct credentials"
                }
            },
            priority="high"
        )
        
        print(f"Created task: {task_id}")
        
        # Process task
        result = await manager.process_task(task_id)
        
        print(f"Task result:")
        print(f"Success: {result.success}")
        print(f"Summary: {result.summary}")
        print(f"Total time: {result.total_time:.2f}s")
        
        # Get status
        status = manager.get_task_status(task_id)
        print(f"Task status: {json.dumps(status, indent=2, default=str)}")
        
        # Get performance stats
        stats = manager.get_performance_stats()
        print(f"Performance stats: {json.dumps(stats, indent=2, default=str)}")
        
    except Exception as e:
        print(f"Error testing agent manager: {e}")


if __name__ == "__main__":
    asyncio.run(test_agent_manager())
