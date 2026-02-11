"""
权限系统 — 严格按需求书定义四类角色权限
"""
from functools import wraps
from typing import List, Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, selectinload
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, Role

security = HTTPBearer()


# ============================================================
#  权限矩阵 — 需求书第一节严格对应
# ============================================================
PERMISSION_MATRIX = {
    "SYSTEM_ADMIN": [
        # 系统管理员：最高权限
        "user.create", "user.read", "user.update", "user.delete",
        "role.assign", "config.update",
        "document.create", "document.read_all", "document.update",
        "document.upload", "document.delete", "document.force_update",
        "document.force_unlock", "document.request_destroy", "document.destroy",
        "number.read", "number.adjust", "number.allocate",
        "number.view_pool", "number.force_adjust",
        "approval.read", "approval.approve", "approval.reject",
        "approval.create_flow", "approval.manage_flow",
        "proofreading.read", "proofreading.submit", "proofreading.complete",
        "audit.read",
    ],
    "NUMBER_ADMIN": [
        # 文件号管理员：编号相关（受 config 开关控制的在 API 层检查）
        "number.read", "number.adjust", "number.view_pool",
        "document.read_all", "document.request_destroy",
    ],
    "APPROVER": [
        # 审批节点人员：仅处理审批和查看文档
        "approval.read", "approval.approve", "approval.reject",
        "document.read_all",
        "proofreading.read", "proofreading.complete",
    ],
    "USER": [
        # 普通用户（起草人）
        "document.create", "document.read_own", "document.update",
        "document.upload", "document.delete",
        "document.submit_proofread", "document.submit_approval",
        "document.request_destroy",
        "proofreading.read",
    ],
}


# ============================================================
#  获取当前用户
# ============================================================
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌"
        )

    user = db.query(User).options(
        selectinload(User.roles)
    ).filter(User.id == user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用"
        )

    return user


# ============================================================
#  权限检查函数
# ============================================================
def get_user_roles(user: User) -> List[str]:
    """获取用户角色名列表"""
    return [role.name for role in user.roles]


def has_permission(permission: str, user: User) -> bool:
    """
    检查用户是否拥有指定权限
    参数顺序：permission 在前，user 在后（统一约定）
    """
    user_roles = get_user_roles(user)
    for role in user_roles:
        if role in PERMISSION_MATRIX:
            if permission in PERMISSION_MATRIX[role]:
                return True
    return False


def check_permission(permission: str, user: User, db: Session = None):
    """
    检查权限，无权限则抛异常并记录审计
    """
    if not has_permission(permission, user):
        # 记录越权操作
        if db:
            from app.services.audit_service import log_audit, AuditEvent
            log_audit(
                db=db,
                user=user,
                action=AuditEvent.PERMISSION_DENIED,
                resource_type="Permission",
                resource_id=permission,
                details={"attempted_permission": permission}
            )
            db.flush()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足: {permission}"
        )


# ============================================================
#  角色判断快捷方法
# ============================================================
def is_system_admin(user: User) -> bool:
    return any(role.name == "SYSTEM_ADMIN" for role in user.roles)


def is_number_admin(user: User) -> bool:
    return any(role.name == "NUMBER_ADMIN" for role in user.roles)


def is_approver(user: User) -> bool:
    return any(role.name == "APPROVER" for role in user.roles)


def has_any_role(user: User, role_names: List[str]) -> bool:
    user_roles = get_user_roles(user)
    return any(r in user_roles for r in role_names)
