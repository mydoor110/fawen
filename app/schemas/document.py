from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from app.models.document import DocumentStatus, LockType

class DocumentBase(BaseModel):
    title: str
    document_type: Optional[str] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    document_type: Optional[str] = None

class DocumentResponse(DocumentBase):
    id: UUID
    draft_number: Optional[str] = None
    official_number: Optional[str] = None
    status: DocumentStatus
    creator_id: UUID
    file_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    destroyed_at: Optional[datetime] = None
    is_locked: bool

    class Config:
        from_attributes = True

class DocumentLockResponse(BaseModel):
    id: UUID
    document_id: UUID
    lock_type: LockType
    locked_by: UUID
    locked_at: datetime
    reason: Optional[str] = None

    class Config:
        from_attributes = True

class DocumentSubmitProofreadingRequest(BaseModel):
    proofreader_ids: List[UUID]

class DocumentSubmitApprovalRequest(BaseModel):
    flow_id: UUID
