"""
文档管理 API — 需求书对标实现
状态机：DRAFT → PROOFREADING → APPROVAL → APPROVED
锁定：提交校对锁编号，提交审批全锁定
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid
import os

from app.core.database import get_db
from app.core.config import settings
from app.models.document import Document, DocumentStatus, LockType, DocumentLock
from app.models.proofreading import ProofreadingTask
from app.models.approval import ApprovalTask
from app.schemas.document import (
    DocumentCreate, DocumentResponse, DocumentUpdate,
    DocumentSubmitProofreadingRequest, DocumentSubmitApprovalRequest
)
from app.auth.dependencies import get_current_user, has_permission, check_permission, is_system_admin
from app.models.user import User
from app.services.document_service import (
    check_document_editable, submit_for_proofreading,
    submit_for_approval, unlock_document
)
from app.services.audit_service import log_audit, AuditEvent

router = APIRouter(prefix="/documents", tags=["Documents"])


# ============================================================
#  创建文档 — 仅起草人 + 系统管理员
# ============================================================
@router.post("", response_model=DocumentResponse)
def create_document(
    document_data: DocumentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_permission("document.create", current_user, db)

    draft_number = f"D-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    document = Document(
        title=document_data.title,
        document_type=document_data.document_type,
        draft_number=draft_number,
        creator_id=current_user.id,
        status=DocumentStatus.DRAFT
    )

    db.add(document)
    db.commit()
    db.refresh(document)
    return document


# ============================================================
#  查看文档 — 普通用户只看自己的，其他角色可看全部
# ============================================================
@router.get("", response_model=List[DocumentResponse])
def list_documents(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if has_permission("document.read_all", current_user):
        documents = db.query(Document).offset(skip).limit(limit).all()
    else:
        documents = db.query(Document).filter(
            Document.creator_id == current_user.id
        ).offset(skip).limit(limit).all()
    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    if not has_permission("document.read_all", current_user) and document.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看此文档")

    return document


# ============================================================
#  修改文档 — 状态锁定检查
# ============================================================
@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: uuid.UUID,
    document_data: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    # 权限：仅创建者可改，系统管理员可强制改
    if document.creator_id != current_user.id and not has_permission("document.force_update", current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改此文档")

    # 状态检查：仅 DRAFT / REJECTED 可改
    check_document_editable(document, field="content")

    for field, value in document_data.model_dump(exclude_unset=True).items():
        setattr(document, field, value)

    db.commit()
    db.refresh(document)
    return document


# ============================================================
#  上传 Word 文件
# ============================================================
@router.post("/{document_id}/upload")
async def upload_document_file(
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    if document.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权上传")

    # 状态检查
    check_document_editable(document, field="content")

    # 提取扩展名并加上点号，与配置格式统一 (如 ".docx")
    ext = ""
    if file.filename and '.' in file.filename:
        ext = '.' + file.filename.rsplit('.', 1)[-1].lower()
    if ext not in settings.document.allowed_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件格式，允许的格式: {', '.join(settings.document.allowed_formats)}"
        )

    # 读取文件内容并验证大小
    content = await file.read()
    max_size_bytes = settings.document.max_size_mb * 1024 * 1024
    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制（最大 {settings.document.max_size_mb} MB）"
        )

    file_path = f"{settings.document.storage_path}/{document_id}{ext}"
    os.makedirs(settings.document.storage_path, exist_ok=True)

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    document.file_path = file_path
    db.commit()

    return {"message": "文件上传成功", "file_path": file_path}


# ============================================================
#  提交校对 — 创建并行校对任务
# ============================================================
@router.post("/{document_id}/submit-proofreading")
def submit_proofreading(
    document_id: uuid.UUID,
    request: DocumentSubmitProofreadingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    # 仅创建者可提交
    if document.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅文档创建者可提交校对")

    submit_for_proofreading(db, document, request.proofreader_ids, current_user)
    return {"message": "已提交校对"}


# ============================================================
#  提交审批 — 校对完成后才能提交
# ============================================================
@router.post("/{document_id}/submit-approval")
def submit_approval(
    document_id: uuid.UUID,
    request: DocumentSubmitApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    if document.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅文档创建者可提交审批")

    submit_for_approval(db, document, request.flow_id, current_user)
    return {"message": "已提交审批"}


# ============================================================
#  强制解锁 — 仅系统管理员
# ============================================================
@router.post("/{document_id}/force-unlock")
def force_unlock(
    document_id: uuid.UUID,
    reason: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_permission("document.force_unlock", current_user, db)

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    log_audit(db, current_user, AuditEvent.NUMBER_FORCE_UNLOCK,
              "Document", str(document_id),
              {"reason": reason, "previous_status": document.status.value})

    unlock_document(db, document, current_user, reason)
    db.commit()

    return {"message": "文档已强制解锁"}


# ============================================================
#  获取文档校对任务
# ============================================================
@router.get("/{document_id}/proofreading-tasks")
def get_document_proofreading_tasks(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    tasks = db.query(ProofreadingTask).filter(
        ProofreadingTask.document_id == document_id
    ).all()
    return tasks


# ============================================================
#  获取文档审批任务
# ============================================================
@router.get("/{document_id}/approval-tasks")
def get_document_approval_tasks(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    tasks = db.query(ApprovalTask).filter(
        ApprovalTask.document_id == document_id
    ).all()
    return tasks


# ============================================================
#  删除文档 — 仅草稿可删
# ============================================================
@router.delete("/{document_id}")
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    if document.creator_id != current_user.id and not has_permission("document.delete", current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除")

    if document.status != DocumentStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅草稿可删除")

    db.delete(document)
    db.commit()
    return {"message": "文档已删除"}


# ============================================================
#  获取文档锁定详情
# ============================================================
@router.get("/{document_id}/locks")
def get_document_locks(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    locks = db.query(DocumentLock).filter(
        DocumentLock.document_id == document_id
    ).all()

    return [
        {
            "id": str(lock.id),
            "document_id": str(lock.document_id),
            "lock_type": lock.lock_type.value,
            "locked_by": str(lock.locked_by),
            "locked_at": lock.locked_at.isoformat() if lock.locked_at else None,
            "reason": lock.reason,
        }
        for lock in locks
    ]


# ============================================================
#  重新提交 — REJECTED → DRAFT (需求书状态机)
# ============================================================
@router.post("/{document_id}/resubmit")
def resubmit_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    if document.creator_id != current_user.id and not is_system_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅文档创建者可重新提交")

    if document.status != DocumentStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅已驳回状态的文档可重新提交"
        )

    # 状态回到草稿，解锁
    document.status = DocumentStatus.DRAFT
    unlock_document(db, document, current_user, "驳回后重新提交，回到草稿")
    db.commit()

    return {"message": "文档已回到草稿状态，可修改后重新提交"}
