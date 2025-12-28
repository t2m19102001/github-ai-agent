#!/usr/bin/env python3
"""
FastAPI Main Application
GitHub AI Agent - Phase 3 Multi-agent Workflow API
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Request, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import uvicorn
import asyncio
import json
import tempfile
import os

# Import logging system
from src.memory.log_manager import get_logs, get_log_stats, log_activity

# Import Phase 3 components
from src.agents.agent_manager import AgentManager, Task
from src.agents.github_issue_agent import GitHubIssueAgent
from src.agents.code_agent import CodeChatAgent
from src.agents.doc_agent import DocumentationAgent
from src.agents.image_agent import ImageAgent
from src.rag.vector_store import VectorStore
from src.memory.memory_manager import MemoryManager
from src.llm.provider import get_llm_provider
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="GitHub AI Agent API",
    description="Multi-agent workflow for GitHub issue analysis - Phase 5",
    version="5.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup templates and static files
templates = Jinja2Templates(directory="src/web/templates")
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

# Initialize components
vector_store = VectorStore(dimension=128, storage_path="data/vector_store")
memory_manager = MemoryManager("data/memory.db")
llm_provider = get_llm_provider("mock")

# Initialize agents
github_agent = GitHubIssueAgent(
    repo="default/repo",
    token="mock_token",
    config={"test_mode": True}
)

doc_agent = DocumentationAgent(config={"test_mode": True})
code_agent = CodeChatAgent(llm_provider=llm_provider)
image_agent = ImageAgent(config={"test_mode": True})

# Agent manager
agent_manager = AgentManager({
    "github_issue": github_agent,
    "documentation": doc_agent,
    "code": code_agent,
    "image": image_agent
})

# Initialize ImageAgent with RAG store
image_agent_with_rag = ImageAgent(
    rag_store=vector_store,
    config={"test_mode": True}
)

# Templates
templates = Jinja2Templates(directory="src/web/templates")

# Pydantic models
class IssueInput(BaseModel):
    """Issue input model"""
    title: str = Field(..., description="Issue title")
    body: str = Field(..., description="Issue body/description")
    file: Optional[str] = Field(None, description="Related file path")
    labels: Optional[List[str]] = Field(default_factory=list, description="Issue labels")
    priority: Optional[str] = Field("medium", description="Issue priority")
    title_embedding: Optional[List[float]] = Field(default_factory=list, description="Title embedding")

class AgentResult(BaseModel):
    """Agent result model"""
    agent_name: str
    success: bool
    result: Dict[str, Any]
    processing_time: float
    error: Optional[str] = None

class WorkflowResponse(BaseModel):
    """Workflow response model"""
    success: bool
    task_id: str
    results: List[AgentResult]
    summary: str
    total_time: float
    metadata: Dict[str, Any]

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with Web UI"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/image-page", response_class=HTMLResponse)
async def image_page(request: Request):
    """Image analysis page"""
    return templates.TemplateResponse("image.html", {"request": request})

@app.post("/analyze_image")
async def analyze_image(file: UploadFile = File(...)):
    """Analyze uploaded image using ImageAgent"""
    try:
        # Log activity
        log_activity(
            agent="ImageAPI",
            action="analyze_image",
            result=f"Processing image: {file.filename}",
            metadata={"filename": file.filename, "content_type": file.content_type}
        )
        
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            # Read and save uploaded file
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Process with ImageAgent
            result = image_agent_with_rag.process(temp_file_path)
            
            # Log successful analysis
            log_activity(
                agent="ImageAPI",
                action="analysis_complete",
                result=f"Successfully analyzed {file.filename}",
                metadata={
                    "filename": file.filename,
                    "success": result.get("success"),
                    "confidence": result.get("confidence_score", 0)
                }
            )
            
            return {"results": result}
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        
        # Log error
        log_activity(
            agent="ImageAPI",
            action="analysis_error",
            result=f"Failed to analyze {file.filename}: {str(e)}",
            status="error",
            metadata={"filename": file.filename, "error": str(e)}
        )
        
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")

@app.get("/logs-page", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Logs page"""
    return templates.TemplateResponse("logs.html", {"request": request})

@app.post("/analyze_issue", response_model=WorkflowResponse)
async def analyze_issue(issue: IssueInput):
    """Analyze GitHub issue using multi-agent workflow"""
    try:
        logger.info(f"Received issue analysis request: {issue.title}")
        
        # Create task for agent manager
        task_data = {
            "type": "github_issue_analysis",
            "data": {
                "title": issue.title,
                "body": issue.body,
                "file": issue.file,
                "labels": issue.labels,
                "priority": issue.priority,
                "title_embedding": issue.title_embedding or [0.0] * 128
            }
        }
        
        # Add task to queue first
        task_id = agent_manager.create_task(
            task_type="github_issue_analysis",
            data=task_data,
            priority=issue.priority or "medium"
        )
        
        # Process task with agent manager
        start_time = asyncio.get_event_loop().time()
        result = await agent_manager.process_task(task_id)
        end_time = asyncio.get_event_loop().time()
        
        # Log the activity
        log_activity(
            agent="AgentManager",
            action="process_task",
            result=f"Task {task_id} processed with {len(result.agent_results)} agents",
            task_id=task_id,
            processing_time=int((end_time - start_time) * 1000)
        )
        
        # Format response
        agent_results = []
        for agent_result in result.agent_results:
            # Convert result to dict if it's not already
            result_data = agent_result.result
            if not isinstance(result_data, dict):
                result_data = {"response": str(result_data)}
            
            agent_results.append(AgentResult(
                agent_name=agent_result.agent_name,
                success=agent_result.success,
                result=result_data,
                processing_time=agent_result.processing_time,
                error=agent_result.error
            ))
        
        response = WorkflowResponse(
            success=result.success,
            task_id=task_id,
            results=agent_results,
            summary=result.summary,
            total_time=end_time - start_time,
            metadata=result.combined_result or {}
        )
        
        logger.info(f"Issue analysis completed: {task_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error analyzing issue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents/status")
async def get_agents_status():
    """Get status of all agents"""
    try:
        status = {
            "agents": [],
            "system_status": "active",
            "timestamp": asyncio.get_event_loop().time()
        }
        
        for agent_name, agent in agent_manager.agents.items():
            agent_status = {
                "name": agent_name,
                "type": type(agent).__name__,
                "status": "active" if hasattr(agent, 'name') else "unknown",
                "capabilities": getattr(agent, 'capabilities', [])
            }
            status["agents"].append(agent_status)
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/stats")
async def get_memory_stats():
    """Get memory system statistics"""
    try:
        stats = memory_manager.get_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/search")
async def search_memory(query: str):
    """Search memory for relevant information"""
    try:
        results = memory_manager.search(query)
        return {
            "success": True,
            "query": query,
            "results": [
                {
                    "key": entry.key,
                    "value": entry.value,
                    "memory_type": entry.memory_type,
                    "importance": entry.importance,
                    "timestamp": entry.timestamp.isoformat()
                }
                for entry in results
            ]
        }
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs")
async def fetch_logs():
    """Get agent activity logs"""
    try:
        logs = get_logs(limit=100)
        return [
            {
                "id": log.id,
                "agent": log.agent,
                "action": log.action,
                "result": log.result,
                "status": log.status,
                "task_id": log.task_id,
                "processing_time": log.processing_time,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None
            }
            for log in logs
        ]
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs/stats")
async def get_logs_statistics():
    """Get log statistics"""
    try:
        stats = get_log_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting log stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vector_store/stats")
async def get_vector_store_stats():
    """Get vector store statistics"""
    try:
        stats = vector_store.get_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting vector store stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vector_store/search")
async def search_vector_store(query: str, k: int = 5):
    """Search vector store for similar documents"""
    try:
        # Generate simple embedding for demo
        import numpy as np
        query_embedding = np.random.rand(128)
        
        results = vector_store.search(query_embedding, k=k)
        return {
            "success": True,
            "query": query,
            "results": [
                {
                    "content": result.document.content,
                    "metadata": result.document.metadata,
                    "score": result.score
                }
                for result in results
            ]
        }
    except Exception as e:
        logger.error(f"Error searching vector store: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "phase": "Phase 3 - Advanced Intelligence",
        "components": {
            "vector_store": "active",
            "memory_manager": "active",
            "agent_manager": "active",
            "llm_provider": "active"
        }
    }

# Static files
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("GitHub AI Agent - Phase 3 starting up...")
    
    # Create data directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/vector_store", exist_ok=True)
    
    # Add some sample documents to vector store
    sample_docs = [
        ("Authentication flow example using JWT tokens", {"type": "tutorial", "topic": "auth"}),
        ("Error handling best practices in Python", {"type": "guide", "topic": "error-handling"}),
        ("GitHub API integration for issue management", {"type": "api", "topic": "github"}),
        ("Multi-agent coordination patterns", {"type": "architecture", "topic": "agents"}),
        ("RAG implementation with vector databases", {"type": "tutorial", "topic": "rag"})
    ]
    
    import numpy as np
    for content, metadata in sample_docs:
        embedding = np.random.rand(128)
        vector_store.add_document(content, metadata, embedding)
    
    logger.info("Application startup complete")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("GitHub AI Agent shutting down...")
    memory_manager.close()
    logger.info("Shutdown complete")

# Run server
if __name__ == "__main__":
    uvicorn.run(
        "src.web.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
