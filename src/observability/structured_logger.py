#!/usr/bin/env python3
"""
Structured JSON Logging.

Production-grade implementation with:
- JSON-formatted log output
- Structured fields
- Trace ID propagation
- Request ID support
- Log level filtering
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger


class StructuredLogger:
    """
    Structured JSON logger.
    
    Outputs logs in JSON format with consistent structure.
    """
    
    def __init__(self, name: str):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
        """
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        self._logger.handlers = []
        
        # Add JSON handler
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        self._logger.addHandler(handler)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._logger.critical(message, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._logger.debug(message, extra=kwargs)


class JSONFormatter(logging.Formatter):
    """JSON log formatter."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add trace context if available
        if hasattr(record, 'trace_id') and record.trace_id:
            log_data["trace_id"] = record.trace_id
        
        if hasattr(record, 'request_id') and record.request_id:
            log_data["request_id"] = record.request_id
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        return json.dumps(log_data)
