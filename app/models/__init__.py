# 导入所有模型，确保 SQLAlchemy 能识别并创建所有表
from app.models.user import User, Role, UserRole, ApprovalRole, UserApprovalRole
from app.models.document import Document, DocumentLock
from app.models.approval import ApprovalFlow, ApprovalNode, ApprovalTask
from app.models.number import NumberPool, NumberRecord, RecyclePool
from app.models.proofreading import ProofreadingTask
from app.models.system import SystemConfig, AuditLog
