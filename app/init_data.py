"""
数据库自动初始化模块
启动时自动创建默认角色和管理员账号
"""
from sqlalchemy.orm import Session
from app.core.security import get_password_hash
from app.models.user import User, Role, UserRole, ApprovalRole
from app.utils.logger import get_logger

logger = get_logger("init_data")

# 审批角色定义（按层级递增）
APPROVAL_ROLES = [
    {"name": "科长审批", "level": 1, "description": "科室负责人审批"},
    {"name": "处长审批", "level": 2, "description": "处室负责人审批"},
    {"name": "局长审批", "level": 3, "description": "局领导审批"},
    {"name": "分管领导审批", "level": 4, "description": "分管领导最终审批"},
]

logger = get_logger("init_data")

# 系统角色定义
SYSTEM_ROLES = [
    {"name": "SYSTEM_ADMIN", "description": "系统管理员"},
    {"name": "USER", "description": "普通用户"},
    {"name": "NUMBER_ADMIN", "description": "文件号管理员"},
    {"name": "APPROVER", "description": "审批节点人员"},
]

# 默认管理员
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "admin123",
    "real_name": "系统管理员",
    "department": "技术部",
}


def init_roles(db: Session) -> dict:
    """初始化系统角色，返回角色名到角色对象的映射"""
    role_map = {}
    for role_def in SYSTEM_ROLES:
        role = db.query(Role).filter(Role.name == role_def["name"]).first()
        if not role:
            role = Role(name=role_def["name"], description=role_def["description"])
            db.add(role)
            db.flush()
            logger.info(f"创建角色: {role_def['name']}")
        role_map[role.name] = role
    return role_map


def init_admin(db: Session, role_map: dict):
    """初始化默认管理员账号"""
    admin = db.query(User).filter(User.username == DEFAULT_ADMIN["username"]).first()
    if admin:
        logger.info("管理员账号已存在，跳过创建")
        return
    
    admin = User(
        username=DEFAULT_ADMIN["username"],
        password_hash=get_password_hash(DEFAULT_ADMIN["password"]),
        real_name=DEFAULT_ADMIN["real_name"],
        department=DEFAULT_ADMIN["department"],
        is_active=True,
    )
    db.add(admin)
    db.flush()
    
    # 分配 SYSTEM_ADMIN 角色
    admin_role = role_map.get("SYSTEM_ADMIN")
    if admin_role:
        user_role = UserRole(user_id=admin.id, role_id=admin_role.id)
        db.add(user_role)
    
    logger.info(f"创建管理员账号: {DEFAULT_ADMIN['username']}")


def init_approval_roles(db: Session):
    """初始化审批角色"""
    for role_def in APPROVAL_ROLES:
        existing = db.query(ApprovalRole).filter(ApprovalRole.name == role_def["name"]).first()
        if not existing:
            role = ApprovalRole(
                name=role_def["name"],
                level=role_def["level"],
                description=role_def["description"]
            )
            db.add(role)
            logger.info(f"创建审批角色: {role_def['name']}")


def init_database(db: Session):
    """执行数据库初始化（幂等操作）"""
    try:
        role_map = init_roles(db)
        init_admin(db, role_map)
        init_approval_roles(db)
        db.commit()
        logger.info("数据库初始化完成")
    except Exception as e:
        db.rollback()
        logger.error(f"数据库初始化失败: {e}")
        raise
