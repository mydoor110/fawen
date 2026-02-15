"""
消息提醒服务
用于审批任务分配时的通知
"""
from typing import List
import uuid
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.user import User
from app.models.system import SystemConfig
from app.utils.logger import get_logger

logger = get_logger("notification")


class NotificationService:
    """消息提醒服务"""
    
    @staticmethod
    def notify_approval_assigned(
        db: Session,
        users: List[User],
        document_id: uuid.UUID,
        document_title: str,
        node_name: str
    ):
        """
        通知用户有新的审批任务
        
        Args:
            db: 数据库会话
            users: 被分配的用户列表
            document_id: 文档ID
            document_title: 文档标题
            node_name: 审批节点名称
        """
        for user in users:
            logger.info(
                f"通知用户审批任务: {user.username} - 文档: {document_title} - 节点: {node_name}"
            )
            
            # 这里可以扩展为实际的通知方式：
            # 1. 邮件通知
            # 2. 短信通知
            # 3. 推送通知
            # 4. 站内消息
            
            # 示例：记录到系统配置表作为简单的消息队列
            try:
                NotificationService._create_in_app_message(
                    db, user.id, document_id, document_title, node_name, "approval"
                )
            except Exception as e:
                logger.error(f"创建站内消息失败: {str(e)}")
    
    @staticmethod
    def notify_proofreading_assigned(
        db: Session,
        users: List[User],
        document_id: uuid.UUID,
        document_title: str
    ):
        """
        通知用户有新的校对任务
        
        Args:
            db: 数据库会话
            users: 被分配的用户列表
            document_id: 文档ID
            document_title: 文档标题
        """
        for user in users:
            logger.info(
                f"通知用户校对任务: {user.username} - 文档: {document_title}"
            )
            
            try:
                NotificationService._create_in_app_message(
                    db, user.id, document_id, document_title, "校对", "proofreading"
                )
            except Exception as e:
                logger.error(f"创建站内消息失败: {str(e)}")
    
    @staticmethod
    def _create_in_app_message(
        db: Session,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        document_title: str,
        node_name: str,
        message_type: str
    ):
        """
        创建站内消息（简化实现，存储到SystemConfig）
        
        实际生产环境应该使用专门的消息表或消息队列
        """
        # 获取或创建用户消息队列
        config_key = f"user_messages_{str(user_id)}"
        config = db.query(SystemConfig).filter(
            SystemConfig.config_key == config_key
        ).first()
        
        message = {
            "id": str(uuid.uuid4()),
            "type": message_type,
            "document_id": str(document_id),
            "document_title": document_title,
            "node_name": node_name,
            "created_at": datetime.utcnow().isoformat(),
            "read": False
        }
        
        if config:
            messages = config.config_value if isinstance(config.config_value, list) else []
            messages.append(message)
            config.config_value = messages
        else:
            config = SystemConfig(
                config_key=config_key,
                config_value=[message],
                description=f"用户 {user_id} 的消息队列"
            )
            db.add(config)
        
        db.commit()
        logger.info(f"创建站内消息: 用户={user_id}, 类型={message_type}, 文档={document_title}")


# 便捷函数
def notify_approval(db: Session, users: List[User], document_id: uuid.UUID, 
                   document_title: str, node_name: str):
    """通知审批任务"""
    NotificationService.notify_approval_assigned(
        db, users, document_id, document_title, node_name
    )


def notify_proofreading(db: Session, users: List[User], document_id: uuid.UUID, 
                       document_title: str):
    """通知校对任务"""
    NotificationService.notify_proofreading_assigned(
        db, users, document_id, document_title
    )
