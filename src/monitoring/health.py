#!/usr/bin/env python3
"""
Health Check Module
Provides health and readiness endpoints for production monitoring
"""

import time
import psutil
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a component"""
    name: str
    status: HealthStatus
    latency_ms: float
    message: str = ""
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class HealthChecker:
    """Comprehensive health checker for all system components"""
    
    def __init__(self):
        self.start_time = time.time()
        self.checks: List[callable] = []
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks"""
        self.register_check("system", self._check_system)
        self.register_check("memory", self._check_memory)
        self.register_check("agents", self._check_agents)
        self.register_check("llm", self._check_llm)
    
    def register_check(self, name: str, check_func: callable):
        """Register a health check function"""
        self.checks.append((name, check_func))
        logger.info(f"Registered health check: {name}")
    
    def _check_system(self) -> ComponentHealth:
        """Check system health"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_status = HealthStatus.HEALTHY if cpu_percent < 80 else HealthStatus.DEGRADED
            
            return ComponentHealth(
                name="system",
                status=cpu_status,
                latency_ms=0,
                message=f"CPU usage: {cpu_percent:.1f}%",
                details={"cpu_percent": cpu_percent}
            )
        except Exception as e:
            return ComponentHealth(
                name="system",
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                message=f"System check failed: {str(e)}"
            )
    
    def _check_memory(self) -> ComponentHealth:
        """Check memory health"""
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            if memory_percent < 80:
                status = HealthStatus.HEALTHY
            elif memory_percent < 90:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
            
            return ComponentHealth(
                name="memory",
                status=status,
                latency_ms=0,
                message=f"Memory usage: {memory_percent:.1f}%",
                details={
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "percent": memory_percent
                }
            )
        except Exception as e:
            return ComponentHealth(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                message=f"Memory check failed: {str(e)}"
            )
    
    def _check_agents(self) -> ComponentHealth:
        """Check agent system health"""
        try:
            start = time.time()
            
            from src.agents import Agent
            
            agents = ["CodeChatAgent", "GitHubIssueAgent", "DocumentationAgent"]
            available_agents = []
            
            try:
                from src.agents import CodeChatAgent
                available_agents.append("CodeChatAgent")
            except ImportError:
                pass
            
            latency_ms = (time.time() - start) * 1000
            
            status = HealthStatus.HEALTHY if available_agents else HealthStatus.DEGRADED
            
            return ComponentHealth(
                name="agents",
                status=status,
                latency_ms=latency_ms,
                message=f"Agents available: {len(available_agents)}",
                details={"agents": available_agents}
            )
        except Exception as e:
            return ComponentHealth(
                name="agents",
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                message=f"Agent check failed: {str(e)}"
            )
    
    def _check_llm(self) -> ComponentHealth:
        """Check LLM provider health"""
        try:
            start = time.time()
            
            from src.llm.provider import get_llm_provider
            provider = get_llm_provider()
            
            latency_ms = (time.time() - start) * 1000
            
            return ComponentHealth(
                name="llm",
                status=HealthStatus.HEALTHY,
                latency_ms=latency_ms,
                message=f"LLM provider: {getattr(provider, 'name', 'unknown')}",
                details={"provider": getattr(provider, 'name', 'unknown')}
            )
        except Exception as e:
            return ComponentHealth(
                name="llm",
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                message=f"LLM check failed: {str(e)}"
            )
    
    def check_all(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = []
        overall_status = HealthStatus.HEALTHY
        
        for name, check_func in self.checks:
            try:
                result = check_func()
                results.append(result)
                
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                    
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                results.append(ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=0,
                    message=str(e)
                ))
                overall_status = HealthStatus.UNHEALTHY
        
        uptime_seconds = time.time() - self.start_time
        
        return {
            "status": overall_status.value,
            "timestamp": time.time(),
            "uptime_seconds": uptime_seconds,
            "components": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "latency_ms": r.latency_ms,
                    "message": r.message,
                    "details": r.details
                }
                for r in results
            ],
            "summary": {
                "total": len(results),
                "healthy": sum(1 for r in results if r.status == HealthStatus.HEALTHY),
                "degraded": sum(1 for r in results if r.status == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for r in results if r.status == HealthStatus.UNHEALTHY)
            }
        }
    
    def is_ready(self) -> bool:
        """Check if system is ready to serve requests"""
        results = self.check_all()
        
        for component in results["components"]:
            if component["name"] in ["agents", "llm"]:
                if component["status"] != "healthy":
                    return False
        
        return True
    
    def is_healthy(self) -> bool:
        """Check if system is healthy"""
        results = self.check_all()
        return results["status"] in ["healthy", "degraded"]


class LivenessProbe:
    """Kubernetes liveness probe handler"""
    
    @staticmethod
    def handle() -> Dict[str, Any]:
        """Handle liveness probe"""
        return {
            "status": "alive",
            "timestamp": time.time()
        }


class ReadinessProbe:
    """Kubernetes readiness probe handler"""
    
    def __init__(self):
        self.health_checker = HealthChecker()
    
    def handle(self) -> Dict[str, Any]:
        """Handle readiness probe"""
        if self.health_checker.is_ready():
            return {
                "status": "ready",
                "timestamp": time.time()
            }
        else:
            return {
                "status": "not_ready",
                "timestamp": time.time(),
                "reason": "System not ready to serve requests"
            }


_global_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get global health checker instance"""
    global _global_health_checker
    if _global_health_checker is None:
        _global_health_checker = HealthChecker()
    return _global_health_checker


def health_check() -> Dict[str, Any]:
    """Quick health check for basic monitoring"""
    try:
        checker = get_health_checker()
        return checker.check_all()
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }


def readiness_check() -> Dict[str, Any]:
    """Quick readiness check"""
    try:
        checker = get_health_checker()
        is_ready = checker.is_ready()
        return {
            "ready": is_ready,
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "ready": False,
            "error": str(e),
            "timestamp": time.time()
        }


__all__ = [
    "HealthChecker",
    "HealthStatus",
    "ComponentHealth",
    "LivenessProbe",
    "ReadinessProbe",
    "get_health_checker",
    "health_check",
    "readiness_check"
]
