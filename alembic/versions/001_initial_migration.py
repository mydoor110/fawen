"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(50), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('real_name', sa.String(100), nullable=False),
        sa.Column('department', sa.String(100)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )
    op.create_index('ix_users_username', 'users', ['username'])

    op.create_table(
        'user_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'approval_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(255)),
    )

    op.create_table(
        'user_approval_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('approval_role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('priority', sa.Integer(), default=0),
    )

    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('document_type', sa.String(50)),
        sa.Column('file_path', sa.String(500)),
        sa.Column('official_number', sa.String(100), unique=True),
        sa.Column('draft_number', sa.String(100)),
        sa.Column('status', sa.Enum('draft', 'proofreading', 'approval', 'approved', 'rejected', 'destroyed', name='documentstatus')),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
        sa.Column('submitted_at', sa.DateTime(timezone=True)),
        sa.Column('approved_at', sa.DateTime(timezone=True)),
        sa.Column('destroyed_at', sa.DateTime(timezone=True)),
        sa.Column('is_locked', sa.Boolean, default=False),
    )
    op.create_index('ix_documents_status', 'documents', ['status'])
    op.create_index('ix_documents_creator_id', 'documents', ['creator_id'])
    op.create_index('ix_documents_created_at', 'documents', ['created_at'])
    op.create_index('ix_documents_official_number', 'documents', ['official_number'])

    op.create_table(
        'document_locks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lock_type', sa.Enum('number', 'content', 'all', name='locktype'), nullable=False),
        sa.Column('locked_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('locked_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('reason', sa.String(500)),
    )

    op.create_table(
        'number_pools',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('prefix', sa.String(10), nullable=False),
        sa.Column('start_number', sa.Integer(), nullable=False),
        sa.Column('current_number', sa.Integer(), nullable=False),
        sa.Column('end_number', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'number_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('official_number', sa.String(100), unique=True, nullable=False),
        sa.Column('status', sa.Enum('reserved', 'allocated', 'recycled', name='numberrecordstatus')),
        sa.Column('allocated_at', sa.DateTime(timezone=True)),
        sa.Column('allocated_by', postgresql.UUID(as_uuid=True)),
        sa.Column('recycled_at', sa.DateTime(timezone=True)),
        sa.Column('recycled_by', postgresql.UUID(as_uuid=True)),
        sa.Column('recycle_reason', sa.String(500)),
        sa.Column('manual_adjustment', sa.Boolean, default=False),
    )
    op.create_index('ix_number_records_status', 'number_records', ['status'])
    op.create_index('ix_number_records_document_id', 'number_records', ['document_id'])
    op.create_index('ix_number_records_official_number', 'number_records', ['official_number'])

    op.create_table(
        'recycle_pool',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('official_number', sa.String(100), unique=True, nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True)),
        sa.Column('reason', sa.String(500)),
        sa.Column('recycled_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('is_available', sa.Boolean, default=True),
    )

    op.create_table(
        'proofreading_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('proofreader_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.Enum('pending', 'passed', 'failed', 'skipped', name='proofreadingstatus')),
        sa.Column('comment', sa.Text()),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_proofreading_tasks_document_id', 'proofreading_tasks', ['document_id'])
    op.create_index('ix_proofreading_tasks_status', 'proofreading_tasks', ['status'])

    op.create_table(
        'approval_flows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'approval_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('flow_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('approval_role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('node_type', sa.Enum('and', 'or', name='nodeapprovaltype')),
        sa.Column('timeout_days', sa.Integer(), default=7),
    )

    op.create_table(
        'approval_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('approver_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', 'skipped', name='approvalstatus')),
        sa.Column('comment', sa.Text()),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_approval_tasks_document_id', 'approval_tasks', ['document_id'])
    op.create_index('ix_approval_tasks_approver_id', 'approval_tasks', ['approver_id'])
    op.create_index('ix_approval_tasks_status', 'approval_tasks', ['status'])

    op.create_table(
        'system_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('config_key', sa.String(100), unique=True, nullable=False),
        sa.Column('config_value', postgresql.JSON, nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True)),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )

    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(100), nullable=False),
        sa.Column('details', postgresql.JSON, nullable=False),
        sa.Column('ip_address', sa.String(50)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('system_configs')
    op.drop_table('approval_tasks')
    op.drop_table('approval_nodes')
    op.drop_table('approval_flows')
    op.drop_table('proofreading_tasks')
    op.drop_table('recycle_pool')
    op.drop_table('number_records')
    op.drop_table('number_pools')
    op.drop_table('document_locks')
    op.drop_table('documents')
    op.drop_table('user_approval_roles')
    op.drop_table('approval_roles')
    op.drop_table('user_roles')
    op.drop_table('users')
    op.drop_table('roles')
