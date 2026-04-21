#!/usr/bin/env python3
"""
GitHub Webhook Signature Verifier.

Production-grade implementation with:
- X-Hub-Signature-256 verification
- HMAC-SHA256 validation
- Timing-safe comparison
- Comprehensive error handling
- Audit logging of verification attempts
"""

import hmac
import hashlib
from typing import Optional
from dataclasses import dataclass

try:
    from src.utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VerificationResult:
    """Result of signature verification."""
    valid: bool
    error: Optional[str] = None
    details: Optional[dict] = None


class SignatureVerifier:
    """
    Verify GitHub webhook signatures using X-Hub-Signature-256.
    
    GitHub webhooks are signed with HMAC-SHA256 using the webhook secret.
    The signature is sent in the X-Hub-Signature-256 header as:
    sha256=<hex_digest>
    
    Verification process:
    1. Extract signature from X-Hub-Signature-256 header
    2. Remove 'sha256=' prefix
    3. Compute HMAC-SHA256 of payload using webhook secret
    4. Compare using timing-safe comparison (hmac.compare_digest)
    
    Security considerations:
    - Use timing-safe comparison to prevent timing attacks
    - Reject requests without signature in production
    - Log all verification attempts for audit trail
    """
    
    def __init__(self, webhook_secret: str, require_signature: bool = True):
        """
        Initialize signature verifier.
        
        Args:
            webhook_secret: GitHub webhook secret
            require_signature: Require signature verification (default: True)
                             Set to False only for development
        """
        if not webhook_secret and require_signature:
            raise ValueError("webhook_secret is required when require_signature=True")
        
        self.webhook_secret = webhook_secret
        self.require_signature = require_signature
        
        logger.info(
            f"SignatureVerifier initialized "
            f"(require_signature: {require_signature})"
        )
    
    def verify(
        self,
        payload: bytes,
        signature_header: str,
        delivery_id: Optional[str] = None
    ) -> VerificationResult:
        """
        Verify webhook signature.
        
        Args:
            payload: Raw webhook payload (bytes)
            signature_header: X-Hub-Signature-256 header value
            delivery_id: X-GitHub-Delivery header value (for logging)
            
        Returns:
            VerificationResult with validity status
            
        Raises:
            ValueError: If signature format is invalid
        """
        # Check if signature is required
        if not signature_header:
            if self.require_signature:
                logger.error("Missing X-Hub-Signature-256 header")
                return VerificationResult(
                    valid=False,
                    error="Missing X-Hub-Signature-256 header",
                    details={"delivery_id": delivery_id}
                )
            else:
                logger.warning("Signature verification disabled, accepting payload")
                return VerificationResult(valid=True)
        
        # Validate signature format
        if not signature_header.startswith("sha256="):
            logger.error(f"Invalid signature format: {signature_header[:20]}...")
            return VerificationResult(
                valid=False,
                error="Invalid signature format (must start with 'sha256=')",
                details={"delivery_id": delivery_id}
            )
        
        # Extract signature
        signature = signature_header[7:]  # Remove 'sha256=' prefix
        
        # Compute expected signature
        expected_signature = self._compute_signature(payload)
        
        # Compare using timing-safe comparison
        is_valid = hmac.compare_digest(signature, expected_signature)
        
        # Log verification result
        if is_valid:
            logger.info(
                f"Webhook signature verified successfully",
                extra={"delivery_id": delivery_id}
            )
            return VerificationResult(
                valid=True,
                details={"delivery_id": delivery_id}
            )
        else:
            logger.warning(
                f"Webhook signature verification FAILED",
                extra={"delivery_id": delivery_id}
            )
            return VerificationResult(
                valid=False,
                error="Signature mismatch",
                details={
                    "delivery_id": delivery_id,
                    "expected": expected_signature[:16] + "...",
                    "received": signature[:16] + "..."
                }
            )
    
    def _compute_signature(self, payload: bytes) -> str:
        """
        Compute HMAC-SHA256 signature of payload.
        
        Args:
            payload: Raw webhook payload (bytes)
            
        Returns:
            Hex digest string
        """
        hmac_obj = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        )
        return hmac_obj.hexdigest()
    
    def validate_header_format(self, signature_header: str) -> bool:
        """
        Validate X-Hub-Signature-256 header format without computing signature.
        
        Used for pre-flight validation.
        
        Args:
            signature_header: X-Hub-Signature-256 header value
            
        Returns:
            True if format is valid, False otherwise
        """
        if not signature_header:
            return False
        
        if not signature_header.startswith("sha256="):
            return False
        
        signature = signature_header[7:]
        
        # Signature should be 64 hex characters (SHA-256 = 256 bits = 64 hex chars)
        if len(signature) != 64:
            return False
        
        # Should be valid hex
        try:
            int(signature, 16)
        except ValueError:
            return False
        
        return True


class SignatureVerificationError(Exception):
    """Exception raised when signature verification fails."""
    
    def __init__(self, message: str, delivery_id: Optional[str] = None):
        self.message = message
        self.delivery_id = delivery_id
        super().__init__(self.message)
