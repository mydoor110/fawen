"""
文档业务逻辑服务层
实现提交校对、提交审批、自动分配文件号等核心业务
"""
from datetime import datetime
from typing import List
import uuid

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.document import Document, DocumentStatus, DocumentLock, LockType
from app.models.proofreading import ProofreadingTask, ProofreadingStatus
from app.models.approval import ApprovalFlow, ApprovalNode, ApprovalTask, ApprovalStatus
from app.models.number import NumberPool, NumberRecord, NumberRecordStatus, RecyclePool
from app.models.user import User, UserApprovalRole
from app.services.audit_service import log_audit, AuditEvent
from app.utils.logger import get_logger

logger = get_logger("document_service")


def _get_users_by_approval_role(db: Session, approval_role_id: uuid.UUID) -> List[uuid.UUID]:
    """
    根据审批角色 ID 查找拥有该角色的所有用户 ID
    按 priority 排序（优先级高的在前）
    """
    user_roles = db.query(UserApprovalRole).filter(
        UserApprovalRole.approval_role_id == approval_role_id
    ).order_by(UserApprovalRole.priority.desc()).all()
    return [ur.user_id for ur in user_roles]


def check_document_editable(document: Document, field: str = "content"):
    """
    检查文档是否可编辑 — 需求书第二节状态锁定关系
    field: "content" | "number"
    """
    if field == "content":
        # Word 可改：仅 DRAFT / REJECTED
        if document.status not in [DocumentStatus.DRAFT, DocumentStatus.REJECTED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"当前状态「{document.status.value}」下文档内容不可修改"
            )
    elif field == "number":
        # 编号：任何非 DRAFT 状态均锁定
        if document.status != DocumentStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="编号字段已锁定，仅草稿状态可修改"
            )


def submit_for_proofreading(
    db: Session,
    document: Document,
    proofreader_ids: List[uuid.UUID],
    current_user: User
):
    """
    提交校对 — 需求书第三节
    创建并行校对任务 + 锁定编号字段
    """
    if document.status != DocumentStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅草稿状态可提交校对"
        )

    if not proofreader_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请指定至少一名校对人员"
        )

    # 创建并行校对任务
    for pid in proofreader_ids:
        task = ProofreadingTask(
            document_id=document.id,
            proofreader_id=pid,
            status=ProofreadingStatus.PENDING
        )
        db.add(task)

    # 锁定编号字段
    lock = DocumentLock(
        document_id=document.id,
        lock_type=LockType.NUMBER,
        locked_by=current_user.id,
        reason="自动锁定：提交校对时锁定编号字段"
    )
    db.add(lock)
    document.is_locked = True
    document.status = DocumentStatus.PROOFREADING
    document.submitted_at = datetime.utcnow()

    # 审计
    log_audit(db, current_user, AuditEvent.NUMBER_LOCK,
              "Document", str(document.id),
              {"reason": "提交校对自动锁定", "proofreader_count": len(proofreader_ids)})

    db.commit()
    logger.info(f"文档 {document.id} 提交校对，校对人 {len(proofreader_ids)} 名")


def check_proofreading_complete(db: Session, document: Document):
    """
    检查校对是否完成 — 支持 all_pass / majority_pass 模式
    返回 (is_complete, passed)
    """
    tasks = db.query(ProofreadingTask).filter(
        ProofreadingTask.document_id == document.id
    ).all()

    if not tasks:
        return True, True  # 无校对任务视为通过

    total = len(tasks)
    passed = sum(1 for t in tasks if t.status == ProofreadingStatus.PASSED)
    failed = sum(1 for t in tasks if t.status == ProofreadingStatus.FAILED)
    pending = sum(1 for t in tasks if t.status == ProofreadingStatus.PENDING)

    mode = getattr(settings, 'proofreading', None)
    proofreading_mode = "all_pass"
    if mode and hasattr(mode, 'mode'):
        proofreading_mode = mode.mode

    if proofreading_mode == "all_pass":
        if pending > 0:
            return False, None  # 还有人未完成
        return True, (failed == 0)
    elif proofreading_mode == "majority_pass":
        # 严格 >50%
        if passed > total / 2:
            return True, True
        if failed >= total / 2:
            return True, False
        return False, None
    else:
        # 默认 all_pass
        if pending > 0:
            return False, None
        return True, (failed == 0)


def submit_for_approval(
    db: Session,
    document: Document,
    flow_id: uuid.UUID,
    current_user: User
):
    """
    提交审批 — 需求书第四节
    前置条件：校对必须已完成
    节点绑定审批角色 → 解析为具体用户 → 为每个用户创建 ApprovalTask
    """
    # 如果文档在校对中，检查校对是否完成
    if document.status == DocumentStatus.PROOFREADING:
        is_complete, passed = check_proofreading_complete(db, document)
        if not is_complete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="校对尚未完成，无法提交审批"
            )
        if not passed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="校对未通过，无法提交审批"
            )
    elif document.status == DocumentStatus.DRAFT:
        # 草稿直接提交审批（跳过校对）—— 允许
        pass
    elif document.status == DocumentStatus.REJECTED:
        # 驳回后重新提交
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"当前状态「{document.status.value}」不可提交审批"
        )

    # 获取审批流程
    flow = db.query(ApprovalFlow).filter(ApprovalFlow.id == flow_id).first()
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="审批流程不存在"
        )

    # 获取审批节点并按顺序排列
    nodes = db.query(ApprovalNode).filter(
        ApprovalNode.flow_id == flow_id
    ).order_by(ApprovalNode.sequence).all()

    if not nodes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="审批流程没有配置节点"
        )

    # 仅激活第一个节点的任务（串行推进节点）
    # 根据节点的 approval_role_id 解析出具体的用户
    first_node = nodes[0]
    approver_user_ids = _get_users_by_approval_role(db, first_node.approval_role_id)

    if not approver_user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"审批节点「{first_node.sequence}」对应的审批角色没有分配用户"
        )

    for user_id in approver_user_ids:
        task = ApprovalTask(
            document_id=document.id,
            node_id=first_node.id,
            approver_id=user_id,
            status=ApprovalStatus.PENDING
        )
        db.add(task)

    # 全锁定
    all_lock = DocumentLock(
        document_id=document.id,
        lock_type=LockType.ALL,
        locked_by=current_user.id,
        reason="自动锁定：提交审批时全部锁定"
    )
    db.add(all_lock)

    document.is_locked = True
    document.status = DocumentStatus.APPROVAL
    document.submitted_at = datetime.utcnow()

    log_audit(db, current_user, AuditEvent.NUMBER_LOCK,
              "Document", str(document.id),
              {"reason": "提交审批全锁定", "flow": flow.name})

    db.commit()
    logger.info(f"文档 {document.id} 提交审批，流程: {flow.name}")


def allocate_official_number(db: Session, document: Document, allocated_by: User):
    """
    分配正式文件号 — 需求书第五节
    仅在审批全部通过后自动调用
    """
    if document.official_number:
        return document.official_number

    # 优先从回收池复用
    recycle_record = db.query(RecyclePool).filter(
        RecyclePool.is_available == True
    ).first()

    recycle_first = True
    if hasattr(settings, 'number') and hasattr(settings.number, 'pool'):
        recycle_first = getattr(settings.number.pool, 'recycle_first', True)

    if recycle_record and recycle_first:
        official_number = recycle_record.official_number
        recycle_record.is_available = False

        number_record = NumberRecord(
            document_id=document.id,
            official_number=official_number,
            status=NumberRecordStatus.ALLOCATED,
            allocated_at=datetime.utcnow(),
            allocated_by=allocated_by.id
        )
        db.add(number_record)
    else:
        current_year = datetime.now().year
        pool = db.query(NumberPool).filter(
            NumberPool.year == current_year
        ).first()

        if not pool:
            prefix = "GW"
            if hasattr(settings, 'number') and hasattr(settings.number, 'format'):
                prefix = getattr(settings.number.format, 'prefix', 'GW')
            pool = NumberPool(
                year=current_year,
                category="default",
                prefix=prefix,
                start_number=1,
                current_number=1,
                end_number=9999
            )
            db.add(pool)
            db.flush()

        official_number = f"{pool.prefix}-{pool.year}-{pool.current_number:04d}"

        number_record = NumberRecord(
            document_id=document.id,
            official_number=official_number,
            status=NumberRecordStatus.ALLOCATED,
            allocated_at=datetime.utcnow(),
            allocated_by=allocated_by.id
        )
        db.add(number_record)
        pool.current_number += 1

    document.official_number = official_number

    log_audit(db, allocated_by, AuditEvent.NUMBER_ALLOCATE,
              "Document", str(document.id),
              {"official_number": official_number})

    logger.info(f"文档 {document.id} 分配正式文件号: {official_number}")
    return official_number


def unlock_document(db: Session, document: Document, user: User, reason: str = ""):
    """解锁文档"""
    locks = db.query(DocumentLock).filter(
        DocumentLock.document_id == document.id
    ).all()
    for lock in locks:
        db.delete(lock)
    document.is_locked = False

    log_audit(db, user, AuditEvent.NUMBER_UNLOCK,
              "Document", str(document.id),
              {"reason": reason})
