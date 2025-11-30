# src/config/settings.py
"""
LLM Provider Configuration
Supports: Ollama (local), Groq (cloud), OpenAI (cloud)
"""
import os
from enum import Enum


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    GROQ = "groq"
    OPENAI = "openai"


# Provider selection from environment
PROVIDER = os.getenv("LLM_PROVIDER", LLMProvider.OLLAMA)

# Model configuration
MODELS = {
    LLMProvider.OLLAMA: "deepseek-coder-v2:16b-instruct-qat",
    LLMProvider.GROQ: "llama3-70b-8192",
    LLMProvider.OPENAI: "gpt-4o-mini"
}

# API Keys
GROQ_KEY = os.getenv("GROQ_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
