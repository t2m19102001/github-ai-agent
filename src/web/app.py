# src/web/app.py
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uuid

from src.agents.code_agent import CodeChatAgent
from src.config.settings import PROVIDER, MODELS, GROQ_KEY, LLMProvider
from src.utils.token_manager import TokenManager

# Validate API keys at startup (with warning instead of crash)
try:
    from src.config.settings import validate_api_keys
    validate_api_keys()
except ValueError as e:
    print(f"⚠️ Warning: {e}")
    print("Server will start but may fail on first request if API key is missing")

app = FastAPI()
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")
templates = Jinja2Templates(directory="src/web/templates")

# Khởi tạo LLM provider dựa trên config
if PROVIDER == "groq":
    from langchain_groq import ChatGroq
    llm = ChatGroq(groq_api_key=GROQ_KEY, model_name=MODELS[PROVIDER])
    print(f"🚀 Using Groq API with model: {MODELS[PROVIDER]}")
else:
    # Test Ollama connection before using it
    import requests
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            from langchain_ollama import OllamaLLM
            llm = OllamaLLM(model=MODELS[PROVIDER])
            print(f"🚀 Using Ollama (local) with model: {MODELS[PROVIDER]}")
        else:
            raise ConnectionError("Ollama not responding")
    except Exception as e:
        print(f"❌ Ollama not accessible: {e}")
        print(f"⚠️ Please start Ollama or set LLM_PROVIDER=groq")
        print(f"Falling back to dummy LLM (will fail on chat)")
        # Create a dummy LLM that will fail gracefully
        class DummyLLM:
            def invoke(self, prompt):
                return "❌ Ollama is not running. Please start Ollama with: ollama serve"
            def call(self, messages):
                return "❌ Ollama is not running. Please start Ollama with: ollama serve"
        llm = DummyLLM()
        print("⚠️ Server started but LLM is unavailable")

agent = CodeChatAgent(llm_provider=llm)
token_manager = TokenManager()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/status")
async def status():
    ready = True
    provider = str(PROVIDER)
    model = MODELS.get(PROVIDER)
    if provider == "groq" and not GROQ_KEY:
        ready = False
    return {"provider": provider, "model": model, "ready": ready}

@app.middleware("http")
async def timing_middleware(request, call_next):
    import time
    start = time.time()
    response = await call_next(request)
    d = int((time.time() - start) * 1000)
    try:
        print(f"REQ {request.url.path} {d}ms")
    except Exception:
        pass
    return response

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            user_msg = data.strip()
            if user_msg:
                user_msg = token_manager.truncate_text(user_msg, 2000)

            # Help command
            if user_msg.lower() in ["/help", "help", "giúp tôi"]:
                help_text = """🤖 **My Private Copilot - Commands**

**🔧 Testing & Auto-Fix:**
• `/autofix` - Chạy all tests, hiện kết quả
• `/autofix <file>` - Auto test & fix file cụ thể
• `/test` - Chạy pytest với verbose
• `/test <args>` - Chạy pytest với args tùy chỉnh

**📚 RAG & Memory:**
• `Index repo trước` - Index toàn bộ codebase (chạy 1 lần đầu)
• Hỏi gì cũng được - AI sẽ tự tìm context từ repo

**🔀 Git Commands:**
• `commit nhé` - Tự động commit & push
• `commit <message>` - Commit với message cụ thể
• `tạo branch <name>` - Tạo branch mới
• `có gì thay đổi` - Xem git status

**💬 Chat:**
• Hỏi về code, architecture, bugs...
• AI nhớ toàn bộ lịch sử chat!

Gõ bất kỳ câu hỏi để bắt đầu!"""
                await websocket.send_text(help_text)
                continue

            # Lệnh đặc biệt: Index repo
            if user_msg == "Index repo trước":
                from src.tools.codebase_rag import index_repo
                index_repo()
                await websocket.send_text("Index repo xong! Giờ hỏi gì cũng được.")
                continue

            # AUTO TEST & FIX LOOP - slash command đỉnh cao
            if user_msg.lower().startswith("/autofix"):
                from src.tools.autofix_tool import run_pytest
                
                # Parse target file (optional)
                parts = user_msg.split()
                if len(parts) > 1:
                    target_file = parts[1]
                    try:
                        with open(target_file, "r", encoding="utf-8") as f:
                            current_code = f.read()
                        await websocket.send_text(f"🔧 Bắt đầu auto test & fix cho: {target_file}")
                    except FileNotFoundError:
                        await websocket.send_text(f"❌ File không tồn tại: {target_file}")
                        continue
                else:
                    # No file specified - just run tests
                    await websocket.send_text("🧪 Chạy tất cả tests...")
                
                # Run tests
                result = run_pytest("-v")
                
                if result["success"]:
                    response_text = f"✅ **TẤT CẢ TESTS ĐÃ PASS!**\n\n```\n{result['output']}\n```"
                else:
                    response_text = f"❌ **Tests failed:**\n\n```\n{result['output']}\n```\n\n💡 Gửi code cần fix và tôi sẽ sửa tự động!"
                
                await websocket.send_text(response_text)
                continue
            
            # Run specific test command
            if user_msg.lower().startswith("/test"):
                from src.tools.autofix_tool import run_pytest
                
                # Extract pytest args
                test_args = user_msg[5:].strip() or "-v"
                
                await websocket.send_text(f"🧪 Chạy pytest {test_args}...")
                result = run_pytest(test_args)
                
                if result["success"]:
                    response_text = f"✅ Tests passed!\n\n```\n{result['output']}\n```"
                else:
                    response_text = f"❌ Tests failed:\n\n```\n{result['output']}\n```"
                
                await websocket.send_text(response_text)
                continue

            # Auto-detect Git commands
            lower_msg = user_msg.lower()
            
            # Git commit & push
            if any(x in lower_msg for x in ["commit", "push", "đẩy code"]):
                from src.tools.git_tool import git_commit
                # Extract commit message
                message = user_msg
                for word in ["commit", "push", "đẩy code", "code", "nhé", "với"]:
                    message = message.replace(word, "").strip()
                if not message or len(message) < 3:
                    message = "AI auto update - FastAPI WebSocket integration"
                
                result = git_commit(message)
                if result["success"]:
                    response_text = f"✅ Đã tự động commit & push!\n\n📝 Message: {message}\n\n{result.get('output', '')}"
                else:
                    response_text = f"❌ Lỗi khi commit:\n{result.get('error', 'Unknown error')}"
                
                await websocket.send_text(response_text)
                continue
            
            # Git create branch
            if any(x in lower_msg for x in ["tạo branch", "create branch", "new branch"]):
                from src.tools.git_tool import git_create_branch
                # Extract branch name
                words = user_msg.split()
                branch_name = words[-1] if words[-1].replace("-", "").replace("_", "").isalnum() else "feature/ai-update"
                
                result = git_create_branch(branch_name)
                if result["success"]:
                    response_text = f"✅ {result['message']}\n\nBạn có thể tiếp tục code, khi xong gõ 'commit nhé' để tôi commit & push giúp!"
                else:
                    response_text = f"❌ {result['message']}: {result.get('error', '')}"
                
                await websocket.send_text(response_text)
                continue
            
            # Git status
            if any(x in lower_msg for x in ["git status", "trạng thái", "có gì thay đổi"]):
                from src.tools.git_tool import git_status
                result = git_status()
                if result["success"]:
                    if result["has_changes"]:
                        response_text = f"📝 **Có thay đổi:**\n```\n{result['status']}\n```"
                    else:
                        response_text = "✅ Không có thay đổi nào"
                else:
                    response_text = f"❌ Lỗi: {result.get('error', '')}"
                
                await websocket.send_text(response_text)
                continue

            try:
                response = agent.chat(user_msg, session_id=session_id)
            except Exception as e:
                response = f"❌ Lỗi tạm thời: {str(e)}. Vui lòng thử lại!"
                print(f"❌ Chat error: {e}")
            try:
                from src.utils.text import format_for_display
                response = format_for_display(response)
            except Exception:
                pass
            await websocket.send_text(response)

    except WebSocketDisconnect:
        print(f"Client {session_id} ngắt kết nối")
