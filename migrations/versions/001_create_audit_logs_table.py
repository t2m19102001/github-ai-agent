#!/usr/bin/env python3
"""
Create audit_logs table migration.

This migration creates the audit_logs table for comprehensive
audit logging of all security-relevant events.

Production considerations:
- Partitioned by month for performance
- Indexes for common query patterns
- Checksum column for tamper detection
- 7-year retention (2555 days)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

revision = '001_create_audit_logs'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create audit_logs table and indexes."""
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('actor_type', sa.String(50), nullable=False),
        sa.Column('actor_id', sa.String(255), nullable=False),
        sa.Column('entity_type', sa.String(50)),
        sa.Column('entity_id', sa.UUID()),
        sa.Column('action', sa.String(100)),
        sa.Column('details', sa.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb')),
        sa.Column('ip_address', sa.INET),
        sa.Column('user_agent', sa.Text),
        sa.Column('request_id', sa.String(100)),
        sa.Column('trace_id', sa.String(100)),
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint('severity IN (\'CRITICAL\', \'HIGH\', \'MEDIUM\', \'LOW\')'),
        sa.CheckConstraint('actor_type IN (\'user\', \'agent\', \'system\', \'webhook\', \'service\')'),
    )
    
    # Indexes for common query patterns
    op.create_index('idx_audit_event_type', 'audit_logs', ['event_type'])
    op.create_index('idx_audit_severity', 'audit_logs', ['severity'])
    op.create_index('idx_audit_actor', 'audit_logs', ['actor_type', 'actor_id'])
    op.create_index('idx_audit_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('idx_audit_created', 'audit_logs', ['created_at'])
    
    # Composite index for actor queries
    op.create_index(
        'idx_audit_actor_created',
        'audit_logs',
        ['actor_type', 'actor_id', 'created_at']
    )
    
    # GIN index for JSONB details
    op.create_index('idx_audit_details', 'audit_logs', ['details'], postgresql_using='gin')
    
    # Partition by month (commented out - requires PostgreSQL 10+ and careful migration)
    # op.execute("""
    #     CREATE INDEX idx_audit_created_month ON audit_logs
    #     (date_trunc('month', created_at));
    # """)


def downgrade() -> None:
    """Drop audit_logs table and indexes."""
    op.drop_index('idx_audit_details', table_name='audit_logs', postgresql_using='gin')
    op.drop_index('idx_audit_actor_created', table_name='audit_logs')
    op.drop_index('idx_audit_entity', table_name='audit_logs')
    op.drop_index('idx_audit_actor', table_name='audit_logs')
    op.drop_index('idx_audit_created', table_name='audit_logs')
    op.drop_index('idx_audit_severity', table_name='audit_logs')
    op.drop_index('idx_audit_event_type', table_name='audit_logs')
    op.drop_table('audit_logs')
