from sqlalchemy import Column, Integer, Text, String, Boolean, DateTime, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.core.database import Base

class NodeApprovalType(str, enum.Enum):
    AND = "and"
    OR = "or"

class ApprovalFlow(Base):
    __tablename__ = "approval_flows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    flow_data = Column(Text)  # AntFlow 流程设计器 JSON 数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ApprovalNode(Base):
    __tablename__ = "approval_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("approval_flows.id"), nullable=False)
    approval_role_id = Column(UUID(as_uuid=True), ForeignKey("approval_roles.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    node_type = Column(
        SQLEnum(NodeApprovalType, values_callable=lambda x: [e.value for e in x]),
        default=NodeApprovalType.AND
    )
    timeout_days = Column(Integer, default=7)

class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"

class ApprovalTask(Base):
    __tablename__ = "approval_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    node_id = Column(UUID(as_uuid=True), ForeignKey("approval_nodes.id"), nullable=False)
    approver_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(
        SQLEnum(ApprovalStatus, values_callable=lambda x: [e.value for e in x]),
        default=ApprovalStatus.PENDING, index=True
    )
    comment = Column(Text)
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
