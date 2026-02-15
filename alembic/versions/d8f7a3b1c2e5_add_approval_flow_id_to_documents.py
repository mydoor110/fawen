"""add approval_flow_id to documents

Revision ID: d8f7a3b1c2e5
Revises: c5366b0f5a4b
Create Date: 2026-02-15 19:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd8f7a3b1c2e5'
down_revision = 'c5366b0f5a4b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 approval_flow_id 字段到 documents 表
    op.add_column('documents', sa.Column('approval_flow_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_documents_approval_flow_id'), 'documents', ['approval_flow_id'], unique=False)
    op.create_foreign_key('fk_documents_approval_flow_id', 'documents', 'approval_flows', ['approval_flow_id'], ['id'])


def downgrade() -> None:
    # 移除外键和索引
    op.drop_constraint('fk_documents_approval_flow_id', 'documents', type_='foreignkey')
    op.drop_index(op.f('ix_documents_approval_flow_id'), table_name='documents')
    op.drop_column('documents', 'approval_flow_id')
