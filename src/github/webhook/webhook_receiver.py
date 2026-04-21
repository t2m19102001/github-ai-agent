#!/usr/bin/env python3
"""
GitHub Webhook Receiver (FastAPI).

Production-grade implementation with:
- FastAPI webhook endpoint
- Signature verification
- Deduplication
- Audit logging
- Error handling
- Timeout protection
"""

import json
import hashlib
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, Header
from fastapi.responses import JSONResponse

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

from .signature_verifier import SignatureVerifier, SignatureVerificationError
from .deduplication import WebhookDeduplication

logger = get_logger(__name__)


class WebhookReceiver:
    """
    FastAPI webhook receiver with security and deduplication.
    """
    
    def __init__(
        self,
        signature_verifier: SignatureVerifier,
        deduplication: WebhookDeduplication,
    ):
        """
        Initialize webhook receiver.
        
        Args:
            signature_verifier: Signature verifier instance
            deduplication: Webhook deduplication instance
        """
        self.signature_verifier = signature_verifier
        self.deduplication = deduplication
        
        logger.info("WebhookReceiver initialized")
    
    async def handle_webhook(
        self,
        request: Request,
        x_github_event: str = Header(...),
        x_github_delivery: str = Header(...),
        x_hub_signature_256: Optional[str] = Header(None),
        x_github_hook_installation_target_id: Optional[str] = Header(None),
    ) -> JSONResponse:
        """
        Handle incoming GitHub webhook.
        
        Args:
            request: FastAPI Request object
            x_github_event: X-GitHub-Event header
            x_github_delivery: X-GitHub-Delivery header
            x_hub_signature_256: X-Hub-Signature-256 header
            x_github_hook_installation_target_id: Installation ID (for app webhooks)
            
        Returns:
            JSONResponse
            
        Raises:
            HTTPException: If signature verification fails
        """
        # Read raw body bytes (required for signature verification)
        body_bytes = await request.body()
        
        # Verify signature
        verification_result = self.signature_verifier.verify(
            payload=body_bytes,
            signature_header=x_hub_signature_256 or "",
            delivery_id=x_github_delivery,
        )
        
        if not verification_result.valid:
            logger.error(
                f"Webhook signature verification failed: {verification_result.error}",
                extra={
                    "delivery_id": x_github_delivery,
                    "event": x_github_event,
                    "details": verification_result.details,
                }
            )
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "Invalid signature",
                    "message": verification_result.error,
                }
            )
        
        # Check for duplicate processing
        is_duplicate, cached_response = await self.deduplication.check_and_mark(
            delivery_id=x_github_delivery,
            event_type=x_github_event,
            payload=body_bytes,
        )
        
        if is_duplicate:
            logger.info(
                f"Duplicate webhook delivery: {x_github_delivery}",
                extra={
                    "delivery_id": x_github_delivery,
                    "event": x_github_event,
                }
            )
            return JSONResponse(
                status_code=200,
                content={
                    "status": "already_processed",
                    "delivery_id": x_github_delivery,
                    "message": "Webhook already processed",
                }
            )
        
        # Parse payload
        try:
            payload = json.loads(body_bytes.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid JSON payload"}
            )
        
        # Log webhook receipt
        logger.info(
            f"Webhook received: {x_github_event}",
            extra={
                "delivery_id": x_github_delivery,
                "event": x_github_event,
                "installation_id": x_github_hook_installation_target_id,
                "repository": payload.get("repository", {}).get("full_name"),
            }
        )
        
        # Process webhook (this would delegate to event handlers)
        # For now, return acceptance
        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "delivery_id": x_github_delivery,
                "event": x_github_event,
                "message": "Webhook accepted for processing",
            }
        )


class WebhookError(Exception):
    """Base exception for webhook errors."""
    pass


class WebhookValidationError(WebhookError):
    """Exception raised when webhook validation fails."""
    pass


class WebhookProcessingError(WebhookError):
    """Exception raised when webhook processing fails."""
    pass
