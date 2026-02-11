from pydantic import BaseModel, field_validator
from typing import List, Optional, Any
from datetime import datetime
from uuid import UUID

class UserBase(BaseModel):
    username: str
    real_name: str
    department: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    roles: List[str] = []
    approval_roles: List[dict] = []

    @field_validator('roles', mode='before')
    @classmethod
    def extract_role_names(cls, v: Any) -> List[str]:
        """将 Role 对象列表转为角色名字符串列表"""
        if not v:
            return []
        if isinstance(v, list) and len(v) > 0:
            if hasattr(v[0], 'name'):
                return [role.name for role in v]
        return v

    @field_validator('approval_roles', mode='before')
    @classmethod
    def extract_approval_roles(cls, v: Any) -> List[dict]:
        """将 ApprovalRole 对象列表转为 dict"""
        if not v:
            return []
        if isinstance(v, list) and len(v) > 0:
            if hasattr(v[0], 'name'):
                return [{"id": str(r.id), "name": r.name, "level": r.level} for r in v]
        return v

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    username: str
    password: str
