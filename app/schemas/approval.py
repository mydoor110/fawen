from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from app.models.approval import ApprovalStatus, NodeApprovalType

class ApprovalFlowResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    is_active: bool
    flow_data: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ApprovalNodeResponse(BaseModel):
    id: UUID
    flow_id: UUID
    approval_role_id: UUID
    sequence: int
    node_type: NodeApprovalType
    timeout_days: int

    class Config:
        from_attributes = True

class ApprovalTaskResponse(BaseModel):
    id: UUID
    document_id: UUID
    node_id: UUID
    approver_id: UUID
    status: ApprovalStatus
    comment: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ApprovalActionRequest(BaseModel):
    comment: Optional[str] = None
