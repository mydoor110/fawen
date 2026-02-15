"""
审批流程 API — 需求书第四节
审批为串行（非并行），逐节点推进
最终通过后自动分配文件号
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime

from app.core.database import get_db
from app.models.approval import ApprovalTask, ApprovalStatus, ApprovalFlow, ApprovalNode, NodeApprovalType
from app.models.document import Document, DocumentStatus
from app.schemas.approval import ApprovalTaskResponse, ApprovalActionRequest, ApprovalFlowResponse, ApprovalNodeResponse
from app.auth.dependencies import get_current_user, check_permission, has_permission
from app.models.user import User
from app.services.document_service import allocate_official_number, unlock_document
from app.services.audit_service import log_audit, AuditEvent
from app.utils.logger import get_logger

router = APIRouter(prefix="/approval", tags=["Approval"])
logger = get_logger("approval")


@router.get("/tasks", response_model=List[ApprovalTaskResponse])
def get_my_approval_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取分配给自己的待审批任务（approver_id 直接存储 User ID）"""
    tasks = db.query(ApprovalTask).filter(
        ApprovalTask.approver_id == current_user.id,
        ApprovalTask.status == ApprovalStatus.PENDING
    ).all()
    return tasks


@router.get("/document/{document_id}/tasks", response_model=List[ApprovalTaskResponse])
def get_document_approval_tasks(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文档的所有审批任务"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    tasks = db.query(ApprovalTask).filter(ApprovalTask.document_id == document_id).all()
    return tasks


@router.post("/task/{task_id}/approve")
def approve_task(
    task_id: uuid.UUID,
    request: ApprovalActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    审批通过
    审批人员：仅处理分配给自己的节点，无权修改文件和编号
    """
    task = db.query(ApprovalTask).filter(ApprovalTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审批任务不存在")

    if task.approver_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该任务未分配给您")

    if task.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该任务已处理")

    # 更新任务状态
    task.status = ApprovalStatus.APPROVED
    task.comment = request.comment
    task.completed_at = datetime.utcnow()

    # 审计 — 审批意见
    log_audit(db, current_user, AuditEvent.APPROVAL_APPROVE,
              "ApprovalTask", str(task_id),
              {"document_id": str(task.document_id), "comment": request.comment})

    # 获取节点信息，判断是否推进
    node = db.query(ApprovalNode).filter(ApprovalNode.id == task.node_id).first()

    if node.node_type == NodeApprovalType.AND:
        # AND 模式：该节点所有任务都通过才推进
        all_node_tasks = db.query(ApprovalTask).filter(
            ApprovalTask.node_id == node.id,
            ApprovalTask.document_id == task.document_id
        ).all()
        all_approved = all(t.status == ApprovalStatus.APPROVED for t in all_node_tasks)

        if all_approved:
            _advance_to_next_node(db, node, task.document_id, current_user)
    else:
        # OR 模式：任一通过即推进（跳过该节点其他人）
        other_tasks = db.query(ApprovalTask).filter(
            ApprovalTask.node_id == node.id,
            ApprovalTask.document_id == task.document_id,
            ApprovalTask.id != task_id
        ).all()
        for t in other_tasks:
            if t.status == ApprovalStatus.PENDING:
                t.status = ApprovalStatus.SKIPPED
                t.completed_at = datetime.utcnow()

        _advance_to_next_node(db, node, task.document_id, current_user)

    db.commit()
    return {"message": "审批通过"}


@router.post("/task/{task_id}/reject")
def reject_task(
    task_id: uuid.UUID,
    request: ApprovalActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    审批驳回 — 文档回到 REJECTED + 解锁
    """
    task = db.query(ApprovalTask).filter(ApprovalTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审批任务不存在")

    if task.approver_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该任务未分配给您")

    if task.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该任务已处理")

    document = db.query(Document).filter(Document.id == task.document_id).first()

    # 更新任务
    task.status = ApprovalStatus.REJECTED
    task.comment = request.comment
    task.completed_at = datetime.utcnow()

    # 审计 — 审批驳回
    log_audit(db, current_user, AuditEvent.APPROVAL_REJECT,
              "ApprovalTask", str(task_id),
              {"document_id": str(task.document_id), "comment": request.comment})

    # 文档回到 REJECTED + 解锁
    document.status = DocumentStatus.REJECTED
    unlock_document(db, document, current_user, f"审批驳回: {request.comment}")

    # 清除该文档剩余待处理的审批任务
    pending_tasks = db.query(ApprovalTask).filter(
        ApprovalTask.document_id == task.document_id,
        ApprovalTask.status == ApprovalStatus.PENDING,
        ApprovalTask.id != task_id
    ).all()
    for t in pending_tasks:
        t.status = ApprovalStatus.SKIPPED
        t.completed_at = datetime.utcnow()

    db.commit()
    return {"message": "审批已驳回，文档退回修改"}


# ============================================================
#  审批流程管理
# ============================================================
@router.get("/flows", response_model=List[ApprovalFlowResponse])
def list_approval_flows(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    flows = db.query(ApprovalFlow).all()
    return flows


@router.post("/flows", response_model=ApprovalFlowResponse)
def create_approval_flow(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_permission("approval.create_flow", current_user, db)
    flow = ApprovalFlow(
        name=data.get("name"),
        description=data.get("description", "")
    )
    db.add(flow)
    db.commit()
    db.refresh(flow)
    return flow


@router.put("/flows/{flow_id}", response_model=ApprovalFlowResponse)
def update_approval_flow(
    flow_id: uuid.UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_permission("approval.create_flow", current_user, db)
    flow = db.query(ApprovalFlow).filter(ApprovalFlow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="审批流程不存在")
    if "name" in data:
        flow.name = data["name"]
    if "description" in data:
        flow.description = data["description"]
    if "is_active" in data:
        flow.is_active = data["is_active"]
    if "flow_data" in data:
        flow.flow_data = data["flow_data"]
    db.commit()
    db.refresh(flow)
    return flow


@router.delete("/flows/{flow_id}")
def delete_approval_flow(
    flow_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_permission("approval.create_flow", current_user, db)
    flow = db.query(ApprovalFlow).filter(ApprovalFlow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="审批流程不存在")
    # 删除流程下的所有节点
    db.query(ApprovalNode).filter(ApprovalNode.flow_id == flow_id).delete()
    db.delete(flow)
    db.commit()
    return {"message": "审批流程已删除"}


# ============================================================
#  审批节点管理
# ============================================================
@router.get("/flows/{flow_id}/nodes", response_model=List[ApprovalNodeResponse])
def list_flow_nodes(
    flow_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    nodes = db.query(ApprovalNode).filter(
        ApprovalNode.flow_id == flow_id
    ).order_by(ApprovalNode.sequence).all()
    return nodes


@router.post("/flows/{flow_id}/nodes", response_model=ApprovalNodeResponse)
def create_flow_node(
    flow_id: uuid.UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_permission("approval.create_flow", current_user, db)
    flow = db.query(ApprovalFlow).filter(ApprovalFlow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="审批流程不存在")

    # 自动计算 sequence
    max_seq = db.query(ApprovalNode).filter(
        ApprovalNode.flow_id == flow_id
    ).count()

    node = ApprovalNode(
        flow_id=flow_id,
        approval_role_id=data.get("approval_role_id"),
        sequence=data.get("sequence", max_seq + 1),
        node_type=data.get("node_type", "and"),
        timeout_days=data.get("timeout_days", 7)
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


@router.put("/flows/{flow_id}/nodes/{node_id}", response_model=ApprovalNodeResponse)
def update_flow_node(
    flow_id: uuid.UUID,
    node_id: uuid.UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_permission("approval.create_flow", current_user, db)
    node = db.query(ApprovalNode).filter(
        ApprovalNode.id == node_id,
        ApprovalNode.flow_id == flow_id
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail="审批节点不存在")
    if "approval_role_id" in data:
        node.approval_role_id = data["approval_role_id"]
    if "sequence" in data:
        node.sequence = data["sequence"]
    if "node_type" in data:
        node.node_type = data["node_type"]
    if "timeout_days" in data:
        node.timeout_days = data["timeout_days"]
    db.commit()
    db.refresh(node)
    return node


@router.delete("/flows/{flow_id}/nodes/{node_id}")
def delete_flow_node(
    flow_id: uuid.UUID,
    node_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_permission("approval.create_flow", current_user, db)
    node = db.query(ApprovalNode).filter(
        ApprovalNode.id == node_id,
        ApprovalNode.flow_id == flow_id
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail="审批节点不存在")
    db.delete(node)
    # 重新排序剩余节点
    remaining = db.query(ApprovalNode).filter(
        ApprovalNode.flow_id == flow_id
    ).order_by(ApprovalNode.sequence).all()
    for i, n in enumerate(remaining):
        n.sequence = i + 1
    db.commit()
    return {"message": "审批节点已删除"}


# ============================================================
#  内部函数
# ============================================================
def _advance_to_next_node(db: Session, current_node: ApprovalNode, document_id: uuid.UUID, user: User):
    """
    推进到下一个审批节点
    如果无下一节点 → 文档审批通过 → 自动分配文件号
    """
    from app.services.document_service import _get_users_by_approval_role

    next_node = db.query(ApprovalNode).filter(
        ApprovalNode.flow_id == current_node.flow_id,
        ApprovalNode.sequence > current_node.sequence
    ).order_by(ApprovalNode.sequence).first()

    if next_node:
        # 激活下一节点任务 — 解析角色为具体用户
        approver_user_ids = _get_users_by_approval_role(db, next_node.approval_role_id)
        if not approver_user_ids:
            logger.warning(f"审批节点 seq={next_node.sequence} 对应角色没有分配用户，跳过该节点")
            # 如果该节点没有用户，递归跳过到下一个节点
            _advance_to_next_node(db, next_node, document_id, user)
            return

        for user_id in approver_user_ids:
            new_task = ApprovalTask(
                document_id=document_id,
                node_id=next_node.id,
                approver_id=user_id,
                status=ApprovalStatus.PENDING
            )
            db.add(new_task)
        logger.info(f"文档 {document_id} 推进到审批节点 seq={next_node.sequence}，审批人 {len(approver_user_ids)} 名")
    else:
        # 最终节点通过 → 审批完成
        document = db.query(Document).filter(Document.id == document_id).first()
        document.status = DocumentStatus.APPROVED
        document.approved_at = datetime.utcnow()

        # 自动分配正式文件号（需求书第五节）
        allocate_official_number(db, document, user)

        # 解锁
        unlock_document(db, document, user, "审批全部通过，自动解锁")

        logger.info(f"文档 {document_id} 审批全部通过，文件号: {document.official_number}")
