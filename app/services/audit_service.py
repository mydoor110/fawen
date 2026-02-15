"""
统一审计日志服务
覆盖需求书第七节要求的 7 类强制记录事件
"""
from sqlalchemy.orm import Session
from app.models.system import AuditLog
from app.models.user import User
from app.utils.logger import get_logger

logger = get_logger("audit")


class AuditEvent:
    """审计事件类型常量"""
    NUMBER_ADJUST = "number.adjust"           # 编号手动修改
    NUMBER_LOCK = "number.lock"               # 编号锁定
    NUMBER_UNLOCK = "number.unlock"           # 编号解锁
    NUMBER_FORCE_UNLOCK = "number.force_unlock"  # 强制解锁
    PROOFREAD_SUBMIT = "proofread.submit"     # 校对意见提交
    PROOFREAD_COMPLETE = "proofread.complete"  # 校对完成
    APPROVAL_APPROVE = "approval.approve"     # 审批通过
    APPROVAL_REJECT = "approval.reject"       # 审批驳回
    DOCUMENT_DESTROY = "document.destroy"     # 销毁操作
    DOCUMENT_SEAL = "document.seal"           # 文档盖章
    NUMBER_RECYCLE = "number.recycle"          # 编号回收
    NUMBER_ALLOCATE = "number.allocate"       # 编号分配
    PERMISSION_DENIED = "permission.denied"   # 越权操作被拒绝


def log_audit(
    db: Session,
    user: User,
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict = None,
    ip_address: str = None
):
    """
    写入审计日志（强制，不受 config 开关控制）
    """
    audit_log = AuditLog(
        user_id=user.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address
    )
    db.add(audit_log)
    logger.info(
        f"审计: {user.username} -> {action} on {resource_type}#{resource_id}"
    )
