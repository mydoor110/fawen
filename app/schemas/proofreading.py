from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.proofreading import ProofreadingStatus


class ProofreadingTaskResponse(BaseModel):
    id: UUID
    document_id: UUID
    proofreader_id: UUID
    status: ProofreadingStatus
    comment: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProofreadingCompleteRequest(BaseModel):
    """校对完成请求 — passed=True 通过，passed=False 不通过"""
    passed: bool
    comment: Optional[str] = None
