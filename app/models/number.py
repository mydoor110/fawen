from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from app.core.database import Base

class NumberRecordStatus(str, enum.Enum):
    RESERVED = "reserved"
    ALLOCATED = "allocated"
    RECYCLED = "recycled"

class NumberPool(Base):
    __tablename__ = "number_pools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    year = Column(Integer, nullable=False)
    category = Column(String(50), nullable=False)
    prefix = Column(String(10), nullable=False)
    start_number = Column(Integer, nullable=False)
    current_number = Column(Integer, nullable=False)
    end_number = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class NumberRecord(Base):
    __tablename__ = "number_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    official_number = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(
        SQLEnum(NumberRecordStatus, values_callable=lambda x: [e.value for e in x]),
        default=NumberRecordStatus.RESERVED, index=True
    )
    allocated_at = Column(DateTime(timezone=True))
    allocated_by = Column(UUID(as_uuid=True))
    recycled_at = Column(DateTime(timezone=True))
    recycled_by = Column(UUID(as_uuid=True))
    recycle_reason = Column(String(500))
    manual_adjustment = Column(Boolean, default=False)

class RecyclePool(Base):
    __tablename__ = "recycle_pool"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    official_number = Column(String(100), unique=True, nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    reason = Column(String(500))
    recycled_at = Column(DateTime(timezone=True), server_default=func.now())
    is_available = Column(Boolean, default=True)
