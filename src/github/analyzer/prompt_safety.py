#!/usr/bin/env python3
"""
Prompt Safety Validation.

Production-grade implementation with:
- Prompt injection detection
- Malicious pattern detection
- Input sanitization
- Output validation
"""

import re
from typing import List, Optional, Dict, Any
from enum import Enum

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class PromptInjectionError(Exception):
    """Exception raised when prompt injection is detected."""
    pass


class ThreatLevel(Enum):
    """Threat level for prompt injection."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PromptSafetyValidator:
    """
    Prompt safety validator.
    
    Detects and prevents prompt injection attacks.
    """
    
    # Known prompt injection patterns
    INJECTION_PATTERNS = [
        r"ignore (previous|all) instructions",
        r"disregard (previous|all) instructions",
        r"forget (previous|all) instructions",
        r"override (previous|all) instructions",
        r"new instructions",
        r"additional instructions",
        r"system prompt",
        r"developer mode",
        r"admin mode",
        r"jailbreak",
        r"dan",  # Do Anything Now
        r"bypass",
        r"ignore constraints",
        r"break character",
        r"escape",
        r"\\n",  # Newline injection
        r"\\r",  # Carriage return injection
        r"\\t",  # Tab injection
        r"<script",  # Script injection
        r"<iframe",  # Iframe injection
        r"javascript:",
        r"data:",
        r"vbscript:",
        r"onload=",
        r"onerror=",
    ]
    
    # Malicious keywords
    MALICIOUS_KEYWORDS = [
        "password",
        "secret",
        "token",
        "api_key",
        "private_key",
        "credential",
        "backdoor",
        "exploit",
        "payload",
        "shell",
        "command",
        "execute",
        "eval",
        "exec",
        "system",
        "subprocess",
        "os.system",
        "__import__",
        "getattr",
        "setattr",
        "delattr",
        "globals",
        "locals",
        "vars",
        "compile",
        "open",
        "file",
        "write",
    ]
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize prompt safety validator.
        
        Args:
            strict_mode: If True, reject any suspicious prompts
        """
        self.strict_mode = strict_mode
        
        # Compile regex patterns
        self._injection_regex = re.compile(
            "|".join(INJECTION_PATTERNS),
            re.IGNORECASE
        )
        
        logger.info(f"PromptSafetyValidator initialized (strict_mode: {strict_mode})")
    
    def validate_prompt(self, prompt: str)
    -> Tuple[bool, ThreatLevel, List[str]]:
        """
        Validate prompt for injection attempts.
        
        Args:
            prompt: Prompt to validate
            
        Returns:
            (is_safe, threat_level, detected_patterns) tuple
        """
        detected_patterns = []
        threat_level = ThreatLevel.SAFE
        
        # Check for injection patterns
        injection_matches = self._injection_regex.findall(prompt)
        if injection_matches:
            detected_patterns.extend(injection_matches)
            threat_level = max(threat_level, ThreatLevel.HIGH)
        
        # Check for malicious keywords
        for keyword in self.MALICIOUS_KEYWORDS:
            if keyword in prompt.lower():
                detected_patterns.append(f"malicious_keyword: {keyword}")
                threat_level = max(threat_level, ThreatLevel.MEDIUM)
        
        # Check for excessive length (potential DoS)
        if len(prompt) > 10000:
            detected_patterns.append("excessive_length")
            threat_level = max(threat_level, ThreatLevel.MEDIUM)
        
        # Check for repeated patterns (potential injection)
        if self._has_repeated_patterns(prompt):
            detected_patterns.append("repeated_patterns")
            threat_level = max(threat_level, ThreatLevel.LOW)
        
        # Determine safety
        if self.strict_mode:
            is_safe = threat_level == ThreatLevel.SAFE
        else:
            is_safe = threat_level in {ThreatLevel.SAFE, ThreatLevel.LOW}
        
        if not is_safe:
            logger.warning(
                f"Prompt injection detected (threat: {threat_level.value})",
                extra={"detected_patterns": detected_patterns}
            )
        
        return is_safe, threat_level, detected_patterns
    
    def _has_repeated_patterns(self, text: str) -> bool:
        """
        Check for repeated patterns (potential injection).
        
        Args:
            text: Text to check
            
        Returns:
            True if repeated patterns detected
        """
        # Check for repeated characters
        if re.search(r"(.)\1{10,}", text):
            return True
        
        # Check for repeated words
        words = text.split()
        word_count = len(words)
        if word_count > 0:
            unique_words = len(set(words))
            if unique_words / word_count < 0.3:  # Less than 30% unique
                return True
        
        return False
    
    def sanitize_prompt(self, prompt: str) -> str:
        """
        Sanitize prompt by removing suspicious content.
        
        Args:
            prompt: Prompt to sanitize
            
        Returns:
            Sanitized prompt
        """
        # Remove escape sequences
        sanitized = prompt.replace("\\n", " ").replace("\\r", " ").replace("\\t", " ")
        
        # Normalize whitespace
        sanitized = re.sub(r"\s+", " ", sanitized)
        
        # Trim
        sanitized = sanitized.strip()
        
        return sanitized
    
    def validate_and_sanitize(self, prompt: str)
    -> Tuple[str, bool, ThreatLevel]:
        """
        Validate and sanitize prompt.
        
        Args:
            prompt: Prompt to validate and sanitize
            
        Returns:
            (sanitized_prompt, is_safe, threat_level) tuple
            
        Raises:
            PromptInjectionError: If prompt is unsafe in strict mode
        """
        is_safe, threat_level, patterns = self.validate_prompt(prompt)
        
        if not is_safe:
            if self.strict_mode:
                raise PromptInjectionError(
                    f"Prompt injection detected (threat: {threat_level.value}, "
                    f"patterns: {patterns})"
                )
            else:
                logger.warning(
                    f"Prompt flagged but allowed in non-strict mode "
                    f"(threat: {threat_level.value})"
                )
        
        sanitized = self.sanitize_prompt(prompt)
        
        return sanitized, is_safe, threat_level
