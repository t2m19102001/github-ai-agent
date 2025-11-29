#!/usr/bin/env python3
"""
Logging configuration and utilities
Centralized logging for the entire application
"""

import logging
import logging.handlers
from pathlib import Path
from src.config import LOG_LEVEL, LOG_FORMAT, LOG_FILE, DEBUG


def setup_logging():
    """Setup centralized logging for the application"""
    
    # Create logs directory
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    
    # File handler
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(LOG_LEVEL)
    file_formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    
    # Add handlers
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)


# Setup logging on import
setup_logging()
