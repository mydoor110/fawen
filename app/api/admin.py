"""
管理员 API — 用户管理、角色分配、审计日志、系统配置、编号池管理
统一使用 check_permission 权限检查
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime

from app.core.database import get_db
from app.models.user import User, Role, UserRole, ApprovalRole, UserApprovalRole
from app.models.system import AuditLog, SystemConfig
from app.models.number import NumberPool
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


# ============================================================
#  审计日志查询
# ============================================================
@router.get("/audit-logs")
def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    action: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    resource_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取审计日志列表 — 仅系统管理员可查看"""
    check_permission("audit.read", current_user, db)

    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": str(log.id),
                "user_id": str(log.user_id),
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
    }


# ============================================================
#  系统配置管理
# ============================================================
@router.get("/config")
def get_system_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有系统配置"""
    check_permission("config.update", current_user, db)
    configs = db.query(SystemConfig).all()
    return [
        {
            "id": str(c.id),
            "config_key": c.config_key,
            "config_value": c.config_value,
            "description": c.description,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in configs
    ]


@router.post("/config")
def update_system_config(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新系统配置项"""
    check_permission("config.update", current_user, db)

    config_key = data.get("config_key", "").strip()
    config_value = data.get("config_value")
    description = data.get("description", "")

    if not config_key:
        raise HTTPException(status_code=400, detail="配置键名不能为空")

    existing = db.query(SystemConfig).filter(SystemConfig.config_key == config_key).first()
    if existing:
        existing.config_value = config_value
        existing.description = description or existing.description
        existing.updated_by = current_user.id
    else:
        config = SystemConfig(
            config_key=config_key,
            config_value=config_value,
            description=description,
            updated_by=current_user.id
        )
        db.add(config)

    db.commit()
    logger.info(f"系统配置 {config_key} 已更新，操作人 {current_user.username}")
    return {"message": "配置更新成功", "config_key": config_key}


@router.delete("/config/{config_key}")
def delete_system_config(
    config_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除系统配置项"""
    check_permission("config.update", current_user, db)

    config = db.query(SystemConfig).filter(SystemConfig.config_key == config_key).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置项不存在")
    db.delete(config)
    db.commit()
    return {"message": "配置项已删除"}


# ============================================================
#  编号池管理
# ============================================================
@router.get("/number-pools")
def list_number_pools(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有编号池"""
    check_permission("number.read", current_user, db)
    pools = db.query(NumberPool).order_by(NumberPool.year.desc()).all()
    return [
        {
            "id": str(p.id),
            "year": p.year,
            "category": p.category,
            "prefix": p.prefix,
            "start_number": p.start_number,
            "current_number": p.current_number,
            "end_number": p.end_number,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in pools
    ]


@router.post("/number-pools")
def create_number_pool(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建编号池"""
    check_permission("number.adjust", current_user, db)

    pool = NumberPool(
        year=data.get("year", datetime.now().year),
        category=data.get("category", "default"),
        prefix=data.get("prefix", "GW"),
        start_number=data.get("start_number", 1),
        current_number=data.get("current_number", 1),
        end_number=data.get("end_number", 9999)
    )
    db.add(pool)
    db.commit()
    db.refresh(pool)
    logger.info(f"创建编号池: {pool.prefix}-{pool.year}，操作人 {current_user.username}")
    return {"message": "编号池创建成功", "id": str(pool.id)}


@router.put("/number-pools/{pool_id}")
def update_number_pool(
    pool_id: uuid.UUID,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新编号池"""
    check_permission("number.adjust", current_user, db)

    pool = db.query(NumberPool).filter(NumberPool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="编号池不存在")

    for key in ["year", "category", "prefix", "start_number", "current_number", "end_number"]:
        if key in data:
            setattr(pool, key, data[key])

    db.commit()
    logger.info(f"更新编号池 {pool_id}，操作人 {current_user.username}")
    return {"message": "编号池更新成功"}


@router.delete("/number-pools/{pool_id}")
def delete_number_pool(
    pool_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除编号池"""
    check_permission("number.force_adjust", current_user, db)

    pool = db.query(NumberPool).filter(NumberPool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="编号池不存在")

    db.delete(pool)
    db.commit()
    logger.info(f"删除编号池 {pool_id}，操作人 {current_user.username}")
    return {"message": "编号池已删除"}


# ============================================================
#  电子印章管理
# ============================================================
from fastapi import UploadFile, File
import os
import shutil
from pathlib import Path


@router.post("/upload-seal")
async def upload_seal(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传电子印章图片
    仅管理员可操作
    """
    check_permission("system.config", current_user, db)
    
    # 验证文件类型
    if file.content_type not in ["image/png", "image/jpeg"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只允许上传 PNG 或 JPG 格式的图片"
        )
    
    # 创建存储目录
    storage_dir = Path("storage/seals")
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名（使用时间戳避免重复）
    file_extension = Path(file.filename).suffix
    filename = f"seal_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{file_extension}"
    file_path = storage_dir / filename
    
    # 保存文件
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"上传印章图片: {filename}，操作人: {current_user.username}")
        
        return {
            "message": "印章图片上传成功",
            "file_path": str(file_path),
            "filename": filename
        }
    except Exception as e:
        logger.error(f"保存印章图片失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存文件失败: {str(e)}"
        )
