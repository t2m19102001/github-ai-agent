#!/usr/bin/env python3
"""
AI Provider Module
Wrapper for LLM providers with adapter pattern
"""

from typing import Dict, Any, Optional, List
import os

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

try:
    from src.llm.groq import GroqProvider
except ImportError:
    GroqProvider = None

try:
    from src.llm.provider import LLMProvider
except ImportError:
    LLMProvider = object

logger = get_logger(__name__)


class ProviderBase:
    """Base class for AI providers"""
    
    name: str = "ProviderBase"
    
    def get_response(self, prompt: str) -> str:
        """Get response from provider"""
        raise NotImplementedError
    
    def is_available(self) -> bool:
        """Check if provider is available"""
        return False


def get_default_provider() -> LLMProvider:
    """Get the default LLM provider based on environment config"""
    provider_name = os.getenv("LLM_PROVIDER", "groq").lower()
    
    if provider_name == "groq" and GroqProvider:
        return GroqProvider()
    
    if provider_name == "ollama":
        try:
            from src.llm.ollama import OllamaProvider
            return OllamaProvider()
        except ImportError:
            pass
    
    return MockProvider()


class GroqAIProvider(ProviderBase):
    """Groq AI provider wrapper"""
    
    name = "groq"
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
    
    def is_available(self) -> bool:
        """Check if Groq is available"""
        return bool(self.api_key)
    
    def get_response(self, prompt: str) -> str:
        """Get response from Groq"""
        if not self.is_available():
            return "Groq not configured"
        
        try:
            import requests
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "mixtral-8x7b-32768",
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            
            if response.ok:
                data = response.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            return f"Error: {response.status_code}"
            
        except Exception as e:
            return f"Error: {str(e)}"


class OllamaAIProvider(ProviderBase):
    """Ollama AI provider wrapper"""
    
    name = "ollama"
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
    
    def is_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.ok
        except Exception:
            return False
    
    def get_response(self, prompt: str) -> str:
        """Get response from Ollama"""
        try:
            import requests
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"prompt": prompt, "model": "llama2"},
                timeout=60
            )
            
            if response.ok:
                data = response.json()
                return data.get("response", "")
            
            return f"Error: {response.status_code}"
            
        except Exception as e:
            return f"Error: {str(e)}"


class HuggingFaceAIProvider(ProviderBase):
    """HuggingFace AI provider wrapper"""
    
    name = "huggingface"
    
    def __init__(self):
        self.token = os.getenv("HUGGINGFACE_TOKEN", "")
        self.model = os.getenv("HUGGINGFACE_MODEL", "gpt2")
    
    def is_available(self) -> bool:
        """Check if HuggingFace is available"""
        return bool(self.token)
    
    def get_response(self, prompt: str) -> str:
        """Get response from HuggingFace"""
        if not self.is_available():
            return "HuggingFace not configured"
        
        try:
            import requests
            response = requests.post(
                "https://api-inference.huggingface.co/models/" + self.model,
                headers={"Authorization": f"Bearer {self.token}"},
                json={"inputs": prompt},
                timeout=60
            )
            
            if response.ok:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("generated_text", "")
                elif isinstance(data, dict):
                    return data.get("generated_text", "")
            
            return f"Error: {response.status_code}"
            
        except Exception as e:
            return f"Error: {str(e)}"


class ProviderAdapter:
    """Adapter wrapper for LLM providers"""
    
    def __init__(self, provider: ProviderBase):
        self.provider = provider
        self.name = provider.name if hasattr(provider, 'name') else "unknown"
    
    def call(self, messages: List[Dict[str, str]]) -> str:
        """Call the provider with messages"""
        prompt = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages])
        return self.provider.get_response(prompt)
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using the underlying provider"""
        if hasattr(self.provider, 'generate_async'):
            return await self.provider.generate_async(prompt, **kwargs)
        elif hasattr(self.provider, 'get_response'):
            return self.provider.get_response(prompt)
        else:
            return f"Mock response for: {prompt[:100]}"
    
    def get_status(self) -> Dict[str, Any]:
        """Get provider status"""
        if hasattr(self.provider, 'get_status'):
            return self.provider.get_status()
        return {
            "name": self.name,
            "status": "active"
        }


class CompositeAIProvider(ProviderBase):
    """Provider that combines multiple providers"""
    
    name = "composite"
    
    def __init__(self, providers: List[ProviderBase] = None):
        self.providers = providers or []
    
    def add_provider(self, provider: ProviderBase) -> None:
        """Add a provider to the composite"""
        self.providers.append(provider)
    
    def is_available(self) -> bool:
        """Check if any provider is available"""
        return any(p.is_available() for p in self.providers)
    
    def get_response(self, prompt: str) -> str:
        """Get response from first available provider"""
        for provider in self.providers:
            if provider.is_available():
                return provider.get_response(prompt)
        return "No provider available"


class MockProvider:
    """Mock provider for testing/development"""
    
    name = "mock"
    
    def __init__(self):
        logger.info("Initialized Mock LLM provider")
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        return f"Mock response for: {prompt[:100]}..."
    
    async def generate_async(self, prompt: str, **kwargs) -> str:
        return await self.generate_response(prompt, **kwargs)
    
    def get_response(self, prompt: str) -> str:
        return f"Mock response for: {prompt[:100]}..."
    
    def is_available(self) -> bool:
        return True
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": "active",
            "type": "mock"
        }


__all__ = [
    "ProviderBase",
    "GroqAIProvider",
    "OllamaAIProvider", 
    "HuggingFaceAIProvider",
    "ProviderAdapter",
    "CompositeAIProvider",
    "get_default_provider",
    "MockProvider"
]
