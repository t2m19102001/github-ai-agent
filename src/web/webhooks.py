#!/usr/bin/env python3
"""
GitHub Webhook Handler with Security Verification
Implements secure webhook processing with performance tracking
"""

import hmac
import hashlib
import json
import time
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, Response
from src.utils.logger import get_logger
from src.security.guardrails import security_guardrails, SecurityError

logger = get_logger(__name__)


class WebhookSecurity:
    """Webhook security verification"""
    
    def __init__(self, secret: str):
        self.secret = secret.encode('utf-8')
        self.validation_times = []
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify GitHub webhook signature
        
        Args:
            payload: Raw request body
            signature: X-Hub-Signature-256 header value
            
        Returns:
            True if signature is valid
        """
        try:
            if not signature or not signature.startswith('sha256='):
                logger.error("Invalid signature format")
                return False
            
            # Calculate expected signature
            expected_signature = hmac.new(
                self.secret,
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures securely
            received = signature.replace('sha256=', '')
            is_valid = hmac.compare_digest(expected_signature, received)
            
            if not is_valid:
                logger.error("Signature mismatch")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation performance stats"""
        if not self.validation_times:
            return {"avg_time": 0, "total_validations": 0}
        
        return {
            "avg_time": sum(self.validation_times) / len(self.validation_times),
            "total_validations": len(self.validation_times),
            "max_time": max(self.validation_times),
            "min_time": min(self.validation_times)
        }


class WebhookProcessor:
    """GitHub webhook event processor"""
    
    def __init__(self, orchestrator, webhook_secret: str):
        self.orchestrator = orchestrator
        self.security = WebhookSecurity(webhook_secret)
        self.processing_times = []
        self.event_counts = {}
        self.error_counts = {}
    
    async def process_webhook(self, request: Request) -> Dict[str, Any]:
        """
        Process GitHub webhook event
        
        Args:
            request: FastAPI request object
            
        Returns:
            Processing result
        """
        processing_start = time.time()
        
        try:
            # Extract headers
            signature = request.headers.get("X-Hub-Signature-256")
            event_type = request.headers.get("X-GitHub-Event")
            delivery_id = request.headers.get("X-GitHub-Delivery")
            
            if not signature:
                raise HTTPException(status_code=401, detail="Missing signature")
            
            if not event_type:
                raise HTTPException(status_code=400, detail="Missing event type")
            
            # Read and verify payload
            body = await request.body()
            
            # Security verification
            security_start = time.time()
            if not self.security.verify_signature(body, signature):
                raise HTTPException(status_code=403, detail="Invalid signature")
            security_time = time.time() - security_start
            self.security.validation_times.append(security_time)
            
            # Parse payload
            try:
                payload = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
            
            # Process event
            result = await self._handle_event(event_type, payload, delivery_id)
            
            # Record metrics
            processing_time = time.time() - processing_start
            self.processing_times.append(processing_time)
            self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
            
            # Success metric: <2s processing time
            if processing_time > 2.0:
                logger.warning(f"Webhook processing exceeded 2s: {processing_time:.2f}s")
            
            logger.info(f"Processed webhook {delivery_id} ({event_type}) in {processing_time:.2f}s")
            
            return {
                "status": "processed",
                "delivery_id": delivery_id,
                "event_type": event_type,
                "processing_time": processing_time,
                "security_time": security_time,
                "result": result
            }
            
        except HTTPException:
            raise
        except Exception as e:
            # Record error
            error_type = type(e).__name__
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            
            processing_time = time.time() - processing_start
            logger.error(f"Webhook processing failed after {processing_time:.2f}s: {e}")
            
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    
    async def _handle_event(self, event_type: str, payload: Dict[str, Any], delivery_id: str) -> Dict[str, Any]:
        """Handle specific webhook event types"""
        
        if event_type == "issues":
            return await self._handle_issues_event(payload)
        elif event_type == "pull_request":
            return await self._handle_pull_request_event(payload)
        elif event_type == "push":
            return await self._handle_push_event(payload)
        elif event_type == "ping":
            return await self._handle_ping_event(payload)
        else:
            logger.info(f"Unsupported event type: {event_type}")
            return {"message": f"Event type {event_type} not supported"}
    
    async def _handle_issues_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle issues event"""
        action = payload.get("action", "")
        issue = payload.get("issue", {})
        repository = payload.get("repository", {})
        
        logger.info(f"Issue {action}: #{issue.get('number')} - {issue.get('title')}")
        
        # Only handle opened issues for now
        if action == "opened":
            try:
                # Validate repository access
                repo_url = repository.get("clone_url", "")
                validation = security_guardrails.validate_repository_access(repo_url, "read")
                if not validation["valid"]:
                    raise SecurityError(f"Repository access blocked: {validation['reason']}")
                
                # Process with orchestrator
                result = self.orchestrator.handle_issue_event(payload)
                return {
                    "action": "issue_processed",
                    "issue_number": issue.get("number"),
                    "orchestrator_result": result
                }
                
            except SecurityError as e:
                logger.error(f"Security error processing issue: {e}")
                return {"error": str(e), "action": "blocked"}
            except Exception as e:
                logger.error(f"Error processing issue: {e}")
                return {"error": str(e), "action": "failed"}
        
        return {"message": f"Issue action {action} not processed"}
    
    async def _handle_pull_request_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pull request event"""
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})
        repository = payload.get("repository", {})
        
        logger.info(f"PR {action}: #{pr.get('number')} - {pr.get('title')}")
        
        # Handle opened and synchronize events
        if action in ["opened", "synchronize"]:
            try:
                # Validate repository access
                repo_url = repository.get("clone_url", "")
                validation = security_guardrails.validate_repository_access(repo_url, "read")
                if not validation["valid"]:
                    raise SecurityError(f"Repository access blocked: {validation['reason']}")
                
                # Process with orchestrator
                result = self.orchestrator.handle_pull_request_event(payload)
                return {
                    "action": "pr_processed",
                    "pr_number": pr.get("number"),
                    "orchestrator_result": result
                }
                
            except SecurityError as e:
                logger.error(f"Security error processing PR: {e}")
                return {"error": str(e), "action": "blocked"}
            except Exception as e:
                logger.error(f"Error processing PR: {e}")
                return {"error": str(e), "action": "failed"}
        
        return {"message": f"PR action {action} not processed"}
    
    async def _handle_push_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle push event"""
        ref = payload.get("ref", "")
        repository = payload.get("repository", {})
        commits = payload.get("commits", [])
        
        logger.info(f"Push to {ref}: {len(commits)} commits")
        
        try:
            # Validate repository access
            repo_url = repository.get("clone_url", "")
            validation = security_guardrails.validate_repository_access(repo_url, "read")
            if not validation["valid"]:
                raise SecurityError(f"Repository access blocked: {validation['reason']}")
            
            # For now, just log push events
            return {
                "action": "push_logged",
                "ref": ref,
                "commit_count": len(commits),
                "message": "Push event logged"
            }
            
        except SecurityError as e:
            logger.error(f"Security error processing push: {e}")
            return {"error": str(e), "action": "blocked"}
        except Exception as e:
            logger.error(f"Error processing push: {e}")
            return {"error": str(e), "action": "failed"}
    
    async def _handle_ping_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping event"""
        logger.info("Received ping event")
        return {"message": "pong"}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get webhook processing performance statistics"""
        stats = {
            "processing_times": {
                "avg": 0,
                "max": 0,
                "min": 0,
                "total": len(self.processing_times)
            },
            "security_validation": self.security.get_validation_stats(),
            "event_counts": self.event_counts,
            "error_counts": self.error_counts,
            "success_rate": 0,
            "meets_latency_target": False,
            "meets_success_rate_target": False
        }
        
        if self.processing_times:
            times = self.processing_times
            stats["processing_times"]["avg"] = sum(times) / len(times)
            stats["processing_times"]["max"] = max(times)
            stats["processing_times"]["min"] = min(times)
            
            # Success rate calculation
            total_events = sum(self.event_counts.values())
            total_errors = sum(self.error_counts.values())
            if total_events + total_errors > 0:
                stats["success_rate"] = total_events / (total_events + total_errors)
            
            # Target checks
            stats["meets_latency_target"] = stats["processing_times"]["avg"] < 2.0
            stats["meets_success_rate_target"] = stats["success_rate"] >= 0.99
        
        return stats


# Global webhook processor instance
webhook_processor: Optional[WebhookProcessor] = None


def initialize_webhook_processor(orchestrator, webhook_secret: str):
    """Initialize global webhook processor"""
    global webhook_processor
    webhook_processor = WebhookProcessor(orchestrator, webhook_secret)
    logger.info("Webhook processor initialized")


def get_webhook_processor() -> Optional[WebhookProcessor]:
    """Get global webhook processor"""
    return webhook_processor


# FastAPI endpoint functions
async def github_webhook_handler(request: Request) -> Dict[str, Any]:
    """FastAPI endpoint for GitHub webhooks"""
    processor = get_webhook_processor()
    if not processor:
        raise HTTPException(status_code=503, detail="Webhook processor not initialized")
    
    return await processor.process_webhook(request)


# Health check endpoint
async def webhook_health_check() -> Dict[str, Any]:
    """Webhook processor health check"""
    processor = get_webhook_processor()
    if not processor:
        return {
            "status": "unhealthy",
            "reason": "Webhook processor not initialized"
        }
    
    stats = processor.get_performance_stats()
    
    health_status = "healthy"
    issues = []
    
    # Check latency target
    if not stats["meets_latency_target"]:
        health_status = "degraded"
        issues.append(f"Average processing time {stats['processing_times']['avg']:.2f}s exceeds 2s target")
    
    # Check success rate target
    if not stats["meets_success_rate_target"]:
        health_status = "unhealthy"
        issues.append(f"Success rate {stats['success_rate']:.2%} below 99% target")
    
    return {
        "status": health_status,
        "performance": stats,
        "issues": issues
    }


# Metrics endpoint
async def webhook_metrics() -> Dict[str, Any]:
    """Webhook processor metrics"""
    processor = get_webhook_processor()
    if not processor:
        return {"error": "Webhook processor not initialized"}
    
    return processor.get_performance_stats()
