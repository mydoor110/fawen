"""
文档销毁 API — 需求书第六节
可发起销毁：起草人 / 文件号管理员 / 系统管理员
销毁通过后：Word 移动到销毁目录 + 编号回收 + 审计
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime
import os
import shutil

from app.core.database import get_db
from app.core.config import settings
from app.models.document import Document, DocumentStatus
from app.models.number import NumberRecord, NumberRecordStatus, RecyclePool
from app.schemas.destroy import DestroyRequestRequest, DestroyApprovalRequest
from app.auth.dependencies import get_current_user, has_permission, has_any_role
from app.models.user import User
from app.services.audit_service import log_audit, AuditEvent
from app.utils.logger import get_logger

router = APIRouter(prefix="/destroy", tags=["Document Destroy"])
logger = get_logger("destroy")


@router.post("/documents/{document_id}/request")
def request_destroy(
    document_id: uuid.UUID,
    request: DestroyRequestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """申请销毁文档 — 仅起草人/NUMBER_ADMIN/SYSTEM_ADMIN"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    # 权限：仅起草人 / 文件号管理员 / 系统管理员
    is_creator = document.creator_id == current_user.id
    can_destroy = has_any_role(current_user, ["SYSTEM_ADMIN", "NUMBER_ADMIN"])
    if not is_creator and not can_destroy:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权发起销毁")

    if document.status == DocumentStatus.DESTROYED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文档已销毁")

    # 非管理员需要走审批
    if not has_any_role(current_user, ["SYSTEM_ADMIN"]):
        from app.models.approval import ApprovalTask, ApprovalNode, ApprovalFlow, ApprovalStatus

        flow = db.query(ApprovalFlow).filter(ApprovalFlow.name == "文档销毁审批").first()
        if flow:
            node = db.query(ApprovalNode).filter(ApprovalNode.flow_id == flow.id).first()
            if node:
                task = ApprovalTask(
                    document_id=document_id,
                    node_id=node.id,
                    approver_id=node.approval_role_id,
                    status=ApprovalStatus.PENDING
                )
                db.add(task)

                log_audit(db, current_user, AuditEvent.DOCUMENT_DESTROY,
                          "Document", str(document_id),
                          {"action": "request", "reason": request.reason})
                db.commit()

                return {"message": "销毁申请已提交审批", "require_approval": True}

    # 系统管理员直接销毁
    _execute_destroy(db, document, current_user, request.reason)
    db.commit()

    return {"message": "文档已销毁", "require_approval": False}


@router.post("/documents/{document_id}/approve")
def approve_destroy_request(
    document_id: uuid.UUID,
    request: DestroyApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """审批销毁申请"""
    if not has_any_role(current_user, ["SYSTEM_ADMIN"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权审批销毁")

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    from app.models.approval import ApprovalTask, ApprovalStatus

    task = db.query(ApprovalTask).filter(
        ApprovalTask.document_id == document_id,
        ApprovalTask.approver_id == current_user.id,
        ApprovalTask.status == ApprovalStatus.PENDING
    ).first()

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="无待审批的销毁申请")

    if not request.approved:
        task.status = ApprovalStatus.REJECTED
        task.comment = request.comment
        task.completed_at = datetime.utcnow()

        log_audit(db, current_user, AuditEvent.DOCUMENT_DESTROY,
                  "Document", str(document_id),
                  {"action": "reject", "comment": request.comment})
        db.commit()
        return {"message": "销毁申请已拒绝"}

    # 审批通过 → 执行销毁
    task.status = ApprovalStatus.APPROVED
    task.comment = request.comment
    task.completed_at = datetime.utcnow()

    _execute_destroy(db, document, current_user, request.comment or "审批通过")
    db.commit()

    return {"message": "文档已销毁"}


def _execute_destroy(db: Session, document: Document, user: User, reason: str):
    """
    执行销毁操作 — 需求书 6.2
    1. Word 移动到销毁目录
    2. 文件状态 = 已销毁
    3. 编号 = 已回收 → 进入回收池
    """
    # 回收编号
    number_record = db.query(NumberRecord).filter(
        NumberRecord.document_id == document.id,
        NumberRecord.status == NumberRecordStatus.ALLOCATED
    ).first()

    if number_record:
        recycle_entry = RecyclePool(
            official_number=number_record.official_number,
            document_id=document.id,
            reason=reason
        )
        db.add(recycle_entry)

        number_record.status = NumberRecordStatus.RECYCLED
        number_record.recycled_at = datetime.utcnow()
        number_record.recycled_by = user.id
        number_record.recycle_reason = reason

        # 审计 — 编号回收
        log_audit(db, user, AuditEvent.NUMBER_RECYCLE,
                  "NumberRecord", str(number_record.id),
                  {"official_number": number_record.official_number, "reason": reason})

    # 移动文件
    if document.file_path and os.path.exists(document.file_path):
        destroy_path = f"{settings.document.destroy_path}/{document.id}"
        os.makedirs(settings.document.destroy_path, exist_ok=True)
        shutil.move(document.file_path, destroy_path)
        document.file_path = destroy_path

    document.status = DocumentStatus.DESTROYED
    document.destroyed_at = datetime.utcnow()

    # 审计 — 销毁操作
    log_audit(db, user, AuditEvent.DOCUMENT_DESTROY,
              "Document", str(document.id),
              {
                  "action": "execute",
                  "reason": reason,
                  "title": document.title,
                  "official_number": document.official_number
              })

    logger.info(f"文档 {document.id} 已销毁，操作人: {user.username}")
