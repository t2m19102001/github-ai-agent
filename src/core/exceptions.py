"""
Custom exceptions for the application
"""

class AgentException(Exception):
    """Base exception for agent errors"""
    pass

class LLMException(Exception):
    """Exception for LLM provider errors"""
    pass

class SecurityException(Exception):
    """Exception for security violations"""
    pass

class AuthenticationException(Exception):
    """Exception for authentication errors"""
    pass

class RateLimitException(Exception):
    """Exception for rate limit errors"""
    pass
