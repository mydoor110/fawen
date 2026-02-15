from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models.document import DocumentStatus, LockType

class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="文档标题")
    document_type: Optional[str] = Field(None, max_length=50, description="文档类型")

class DocumentCreate(DocumentBase):
    """创建文档请求"""
    pass

class DocumentUpdate(BaseModel):
    """更新文档请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    document_type: Optional[str] = Field(None, max_length=50)

# ===== 详细的响应Schema =====

class ProofreadingProgress(BaseModel):
    """校对进度信息"""
    status: str = Field(..., description="校对状态: not_started|in_progress|completed|failed")
    passed: int = Field(..., description="已通过的校对任务数")
    total: int = Field(..., description="总校对任务数")
    details: List[Dict[str, Any]] = Field(default_factory=list, description="校对详情列表")

class ApprovalNodeProgress(BaseModel):
    """审批节点进度"""
    sequence: int = Field(..., description="节点序号")
    name: str = Field(..., description="节点名称")
    status: str = Field(..., description="节点状态: pending|in_progress|completed|rejected")
    approvers: List[Dict[str, Any]] = Field(default_factory=list, description="审批人列表")

class ApprovalProgress(BaseModel):
    """审批进度信息"""
    status: str = Field(..., description="审批状态: not_started|in_progress|completed|rejected")
    current_node: int = Field(..., description="当前节点序号")
    total_nodes: int = Field(..., description="总节点数")
    nodes: List[ApprovalNodeProgress] = Field(default_factory=list, description="节点详情")

class DocumentProgress(BaseModel):
    """文档整体进度"""
    proofreading: Optional[ProofreadingProgress] = None
    approval: Optional[ApprovalProgress] = None

class DocumentDetailResponse(DocumentBase):
    """文档详情响应(包含进度和操作权限)"""
    id: UUID
    draft_number: Optional[str] = None
    official_number: Optional[str] = None
    status: DocumentStatus
    status_display: str = Field(..., description="状态显示名称")
    status_color: str = Field(..., description="状态颜色(HEX)")
    creator_id: UUID
    creator_name: Optional[str] = None
    file_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    destroyed_at: Optional[datetime] = None
    is_locked: bool
    
    # 进度信息
    progress: Optional[DocumentProgress] = None
    
    # 可用操作
    available_actions: List[str] = Field(
        default_factory=list,
        description="当前用户可执行的操作: [edit, delete, upload, submit_proofreading, submit_approval, download]"
    )
    disabled_actions: Dict[str, str] = Field(
        default_factory=dict,
        description="禁用操作及原因, {action: reason}"
    )

    class Config:
        from_attributes = True

class DocumentResponse(DocumentBase):
    """文档基本响应"""
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

# ===== 请求Schema =====

class DocumentSubmitProofreadingRequest(BaseModel):
    """提交校对请求"""
    proofreader_ids: List[UUID] = Field(
        ...,
        min_items=1,
        description="校对人ID列表"
    )
    deadline: Optional[datetime] = Field(
        None,
        description="校对截止时间(可选)"
    )
    note: Optional[str] = Field(
        None,
        max_length=500,
        description="备注说明"
    )

class DocumentSubmitApprovalRequest(BaseModel):
    """提交审批请求"""
    flow_id: UUID = Field(..., description="审批流程ID")
    skip_proofreading: bool = Field(
        False,
        description="是否跳过校对(需要权限)"
    )

# ===== 响应Schema =====

class DocumentSubmitProofreadingResponse(BaseModel):
    """提交校对响应"""
    task_ids: List[UUID] = Field(..., description="创建的校对任务ID列表")
    status: str = Field(..., description="文档新状态")
    created_at: datetime = Field(..., description="提交时间")

class DocumentSubmitApprovalResponse(BaseModel):
    """提交审批响应"""
    task_ids: List[UUID] = Field(..., description="创建的审批任务ID列表")
    status: str = Field(..., description="文档新状态")
    flow_name: str = Field(..., description="审批流程名称")
    created_at: datetime = Field(..., description="提交时间")

# ===== 错误响应Schema =====

class ErrorResponse(BaseModel):
    """统一错误响应"""
    error: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误详细信息")
    details: Optional[Dict[str, Any]] = Field(None, description="额外详情")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "error": "INVALID_STATUS",
                    "message": "当前文档状态为 'approval',无法提交校对",
                    "details": {"current_status": "approval"}
                },
                {
                    "error": "PERMISSION_DENIED",
                    "message": "您没有权限执行此操作",
                    "details": {"required_role": "SYSTEM_ADMIN"}
                }
            ]
        }

