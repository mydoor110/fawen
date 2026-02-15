"""
编号管理 API — 需求书第二节
关键限制：审批中编号默认锁定、调整必须审计
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.models.number import NumberPool, NumberRecord, NumberRecordStatus, RecyclePool
from app.models.document import Document, DocumentStatus
from app.schemas.number import NumberPoolResponse, NumberRecordResponse, NumberAdjustRequest, RecyclePoolResponse
from app.auth.dependencies import get_current_user, check_permission, has_permission, is_system_admin
from app.models.user import User
from app.services.audit_service import log_audit, AuditEvent
from app.utils.logger import get_logger

router = APIRouter(prefix="/numbers", tags=["Number Management"])
logger = get_logger("number")


@router.get("/pools", response_model=List[NumberPoolResponse])
def list_number_pools(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_permission("number.read", current_user, db)
    pools = db.query(NumberPool).all()
    return pools


@router.get("/records", response_model=List[NumberRecordResponse])
def list_number_records(
    record_status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_permission("number.read", current_user, db)

    query = db.query(NumberRecord)
    if record_status:
        try:
            enum_status = NumberRecordStatus(record_status)
            query = query.filter(NumberRecord.status == enum_status)
        except ValueError:
            pass

    records = query.all()
    return records


@router.post("/records/{record_id}/adjust")
def adjust_number(
    record_id: uuid.UUID,
    request: NumberAdjustRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    手动调整编号 — 需求书 2.2
    必须填写原因、写入审计日志
    审批中默认禁止调整，由配置 allow_edit_during_approval 控制
    文件管理员可以调整已分配的编号（需要 number.force_adjust 权限）
    """
    check_permission("number.adjust", current_user, db)

    record = db.query(NumberRecord).filter(NumberRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="编号记录不存在")

    # 校验调整原因
    if not request.reason or len(request.reason.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="调整原因不能为空"
        )

    # 检查对应文档是否在审批中
    if record.document_id:
        document = db.query(Document).filter(Document.id == record.document_id).first()
        if document and document.status == DocumentStatus.APPROVAL:
            # 检查配置是否允许
            allow_edit = False
            if hasattr(settings, 'number') and hasattr(settings.number, 'policies'):
                allow_edit = getattr(settings.number.policies, 'allow_edit_during_approval', False)

            if not allow_edit and not is_system_admin(current_user):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="文件在审批流中，编号字段已锁定。如需修改请联系系统管理员"
                )

    # 🔧 新增：允许文件管理员调整已分配的编号
    if record.status == NumberRecordStatus.ALLOCATED:
        # 检查是否有强制调整权限（文件管理员专属）
        if not has_permission("number.force_adjust", current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅文件管理员可调整已分配的编号"
            )
        
        # 对已分配编号的调整要求更详细的原因说明
        if len(request.reason.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="调整已分配编号需要详细说明原因（至少10个字符）"
            )

    # 🔧 新增：文件号合规性校验
    from app.utils.number_validator import validate_number
    
    # 获取配置的允许前缀列表（如果有）
    allowed_prefixes = None
    if hasattr(settings, 'number') and hasattr(settings.number, 'format'):
        prefix = getattr(settings.number.format, 'prefix', None)
        if prefix:
            allowed_prefixes = [prefix]  # 也可以配置为列表
    
    # 执行校验（排除当前文档，允许保持原编号）
    is_valid, error_msg = validate_number(
        request.new_number, 
        db, 
        allowed_prefixes,
        exclude_document_id=str(record.document_id) if record.document_id else None
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    old_number = record.official_number
    record.official_number = request.new_number
    record.manual_adjustment = True

    # 如果文档已有编号，同步更新文档的编号字段
    if record.document_id:
        document = db.query(Document).filter(Document.id == record.document_id).first()
        if document:
            document.official_number = request.new_number

    # 审计 — 编号手动修改（强制记录）
    log_audit(db, current_user, AuditEvent.NUMBER_ADJUST,
              "NumberRecord", str(record_id),
              {
                  "old_number": old_number,
                  "new_number": request.new_number,
                  "reason": request.reason,
                  "status": record.status.value
              })

    db.commit()
    logger.info(f"编号 {old_number} → {request.new_number}，操作人: {current_user.username}，原因: {request.reason}")
    return {"message": "编号调整成功", "old_number": old_number, "new_number": request.new_number}


@router.get("/recycle-pool", response_model=List[RecyclePoolResponse])
def list_recycle_pool(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_permission("number.view_pool", current_user, db)
    records = db.query(RecyclePool).filter(RecyclePool.is_available == True).all()
    return records

from pydantic import BaseModel


class AllocateNumberRequest(BaseModel):
    document_id: uuid.UUID


@router.post("/allocate")
def allocate_number(
    request: AllocateNumberRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    手动分配编号 — 仅用于管理员手动触发
    正常流程中，编号在审批通过后自动分配
    """
    check_permission("number.allocate", current_user, db)

    document = db.query(Document).filter(Document.id == request.document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    if document.status != DocumentStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文档必须为已通过状态")

    if document.official_number:
        return {"message": "文档已有正式编号", "number": document.official_number}

    from app.services.document_service import allocate_official_number
    number = allocate_official_number(db, document, current_user)
    db.commit()

    return {"message": "编号分配成功", "number": number}
