from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import os
import requests

from src.agents.base import LLMProvider
from src.llm.groq import GroqProvider as _Groq
from src.llm.ollama import OllamaProvider as _Ollama
from src.core.config import (
    LLM_PROVIDER,
    GROQ_API_KEY,
    HUGGINGFACE_TOKEN,
    HUGGINGFACE_MODEL,
)


class ProviderBase(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def get_response(self, prompt: str) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass


class GroqAIProvider(ProviderBase):
    def __init__(self):
        self._provider = _Groq()

    @property
    def name(self) -> str:
        return "Groq"

    def get_response(self, prompt: str) -> str:
        result = self._provider.call([{"role": "user", "content": prompt}])
        if not result:
            raise RuntimeError("Groq response empty")
        return result

    def is_available(self) -> bool:
        return bool(GROQ_API_KEY)


class OllamaAIProvider(ProviderBase):
    def __init__(self, model: Optional[str] = None):
        self._provider = _Ollama(model=model or "deepseek-coder-v2:16b-instruct-qat")

    @property
    def name(self) -> str:
        return "Ollama"

    def get_response(self, prompt: str) -> str:
        result = self._provider.call([{"role": "user", "content": prompt}])
        if not result:
            raise RuntimeError("Ollama response empty")
        return result

    def is_available(self) -> bool:
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False


class HuggingFaceAIProvider(ProviderBase):
    def __init__(self, model: Optional[str] = None):
        self.model = model or HUGGINGFACE_MODEL
        self.token = HUGGINGFACE_TOKEN

    @property
    def name(self) -> str:
        return "HuggingFace"

    def get_response(self, prompt: str) -> str:
        if not self.token or not self.model:
            raise RuntimeError("HuggingFace not configured")
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload = {"inputs": prompt}
        url = f"https://api-inference.huggingface.co/models/{self.model}"
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "error" in data:
            raise RuntimeError(str(data["error"]))
        if isinstance(data, list) and data and isinstance(data[0], dict):
            val = data[0].get("generated_text") or data[0].get("summary_text")
            if val:
                return str(val)
        if isinstance(data, str):
            return data
        raise RuntimeError("HuggingFace response empty")

    def is_available(self) -> bool:
        return bool(self.token)


class ProviderAdapter(LLMProvider):
    def __init__(self, base: ProviderBase):
        super().__init__(name=base.name, model="generic")
        self.base = base

    def call(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        prompt_parts = []
        for m in messages:
            role = m.get("role", "user").upper()
            content = m.get("content", "")
            prompt_parts.append(f"{role}: {content}")
        prompt = "\n\n".join(prompt_parts)
        try:
            return self.base.get_response(prompt)
        except Exception:
            return None

    def get_available_models(self) -> List[str]:
        return []


class CompositeAIProvider(ProviderBase):
    def __init__(self, providers: List[ProviderBase]):
        self.providers = providers

    @property
    def name(self) -> str:
        return "Composite"

    def get_response(self, prompt: str) -> str:
        last_err = None
        for p in self.providers:
            if not p.is_available():
                continue
            try:
                resp = p.get_response(prompt)
                if resp and isinstance(resp, str):
                    return resp
            except Exception as e:
                last_err = e
                continue
        raise RuntimeError(str(last_err or "All providers failed"))

    def is_available(self) -> bool:
        return any(p.is_available() for p in self.providers)


def get_default_provider() -> ProviderBase:
    provider = (LLM_PROVIDER or "ollama").lower()
    groq = GroqAIProvider()
    ollama = OllamaAIProvider()
    hf = HuggingFaceAIProvider()
    ordered: List[ProviderBase] = []
    if provider == "groq":
        ordered = [groq, ollama, hf]
    elif provider == "openai":
        ordered = [hf, groq, ollama]
    else:
        ordered = [ollama, groq, hf]
    return CompositeAIProvider(ordered)
