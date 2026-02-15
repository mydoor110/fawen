"""Add approval timeout and number sequence support

Revision ID: 2026021501
Revises: 
Create Date: 2026-02-15 21:38:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '2026021501'
down_revision = None  # 请根据实际情况修改为上一个revision ID
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库结构"""
    conn = op.get_bind()
    
    # 1. 为 number_pools 表添加 sequence_name 字段
    op.add_column('number_pools', 
        sa.Column('sequence_name', sa.String(100), nullable=True)
    )
    
    # 2. 为 approval_tasks 表添加超时相关字段
    op.add_column('approval_tasks',
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('approval_tasks',
        sa.Column('timeout_notified', sa.Boolean(), server_default='false', nullable=False)
    )
    
    # 3. 为现有编号池创建PostgreSQL序列
    # 查询现有编号池
    pools = conn.execute(
        text("SELECT id, year, category, current_number FROM number_pools")
    ).fetchall()
    
    for pool_id, year, category, current in pools:
        # 生成序列名
        seq_name = f"number_seq_{category}_{year}"
        
        # 创建序列(从current_number开始)
        try:
            conn.execute(
                text(f"CREATE SEQUENCE IF NOT EXISTS {seq_name} START {current + 1}")
            )
            
            # 更新编号池,记录序列名
            conn.execute(
                text("UPDATE number_pools SET sequence_name = :seq WHERE id = :id"),
                {"seq": seq_name, "id": str(pool_id)}
            )
            
            print(f"✓ 为编号池 {pool_id} 创建序列 {seq_name}")
        except Exception as e:
            print(f"✗ 创建序列失败 {seq_name}: {e}")


def downgrade():
    """回滚数据库结构"""
    conn = op.get_bind()
    
    # 删除PostgreSQL序列
    pools = conn.execute(
        text("SELECT sequence_name FROM number_pools WHERE sequence_name IS NOT NULL")
    ).fetchall()
    
    for (seq_name,) in pools:
        try:
            conn.execute(text(f"DROP SEQUENCE IF EXISTS {seq_name}"))
            print(f"✓ 删除序列 {seq_name}")
        except Exception as e:
            print(f"✗ 删除序列失败 {seq_name}: {e}")
    
    # 删除新增字段
    op.drop_column('approval_tasks', 'timeout_notified')
    op.drop_column('approval_tasks', 'deadline')
    op.drop_column('number_pools', 'sequence_name')
