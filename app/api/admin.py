"""
管理员 API — 用户管理、角色分配
统一使用 check_permission 权限检查
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.core.database import get_db
from app.models.user import User, Role, UserRole, ApprovalRole, UserApprovalRole
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.auth.dependencies import get_current_user, check_permission
from app.utils.logger import get_logger
from app.core.security import get_password_hash

router = APIRouter(prefix="/admin", tags=["System Admin"])
logger = get_logger("admin")


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_permission("user.create", current_user, db)

    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")

    user = User(
        username=user_data.username,
        real_name=user_data.real_name,
        department=user_data.department,
        password_hash=get_password_hash(user_data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"用户 {user.username} 由 {current_user.username} 创建")
    return user


@router.get("/users", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_permission("user.read", current_user, db)
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_permission("user.read", current_user, db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: uuid.UUID,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_permission("user.update", current_user, db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    for field, value in user_data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    logger.info(f"用户 {user_id} 被 {current_user.username} 更新")
    return user


@router.delete("/users/{user_id}")
def delete_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_permission("user.delete", current_user, db)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除自己")

    db.query(UserRole).filter(UserRole.user_id == user_id).delete()
    db.delete(user)
    db.commit()

    logger.info(f"用户 {user_id} 被 {current_user.username} 删除")
    return {"message": "用户删除成功"}


@router.post("/users/{user_id}/roles")
def assign_roles(
    user_id: uuid.UUID,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_permission("role.assign", current_user, db)
    role_names = data.get("role_names", [])

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    db.query(UserRole).filter(UserRole.user_id == user_id).delete()

    for role_name in role_names:
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            continue
        user_role = UserRole(user_id=user_id, role_id=role.id)
        db.add(user_role)

    db.commit()
    logger.info(f"角色 {role_names} 分配给用户 {user_id}，操作人 {current_user.username}")
    return {"message": "角色分配成功", "roles": role_names}


@router.get("/roles")
def list_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    roles = db.query(Role).all()
    return [{"id": str(role.id), "name": role.name, "description": role.description} for role in roles]


@router.get("/approval-roles")
def list_approval_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    roles = db.query(ApprovalRole).order_by(ApprovalRole.level).all()
    return [{"id": str(role.id), "name": role.name, "level": role.level, "description": role.description} for role in roles]


@router.post("/approval-roles/{user_id}")
def assign_approval_role(
    user_id: uuid.UUID,
    approval_role_id: uuid.UUID,
    priority: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_permission("role.assign", current_user, db)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    existing = db.query(UserApprovalRole).filter(
        UserApprovalRole.user_id == user_id,
        UserApprovalRole.approval_role_id == approval_role_id
    ).first()

    if existing:
        existing.priority = priority
    else:
        user_approval_role = UserApprovalRole(
            user_id=user_id,
            approval_role_id=approval_role_id,
            priority=priority
        )
        db.add(user_approval_role)

    db.commit()
    logger.info(f"审批角色 {approval_role_id} 分配给用户 {user_id}，操作人 {current_user.username}")
    return {"message": "审批角色分配成功"}


@router.delete("/users/{user_id}/approval-roles/{approval_role_id}")
def remove_user_approval_role(
    user_id: uuid.UUID,
    approval_role_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_permission("role.assign", current_user, db)
    deleted = db.query(UserApprovalRole).filter(
        UserApprovalRole.user_id == user_id,
        UserApprovalRole.approval_role_id == approval_role_id
    ).delete()
    if not deleted:
        raise HTTPException(status_code=404, detail="该用户未分配此审批角色")
    db.commit()
    return {"message": "审批角色移除成功"}


# ===== 审批角色 CRUD =====
@router.post("/approval-roles")
def create_approval_role(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_permission("role.assign", current_user, db)
    name = data.get("name", "").strip()
    level = data.get("level", 1)
    description = data.get("description", "")

    if not name:
        raise HTTPException(status_code=400, detail="角色名称不能为空")

    existing = db.query(ApprovalRole).filter(ApprovalRole.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="角色名称已存在")

    role = ApprovalRole(name=name, level=level, description=description)
    db.add(role)
    db.commit()
    db.refresh(role)
    logger.info(f"创建审批角色: {name}，操作人 {current_user.username}")
    return {"id": str(role.id), "name": role.name, "level": role.level, "description": role.description}


@router.put("/approval-roles/{role_id}")
def update_approval_role(
    role_id: uuid.UUID,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_permission("role.assign", current_user, db)
    role = db.query(ApprovalRole).filter(ApprovalRole.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="审批角色不存在")

    if "name" in data:
        role.name = data["name"].strip()
    if "level" in data:
        role.level = data["level"]
    if "description" in data:
        role.description = data["description"]

    db.commit()
    db.refresh(role)
    logger.info(f"更新审批角色: {role.name}，操作人 {current_user.username}")
    return {"id": str(role.id), "name": role.name, "level": role.level, "description": role.description}


@router.delete("/approval-roles/{role_id}")
def delete_approval_role(
    role_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_permission("role.assign", current_user, db)
    role = db.query(ApprovalRole).filter(ApprovalRole.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="审批角色不存在")

    # 先移除关联
    db.query(UserApprovalRole).filter(UserApprovalRole.approval_role_id == role_id).delete()
    db.delete(role)
    db.commit()
    logger.info(f"删除审批角色: {role.name}，操作人 {current_user.username}")
    return {"message": "审批角色删除成功"}
