#!/usr/bin/env python3
"""
JWT Authentication and Rate Limiting for API
"""

import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from src.utils.logger import get_logger

logger = get_logger(__name__)

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


def create_token(user_id: str, username: str) -> str:
    """Create JWT token"""
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_token(token: str) -> dict:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


def require_auth(f):
    """Decorator to require JWT authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for token in Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return jsonify({"error": "No authorization header"}), 401
        
        try:
            # Format: "Bearer <token>"
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return jsonify({"error": "Invalid authorization header format"}), 401
            
            token = parts[1]
            payload = decode_token(token)
            
            # Add user info to request context
            request.user_id = payload["user_id"]
            request.username = payload["username"]
            
            logger.info(f"✅ Authenticated request from {request.username}")
            return f(*args, **kwargs)
        
        except ValueError as e:
            logger.warning(f"❌ Auth failed: {e}")
            return jsonify({"error": str(e)}), 401
        except Exception as e:
            logger.error(f"❌ Auth error: {e}")
            return jsonify({"error": "Authentication failed"}), 401
    
    return decorated_function


def optional_auth(f):
    """Decorator for optional authentication (higher rate limits if authenticated)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        
        if auth_header:
            try:
                parts = auth_header.split()
                if len(parts) == 2 and parts[0].lower() == "bearer":
                    token = parts[1]
                    payload = decode_token(token)
                    request.user_id = payload["user_id"]
                    request.username = payload["username"]
                    request.is_authenticated = True
            except Exception:
                # Auth failed, continue as unauthenticated
                request.is_authenticated = False
        else:
            request.is_authenticated = False
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_limiter(app):
    """Initialize rate limiter"""
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["100 per hour", "20 per minute"],
        storage_uri="memory://",  # Use memory storage (can upgrade to Redis)
        strategy="fixed-window"
    )
    
    logger.info("✅ Rate limiter initialized")
    return limiter


# Rate limit configurations for different endpoints
RATE_LIMITS = {
    "chat": {
        "authenticated": "60 per hour",
        "unauthenticated": "10 per hour"
    },
    "knowledge": {
        "authenticated": "100 per hour",
        "unauthenticated": "20 per hour"
    },
    "code_execution": {
        "authenticated": "30 per hour",
        "unauthenticated": "5 per hour"
    }
}


def get_rate_limit_for_endpoint(endpoint: str) -> str:
    """Get rate limit based on authentication status"""
    is_authenticated = getattr(request, 'is_authenticated', False)
    limits = RATE_LIMITS.get(endpoint, {"authenticated": "50 per hour", "unauthenticated": "10 per hour"})
    
    if is_authenticated:
        return limits["authenticated"]
    else:
        return limits["unauthenticated"]
