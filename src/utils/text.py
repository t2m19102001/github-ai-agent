#!/usr/bin/env python3
"""
Utility functions for text processing and validation
"""

import re
from typing import Optional
from src.config import MAX_PROMPT_LENGTH, MAX_ISSUE_BODY_LENGTH


def sanitize_text(text: str, max_length: int = MAX_ISSUE_BODY_LENGTH) -> str:
    """
    Sanitize input text to prevent injection attacks
    - Remove potentially harmful characters
    - Limit length
    - Normalize whitespace
    """
    if not text:
        return ""
    
    # Remove null bytes and control characters
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    return text


def validate_prompt(prompt: str, max_length: int = MAX_PROMPT_LENGTH) -> bool:
    """Validate that prompt is safe and within limits"""
    if not prompt or not isinstance(prompt, str):
        return False
    
    if len(prompt.strip()) == 0:
        return False
    
    if len(prompt) > max_length:
        return False
    
    return True


def extract_code_blocks(text: str) -> list[dict]:
    """Extract code blocks from text"""
    pattern = r'```(?:(\w+)\n)?(.*?)```'
    matches = re.finditer(pattern, text, re.DOTALL)
    
    blocks = []
    for match in matches:
        language = match.group(1) or "text"
        code = match.group(2).strip()
        blocks.append({"language": language, "code": code})
    
    return blocks


def format_code_block(code: str, language: str = "python") -> str:
    """Format code into a markdown code block"""
    return f"```{language}\n{code}\n```"


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """Truncate text with suffix if exceeds max length"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
