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
from src.config import validate_config, print_config, CHAT_HOST, CHAT_PORT, DEBUG

logger = get_logger(__name__)


def main():
    """Main entry point for web interface"""
    try:
        # Setup logging
        setup_logging()
        
        # Validate configuration
        validate_config()
        
        # Print config
        print_config()
        
        logger.info("🚀 Starting Code Chat Web Server...")
        
        # Create Flask app
        from src.web.app import create_app
        
        app = create_app()
        
        print(f"\n{'='*70}")
        print(f"🌐 Web Server running on http://{CHAT_HOST}:{CHAT_PORT}")
        print(f"{'='*70}\n")
        
        app.run(
            host=CHAT_HOST,
            port=CHAT_PORT,
            debug=DEBUG,
            use_reloader=DEBUG
        )
    
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
