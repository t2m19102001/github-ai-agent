#!/usr/bin/env python3
"""
Logging configuration and utilities
Centralized logging for the entire application
"""

import logging
import logging.handlers
from pathlib import Path
from src.core.config import LOG_LEVEL, LOG_FORMAT, LOG_FILE, DEBUG


def setup_logging():
    """Setup centralized logging for the application"""

    # Create logs directory
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    
    # Only construct handlers when they will be attached. Creating a file
    # handler before this check leaks an open descriptor when a host such as
    # pytest has already configured root logging.
    if not root_logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(LOG_LEVEL)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(LOG_LEVEL)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)


# Setup logging on import
setup_logging()
