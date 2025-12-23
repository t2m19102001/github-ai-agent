#!/usr/bin/env python3
"""
GitHub Webhook Manager
Advanced webhook management for GitHub AI Agent
"""

import hashlib
import hmac
import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from src.utils.logger import get_logger
from src.github.api_client import get_github_client

logger = get_logger(__name__)


class WebhookEvent(Enum):
    """GitHub webhook event types"""
    PUSH = "push"
    PULL_REQUEST = "pull_request"
    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"
    RELEASE = "release"
    CREATE = "create"
    DELETE = "delete"
    FORK = "fork"
    WATCH = "watch"
    STAR = "star"


@dataclass
class WebhookConfig:
    """Webhook configuration"""
    id: int
    url: str
    events: List[str]
    active: bool
    secret: Optional[str]
    content_type: str = "json"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class WebhookDelivery:
    """Webhook delivery information"""
    id: str
    event: str
    delivered: bool
    timestamp: datetime
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class WebhookStats:
    """Webhook statistics"""
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    average_delivery_time: float = 0.0
    last_delivery: Optional[datetime] = None
    deliveries_by_event: Dict[str, int] = field(default_factory=dict)
    recent_deliveries: List[WebhookDelivery] = field(default_factory=list)


class WebhookManager:
    """Advanced webhook management system"""
    
    def __init__(self, secret: Optional[str] = None):
        self.secret = secret
        self.github_client = get_github_client()
        self.webhook_configs: Dict[str, List[WebhookConfig]] = {}  # repo -> configs
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.delivery_stats: Dict[str, WebhookStats] = {}  # repo -> stats
        self.recent_deliveries: List[WebhookDelivery] = []
        
        logger.info("WebhookManager initialized")
    
    def verify_signature(self, payload: str, signature: str) -> bool:
        """Verify webhook signature"""
        if not self.secret:
            logger.warning("No webhook secret configured, skipping signature verification")
            return True
        
        try:
            expected_signature = "sha256=" + hmac.new(
                self.secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
    
    def parse_webhook_event(self, headers: Dict[str, str], body: str) -> Dict[str, Any]:
        """Parse webhook event from headers and body"""
        try:
            # Extract event type
            event_type = headers.get('X-GitHub-Event', '')
            delivery_id = headers.get('X-GitHub-Delivery', '')
            signature = headers.get('X-Hub-Signature-256', '')
            
            # Verify signature
            if not self.verify_signature(body, signature):
                raise ValueError("Invalid webhook signature")
            
            # Parse payload
            payload = json.loads(body)
            
            # Extract repository information
            repo_info = payload.get('repository', {})
            repo_name = repo_info.get('full_name', '')
            
            # Create delivery record
            delivery = WebhookDelivery(
                id=delivery_id,
                event=event_type,
                delivered=False,
                timestamp=datetime.now()
            )
            
            return {
                "event_type": event_type,
                "delivery_id": delivery_id,
                "repository": repo_name,
                "payload": payload,
                "delivery": delivery,
                "verified": True
            }
            
        except Exception as e:
            logger.error(f"Failed to parse webhook event: {e}")
            return {
                "error": str(e),
                "verified": False
            }
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler for specific event type"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered handler for {event_type} events")
    
    async def handle_webhook_event(self, headers: Dict[str, str], body: str) -> Dict[str, Any]:
        """Handle incoming webhook event"""
        start_time = datetime.now()
        
        try:
            # Parse event
            event_data = self.parse_webhook_event(headers, body)
            
            if not event_data.get("verified"):
                return {
                    "success": False,
                    "error": "Invalid webhook signature",
                    "status_code": 401
                }
            
            event_type = event_data["event_type"]
            repo_name = event_data["repository"]
            delivery = event_data["delivery"]
            
            # Update stats
            self._update_delivery_stats(repo_name, delivery)
            
            # Find handlers
            handlers = self.event_handlers.get(event_type, [])
            if not handlers:
                logger.warning(f"No handlers registered for {event_type}")
                return {
                    "success": True,
                    "message": f"No handlers for {event_type}",
                    "status_code": 200
                }
            
            # Execute handlers
            results = []
            for handler in handlers:
                try:
                    result = await handler(event_data)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Handler failed for {event_type}: {e}")
                    results.append({"error": str(e)})
            
            # Update delivery record
            delivery.delivered = True
            delivery.timestamp = datetime.now()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "event_type": event_type,
                "repository": repo_name,
                "handlers_executed": len(handlers),
                "results": results,
                "processing_time": processing_time,
                "status_code": 200
            }
            
        except Exception as e:
            logger.error(f"Failed to handle webhook: {e}")
            return {
                "success": False,
                "error": str(e),
                "status_code": 500
            }
    
    def create_webhook(self, repo_name: str, webhook_url: str, events: List[str], 
                      secret: Optional[str] = None, active: bool = True) -> Optional[WebhookConfig]:
        """Create webhook for repository"""
        if not self.github_client:
            logger.error("GitHub client not available")
            return None
        
        try:
            repo = self.github_client.client.get_repo(repo_name)
            
            # Create webhook
            webhook = repo.create_hook(
                name="web",
                config={
                    "url": webhook_url,
                    "content_type": "json",
                    "secret": secret or self.secret,
                    "insecure_ssl": "0"
                },
                events=events,
                active=active
            )
            
            config = WebhookConfig(
                id=webhook.id,
                url=webhook_url,
                events=events,
                active=active,
                secret=secret or self.secret,
                created_at=webhook.created_at,
                updated_at=webhook.updated_at
            )
            
            # Store config
            if repo_name not in self.webhook_configs:
                self.webhook_configs[repo_name] = []
            self.webhook_configs[repo_name].append(config)
            
            logger.info(f"Created webhook for {repo_name}: {webhook_url}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to create webhook: {e}")
            return None
    
    def list_webhooks(self, repo_name: str) -> List[WebhookConfig]:
        """List webhooks for repository"""
        if not self.github_client:
            return []
        
        try:
            repo = self.github_client.client.get_repo(repo_name)
            webhooks = []
            
            for hook in repo.get_hooks():
                config = WebhookConfig(
                    id=hook.id,
                    url=hook.config.get("url", ""),
                    events=hook.events,
                    active=hook.active,
                    secret=hook.config.get("secret"),
                    content_type=hook.config.get("content_type", "json"),
                    created_at=hook.created_at,
                    updated_at=hook.updated_at
                )
                webhooks.append(config)
            
            # Cache configs
            self.webhook_configs[repo_name] = webhooks
            
            return webhooks
            
        except Exception as e:
            logger.error(f"Failed to list webhooks: {e}")
            return []
    
    def update_webhook(self, repo_name: str, webhook_id: int, **kwargs) -> bool:
        """Update webhook configuration"""
        if not self.github_client:
            return False
        
        try:
            repo = self.github_client.client.get_repo(repo_name)
            hook = repo.get_hook(webhook_id)
            
            # Update webhook
            if "events" in kwargs:
                hook.edit(events=kwargs["events"])
            if "active" in kwargs:
                hook.edit(active=kwargs["active"])
            if "config" in kwargs:
                hook.edit(config=kwargs["config"])
            
            logger.info(f"Updated webhook {webhook_id} for {repo_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update webhook: {e}")
            return False
    
    def delete_webhook(self, repo_name: str, webhook_id: int) -> bool:
        """Delete webhook"""
        if not self.github_client:
            return False
        
        try:
            repo = self.github_client.client.get_repo(repo_name)
            hook = repo.get_hook(webhook_id)
            hook.delete()
            
            # Remove from cache
            if repo_name in self.webhook_configs:
                self.webhook_configs[repo_name] = [
                    config for config in self.webhook_configs[repo_name]
                    if config.id != webhook_id
                ]
            
            logger.info(f"Deleted webhook {webhook_id} for {repo_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete webhook: {e}")
            return False
    
    def _update_delivery_stats(self, repo_name: str, delivery: WebhookDelivery):
        """Update delivery statistics"""
        if repo_name not in self.delivery_stats:
            self.delivery_stats[repo_name] = WebhookStats()
        
        stats = self.delivery_stats[repo_name]
        stats.total_deliveries += 1
        
        if delivery.delivered:
            stats.successful_deliveries += 1
        else:
            stats.failed_deliveries += 1
        
        stats.last_delivery = delivery.timestamp
        stats.deliveries_by_event[delivery.event] = stats.deliveries_by_event.get(delivery.event, 0) + 1
        
        # Keep recent deliveries (last 100)
        stats.recent_deliveries.append(delivery)
        if len(stats.recent_deliveries) > 100:
            stats.recent_deliveries = stats.recent_deliveries[-100:]
    
    def get_webhook_stats(self, repo_name: Optional[str] = None) -> Dict[str, Any]:
        """Get webhook statistics"""
        if repo_name:
            if repo_name in self.delivery_stats:
                stats = self.delivery_stats[repo_name]
                return {
                    "repository": repo_name,
                    "total_deliveries": stats.total_deliveries,
                    "successful_deliveries": stats.successful_deliveries,
                    "failed_deliveries": stats.failed_deliveries,
                    "success_rate": (stats.successful_deliveries / stats.total_deliveries * 100) if stats.total_deliveries > 0 else 0,
                    "last_delivery": stats.last_delivery.isoformat() if stats.last_delivery else None,
                    "deliveries_by_event": stats.deliveries_by_event
                }
            else:
                return {"repository": repo_name, "error": "No statistics available"}
        else:
            # Return stats for all repositories
            all_stats = {}
            for repo, stats in self.delivery_stats.items():
                all_stats[repo] = {
                    "total_deliveries": stats.total_deliveries,
                    "successful_deliveries": stats.successful_deliveries,
                    "failed_deliveries": stats.failed_deliveries,
                    "success_rate": (stats.successful_deliveries / stats.total_deliveries * 100) if stats.total_deliveries > 0 else 0,
                    "last_delivery": stats.last_delivery.isoformat() if stats.last_delivery else None
                }
            
            return {
                "repositories": all_stats,
                "total_repositories": len(all_stats),
                "total_deliveries": sum(stats.total_deliveries for stats in self.delivery_stats.values()),
                "total_successful": sum(stats.successful_deliveries for stats in self.delivery_stats.values()),
                "total_failed": sum(stats.failed_deliveries for stats in self.delivery_stats.values())
            }
    
    def test_webhook(self, repo_name: str, webhook_id: int) -> bool:
        """Test webhook delivery"""
        if not self.github_client:
            return False
        
        try:
            repo = self.github_client.client.get_repo(repo_name)
            hook = repo.get_hook(webhook_id)
            
            # Ping webhook
            hook.ping()
            
            logger.info(f"Tested webhook {webhook_id} for {repo_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to test webhook: {e}")
            return False


# Global webhook manager instance
_webhook_manager: Optional[WebhookManager] = None


def get_webhook_manager() -> WebhookManager:
    """Get global webhook manager instance"""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager


def initialize_webhook_manager(secret: Optional[str] = None) -> WebhookManager:
    """Initialize webhook manager with custom secret"""
    global _webhook_manager
    _webhook_manager = WebhookManager(secret)
    return _webhook_manager


# Default webhook handlers
async def default_push_handler(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Default handler for push events"""
    payload = event_data["payload"]
    repo_name = event_data["repository"]
    
    commits = payload.get("commits", [])
    branch = payload.get("ref", "").replace("refs/heads/", "")
    
    logger.info(f"Push event: {repo_name}, branch: {branch}, commits: {len(commits)}")
    
    return {
        "event": "push",
        "repository": repo_name,
        "branch": branch,
        "commits_count": len(commits),
        "handled": True
    }


async def default_pull_request_handler(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Default handler for pull request events"""
    payload = event_data["payload"]
    repo_name = event_data["repository"]
    
    action = payload.get("action", "")
    pr = payload.get("pull_request", {})
    pr_number = pr.get("number", 0)
    title = pr.get("title", "")
    
    logger.info(f"PR event: {repo_name}, action: {action}, PR: #{pr_number}")
    
    return {
        "event": "pull_request",
        "repository": repo_name,
        "action": action,
        "pr_number": pr_number,
        "title": title,
        "handled": True
    }


async def default_issues_handler(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Default handler for issues events"""
    payload = event_data["payload"]
    repo_name = event_data["repository"]
    
    action = payload.get("action", "")
    issue = payload.get("issue", {})
    issue_number = issue.get("number", 0)
    title = issue.get("title", "")
    
    logger.info(f"Issue event: {repo_name}, action: {action}, issue: #{issue_number}")
    
    return {
        "event": "issues",
        "repository": repo_name,
        "action": action,
        "issue_number": issue_number,
        "title": title,
        "handled": True
    }


# Register default handlers
def register_default_handlers():
    """Register default webhook handlers"""
    manager = get_webhook_manager()
    manager.register_event_handler("push", default_push_handler)
    manager.register_event_handler("pull_request", default_pull_request_handler)
    manager.register_event_handler("issues", default_issues_handler)
    logger.info("Default webhook handlers registered")
