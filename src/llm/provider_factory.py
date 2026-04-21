#!/usr/bin/env python3
"""
Provider Factory with Fallback Chain.

Production-grade implementation with:
- Provider registration
- Fallback chain configuration
- Safe failover logic
- Provider selection
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .provider_interface import LLMProvider, LLMRequest, LLMResponse, LLMProviderError
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig

logger = get_logger(__name__)


@dataclass
class ProviderChain:
    """Provider chain with fallback order."""
    providers: List[LLMProvider]
    circuit_breakers: Dict[str, CircuitBreaker]
    
    def __init__(self, providers: List[LLMProvider]):
        """
        Initialize provider chain.
        
        Args:
            providers: Ordered list of providers (primary first)
        """
        self.providers = providers
        self.circuit_breakers = {}
        
        # Create circuit breaker for each provider
        for provider in providers:
            self.circuit_breakers[provider.name] = CircuitBreaker(
                provider_name=provider.name
            )
        
        logger.info(f"ProviderChain initialized with {len(providers)} providers")


class ProviderFactory:
    """
    Provider factory with fallback chain.
    
    Manages provider registration and selection with safe failover.
    """
    
    def __init__(self):
        """Initialize provider factory."""
        self._providers: Dict[str, LLMProvider] = {}
        self._chain: Optional[ProviderChain] = None
        
        logger.info("ProviderFactory initialized")
    
    def register_provider(self, provider: LLMProvider, priority: int = 0):
        """
        Register provider.
        
        Args:
            provider: LLM provider instance
            priority: Priority in chain (lower = higher priority)
        """
        self._providers[provider.name] = {
            "provider": provider,
            "priority": priority,
        }
        
        logger.info(f"Registered provider: {provider.name} (priority: {priority})")
    
    def configure_chain(self, provider_names: List[str]):
        """
        Configure fallback chain.
        
        Args:
            provider_names: Ordered list of provider names
        """
        providers = []
        for name in provider_names:
            if name not in self._providers:
                raise ValueError(f"Provider not registered: {name}")
            providers.append(self._providers[name]["provider"])
        
        self._chain = ProviderChain(providers)
        
        logger.info(f"Provider chain configured: {provider_names}")
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response using provider chain with fallback.
        
        Args:
            request: LLM request
            
        Returns:
            LLM response
            
        Raises:
            LLMProviderError: If all providers fail
        """
        if not self._chain:
            raise LLMProviderError("No provider chain configured")
        
        last_error = None
        
        for provider in self._chain.providers:
            circuit_breaker = self._chain.circuit_breakers[provider.name]
            
            # Check if circuit breaker allows execution
            if not circuit_breaker.can_execute():
                logger.warning(f"Circuit breaker blocking provider: {provider.name}")
                continue
            
            # Check if provider is available
            if not provider.is_available():
                logger.warning(f"Provider unavailable: {provider.name}")
                continue
            
            try:
                # Generate response
                response = await provider.generate(request)
                
                # Record success
                circuit_breaker.record_success()
                
                logger.info(f"Successfully generated response using: {provider.name}")
                return response
                
            except LLMProviderError as e:
                last_error = e
                circuit_breaker.record_failure()
                
                logger.warning(
                    f"Provider failed: {provider.name}, trying next in chain",
                    extra={"error": str(e)}
                )
                continue
        
        # All providers failed
        raise LLMProviderError(
            f"All providers in chain failed. Last error: {last_error}"
        )
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all providers.
        
        Returns:
            Dictionary of provider name to health status
        """
        if not self._chain:
            return {}
        
        health_status = {}
        
        for provider in self._chain.providers:
            try:
                is_healthy = await provider.health_check()
                health_status[provider.name] = is_healthy
            except Exception as e:
                logger.error(f"Health check failed for {provider.name}: {e}")
                health_status[provider.name] = False
        
        return health_status
    
    def get_chain_status(self) -> Dict[str, Any]:
        """Get provider chain status."""
        if not self._chain:
            return {"status": "no_chain_configured"}
        
        return {
            "providers": [p.name for p in self._chain.providers],
            "circuit_breakers": {
                name: cb.get_stats()
                for name, cb in self._chain.circuit_breakers.items()
            },
        }
