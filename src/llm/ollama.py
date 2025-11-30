#!/usr/bin/env python3
"""
LLM Provider implementation for Ollama (Local)
"""

import requests
from typing import List, Dict, Optional
from src.agents.base import LLMProvider
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama LLM Provider (Local)"""
    
    def __init__(self, model: str = "deepseek-coder-v2:16b-instruct-qat"):
        super().__init__(name="Ollama", model=model)
        self.base_url = "http://localhost:11434"
    
    def call(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """Call Ollama API"""
        try:
            # Convert messages to Ollama format
            prompt = self._format_messages(messages)
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "top_p": kwargs.get("top_p", 0.9),
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=kwargs.get("timeout", 120)
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
            
        except requests.exceptions.ConnectionError:
            logger.error("❌ Ollama connection error. Is Ollama running? Run: ollama serve")
            return None
        except requests.exceptions.Timeout:
            logger.error("❌ Ollama API timeout")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Ollama API error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return None
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Convert chat messages to single prompt"""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                formatted.append(f"System: {content}")
            elif role == "user":
                formatted.append(f"User: {content}")
            elif role == "assistant":
                formatted.append(f"Assistant: {content}")
        
        return "\n\n".join(formatted)
    
    def get_available_models(self) -> List[str]:
        """Get available Ollama models"""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10
            )
            response.raise_for_status()
            
            models = response.json()
            return [m["name"] for m in models.get("models", [])]
        except Exception as e:
            logger.error(f"Error fetching Ollama models: {e}")
            return []
