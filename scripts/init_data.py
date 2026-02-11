"""初始化系统基础数据

Usage:
    python scripts/init_data.py
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.user import User, Role, ApprovalRole
from app.models.approval import ApprovalFlow, ApprovalNode
from app.models.number import NumberPool
from app.core.security import get_password_hash
from datetime import datetime


def init_roles(db: Session):
    """初始化系统角色"""
    roles = [
        Role(name="USER", description="普通用户：创建文档、提交审批、查看自己的文档"),
        Role(name="NUMBER_ADMIN", description="文件号管理员：管理编号池、调整编号、查看回收池"),
        Role(name="APPROVER", description="审批节点人员：审批文档、查看校对任务"),
        Role(name="SYSTEM_ADMIN", description="系统管理员：最高权限、用户管理、流程配置"),
    ]
    
    for role in roles:
        existing = db.query(Role).filter(Role.name == role.name).first()
        if not existing:
            db.add(role)
    
    db.commit()
    print("✅ 角色初始化完成")


def init_approval_roles(db: Session):
    """初始化审批角色"""
    roles = [
        ApprovalRole(name="主任", level=3, description="部门主任，负责最终审批"),
        ApprovalRole(name="技术岗", level=2, description="技术岗，负责技术审核"),
        ApprovalRole(name="中心负责人", level=1, description="中心负责人，负责初审"),
    ]
    
    for role in roles:
        existing = db.query(ApprovalRole).filter(ApprovalRole.name == role.name).first()
        if not existing:
            db.add(role)
    
    db.commit()
    print("✅ 审批角色初始化完成")


def init_approval_flows(db: Session):
    """初始化审批流程"""
    
    director_role = db.query(ApprovalRole).filter(ApprovalRole.name == "主任").first()
    tech_role = db.query(ApprovalRole).filter(ApprovalRole.name == "技术岗").first()
    center_role = db.query(ApprovalRole).filter(ApprovalRole.name == "中心负责人").first()
    
    if not all([director_role, tech_role, center_role]):
        print("⚠️  审批角色不存在，跳过审批流程初始化")
        return
    
    flow = ApprovalFlow(
        name="标准公文审批流程",
        description="中心负责人初审 → 技术岗审核 → 主任终审",
        is_active=True
    )
    db.add(flow)
    db.flush()
    
    node1 = ApprovalNode(
        flow_id=flow.id,
        approval_role_id=center_role.id,
        sequence=1,
        node_type="and",
        timeout_days=7
    )
    db.add(node1)
    
    node2 = ApprovalNode(
        flow_id=flow.id,
        approval_role_id=tech_role.id,
        sequence=2,
        node_type="and",
        timeout_days=7
    )
    db.add(node2)
    
    node3 = ApprovalNode(
        flow_id=flow.id,
        approval_role_id=director_role.id,
        sequence=3,
        node_type="and",
        timeout_days=7
    )
    db.add(node3)
    
    db.commit()
    print("✅ 审批流程初始化完成")


def init_number_pool(db: Session):
    """初始化编号池"""
    current_year = datetime.now().year
    
    existing = db.query(NumberPool).filter(
        NumberPool.year == current_year,
        NumberPool.category == "default"
    ).first()
    
    if not existing:
        pool = NumberPool(
            year=current_year,
            category="default",
            prefix="FW",
            start_number=1,
            current_number=1,
            end_number=9999
        )
        db.add(pool)
        db.commit()
        print("✅ 编号池初始化完成")
    else:
        print("✅ 编号池已存在")


def create_admin_user(db: Session):
    """创建默认管理员账号"""
    admin_role = db.query(Role).filter(Role.name == "SYSTEM_ADMIN").first()
    
    existing_user = db.query(User).filter(User.username == "admin").first()
    
    if not existing_user:
        admin_user = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            real_name="系统管理员",
            department="技术部",
            is_active=True
        )
        db.add(admin_user)
        db.flush()
        
        if admin_role:
            from app.models.user import UserRole
            user_role = UserRole(
                user_id=admin_user.id,
                role_id=admin_role.id
            )
            db.add(user_role)
        
        db.commit()
        print("✅ 默认管理员账号创建完成")
        print("   用户名: admin")
        print("   密码: admin123")
        print("   ⚠️  请尽快修改默认密码！")
    else:
        print("✅ 管理员账号已存在")


def main():
    """主函数"""
    print("=" * 50)
    print("公文文件号管理系统 - 数据初始化")
    print("=" * 50)
    print()
    
    db = SessionLocal()
    try:
        init_roles(db)
        init_approval_roles(db)
        init_number_pool(db)
        create_admin_user(db)
        
        try:
            init_approval_flows(db)
        except Exception as e:
            print(f"⚠️  审批流程初始化失败（可后续手动配置）: {e}")
        
        print()
        print("=" * 50)
        print("数据初始化完成！")
        print("=" * 50)
    except Exception as e:
        db.rollback()
        print(f"❌ 初始化失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
