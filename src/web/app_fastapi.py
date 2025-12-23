#!/usr/bin/env python3
"""
FastAPI Web Application with WebSocket support for real-time chat
Modern UI backend with streaming LLM responses and long-term memory
"""

from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.agents.code_agent import CodeChatAgent
from src.agent.ai_provider import get_default_provider, ProviderAdapter
from src.utils.logger import get_logger
from src.core.config import DEBUG, CHAT_PORT
from src.tools.git_tool import git_commit, git_create_branch, git_status, git_diff, git_branch_list, git_log
from src.tools.autofix_tool import run_pytest, auto_fix
import uuid
import json

logger = get_logger(__name__)

app = FastAPI(title="GitHub AI Agent", version="2.0")

# Static files and templates
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")
templates = Jinja2Templates(directory="src/web/templates")

# Initialize LLM provider
llm = ProviderAdapter(get_default_provider())

# Store active sessions {session_id: agent}
active_sessions = {}

logger.info("✅ FastAPI app initialized")


@app.get("/")
async def index(request: Request):
    """Serve main chat interface with HTMX"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    """WebSocket endpoint for streaming chat responses with session memory"""
    await ws.accept()
    
    # Create new session with unique agent
    session_id = str(uuid.uuid4())
    agent = CodeChatAgent(llm_provider=llm)
    active_sessions[session_id] = agent
    
    logger.info(f"🔌 WebSocket connected - Session: {session_id}")
    
    # Send session ID to client
    await ws.send_text(json.dumps({
        "type": "session",
        "session_id": session_id
    }))
    
    try:
        while True:
            # Receive message from client
            data = await ws.receive_text()
            
            # Try to parse as JSON (for future features)
            try:
                message_data = json.loads(data)
                message = message_data.get("message", data)
            except:
                message = data
            
            logger.info(f"📨 [{session_id[:8]}] Received: {message[:50]}...")
            
            # Handle slash commands
            if message.startswith("/autofix"):
                # Auto-fix command
                logger.info(f"🔧 Auto-fix command detected")
                
                # Extract code if provided, otherwise use a default test
                code_to_fix = message.replace("/autofix", "").strip()
                
                if not code_to_fix:
                    await ws.send_text(json.dumps({
                        "type": "message",
                        "content": "⚠️ Usage: /autofix <code>\n\nExample: /autofix def test(): assert 1 == 2"
                    }))
                    continue
                
                # Send progress update
                await ws.send_text(json.dumps({
                    "type": "message",
                    "content": "🔄 Starting auto-fix loop...\n"
                }))
                
                # Run auto-fix
                result = auto_fix(code_to_fix, agent=agent, max_iterations=5)
                
                # Format response
                if result["success"]:
                    response = f"✅ {result['message']}\n\n"
                    response += f"**Iterations:** {len(result['iterations'])}\n\n"
                    response += f"**Fixed Code:**\n```python\n{result['code']}\n```"
                else:
                    response = f"❌ {result['message']}\n\n"
                    response += f"**Iterations attempted:** {len(result['iterations'])}\n\n"
                    if result.get('final_error'):
                        response += f"**Last error:**\n{result['final_error'][:500]}"
                
                await ws.send_text(json.dumps({
                    "type": "message",
                    "content": response
                }))
                continue
            
            # Get response from agent (with memory)
            response = agent.chat(message)
            
            # Stream response character by character for real-time effect
            if isinstance(response, str):
                # Send start marker
                await ws.send_text(json.dumps({
                    "type": "start",
                    "session_id": session_id
                }))
                
                # Simulate streaming by sending chunks
                chunk_size = 10  # characters per chunk
                for i in range(0, len(response), chunk_size):
                    chunk = response[i:i+chunk_size]
                    await ws.send_text(json.dumps({
                        "type": "chunk",
                        "content": chunk
                    }))
                    # Small delay for visual streaming effect
                    import asyncio
                    await asyncio.sleep(0.01)
                
                # Send end marker
                await ws.send_text(json.dumps({
                    "type": "end",
                    "session_id": session_id
                }))
            else:
                await ws.send_text(json.dumps({
                    "type": "message",
                    "content": str(response)
                }))
            
    except Exception as e:
        logger.error(f"WebSocket error [{session_id[:8]}]: {e}")
    finally:
        # Cleanup session
        if session_id in active_sessions:
            del active_sessions[session_id]
        logger.info(f"🔌 WebSocket disconnected - Session: {session_id}")


# ========== GIT OPERATIONS ENDPOINTS ==========

@app.post("/api/git/commit")
async def api_git_commit(request: Request):
    """Commit all changes with message"""
    data = await request.json()
    message = data.get("message", "").strip()
    
    if not message:
        return {"success": False, "error": "Commit message required"}
    
    logger.info(f"📝 Git commit: {message}")
    result = git_commit(message)
    return result


@app.post("/api/git/branch")
async def api_git_branch(request: Request):
    """Create new branch"""
    data = await request.json()
    name = data.get("name", "").strip()
    
    if not name:
        return {"success": False, "error": "Branch name required"}
    
    logger.info(f"🌿 Git branch: {name}")
    result = git_create_branch(name)
    return result


@app.get("/api/git/status")
async def api_git_status():
    """Get Git status"""
    logger.info("📊 Git status")
    result = git_status()
    return result


@app.get("/api/git/diff")
async def api_git_diff():
    """Get Git diff"""
    logger.info("🔍 Git diff")
    result = git_diff()
    return result


@app.get("/api/git/branches")
async def api_git_branches():
    """List all branches"""
    logger.info("🌳 Git branches")
    result = git_branch_list()
    return result


@app.get("/api/git/log")
async def api_git_log(n: int = 10):
    """Get commit history"""
    logger.info(f"📜 Git log (n={n})")
    result = git_log(n)
    return result


# ========== AUTO-FIX ENDPOINTS ==========

@app.post("/api/autofix")
async def api_autofix(request: Request):
    """Auto test & fix code"""
    data = await request.json()
    code = data.get("code", "").strip()
    max_iterations = data.get("max_iterations", 5)
    
    if not code:
        return {"success": False, "error": "Code required"}
    
    logger.info(f"🔧 Auto-fix request (max {max_iterations} iterations)")
    
    # Need agent instance - create temporary one
    from src.llm.groq import GroqProvider
    from src.agents.code_agent import CodeChatAgent
    
    temp_llm = GroqProvider()
    temp_agent = CodeChatAgent(llm_provider=temp_llm)
    
    result = auto_fix(code, agent=temp_agent, max_iterations=max_iterations)
    return result


@app.post("/api/pytest")
async def api_pytest(request: Request):
    """Run pytest"""
    data = await request.json()
    args = data.get("args", "-q")
    
    logger.info(f"🧪 Running pytest: {args}")
    result = run_pytest(args)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=CHAT_PORT, log_level="info")
