#!/usr/bin/env python3
"""
Run FastAPI application with WebSocket support
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    import uvicorn
    from src.core.config import CHAT_PORT, DEBUG
    
    print("🚀 Starting FastAPI server with WebSocket...")
    print(f"📡 Server: http://localhost:{CHAT_PORT}")
    print(f"🔌 WebSocket: ws://localhost:{CHAT_PORT}/ws")
    
    uvicorn.run(
        "src.web.app_fastapi:app",
        host="0.0.0.0",
        port=CHAT_PORT,
        reload=DEBUG,
        log_level="info"
    )
