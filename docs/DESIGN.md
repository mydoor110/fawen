公文文件号管理系统 - 设计文档

版本：v1.0
日期：2026-02-10

================================================================================

一、技术架构选型
================================================================================

后端框架：FastAPI (Python 3.11+)
数据库：PostgreSQL 15+
ORM：SQLAlchemy 2.0+
认证：JWT + RBAC
文档处理：python-docx
日志：loguru
测试：pytest + pytest-asyncio

目录结构：
```
fawen/
├── app/
│   ├── api/                 # API 路由
│   ├── core/                # 核心配置
│   ├── models/              # 数据模型
│   ├── schemas/             # Pydantic 模式
│   ├── services/            # 业务逻辑层
│   ├── auth/                # 认证授权
│   ├── utils/               # 工具函数
│   └── main.py              # 应用入口
├── docs/                    # 设计文档
├── tests/                   # 测试
├── alembic/                 # 数据库迁移
├── requirements.txt         # 依赖
└── config.yaml              # 配置文件
```

================================================================================

二、数据模型设计 (ERD)
================================================================================

2.1 用户与角色模型

User (用户表)
├── id: UUID (主键)
├── username: String (唯一)
├── password_hash: String
├── real_name: String
├── department: String
├── is_active: Boolean
├── created_at: DateTime
└── updated_at: DateTime

Role (角色表)
├── id: UUID (主键)
├── name: String (唯一) [普通用户|文件号管理员|审批节点人员|系统管理员]
├── description: String
└── created_at: DateTime

UserRole (用户角色关联表)
├── user_id: UUID (外键 -> User)
├── role_id: UUID (外键 -> Role)
└── assigned_at: DateTime

ApprovalRole (审批角色定义)
├── id: UUID (主键)
├── name: String (主任|技术岗|中心负责人)
├── level: Integer (审批层级)
└── description: String

UserApprovalRole (用户审批角色关联)
├── user_id: UUID (外键 -> User)
├── approval_role_id: UUID (外键 -> ApprovalRole)
└── priority: Integer (同一角色多人的优先级)

2.2 文件与编号模型

Document (文件主表)
├── id: UUID (主键)
├── title: String
├── document_type: String
├── file_path: String (Word文档路径)
├── official_number: String (正式文件号，可为空)
├── draft_number: String (草稿编号)
├── status: Enum (draft|proofreading|approval|approved|rejected|destroyed)
├── creator_id: UUID (外键 -> User)
├── created_at: DateTime
├── updated_at: DateTime
├── submitted_at: DateTime (提交审批时间)
├── approved_at: DateTime (审批通过时间)
├── destroyed_at: DateTime (销毁时间)
└── is_locked: Boolean (文档锁定状态)

DocumentLock (文档锁表)
├── id: UUID (主键)
├── document_id: UUID (外键 -> Document)
├── lock_type: Enum (number|content|all)
├── locked_by: UUID (外键 -> User)
├── locked_at: DateTime
└── reason: String (锁定原因)

NumberPool (编号池)
├── id: UUID (主键)
├── year: Integer
├── category: String
├── prefix: String
├── start_number: Integer
├── current_number: Integer
├── end_number: Integer
└── created_at: DateTime

NumberRecord (编号记录表)
├── id: UUID (主键)
├── document_id: UUID (外键 -> Document)
├── official_number: String
├── status: Enum (reserved|allocated|recycled)
├── allocated_at: DateTime
├── allocated_by: UUID (外键 -> User)
├── recycled_at: DateTime
├── recycled_by: UUID (外键 -> User)
├── recycle_reason: String
└── manual_adjustment: Boolean

2.3 校对与审批模型

ProofreadingTask (校对任务表)
├── id: UUID (主键)
├── document_id: UUID (外键 -> Document)
├── proofreader_id: UUID (外键 -> User)
├── status: Enum (pending|passed|failed|skipped)
├── comment: Text (校对意见)
├── completed_at: DateTime
└── created_at: DateTime

ApprovalFlow (审批流程定义)
├── id: UUID (主键)
├── name: String
├── description: String
├── is_active: Boolean
└── created_at: DateTime

ApprovalNode (审批节点定义)
├── id: UUID (主键)
├── flow_id: UUID (外键 -> ApprovalFlow)
├── approval_role_id: UUID (外键 -> ApprovalRole)
├── sequence: Integer (节点顺序)
├── node_type: Enum (and|or) (AND:所有审批人通过|OR:任一审批人通过)
└── timeout_days: Integer

ApprovalTask (审批任务表)
├── id: UUID (主键)
├── document_id: UUID (外键 -> Document)
├── node_id: UUID (外键 -> ApprovalNode)
├── approver_id: UUID (外键 -> User)
├── status: Enum (pending|approved|rejected|skipped)
├── comment: Text (审批意见)
├── completed_at: DateTime
└── created_at: DateTime

2.4 系统配置与审计模型

SystemConfig (系统配置表)
├── id: UUID (主键)
├── config_key: String (唯一)
├── config_value: JSON
├── description: String
└── updated_by: UUID (外键 -> User)

AuditLog (审计日志表)
├── id: UUID (主键)
├── user_id: UUID (外键 -> User)
├── action: String (操作类型)
├── resource_type: String (资源类型)
├── resource_id: String
├── details: JSON (详细信息)
├── ip_address: String
└── created_at: DateTime

RecyclePool (编号回收池)
├── id: UUID (主键)
├── official_number: String
├── document_id: UUID (原关联文档)
├── reason: String
├── recycled_at: DateTime
└── is_available: Boolean

================================================================================

三、状态机设计 (文件状态流转)
================================================================================

文件状态枚举：
- DRAFT: 草稿
- PROOFREADING: 校对中
- APPROVAL: 审批中
- APPROVED: 已通过
- REJECTED: 已驳回
- DESTROYED: 已销毁

状态转换规则：

┌─────────────────────────────────────────────────────────────────┐
│                      文件状态机                                  │
└─────────────────────────────────────────────────────────────────┘

[初始状态] DRAFT
    │
    ├─→ submit_for_proofreading() ──→ PROOFREADING
    │                                    │
    │                                    ├─→ all_proofreading_passed() ──→ APPROVAL
    │                                    │                                    │
    │                                    └─→ proofreading_failed() ────────┘ DRAFT
    │
    └─→ submit_direct_approval() ──→ APPROVAL (跳过校对，仅允许特定角色)
                                          │
                                          ├─→ approval_rejected() ──────────→ REJECTED
                                          │
                                          └─→ all_nodes_passed() ───────────→ APPROVED

REJECTED
    │
    └─→ resubmit() ──────────────────────→ DRAFT

APPROVED
    │
    ├─→ destroy_with_approval() ────────→ DESTROYED
    │
    └─→ number_allocated() ──────────────→ APPROVED (状态不变，但已生成正式编号)

DESTROYED
    └─→ [终态，不可转换]

锁定状态矩阵：

状态              | Word可改 | 编号可改 | 校对可进行 | 审批可进行
------------------|---------|---------|-----------|-----------
DRAFT             | ✅      | ❌       | ✅        | ✅
PROOFREADING      | ✅      | ❌       | ✅        | ❌
APPROVAL          | ❌      | ❌       | ✅        | ✅
APPROVED          | ❌      | ❌       | ❌        | ❌
REJECTED          | ✅      | ❌       | ✅        | ✅
DESTROYED         | ❌      | ❌       | ❌        | ❌

编号字段特殊锁定规则：
- 进入 PROOFREADING 后，编号字段锁定
- 进入 APPROVAL 后，编号字段锁定（受配置控制是否可改）
- 系统管理员可强制解锁（需记录原因）

================================================================================

四、权限矩阵设计 (RBAC)
================================================================================

角色列表：
1. 普通用户 (USER)
2. 文件号管理员 (NUMBER_ADMIN)
3. 审批节点人员 (APPROVER)
4. 系统管理员 (SYSTEM_ADMIN)

操作列表：

┌─────────────────────────────────────────────────────────────────┐
│                        权限矩阵                                   │
└─────────────────────────────────────────────────────────────────┘

操作类别                  | USER | NUMBER_ADMIN | APPROVER | SYSTEM_ADMIN
--------------------------|------|--------------|----------|-------------
文档操作
  创建草稿               | ✅   | ✅           | ✅       | ✅
  修改草稿内容(未锁定)   | ✅   | ❌           | ❌       | ✅
  上传Word文档           | ✅   | ❌           | ❌       | ✅
  查看自己创建的文件     | ✅   | ❌           | ❌       | ✅
  查看所有文件           | ❌   | ✅           | ✅       | ✅
  删除草稿               | ✅   | ❌           | ❌       | ✅

编号操作
  查看编号状态           | ❌   | ✅           | ❌       | ✅
  手动调整编号           | ❌   | ⚠️          | ❌       | ✅
  查看编号回收池         | ❌   | ✅           | ❌       | ✅
  修正异常编号           | ❌   | ✅           | ❌       | ✅
  强制解锁编号           | ❌   | ❌           | ❌       | ✅
  审批流中修改编号       | ❌   | ⚠️          | ❌       | ✅

校对操作
  提交校对               | ✅   | ✅           | ✅       | ✅
  查看校对任务           | ✅   | ✅           | ✅       | ✅
  提交校对意见           | ✅   | ✅           | ✅       | ✅
  标记校对通过/不通过    | ✅   | ✅           | ✅       | ✅

审批操作
  提交审批               | ✅   | ❌           | ❌       | ✅
  查看审批任务           | ❌   | ❌           | ✅       | ✅
  提交审批意见           | ❌   | ❌           | ✅       | ✅
  通过/驳回              | ❌   | ❌           | ✅       | ✅

销毁操作
  发起销毁               | ✅   | ✅           | ❌       | ✅
  审批销毁               | ❌   | ❌           | ✅       | ✅
  执行销毁               | ❌   | ❌           | ❌       | ✅

系统操作
  用户管理               | ❌   | ❌           | ❌       | ✅
  角色分配               | ❌   | ❌           | ❌       | ✅
  审批流程配置           | ❌   | ❌           | ❌       | ✅
  编号规则配置           | ❌   | ❌           | ❌       | ✅
  强制解锁文档           | ❌   | ❌           | ❌       | ✅
  查看审计日志           | ❌   | ❌           | ❌       | ✅

说明：
- ✅ = 允许
- ❌ = 拒绝
- ⚠️ = 受配置控制

编号编辑策略配置：
number_edit_policy:
  allow_edit_during_approval: false  # 审批中是否允许修改编号
  require_reason: true              # 是否必须填写修改原因
  log_all_changes: true             # 是否记录所有修改

校对通过策略配置：
proofreading_policy:
  mode: all_pass                    # all_pass | majority_pass
  timeout_days: 7                   # 校对超时天数
  can_skip: false                   # 是否允许跳过校对

================================================================================

五、关键业务流程设计
================================================================================

5.1 文件创建与提交流程

流程图：
```
用户登录 → 创建文档草稿 → 上传Word文档 → 填写基本信息
    ↓
选择流程
    ├─→ 提交校对 → 创建校对任务(并行) → 等待所有校对完成
    └─→ 直接审批(需权限) → 创建审批任务(串行) → 等待审批
```

校对并行执行：
```
文档 → 校对任务A(校对人1) ──┐
     → 校对任务B(校对人2) ──┤
     → 校对任务C(校对人3) ──┼─→ 全部通过 → 进入审批流程
     → ...                  └─→ 任一失败 → 返回草稿
```

审批串行执行：
```
文档 → 审批节点1 ──通过──→ 审批节点2 ──通过──→ ... → 最终通过
       │                 │
       └─驳回─────────────┴─────────────────────→ 返回草稿
```

5.2 正式文件号生成流程

触发条件（全部满足）：
1. 文件状态 = APPROVED
2. 所有校对任务 = PASSED
3. 所有审批节点 = APPROVED

生成步骤：
```
检查编号池 → 分配正式序号 → 写入Word文档 → 盖电子章
    ↓
更新编号记录(状态=allocated) → 更新文件记录 → 写入审计日志
```

5.3 编号回收流程

触发条件：
- 文件销毁审批通过
- 手动回收(文件号管理员或系统管理员)

回收步骤：
```
发起销毁申请 → 销毁审批 → 审批通过 → 移动Word到销毁目录
    ↓
更新文件状态=destroyed → 编号状态=recycled → 编号进入回收池
    ↓
记录审计日志(谁在什么时候销毁了什么文件，原因是什么)
```

编号复用策略：
- 优先使用回收池中的编号
- 回收编号标记原文档ID
- 复用时记录关联关系

5.4 锁定机制

自动锁定时机：
- 文件提交校对 → 锁定编号字段
- 文件进入审批 → 锁定内容(Word)、编号(默认)
- 文件已通过 → 全部锁定

解锁规则：
- 草稿状态 → 可解锁(由创建者或系统管理员)
- 已驳回 → 可解锁(由创建者或系统管理员)
- 审批中 → 仅系统管理员可强制解锁(需记录原因)
- 审批中 → 文件号管理员可解锁编号(若配置允许)

锁定类型：
1. number_lock: 仅编号字段锁定
2. content_lock: Word内容锁定
3. all_lock: 全部锁定

================================================================================

六、核心配置项
================================================================================

# 系统配置示例
system:
  name: "公文文件号管理系统"
  version: "1.0.0"
  environment: "production"

# 编号配置
number:
  policies:
    allow_edit_during_approval: false
    require_reason: true
    log_all_changes: true
  pool:
    auto_allocate: true
    recycle_first: true
  format:
    prefix: "FW"
    year_length: 4
    number_length: 4
    separator: "-"

# 校对配置
proofreading:
  mode: "all_pass"  # all_pass | majority_pass
  timeout_days: 7
  can_skip: false
  require_comment: true

# 审批配置
approval:
  allow_skip_proofreading: false
  timeout_days: 30
  notify_on_assign: true
  allow_reassign: false

# 文档配置
document:
  max_size_mb: 50
  allowed_formats: [".docx"]
  storage_path: "/data/documents"
  destroy_path: "/data/destroyed"

# 审计配置
audit:
  log_all_actions: true
  retain_days: 365
  include_ip: true

# 安全配置
security:
  jwt:
    secret_key: "${JWT_SECRET}"
    algorithm: "HS256"
    expire_hours: 24
  password:
    min_length: 8
    require_special_char: true

================================================================================

七、数据库索引设计
================================================================================

-- 索引列表
CREATE INDEX idx_document_status ON documents(status);
CREATE INDEX idx_document_creator ON documents(creator_id);
CREATE INDEX idx_document_created_at ON documents(created_at);
CREATE INDEX idx_number_record_status ON number_records(status);
CREATE INDEX idx_number_record_document ON number_records(document_id);
CREATE INDEX idx_audit_log_user ON audit_logs(user_id);
CREATE INDEX idx_audit_log_action ON audit_logs(action);
CREATE INDEX idx_audit_log_created_at ON audit_logs(created_at);
CREATE INDEX idx_proofreading_task_document ON proofreading_tasks(document_id);
CREATE INDEX idx_proofreading_task_status ON proofreading_tasks(status);
CREATE INDEX idx_approval_task_document ON approval_tasks(document_id);
CREATE INDEX idx_approval_task_approver ON approval_tasks(approver_id);
CREATE INDEX idx_approval_task_status ON approval_tasks(status);

================================================================================

八、API 接口概览
================================================================================

认证相关
POST /api/auth/login          # 用户登录
POST /api/auth/logout         # 用户登出
GET  /api/auth/me             # 获取当前用户信息

文档相关
POST   /api/documents         # 创建草稿
GET    /api/documents         # 获取文档列表
GET    /api/documents/{id}    # 获取文档详情
PUT    /api/documents/{id}    # 更新文档
DELETE /api/documents/{id}    # 删除文档
POST   /api/documents/{id}/upload  # 上传Word文档
POST   /api/documents/{id}/submit-proofreading  # 提交校对
POST   /api/documents/{id}/submit-approval      # 提交审批

校对相关
GET  /api/documents/{id}/proofreading-tasks  # 获取校对任务
POST /api/proofreading/{id}/complete         # 完成校对

审批相关
GET  /api/documents/{id}/approval-tasks    # 获取审批任务
POST /api/approval/{id}/approve            # 审批通过
POST /api/approval/{id}/reject             # 审批驳回

编号管理
GET    /api/number-pool                    # 获取编号池
GET    /api/number-records                 # 获取编号记录
POST   /api/number-records/{id}/adjust     # 手动调整编号
GET    /api/recycle-pool                   # 获取回收池

销毁相关
POST /api/documents/{id}/request-destroy  # 发起销毁申请
POST /api/destroy/{id}/approve             # 审批销毁

系统管理
GET    /api/users                          # 获取用户列表
POST   /api/users                          # 创建用户
PUT    /api/users/{id}                     # 更新用户
DELETE /api/users/{id}                    # 删除用户
POST   /api/users/{id}/roles               # 分配角色
GET    /api/roles                          # 获取角色列表
GET    /api/audit-logs                     # 获取审计日志
POST   /api/config                         # 更新系统配置

================================================================================

九、安全注意事项
================================================================================

1. 所有接口必须通过JWT认证
2. 敏感操作（删除、销毁、调整编号）必须记录审计日志
3. 跨越权限的操作必须在控制器层拒绝
4. 文件上传必须验证大小和格式
5. 数据库操作必须使用参数化查询
6. 密码必须使用 bcrypt 加密存储
7. 配置文件中禁止明文存储敏感信息

================================================================================

十、开发计划
================================================================================

Phase 1: 基础架构 (Week 1)
- 项目初始化
- 数据库模型定义
- 认证授权模块
- 基础API框架

Phase 2: 核心功能 (Week 2-3)
- 文档管理模块
- 编号池管理
- 锁定机制实现

Phase 3: 流程引擎 (Week 3-4)
- 校对流程
- 审批流程
- 状态机实现

Phase 4: 高级功能 (Week 5)
- 编号回收
- 审计日志
- Word文档处理

Phase 5: 测试与部署 (Week 6)
- 单元测试
- 集成测试
- 性能优化
- 部署文档

================================================================================
