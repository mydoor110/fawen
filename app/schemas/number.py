from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from app.models.number import NumberRecordStatus

class NumberPoolResponse(BaseModel):
    id: UUID
    year: int
    category: str
    prefix: str
    start_number: int
    current_number: int
    end_number: int

    class Config:
        from_attributes = True

class NumberRecordResponse(BaseModel):
    id: UUID
    document_id: UUID
    official_number: str
    status: NumberRecordStatus
    allocated_at: Optional[datetime] = None
    allocated_by: Optional[UUID] = None
    recycled_at: Optional[datetime] = None
    recycled_by: Optional[UUID] = None
    recycle_reason: Optional[str] = None
    manual_adjustment: bool

    class Config:
        from_attributes = True

class NumberAdjustRequest(BaseModel):
    new_number: str
    reason: str

class RecyclePoolResponse(BaseModel):
    id: UUID
    official_number: str
    document_id: Optional[UUID] = None
    reason: Optional[str] = None
    recycled_at: datetime
    is_available: bool

    class Config:
        from_attributes = True
