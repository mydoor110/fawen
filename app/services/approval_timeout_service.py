"""
审批超时处理服务
Author: AI Assistant
Date: 2026-02-15

功能:
1. 检测超时的审批任务
2. 发送超时提醒通知
3. 根据策略自动处理超时任务
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
import enum

from app.models.approval import ApprovalTask, ApprovalStatus, ApprovalNode
from app.models.document import Document, DocumentStatus
from app.services.notification_service import NotificationService
from app.services.audit_service import log_audit, AuditEvent
from app.core.config import settings
from loguru import logger


class TimeoutStrategy(str, enum.Enum):
    """超时处理策略"""
    AUTO_APPROVE = "auto_approve"      # 自动通过
    AUTO_REJECT = "auto_reject"        # 自动驳回
    ESCALATE = "escalate"              # 升级给上级/系统管理员
    NOTIFY_ONLY = "notify_only"        # 仅通知,不自动处理


class ApprovalTimeoutService:
    """审批超时处理服务"""
    
    @staticmethod
    def get_timeout_strategy() -> TimeoutStrategy:
        """获取超时策略配置"""
        if hasattr(settings, 'approval') and hasattr(settings.approval, 'timeout_strategy'):
            return TimeoutStrategy(settings.approval.timeout_strategy)
        return TimeoutStrategy.NOTIFY_ONLY  # 默认仅通知
    
    @staticmethod
    def check_and_handle_timeouts(db: Session) -> dict:
        """
        检查并处理超时的审批任务
        
        Returns:
            处理统计信息
        """
        now = datetime.utcnow()
        strategy = ApprovalTimeoutService.get_timeout_strategy()
        
        # 查找已超时但未处理的待审批任务
        timeout_tasks = db.query(ApprovalTask).filter(
            and_(
                ApprovalTask.status == ApprovalStatus.PENDING,
                ApprovalTask.deadline < now,
                ApprovalTask.deadline.isnot(None)
            )
        ).all()
        
        stats = {
            "total_timeout": len(timeout_tasks),
            "auto_approved": 0,
            "auto_rejected": 0,
            "escalated": 0,
            "notified": 0
        }
        
        for task in timeout_tasks:
            logger.warning(
                f"审批任务 {task.id} 已超时: "
                f"截止时间={task.deadline}, 当前时间={now}"
            )
            
            # 根据策略处理
            if strategy == TimeoutStrategy.AUTO_APPROVE:
                ApprovalTimeoutService._auto_approve(db, task)
                stats["auto_approved"] += 1
                
            elif strategy == TimeoutStrategy.AUTO_REJECT:
                ApprovalTimeoutService._auto_reject(db, task)
                stats["auto_rejected"] += 1
                
            elif strategy == TimeoutStrategy.ESCALATE:
                ApprovalTimeoutService._escalate(db, task)
                stats["escalated"] += 1
                
            else:  # NOTIFY_ONLY
                ApprovalTimeoutService._send_timeout_notification(db, task)
                stats["notified"] += 1
        
        logger.info(f"审批超时处理完成: {stats}")
        return stats
    
    @staticmethod
    def check_upcoming_timeouts(db: Session, remind_days: int = 3) -> List[ApprovalTask]:
        """
        检查即将超时的审批任务(用于提前提醒)
        
        Args:
            remind_days: 提前几天提醒
        """
        now = datetime.utcnow()
        remind_time = now + timedelta(days=remind_days)
        
        upcoming_timeout_tasks = db.query(ApprovalTask).filter(
            and_(
                ApprovalTask.status == ApprovalStatus.PENDING,
                ApprovalTask.deadline.between(now, remind_time),
                ApprovalTask.deadline.isnot(None),
                ApprovalTask.timeout_notified == False
            )
        ).all()
        
        for task in upcoming_timeout_tasks:
            ApprovalTimeoutService._send_reminder(db, task, remind_days)
            task.timeout_notified = True
        
        db.commit()
        return upcoming_timeout_tasks
    
    @staticmethod
    def _auto_approve(db: Session, task: ApprovalTask):
        """自动通过审批"""
        from app.services.document_service import process_approval_action
        
        task.status = ApprovalStatus.APPROVED
        task.comment = f"[系统自动通过] 审批超时,根据配置自动通过 (截止时间: {task.deadline})"
        task.completed_at = datetime.utcnow()
        
        # 记录审计日志
        log_audit(
            db, None, AuditEvent.APPROVAL_TIMEOUT_AUTO_APPROVED,
            "ApprovalTask", str(task.id),
            {"deadline": str(task.deadline), "document_id": str(task.document_id)}
        )
        
        # 发送通知
        NotificationService.send_notification(
            db,
            user_id=task.approver_id,
            title="审批任务已自动通过",
            message=f"您的审批任务已超时,系统已自动通过该审批。",
            type="warning"
        )
        
        db.commit()
        logger.info(f"审批任务 {task.id} 超时自动通过")
    
    @staticmethod
    def _auto_reject(db: Session, task: ApprovalTask):
        """自动驳回审批"""
        task.status = ApprovalStatus.REJECTED
        task.comment = f"[系统自动驳回] 审批超时,根据配置自动驳回 (截止时间: {task.deadline})"
        task.completed_at = datetime.utcnow()
        
        # 更新文档状态为已驳回
        document = db.query(Document).filter(Document.id == task.document_id).first()
        if document:
            document.status = DocumentStatus.REJECTED
        
        # 记录审计日志
        log_audit(
            db, None, AuditEvent.APPROVAL_TIMEOUT_AUTO_REJECTED,
            "ApprovalTask", str(task.id),
            {"deadline": str(task.deadline), "document_id": str(task.document_id)}
        )
        
        # 发送通知
        NotificationService.send_notification(
            db,
            user_id=task.approver_id,
            title="审批任务已自动驳回",
            message=f"您的审批任务已超时,系统已自动驳回该文档。",
            type="error"
        )
        
        db.commit()
        logger.info(f"审批任务 {task.id} 超时自动驳回")
    
    @staticmethod
    def _escalate(db: Session, task: ApprovalTask):
        """升级给系统管理员"""
        from app.models.user import User, Role
        
        # 查找系统管理员
        admin_role = db.query(Role).filter(Role.name == "系统管理员").first()
        if not admin_role:
            logger.error("未找到系统管理员角色,无法升级审批任务")
            ApprovalTimeoutService._send_timeout_notification(db, task)
            return
        
        admins = db.query(User).join(User.roles).filter(
            Role.id == admin_role.id,
            User.is_active == True
        ).all()
        
        if not admins:
            logger.error("未找到可用的系统管理员,无法升级审批任务")
            ApprovalTimeoutService._send_timeout_notification(db, task)
            return
        
        # 转移给第一个系统管理员
        original_approver_id = task.approver_id
        task.approver_id = admins[0].id
        
        # 记录审计日志
        log_audit(
            db, None, AuditEvent.APPROVAL_TIMEOUT_ESCALATED,
            "ApprovalTask", str(task.id),
            {
                "deadline": str(task.deadline),
                "original_approver": str(original_approver_id),
                "escalated_to": str(admins[0].id)
            }
        )
        
        # 发送通知给原审批人
        NotificationService.send_notification(
            db,
            user_id=original_approver_id,
            title="审批任务已升级",
            message=f"您的审批任务已超时,已升级给系统管理员处理。",
            type="warning"
        )
        
        # 发送通知给新审批人
        NotificationService.send_notification(
            db,
            user_id=admins[0].id,
            title="收到升级的审批任务",
            message=f"收到一个超时升级的审批任务,请尽快处理。",
            type="info"
        )
        
        db.commit()
        logger.info(f"审批任务 {task.id} 超时升级: {original_approver_id} -> {admins[0].id}")
    
    @staticmethod
    def _send_timeout_notification(db: Session, task: ApprovalTask):
        """发送超时通知"""
        NotificationService.send_notification(
            db,
            user_id=task.approver_id,
            title="审批任务已超时",
            message=f"您有一个审批任务已超时,请尽快处理。截止时间: {task.deadline}",
            type="error"
        )
        
        # 标记已通知
        task.timeout_notified = True
        db.commit()
        
        logger.info(f"审批任务 {task.id} 发送超时通知")
    
    @staticmethod
    def _send_reminder(db: Session, task: ApprovalTask, days: int):
        """发送即将超时提醒"""
        NotificationService.send_notification(
            db,
            user_id=task.approver_id,
            title=f"审批任务将在{days}天后超时",
            message=f"您有一个审批任务即将超时,请及时处理。截止时间: {task.deadline}",
            type="warning"
        )
        
        logger.info(f"审批任务 {task.id} 发送提前{days}天提醒")
