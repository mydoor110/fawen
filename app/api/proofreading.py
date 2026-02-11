"""
校对任务 API — 需求书第三节
校对 ≠ 审批，校对为并行多人确认
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.proofreading import ProofreadingTask, ProofreadingStatus
from app.models.document import Document, DocumentStatus
from app.schemas.proofreading import ProofreadingTaskResponse, ProofreadingCompleteRequest
from app.auth.dependencies import get_current_user, has_permission
from app.models.user import User
from app.services.document_service import check_proofreading_complete, unlock_document
from app.services.audit_service import log_audit, AuditEvent
from app.utils.logger import get_logger

router = APIRouter(prefix="/proofreading", tags=["Proofreading"])
logger = get_logger("proofreading")


@router.get("/tasks", response_model=List[ProofreadingTaskResponse])
def get_my_proofreading_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取分配给自己的待处理校对任务"""
    tasks = db.query(ProofreadingTask).filter(
        ProofreadingTask.proofreader_id == current_user.id,
        ProofreadingTask.status == ProofreadingStatus.PENDING
    ).all()
    return tasks


@router.post("/task/{task_id}/complete")
def complete_proofreading_task(
    task_id: uuid.UUID,
    request: ProofreadingCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    完成校对任务
    校对人员可以：查看内容、标记问题、提出修改建议、标记通过/不通过
    校对人员不能：修改 Word、修改编号、盖章、审批
    """
    task = db.query(ProofreadingTask).filter(ProofreadingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="校对任务不存在")

    # 仅分配的校对人可操作
    if task.proofreader_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该校对任务未分配给您")

    if task.status != ProofreadingStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该校对任务已处理")

    # 更新校对结果
    task.status = ProofreadingStatus.PASSED if request.passed else ProofreadingStatus.FAILED
    task.comment = request.comment
    task.completed_at = datetime.utcnow()

    # 审计 — 校对意见
    log_audit(db, current_user, AuditEvent.PROOFREAD_COMPLETE,
              "ProofreadingTask", str(task_id),
              {
                  "document_id": str(task.document_id),
                  "passed": request.passed,
                  "comment": request.comment
              })

    # 检查文档的所有校对任务是否完成
    document = db.query(Document).filter(Document.id == task.document_id).first()
    if document and document.status == DocumentStatus.PROOFREADING:
        is_complete, passed = check_proofreading_complete(db, document)

        if is_complete:
            if passed:
                # 全部通过 → 保持 PROOFREADING 状态，等待创建者提交审批
                logger.info(f"文档 {document.id} 校对全部通过，等待提交审批")
            else:
                # 校对失败 → 回到 DRAFT + 解锁
                document.status = DocumentStatus.DRAFT
                unlock_document(db, document, current_user, "校对未通过，自动解锁")
                logger.info(f"文档 {document.id} 校对未通过，回退到草稿")

    db.commit()

    result_text = "通过" if request.passed else "不通过"
    return {"message": f"校对已标记为{result_text}"}
