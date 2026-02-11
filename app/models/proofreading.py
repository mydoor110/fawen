from sqlalchemy import Column, Text, String, DateTime, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.core.database import Base

class ProofreadingStatus(str, enum.Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"

class ProofreadingTask(Base):
    __tablename__ = "proofreading_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    proofreader_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(
        SQLEnum(ProofreadingStatus, values_callable=lambda x: [e.value for e in x]),
        default=ProofreadingStatus.PENDING, index=True
    )
    comment = Column(Text)
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
