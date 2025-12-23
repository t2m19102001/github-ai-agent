#!/usr/bin/env python3
"""
Configuration management for AI Agent
Environment-based settings and constants
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Literal

# Load environment variables
load_dotenv()

# Directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
TESTS_DIR = PROJECT_ROOT / "tests"
DOCS_DIR = PROJECT_ROOT / "docs"
LOGS_DIR = PROJECT_ROOT / "logs"

# Create logs directory if doesn't exist
LOGS_DIR.mkdir(exist_ok=True)

# ============================================================================
# Environment Configuration
# ============================================================================

ENV = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ============================================================================
# GitHub Configuration
# ============================================================================

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_FULL_NAME = os.getenv("REPO_FULL_NAME")

# ============================================================================
# LLM Configuration
# ============================================================================

# GROQ (Primary LLM)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_TIMEOUT = int(os.getenv("GROQ_TIMEOUT", "30"))
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "2048"))
GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.7"))

# HuggingFace (Fallback LLM)
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-2-7b-chat-hf")
HUGGINGFACE_TIMEOUT = int(os.getenv("HUGGINGFACE_TIMEOUT", "60"))

# At least one LLM key required unless using local provider
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

# ============================================================================
# Web Server Configuration
# ============================================================================

CHAT_HOST = os.getenv("CHAT_HOST", "0.0.0.0")
CHAT_PORT = int(os.getenv("CHAT_PORT", "5000"))
FLASK_DEBUG = DEBUG

# ============================================================================
# Agent Configuration
# ============================================================================

AGENT_MODE: Literal["cloud"] = "cloud"  # Only cloud mode supported
MAX_PROMPT_LENGTH = int(os.getenv("MAX_PROMPT_LENGTH", "4000"))
MAX_ISSUE_BODY_LENGTH = int(os.getenv("MAX_ISSUE_BODY_LENGTH", "2000"))

# Code extensions to analyze
CODE_EXTENSIONS = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rb', '.php']

# ============================================================================
# Execution Configuration
# ============================================================================

# Python code execution
ENABLE_CODE_EXECUTION = os.getenv("ENABLE_CODE_EXECUTION", "true").lower() == "true"
CODE_EXECUTION_TIMEOUT = int(os.getenv("CODE_EXECUTION_TIMEOUT", "10"))

# Shell command execution
ENABLE_SHELL_EXECUTION = os.getenv("ENABLE_SHELL_EXECUTION", "false").lower() == "true"
SHELL_EXECUTION_TIMEOUT = int(os.getenv("SHELL_EXECUTION_TIMEOUT", "30"))

# Git operations
ENABLE_GIT_OPERATIONS = os.getenv("ENABLE_GIT_OPERATIONS", "true").lower() == "true"

# ============================================================================
# Logging Configuration
# ============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = LOGS_DIR / "agent.log"

# ============================================================================
# Security Configuration
# ============================================================================

# Allowed file operations
ALLOWED_FILE_EXTENSIONS = {'.py', '.js', '.ts', '.md', '.txt', '.json', '.yaml', '.yml', '.env.example'}
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB

# Plugins configuration
AGENT_PLUGINS = [p.strip() for p in os.getenv("AGENT_PLUGINS", "").split(",") if p.strip()]
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

# REST API configuration
API_PORT = int(os.getenv("API_PORT", os.getenv("CHAT_PORT", "5000")))
API_DEBUG = os.getenv("API_DEBUG", str(DEBUG)).lower() == "true"
API_TOKEN = os.getenv("API_TOKEN", "")
API_ALLOWLIST = [ip.strip() for ip in os.getenv("API_ALLOWLIST", "").split(",") if ip.strip()]

# ============================================================================
# Validation
# ============================================================================

def validate_config():
    """Validate configuration"""
    errors = []
    if not GITHUB_TOKEN:
        errors.append("GITHUB_TOKEN not set (GitHub features disabled)")
    if not REPO_FULL_NAME:
        errors.append("REPO_FULL_NAME not set (PR analysis disabled)")
    if LLM_PROVIDER in ("groq", "openai"):
        if LLM_PROVIDER == "groq" and not GROQ_API_KEY:
            errors.append("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        if LLM_PROVIDER == "openai" and not HUGGINGFACE_TOKEN and not os.getenv("OPENAI_API_KEY"):
            errors.append("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
    else:
        if not (GROQ_API_KEY or HUGGINGFACE_TOKEN):
            # Only warn when using local provider
            pass
    
    if errors:
        raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

# ============================================================================
# Summary
# ============================================================================

def print_config():
    """Print configuration summary"""
    print("=" * 70)
    print("⚙️  Configuration Summary")
    print("=" * 70)
    print(f"Environment: {ENV}")
    print(f"Debug: {DEBUG}")
    print(f"Repository: {REPO_FULL_NAME or 'not set'}")
    print(f"LLM Primary: GROQ ({GROQ_MODEL})")
    print(f"LLM Fallback: {'HuggingFace' if HUGGINGFACE_TOKEN else 'None'}")
    print(f"Web Server: http://{CHAT_HOST}:{CHAT_PORT}")
    print(f"Code Execution: {'Enabled' if ENABLE_CODE_EXECUTION else 'Disabled'}")
    print(f"Shell Execution: {'Enabled' if ENABLE_SHELL_EXECUTION else 'Disabled'}")
    print(f"Git Operations: {'Enabled' if ENABLE_GIT_OPERATIONS else 'Disabled'}")
    print("=" * 70)

if __name__ == "__main__":
    validate_config()
    print_config()
