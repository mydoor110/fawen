from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from app.core.database import Base

class DocumentStatus(str, enum.Enum):
    DRAFT = "draft"
    PROOFREADING = "proofreading"
    APPROVAL = "approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    DESTROYED = "destroyed"

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    document_type = Column(String(50))
    file_path = Column(String(500))
    official_number = Column(String(100), unique=True, index=True)
    draft_number = Column(String(100), index=True)
    status = Column(
        SQLEnum(DocumentStatus, values_callable=lambda x: [e.value for e in x]),
        default=DocumentStatus.DRAFT, index=True
    )
    creator_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    approval_flow_id = Column(UUID(as_uuid=True), index=True)  # 记录使用的审批流程
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    submitted_at = Column(DateTime(timezone=True))
    approved_at = Column(DateTime(timezone=True))
    destroyed_at = Column(DateTime(timezone=True))
    is_locked = Column(Boolean, default=False)

class LockType(str, enum.Enum):
    NUMBER = "number"
    CONTENT = "content"
    ALL = "all"

class DocumentLock(Base):
    __tablename__ = "document_locks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    lock_type = Column(
        SQLEnum(LockType, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    locked_by = Column(UUID(as_uuid=True), nullable=False)
    locked_at = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(String(500))
