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
    LLMProvider.GROQ: "llama-3.3-70b-versatile",
    LLMProvider.OPENAI: "gpt-4o-mini"
}

# API Keys
GROQ_KEY = os.getenv("GROQ_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# Context Configuration
# Max input tokens to send to LLM (reserve some for output)
# Llama 3 supports 8k-128k, but we stick to a safe default to avoid timeouts/costs
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", 12000))

# Validation helper (call this explicitly when needed)
def validate_api_keys():
    """Validate that required API keys are set"""
    if PROVIDER == "groq" and not GROQ_KEY:
        raise ValueError("❌ GROQ_API_KEY is required when LLM_PROVIDER=groq. Get it from https://console.groq.com/keys")
    if PROVIDER == "openai" and not OPENAI_KEY:
        raise ValueError("❌ OPENAI_API_KEY is required when LLM_PROVIDER=openai")
