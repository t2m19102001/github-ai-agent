#!/usr/bin/env python3
"""
LLM Provider implementation for GROQ API
"""

import requests
from typing import List, Dict, Optional
from src.agents.base import LLMProvider
from src.utils.logger import get_logger
from src.core.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_TIMEOUT,
    GROQ_MAX_TOKENS,
    GROQ_TEMPERATURE
)

logger = get_logger(__name__)


class GroqProvider(LLMProvider):
    """GROQ LLM Provider"""
    
    def __init__(self):
        super().__init__(name="GROQ", model=GROQ_MODEL)
        self.api_key = GROQ_API_KEY
        self.base_url = "https://api.groq.com/openai/v1"
    
    def call(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """Call GROQ API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messages": messages,
                "model": self.model,
                "temperature": kwargs.get("temperature", GROQ_TEMPERATURE),
                "max_tokens": kwargs.get("max_tokens", GROQ_MAX_TOKENS),
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=GROQ_TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0].get("message", {}).get("content", "").strip()
            
            return None
        except requests.exceptions.Timeout:
            logger.error("❌ GROQ API timeout")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ GROQ API error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return None
    
    def get_available_models(self) -> List[str]:
        """Get available GROQ models"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=GROQ_TIMEOUT
            )
            response.raise_for_status()
            
            models = response.json()
            return [m["id"] for m in models.get("data", [])]
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            return []
