from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class DestroyRequestRequest(BaseModel):
    reason: str

class DestroyApprovalRequest(BaseModel):
    approved: bool
    comment: Optional[str] = None
