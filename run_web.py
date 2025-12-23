#!/usr/bin/env python3
"""
Web UI entry point
Run with: python run_web.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import setup_logging, get_logger
from src.core.config import validate_config, print_config, CHAT_HOST, CHAT_PORT, DEBUG

logger = get_logger(__name__)


def main():
    """Main entry point for web interface"""
    try:
        setup_logging()
        try:
            validate_config()
        except ValueError as e:
            print(f"⚠️ Configuration warning: {e}")
            print("Proceeding with startup for local development. Some features may be disabled.")
        print_config()
        logger.info("🚀 Starting Code Chat Web Server...")

        # Prefer FastAPI app
        from src.web.app import app as fastapi_app
        print(f"\n{'='*70}")
        print(f"🌐 FastAPI server on http://{CHAT_HOST}:{CHAT_PORT}")
        print(f"{'='*70}\n")
        import uvicorn
        uvicorn.run(fastapi_app, host=CHAT_HOST, port=CHAT_PORT, reload=DEBUG, log_level="debug" if DEBUG else "info")
    
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
