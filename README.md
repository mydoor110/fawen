# 公文文件号管理系统

基于 FastAPI + PostgreSQL 的公文文件号管理系统，实现了完整的角色权限控制、审批流转和编号管理功能。

## 功能特性

### 1. 角色权限体系
- **普通用户 (USER)**: 创建文档、提交审批、查看自己的文档
- **文件号管理员 (NUMBER_ADMIN)**: 管理编号池、调整编号、查看回收池
- **审批节点人员 (APPROVER)**: 审批文档、查看校对任务
- **系统管理员 (SYSTEM_ADMIN)**: 最高权限、用户管理、流程配置

### 2. 核心功能
- 文档管理: 创建、修改、上传 Word 文档
- 校对流程: 并行多人校对、校对意见记录
- 审批流程: 串行审批、节点控制、通过/驳回
- 编号管理: 编号池管理、编号分配、编号回收
- 文档锁定: 内容锁定、编号锁定、强制解锁
- 审计日志: 记录所有敏感操作
- 文档销毁: 销毁审批、编号回收

### 3. 状态机
- DRAFT (草稿) → PROOFREADING (校对中) → APPROVAL (审批中) → APPROVED (已通过)
- 支持驳回回草稿状态
- 支持文档销毁流程

## 快速开始

### 1. 环境准备
- Python 3.11+
- PostgreSQL 15+

### 2. 使用启动脚本

**Linux / macOS:**
```bash
./start.sh
```

**Windows:**
```cmd
start.bat
```

### 3. 手动配置

#### 安装依赖
```bash
pip install -r requirements.txt
```

#### 配置数据库
编辑 `config.yaml` 文件，修改数据库连接信息：
```yaml
database:
  url: "postgresql://user:password@localhost:5432/fawen"
```

#### 初始化数据库
```bash
# 创建数据库
createdb fawen

# 运行迁移
alembic upgrade head

# 初始化数据
python scripts/init_data.py
```

#### 启动服务
```bash
uvicorn app.main:app --reload
```

## API 使用示例

### 1. 用户注册和登录

```bash
# 注册用户
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "test123",
    "real_name": "测试用户",
    "department": "测试部门"
  }'

# 登录获取 token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=test123"
```

### 2. 创建文档

```bash
# 创建草稿
curl -X POST http://localhost:8000/api/documents \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试文档",
    "document_type": "通知"
  }'
```

### 3. 提交校对

```bash
# 提交校对（需要校对人 ID）
curl -X POST http://localhost:8000/api/documents/{document_id}/submit-proofreading \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "proofreader_ids": ["校对人1的ID", "校对人2的ID"]
  }'
```

### 4. 完成校对

```bash
# 校对人完成任务
curl -X POST http://localhost:8000/api/proofreading/task/{task_id}/complete \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "passed",
    "comment": "校对通过"
  }'
```

### 5. 提交审批

```bash
# 提交审批
curl -X POST http://localhost:8000/api/documents/{document_id}/submit-approval \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "flow_id": "审批流程ID"
  }'
```

### 6. 审批文档

```bash
# 审批人通过
curl -X POST http://localhost:8000/api/approval/task/{task_id}/approve \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "comment": "审批通过"
  }'
```

### 7. 分配文件号

```bash
# 文档审批通过后，分配正式文件号
curl -X POST http://localhost:8000/api/numbers/allocate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "文档ID"
  }'
```

### 8. 销毁文档

```bash
# 申请销毁文档
curl -X POST http://localhost:8000/api/destroy/documents/{document_id}/request \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "文档不再需要"
  }'

# 审批销毁（管理员）
curl -X POST http://localhost:8000/api/destroy/documents/{document_id}/approve \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "comment": "同意销毁"
  }'
```

## 默认账号

初始化脚本会创建默认管理员账号：
- **用户名**: admin
- **密码**: admin123
- **角色**: SYSTEM_ADMIN

⚠️ **请尽快修改默认密码！**

## API 文档

启动服务后，访问以下地址查看 API 文档：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构
```
fawen/
├── app/
│   ├── api/          # API 路由
│   ├── core/         # 核心配置
│   ├── models/       # 数据模型
│   ├── schemas/      # Pydantic 模式
│   ├── auth/         # 认证授权
│   └── utils/        # 工具函数
├── docs/             # 设计文档
├── tests/            # 测试
├── scripts/          # 脚本
├── alembic/          # 数据库迁移
├── storage/          # 文件存储
├── logs/             # 日志
├── requirements.txt  # 依赖
└── config.yaml       # 配置文件
```

## 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-asyncio

# 运行测试
pytest tests/
```

## 部署

详细部署指南请查看 `docs/DEPLOYMENT.md` 文件。

## 开发指南

详见 `docs/DESIGN.md` 文件，包含：
- 数据模型设计
- 状态机设计
- 权限矩阵设计
- 业务流程设计
- 安全注意事项

## 常见问题

### 数据库连接失败
检查 `config.yaml` 中的数据库配置是否正确，确保 PostgreSQL 已启动。

### 权限不足
检查用户角色是否正确分配，使用管理员账号在 `/api/admin` 端点管理用户角色。

### 文件上传失败
检查 `storage/` 目录是否有写入权限。
