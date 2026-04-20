#!/usr/bin/env python3
"""
Rate Limiter Module
Implements rate limiting for API endpoints
"""

import time
import threading
from typing import Dict, Optional
from dataclasses import dataclass
from collections import defaultdict
from functools import wraps

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    window_seconds: int = 60


class TokenBucket:
    """Token bucket algorithm for rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens"""
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        """Refill tokens based on time elapsed"""
        now = time.time()
        elapsed = now - self.last_refill
        
        if elapsed > 0:
            new_tokens = elapsed * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_refill = now


class SlidingWindowCounter:
    """Sliding window counter for rate limiting"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
        self.lock = threading.Lock()
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed"""
        with self.lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            self.requests[key] = [
                t for t in self.requests[key]
                if t > cutoff
            ]
            
            if len(self.requests[key]) < self.max_requests:
                self.requests[key].append(now)
                return True
            
            return False
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests"""
        with self.lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            current = len([
                t for t in self.requests[key]
                if t > cutoff
            ])
            
            return max(0, self.max_requests - current)


class RateLimiter:
    """Multi-tier rate limiter"""
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        
        self.minute_limiter = SlidingWindowCounter(
            max_requests=self.config.requests_per_minute,
            window_seconds=60
        )
        
        self.hour_limiter = SlidingWindowCounter(
            max_requests=self.config.requests_per_hour,
            window_seconds=3600
        )
        
        self.burst_limiter = TokenBucket(
            capacity=self.config.burst_size,
            refill_rate=self.config.requests_per_minute / 60
        )
        
        self.client_limits: Dict[str, SlidingWindowCounter] = {}
        self.lock = threading.Lock()
    
    def is_allowed(self, client_id: str = "default") -> bool:
        """Check if request is allowed"""
        if not self.burst_limiter.consume():
            return False
        
        if not self.minute_limiter.is_allowed(f"minute_{client_id}"):
            return False
        
        if not self.hour_limiter.is_allowed(f"hour_{client_id}"):
            return False
        
        return True
    
    def get_status(self, client_id: str = "default") -> Dict:
        """Get rate limit status"""
        return {
            "allowed": self.is_allowed(client_id),
            "minute_remaining": self.minute_limiter.get_remaining(f"minute_{client_id}"),
            "hour_remaining": self.hour_limiter.get_remaining(f"hour_{client_id}"),
            "config": {
                "requests_per_minute": self.config.requests_per_minute,
                "requests_per_hour": self.config.requests_per_hour,
                "burst_size": self.config.burst_size
            }
        }
    
    def reset(self, client_id: str = None):
        """Reset rate limits for a client"""
        with self.lock:
            if client_id:
                self.minute_limiter.requests.pop(f"minute_{client_id}", None)
                self.hour_limiter.requests.pop(f"hour_{client_id}", None)
            else:
                self.minute_limiter.requests.clear()
                self.hour_limiter.requests.clear()


class RateLimitMiddleware:
    """Middleware for rate limiting FastAPI/Starlette"""
    
    def __init__(self, config: RateLimitConfig = None):
        self.limiter = RateLimiter(config)
    
    async def __call__(self, request, call_next):
        """Process request with rate limiting"""
        client_id = self._get_client_id(request)
        
        if not self.limiter.is_allowed(client_id):
            return {
                "error": "Rate limit exceeded",
                "status": 429,
                "retry_after": 60
            }
        
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(
            self.limiter.limiter.minute_limiter.get_remaining(client_id)
        )
        
        return response
    
    def _get_client_id(self, request) -> str:
        """Extract client identifier from request"""
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        if hasattr(request, 'headers'):
            api_key = request.headers.get("X-API-Key", "")
            if api_key:
                return f"api_{api_key[:8]}"
        
        return "anonymous"


def rate_limit(limiter: RateLimiter, client_id: str = "default"):
    """Decorator for rate limiting functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not limiter.is_allowed(client_id):
                raise RateLimitExceeded(
                    f"Rate limit exceeded. Try again later.",
                    retry_after=60
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""
    
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class IPRateLimiter:
    """IP-based rate limiter for web applications"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.request_times: Dict[str, list] = defaultdict(list)
        self.lock = threading.Lock()
    
    def is_allowed(self, ip: str) -> bool:
        """Check if IP is allowed"""
        with self.lock:
            now = time.time()
            cutoff = now - 60
            
            self.request_times[ip] = [
                t for t in self.request_times[ip]
                if t > cutoff
            ]
            
            if len(self.request_times[ip]) < self.requests_per_minute:
                self.request_times[ip].append(now)
                return True
            
            return False
    
    def get_reset_time(self, ip: str) -> int:
        """Get seconds until rate limit resets"""
        with self.lock:
            if ip not in self.request_times or not self.request_times[ip]:
                return 0
            
            oldest = min(self.request_times[ip])
            return max(0, int(60 - (time.time() - oldest)))


_global_limiter: Optional[RateLimiter] = None


def get_rate_limiter(config: RateLimitConfig = None) -> RateLimiter:
    """Get global rate limiter instance"""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter(config)
    return _global_limiter


__all__ = [
    "RateLimiter",
    "RateLimitConfig",
    "TokenBucket",
    "SlidingWindowCounter",
    "RateLimitMiddleware",
    "RateLimitExceeded",
    "IPRateLimiter",
    "get_rate_limiter",
    "rate_limit"
]
