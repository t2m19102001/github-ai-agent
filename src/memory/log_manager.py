#!/usr/bin/env python3
"""
Log Manager Module
Handles agent activity logging with database persistence
"""

import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///logs.db")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class AgentLog(Base):
    """Agent activity log model"""
    __tablename__ = "agent_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    agent = Column(String(100), index=True, nullable=False)
    action = Column(String(100), nullable=False)
    result = Column(Text, nullable=False)
    status = Column(String(20), default="success")  # success, error, warning
    task_id = Column(String(100), index=True)
    processing_time = Column(Integer, default=0)  # in milliseconds
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    extra_data = Column(Text)  # JSON string for additional data (renamed from metadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'agent': self.agent,
            'action': self.action,
            'result': self.result,
            'status': self.status,
            'task_id': self.task_id,
            'processing_time': self.processing_time,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'extra_data': self.extra_data
        }

class LogManager:
    """Centralized logging manager for agent activities"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or DATABASE_URL
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
        logger.info(f"LogManager initialized with database: {self.database_url}")
    
    def log_activity(self, 
                   agent: str, 
                   action: str, 
                   result: str,
                   status: str = "success",
                   task_id: str = None,
                   processing_time: int = 0,
                   metadata: Dict[str, Any] = None) -> AgentLog:
        """Log agent activity"""
        try:
            db = self.SessionLocal()
            
            import json
            extra_data_json = json.dumps(metadata) if metadata else None
            
            log_entry = AgentLog(
                agent=agent,
                action=action,
                result=result,
                status=status,
                task_id=task_id,
                processing_time=processing_time,
                extra_data=extra_data_json
            )
            
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            
            logger.info(f"Logged activity: {agent} - {action} - {status}")
            return log_entry
            
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            return None
        finally:
            db.close()
    
    def get_logs(self, 
                 limit: int = 50, 
                 agent: str = None,
                 action: str = None,
                 status: str = None,
                 task_id: str = None) -> List[AgentLog]:
        """Get logs with optional filtering"""
        try:
            db = self.SessionLocal()
            query = db.query(AgentLog)
            
            # Apply filters
            if agent:
                query = query.filter(AgentLog.agent == agent)
            if action:
                query = query.filter(AgentLog.action == action)
            if status:
                query = query.filter(AgentLog.status == status)
            if task_id:
                query = query.filter(AgentLog.task_id == task_id)
            
            # Order by timestamp descending and limit
            logs = query.order_by(AgentLog.timestamp.desc()).limit(limit).all()
            
            return logs
            
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return []
        finally:
            db.close()
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get log statistics"""
        try:
            db = self.SessionLocal()
            
            # Total logs
            total_logs = db.query(func.count(AgentLog.id)).scalar()
            
            # Logs by status
            success_count = db.query(func.count(AgentLog.id)).filter(AgentLog.status == "success").scalar()
            error_count = db.query(func.count(AgentLog.id)).filter(AgentLog.status == "error").scalar()
            warning_count = db.query(func.count(AgentLog.id)).filter(AgentLog.status == "warning").scalar()
            
            # Logs by agent
            agent_stats = db.query(
                AgentLog.agent,
                func.count(AgentLog.id).label('count')
            ).group_by(AgentLog.agent).all()
            
            # Recent activity (last 24 hours)
            from datetime import timedelta
            recent_time = datetime.utcnow() - timedelta(hours=24)
            recent_count = db.query(func.count(AgentLog.id)).filter(
                AgentLog.timestamp >= recent_time
            ).scalar()
            
            # Average processing time
            avg_processing_time = db.query(func.avg(AgentLog.processing_time)).scalar() or 0
            
            return {
                'total_logs': total_logs,
                'success_count': success_count,
                'error_count': error_count,
                'warning_count': warning_count,
                'recent_count': recent_count,
                'avg_processing_time': round(avg_processing_time, 2),
                'agent_stats': [{'agent': stat[0], 'count': stat[1]} for stat in agent_stats]
            }
            
        except Exception as e:
            logger.error(f"Error getting log stats: {e}")
            return {}
        finally:
            db.close()
    
    def clear_old_logs(self, days: int = 30) -> int:
        """Clear logs older than specified days"""
        try:
            db = self.SessionLocal()
            
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            deleted_count = db.query(AgentLog).filter(
                AgentLog.timestamp < cutoff_time
            ).delete()
            
            db.commit()
            logger.info(f"Cleared {deleted_count} old logs (older than {days} days)")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error clearing old logs: {e}")
            return 0
        finally:
            db.close()
    
    def get_agent_activity_summary(self, agent: str, days: int = 7) -> Dict[str, Any]:
        """Get activity summary for specific agent"""
        try:
            db = self.SessionLocal()
            
            from datetime import timedelta
            start_time = datetime.utcnow() - timedelta(days=days)
            
            # Agent's recent logs
            logs = db.query(AgentLog).filter(
                AgentLog.agent == agent,
                AgentLog.timestamp >= start_time
            ).order_by(AgentLog.timestamp.desc()).all()
            
            # Calculate metrics
            total_actions = len(logs)
            success_rate = (len([log for log in logs if log.status == "success"]) / total_actions * 100) if total_actions > 0 else 0
            avg_processing_time = sum(log.processing_time for log in logs) / total_actions if total_actions > 0 else 0
            
            # Action breakdown
            action_counts = {}
            for log in logs:
                action_counts[log.action] = action_counts.get(log.action, 0) + 1
            
            return {
                'agent': agent,
                'period_days': days,
                'total_actions': total_actions,
                'success_rate': round(success_rate, 2),
                'avg_processing_time': round(avg_processing_time, 2),
                'action_breakdown': action_counts,
                'last_activity': logs[0].timestamp.isoformat() if logs else None
            }
            
        except Exception as e:
            logger.error(f"Error getting agent activity summary: {e}")
            return {}
        finally:
            db.close()

# Global log manager instance
log_manager = LogManager()

# Convenience functions
def log_activity(agent: str, 
               action: str, 
               result: str,
               status: str = "success",
               task_id: str = None,
               processing_time: int = 0,
               metadata: Dict[str, Any] = None) -> AgentLog:
    """Log agent activity using global log manager"""
    return log_manager.log_activity(
        agent=agent,
        action=action,
        result=result,
        status=status,
        task_id=task_id,
        processing_time=processing_time,
        metadata=metadata
    )

def get_logs(limit: int = 50, 
             agent: str = None,
             action: str = None,
             status: str = None,
             task_id: str = None) -> List[AgentLog]:
    """Get logs using global log manager"""
    return log_manager.get_logs(
        limit=limit,
        agent=agent,
        action=action,
        status=status,
        task_id=task_id
    )

def get_log_stats() -> Dict[str, Any]:
    """Get log statistics using global log manager"""
    return log_manager.get_log_stats()

def get_agent_activity_summary(agent: str, days: int = 7) -> Dict[str, Any]:
    """Get agent activity summary using global log manager"""
    return log_manager.get_agent_activity_summary(agent, days)
