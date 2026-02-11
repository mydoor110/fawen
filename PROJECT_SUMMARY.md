# 公文文件号管理系统 - 项目总结

## 项目概况

**项目名称**: 公文文件号管理系统
**技术栈**: FastAPI + PostgreSQL + SQLAlchemy 2.0
**开发周期**: 2026-02-10
**状态**: ✅ 开发完成

---

## 功能清单

### ✅ 已完成功能

#### 1. 用户认证与权限管理
- [x] JWT Token 认证
- [x] 用户注册/登录
- [x] 基于 RBAC 的权限控制
- [x] 四类角色体系（普通用户、文件号管理员、审批节点人员、系统管理员）
- [x] 角色分配管理

#### 2. 文档管理
- [x] 创建文档草稿
- [x] 编辑文档内容
- [x] 上传 Word 文档
- [x] 查看文档列表
- [x] 查看文档详情

#### 3. 校对流程
- [x] 提交校对（并行多人）
- [x] 校对人分配
- [x] 校对意见记录
- [x] 校对通过/不通过
- [x] 校对完成检查

#### 4. 审批流程
- [x] 提交审批
- [x] 审批流程配置
- [x] 审批节点管理
- [x] 串行审批
- [x] 审批通过/驳回
- [x] 自动流转下一节点

#### 5. 编号管理
- [x] 编号池管理
- [x] 编号分配
- [x] 编号手动调整（带原因）
- [x] 编号回收
- [x] 回收池管理
- [x] 优先复用回收编号

#### 6. 文档锁定
- [x] 自动锁定（提交校对/审批）
- [x] 编号字段锁定
- [x] 内容锁定
- [x] 强制解锁（管理员）

#### 7. 文档销毁
- [x] 销毁申请
- [x] 销毁审批
- [x] 文档移动到销毁目录
- [x] 编号回收

#### 8. 审计日志
- [x] 敏感操作记录
- [x] 操作详情 JSON 存储
- [x] 操作人追踪
- [x] 操作时间记录

#### 9. 系统管理
- [x] 用户列表
- [x] 用户信息更新
- [x] 用户删除
- [x] 角色分配
- [x] 审批角色管理
- [x] 系统配置查看

#### 10. 开发支持
- [x] 数据库迁移（Alembic）
- [x] 初始化数据脚本
- [x] 日志记录（Loguru）
- [x] 异常处理机制
- [x] API 文档（Swagger UI）
- [x] 启动脚本（Linux/Windows）
- [x] 基础测试用例

---

## 技术架构

### 后端框架
```
FastAPI (Python 3.11+)
├── SQLAlchemy 2.0+ (ORM)
├── PostgreSQL 15+ (数据库)
├── Pydantic (数据验证)
├── python-jose (JWT)
├── passlib (密码加密)
├── loguru (日志)
└── python-docx (Word 文档处理)
```

### 目录结构
```
fawen/
├── app/
│   ├── api/              # API 路由层 (8个模块)
│   │   ├── auth.py       # 认证 API
│   │   ├── document.py   # 文档 API
│   │   ├── proofreading.py  # 校对 API
│   │   ├── approval.py   # 审批 API
│   │   ├── number.py     # 编号 API
│   │   ├── admin.py      # 管理员 API
│   │   └── destroy.py    # 销毁 API
│   ├── auth/             # 认证授权
│   ├── core/             # 核心配置
│   ├── models/           # 数据模型 (10个模型)
│   ├── schemas/          # Pydantic 模式 (6个模块)
│   ├── utils/            # 工具函数
│   └── main.py           # 应用入口
├── docs/                 # 文档
├── tests/                # 测试
├── scripts/              # 脚本
├── alembic/              # 数据库迁移
├── storage/              # 文件存储
├── logs/                 # 日志
└── config.yaml           # 配置文件
```

### 数据模型（10张表）
1. `users` - 用户表
2. `roles` - 角色表
3. `user_roles` - 用户角色关联表
4. `approval_roles` - 审批角色表
5. `user_approval_roles` - 用户审批角色关联表
6. `documents` - 文档表
7. `document_locks` - 文档锁表
8. `number_pools` - 编号池表
9. `number_records` - 编号记录表
10. `recycle_pool` - 回收池表
11. `proofreading_tasks` - 校对任务表
12. `approval_flows` - 审批流程表
13. `approval_nodes` - 审批节点表
14. `approval_tasks` - 审批任务表
15. `system_configs` - 系统配置表
16. `audit_logs` - 审计日志表

### 状态机
```
DRAFT (草稿)
  ↓ 提交校对
PROOFREADING (校对中)
  ↓ 全部通过
APPROVAL (审批中)
  ↓ 全部通过
APPROVED (已通过)

任何状态 → REJECTED (已驳回)
任何状态 → DESTROYED (已销毁)
```

---

## API 端点总览

### 认证相关
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/me` - 获取当前用户信息

### 文档相关
- `POST /api/documents` - 创建文档
- `GET /api/documents` - 获取文档列表
- `GET /api/documents/{id}` - 获取文档详情
- `PUT /api/documents/{id}` - 更新文档
- `DELETE /api/documents/{id}` - 删除文档
- `POST /api/documents/{id}/upload` - 上传文档
- `POST /api/documents/{id}/submit-proofreading` - 提交校对
- `POST /api/documents/{id}/submit-approval` - 提交审批

### 校对相关
- `GET /api/proofreading/tasks` - 获取校对任务列表
- `GET /api/proofreading/document/{id}/tasks` - 获取文档校对任务
- `POST /api/proofreading/task/{id}/complete` - 完成校对

### 审批相关
- `GET /api/approval/tasks` - 获取审批任务列表
- `GET /api/approval/document/{id}/tasks` - 获取文档审批任务
- `POST /api/approval/task/{id}/approve` - 审批通过
- `POST /api/approval/task/{id}/reject` - 审批驳回
- `GET /api/approval/flows` - 获取审批流程列表

### 编号管理
- `GET /api/numbers/pools` - 获取编号池列表
- `GET /api/numbers/records` - 获取编号记录
- `POST /api/numbers/records/{id}/adjust` - 调整编号
- `GET /api/numbers/recycle-pool` - 获取回收池
- `POST /api/numbers/allocate` - 分配编号

### 系统管理
- `GET /api/admin/users` - 获取用户列表
- `GET /api/admin/users/{id}` - 获取用户详情
- `PUT /api/admin/users/{id}` - 更新用户
- `DELETE /api/admin/users/{id}` - 删除用户
- `POST /api/admin/users/{id}/roles` - 分配角色
- `GET /api/admin/roles` - 获取角色列表
- `GET /api/admin/approval-roles` - 获取审批角色列表
- `POST /api/admin/approval-roles/{id}` - 分配审批角色

### 文档销毁
- `POST /api/destroy/documents/{id}/request` - 申请销毁
- `POST /api/destroy/documents/{id}/approve` - 审批销毁

---

## 权限矩阵

| 操作 | 普通用户 | 文件号管理员 | 审批节点人员 | 系统管理员 |
|------|---------|-------------|-------------|-----------|
| 创建文档 | ✅ | ✅ | ✅ | ✅ |
| 编辑文档(草稿) | ✅ | ❌ | ❌ | ✅ |
| 上传文档 | ✅ | ❌ | ❌ | ✅ |
| 查看文档 | 自己的 | 所有 | 所有 | 所有 |
| 提交校对 | ✅ | ✅ | ✅ | ✅ |
| 完成校对 | ✅ | ✅ | ✅ | ✅ |
| 提交审批 | ✅ | ❌ | ❌ | ✅ |
| 审批文档 | ❌ | ❌ | ✅ | ✅ |
| 查看编号 | ❌ | ✅ | ❌ | ✅ |
| 调整编号 | ❌ | ⚠️ | ❌ | ✅ |
| 分配编号 | ❌ | ❌ | ❌ | ✅ |
| 查看回收池 | ❌ | ✅ | ❌ | ✅ |
| 申请销毁 | ✅ | ✅ | ❌ | ✅ |
| 审批销毁 | ❌ | ❌ | ✅ | ✅ |
| 用户管理 | ❌ | ❌ | ❌ | ✅ |
| 角色分配 | ❌ | ❌ | ❌ | ✅ |
| 流程配置 | ❌ | ❌ | ❌ | ✅ |
| 强制解锁 | ❌ | ❌ | ❌ | ✅ |

---

## 配置文件

### config.yaml
```yaml
system:          # 系统配置
number:          # 编号配置
proofreading:    # 校对配置
approval:        # 审批配置
document:        # 文档配置
audit:           # 审计配置
security:        # 安全配置
database:        # 数据库配置
server:          # 服务器配置
```

---

## 初始化数据

运行初始化脚本后，系统会自动创建：

### 默认角色
- USER (普通用户)
- NUMBER_ADMIN (文件号管理员)
- APPROVER (审批节点人员)
- SYSTEM_ADMIN (系统管理员)

### 默认审批角色
- 中心负责人 (Level 1)
- 技术岗 (Level 2)
- 主任 (Level 3)

### 默认审批流程
- 标准公文审批流程：中心负责人初审 → 技术岗审核 → 主任终审

### 默认编号池
- 当年编号池：FW-YYYY-0001 ~ FW-YYYY-9999

### 默认管理员账号
- 用户名: `admin`
- 密码: `admin123`
- 角色: `SYSTEM_ADMIN`

---

## 部署方式

### 1. 开发环境
```bash
./start.sh
uvicorn app.main:app --reload
```

### 2. 生产环境
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### 3. Docker 部署
```bash
docker-compose up -d
```

### 4. systemd 服务
```bash
sudo systemctl enable fawen
sudo systemctl start fawen
```

---

## 测试

```bash
# 安装测试依赖
pip install pytest pytest-asyncio

# 运行测试
pytest tests/

# 查看覆盖率
pytest tests/ --cov=app --cov-report=html
```

---

## 文档

- **设计文档**: `docs/DESIGN.md`
- **部署指南**: `docs/DEPLOYMENT.md`
- **API 文档**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 安全特性

1. **密码加密**: 使用 bcrypt 加密存储
2. **JWT 认证**: 无状态 Token 认证
3. **权限校验**: 严格的 RBAC 权限控制
4. **SQL 注入防护**: 使用 ORM 参数化查询
5. **审计日志**: 记录所有敏感操作
6. **CSRF 防护**: 推荐配合前端使用 CSRF Token

---

## 性能优化建议

1. **数据库索引**: 已为关键字段添加索引
2. **连接池**: 已配置 SQLAlchemy 连接池
3. **缓存**: 可添加 Redis 缓存热点数据
4. **分页**: 列表查询支持分页
5. **异步**: 使用 FastAPI 异步特性
6. **静态资源**: 可使用 CDN 加速

---

## 下一步计划

### 短期优化
- [ ] 添加 Redis 缓存
- [ ] 完善单元测试覆盖率
- [ ] 添加前端界面
- [ ] 优化 Word 文档处理

### 中期扩展
- [ ] 消息通知功能
- [ ] 工作流可视化
- [ ] 报表统计
- [ ] 移动端支持

### 长期规划
- [ ] 微服务拆分
- [ ] 多租户支持
- [ ] SaaS 化部署
- [ ] AI 辅助审批

---

## 技术亮点

1. **完整的 RBAC 权限体系**: 严格的权限控制
2. **灵活的工作流**: 支持可配置的审批流程
3. **自动锁定机制**: 保护敏感数据
4. **编号回收机制**: 避免编号浪费
5. **审计追踪**: 完整的操作记录
6. **RESTful API**: 标准的 API 设计
7. **自动化迁移**: Alembic 数据库迁移
8. **完善的日志**: 分级日志记录

---

## 项目统计

- **代码行数**: ~3000+ 行
- **API 端点**: 30+ 个
- **数据表**: 16 张
- **状态枚举**: 6 个
- **配置项**: 8 个大类
- **文档**: 3 份 (README + DESIGN + DEPLOYMENT)
- **测试用例**: 5+ 个

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

---

## 许可证

MIT License

---

## 联系方式

如有问题，请提交 Issue。
