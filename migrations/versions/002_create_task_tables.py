#!/usr/bin/env python3
"""
Create task tables migration.

This migration creates tables for:
- tasks (main task table)
- dead_letter_queue (permanently failed tasks)
- task_history (task state changes)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

revision = '002_create_task_tables'
down_revision = '001_create_audit_logs_table'
branch_labels = None
depends_on = '001_create_audit_logs_table'


def upgrade() -> None:
    """Create task tables and indexes."""
    
    # Main tasks table
    op.create_table(
        'tasks',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('task_type', sa.String(100), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('payload', sa.JSONB(), nullable=False, server_default=sa.text('{}::jsonb')),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('scheduled_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('error', sa.TEXT),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('worker_id', sa.String(100)),
        sa.Column('result', sa.JSONB()),
        sa.Column('metadata', sa.JSONB(), nullable=False, server_default=sa.text('{}::jsonb')),
        sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')"),
        sa.CheckConstraint("priority BETWEEN 1 AND 10"),
        sa.CheckConstraint("retry_count >= 0"),
        sa.CheckConstraint("max_retries >= 0"),
    )
    
    # Indexes for common query patterns
    op.create_index('idx_tasks_status', 'tasks', ['status'])
    op.create_index('idx_tasks_priority', 'tasks', ['priority'])
    op.create_index('idx_tasks_worker', 'tasks', ['worker_id'])
    op.create_index('idx_tasks_scheduled', 'tasks', ['scheduled_at'])
    
    # Composite index for worker claiming
    op.create_index(
        'idx_tasks_claiming',
        'tasks',
        ['status', 'priority', 'scheduled_at']
    )
    
    # GIN index for JSONB payload and metadata
    op.create_index('idx_tasks_payload', 'tasks', ['payload'], postgresql_using='gin')
    op.create_index('idx_tasks_metadata', 'tasks', ['metadata'], postgresql_using='gin')
    
    # Dead letter queue table
    op.create_table(
        'dead_letter_queue',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('task_id', sa.UUID(), nullable=False),
        sa.Column('task_type', sa.String(100), nullable=False),
        sa.Column('failure_reason', sa.String(50), nullable=False),
        sa.Column('error_message', sa.TEXT, nullable=False),
        sa.Column('stack_trace', sa.TEXT),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('payload', sa.JSONB()),
        sa.Column('failed_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('reviewed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('reviewed_by', sa.String(100)),
        sa.Column('reviewed_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('action_taken', sa.String(100)),
        sa.Column('metadata', sa.JSONB(), nullable=False, server_default=sa.text('{}::jsonb')),
        sa.CheckConstraint("failure_reason IN ('max_retries_exceeded', 'fatal_error', 'timeout', 'resource_exhausted', 'dependency_failure', 'unknown')"),
    )
    
    # DLQ indexes
    op.create_index('idx_dlq_task_id', 'dead_letter_queue', ['task_id'])
    op.create_index('idx_dlq_reviewed', 'dead_letter_queue', ['reviewed'])
    op.create_index('idx_dlq_failed_at', 'dead_letter_queue', ['failed_at'])
    op.create_index('idx_dlq_task_type', 'dead_letter_queue', ['task_type'])
    op.create_index('idx_dlq_failure_reason', 'dead_letter_queue', ['failure_reason'])
    
    # GIN index for DLQ payload
    op.create_index('idx_dlq_payload', 'dead_letter_queue', ['payload'], postgresql_using='gin')
    
    # Task history table (for audit trail)
    op.create_table(
        'task_history',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('task_id', sa.UUID(), nullable=False),
        sa.Column('from_status', sa.String(20)),
        sa.Column('to_status', sa.String(20), nullable=False),
        sa.Column('changed_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('worker_id', sa.String(100)),
        sa.Column('metadata', sa.JSONB(), nullable=False, server_default=sa.text('{}::jsonb')),
        sa.CheckConstraint("to_status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')"),
    )
    
    # Task history indexes
    op.create_index('idx_task_history_task_id', 'task_history', ['task_id'])
    op.create_index('idx_task_history_changed_at', 'task_history', ['changed_at'])
    op.create_index('idx_task_history_worker', 'task_history', ['worker_id'])


def downgrade() -> None:
    """Drop task tables and indexes."""
    # Drop task history
    op.drop_index('idx_task_history_worker', table_name='task_history')
    op.drop_index('idx_task_history_changed_at', table_name='task_history')
    op.drop_index('idx_task_history_task_id', table_name='task_history')
    op.drop_table('task_history')
    
    # Drop DLQ
    op.drop_index('idx_dlq_payload', table_name='dead_letter_queue', postgresql_using='gin')
    op.drop_index('idx_dlq_failure_reason', table_name='dead_letter_queue')
    op.drop_index('idx_dlq_task_type', table_name='dead_letter_queue')
    op.drop_index('idx_dlq_failed_at', table_name='dead_letter_queue')
    op.drop_index('idx_dlq_reviewed', table_name='dead_letter_queue')
    op.drop_index('idx_dlq_task_id', table_name='dead_letter_queue')
    op.drop_table('dead_letter_queue')
    
    # Drop tasks
    op.drop_index('idx_tasks_metadata', table_name='tasks', postgresql_using='gin')
    op.drop_index('idx_tasks_payload', table_name='tasks', postgresql_using='gin')
    op.drop_index('idx_tasks_claiming', table_name='tasks')
    op.drop_index('idx_tasks_scheduled', table_name='tasks')
    op.drop_index('idx_tasks_worker', table_name='tasks')
    op.drop_index('idx_tasks_priority', table_name='tasks')
    op.drop_index('idx_tasks_status', table_name='tasks')
    op.drop_table('tasks')
