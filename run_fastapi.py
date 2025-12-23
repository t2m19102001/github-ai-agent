#!/usr/bin/env python3
"""
REST API entry point
Run with: python run_fastapi.py
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import setup_logging, get_logger
from src.core.config import API_PORT, API_DEBUG

logger = get_logger(__name__)


def main():
    try:
        setup_logging()
        from src.agent.api import app
        import uvicorn
        logger.info(f"🚀 Starting REST API on http://0.0.0.0:{API_PORT}")
        uvicorn.run(app, host="0.0.0.0", port=API_PORT, reload=API_DEBUG, log_level="debug" if API_DEBUG else "info")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

