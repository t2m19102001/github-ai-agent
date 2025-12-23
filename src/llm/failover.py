#!/usr/bin/env python3
from typing import List, Dict, Optional
from src.agents.base import LLMProvider
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FailoverProvider(LLMProvider):
    """
    Composite LLM provider that tries a list of providers in order.
    If one fails or returns no content, it falls back to the next.
    """
    def __init__(self, providers: List[LLMProvider]):
        super().__init__(name="FailoverLLM", model=providers[0].model if providers else "unknown")
        self.providers = providers

    def call(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        last_error = None
        for idx, p in enumerate(self.providers):
            try:
                logger.info(f"🔄 Trying provider: {p.name} ({p.model})")
                resp = p.call(messages, **kwargs)
                if resp and isinstance(resp, str) and len(resp.strip()) > 0:
                    if idx > 0:
                        logger.info(f"✅ Failover succeeded on provider: {p.name}")
                    return resp.strip()
                else:
                    logger.warning(f"⚠️ Provider {p.name} returned empty response")
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Provider {p.name} failed: {e}")
        if last_error:
            logger.error(f"❌ All providers failed: {last_error}")
        else:
            logger.error("❌ All providers returned empty response")
        return None

    def get_available_models(self) -> List[str]:
        result = []
        for p in self.providers:
            try:
                result.extend(p.get_available_models())
            except Exception:
                continue
        return list(dict.fromkeys(result))

