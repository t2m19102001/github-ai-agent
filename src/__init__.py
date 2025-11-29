"""
GitHub AI Agent - Professional AI Agent for GitHub Issues
Modular architecture with LLM integration, code execution, and Git operations
"""

__version__ = "2.0.0"
__author__ = "Your Name"
__license__ = "MIT"

from src.config import (
    DEBUG,
    ENV,
    GITHUB_TOKEN,
    REPO_FULL_NAME,
    GROQ_API_KEY,
    GROQ_MODEL,
    print_config,
    validate_config
)

__all__ = [
    "DEBUG",
    "ENV",
    "GITHUB_TOKEN",
    "REPO_FULL_NAME",
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "print_config",
    "validate_config",
]
