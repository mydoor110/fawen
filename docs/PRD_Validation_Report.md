# PRD 验证报告 - 公文文件号管理系统设计文档

**验证时间**: 2026-02-15  
**文档版本**: v1.0  
**验证人**: AI Solutions Architect

---

## 1. 执行摘要

**整体评级**: ⚠️ **需要改进** (Needs Improvement)

**核心发现**:
- ✅ **优势**: 数据模型设计完整,状态机设计清晰,权限矩阵详尽
- ⚠️ **中等问题**: 缺少部分异常处理细节,UI/UX描述不足,API规范不够具体
- ❌ **严重问题**: 缺少分布式场景下的并发控制,编号分配存在竞态条件风险,审批流程缺少超时处理细节

**可实施性**: 70/100
- AI可读性: 75/100
- 业务逻辑完整性: 65/100
- 边缘情况覆盖: 55/100

---

## 2. 关键问题汇总 (Critical Issues)

| ID | 类别 | 严重程度 | 问题描述 | 建议修复 |
|----|------|---------|---------|---------|
| C-01 | 数据一致性 | 🔴 高 | 编号分配存在并发竞态条件,多用户同时分配可能导致编号重复 | 实现数据库行级锁或使用序列生成器,添加唯一约束 |
| C-02 | 业务逻辑 | 🔴 高 | 审批节点超时后的自动处理逻辑未定义 | 明确超时策略:自动通过/自动驳回/转交/升级 |
| C-03 | 状态机 | 🟡 中 | 并行校对中部分通过后,其他校对人无法撤销已提交的意见 | 添加"校对中止"状态和撤销机制 |
| C-04 | 权限控制 | 🟡 中 | 文件号管理员在审批流程中修改编号的权限边界不清晰 | 明确哪些审批阶段允许修改,需要哪些角色审批修改 |
| C-05 | API设计 | 🟡 中 | 缺少请求/响应的详细Schema定义,AI难以生成准确代码 | 为每个API端点补充完整的Request/Response Schema |
| C-06 | 数据完整性 | 🟡 中 | 文档销毁后编号回收,但缺少原文档追溯机制的详细设计 | 添加销毁文档归档表,保留元数据用于审计 |
| C-07 | 安全性 | 🟡 中 | 强制解锁操作缺少二次验证机制 | 要求强制解锁需要另一位管理员确认或OTP验证 |
| C-08 | 边缘情况 | 🟢 低 | 年度切换时编号池的处理逻辑未定义 | 明确跨年编号策略:自动创建新池/手动配置/归档旧池 |
| C-09 | 用户体验 | 🟢 低 | 并行校对时,用户无法看到其他校对人的实时进度 | 添加校对进度仪表板API |
| C-10 | 可维护性 | 🟢 低 | 配置项说明不够详细,缺少默认值和取值范围 | 为每个配置项添加注释、默认值、valid范围 |

---

## 3. 详细分析

### 3.1 AI可读性与OpenSpec对齐 (评分: 75/100)

#### ✅ 做得好的地方:
1. **数据模型明确**: 每个表都有清晰的字段定义和类型
2. **状态枚举清晰**: 文档状态、任务状态都有明确的枚举值
3. **关系定义完整**: 外键关系、关联表都有说明

#### ❌ 存在的问题:

**问题1: API端点缺少详细Schema**

**当前状态**:
```
POST /api/documents/{id}/submit-proofreading  # 提交校对
```

**问题分析**:
- 缺少请求体结构定义
- 缺少响应格式说明
- AI无法确定需要传递哪些参数
- 校对人列表是ID数组还是对象数组?
- 是否需要指定校对截止时间?

**建议改进**:
```yaml
POST /api/documents/{id}/submit-proofreading
  Request:
    body:
      proofreader_ids: array[UUID]  # 校对人ID列表
      deadline: DateTime (optional)  # 校对截止时间
      note: string (optional)        # 备注说明
  Response:
    200 OK:
      task_ids: array[UUID]         # 创建的校对任务ID列表
      status: string                # 文档新状态: "proofreading"
      created_at: DateTime
    400 Bad Request:
      error: "INVALID_STATUS"        # 文档状态不允许提交校对
      message: "当前文档状态为 'approval',无法提交校对"
    403 Forbidden:
      error: "PERMISSION_DENIED"
```

**问题2: 枚举值未标准化**

**当前状态**:
```
status: Enum (draft|proofreading|approval|approved|rejected|destroyed)
```

**问题分析**:
- 使用小写+下划线还是大写?
- 前端和后端如何统一?
- 应该定义为常量还是字符串?

**建议改进**:
```python
# 明确定义枚举类型和值的映射
class DocumentStatus(str, Enum):
    DRAFT = "draft"
    PROOFREADING = "proofreading"
    APPROVAL = "approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    DESTROYED = "destroyed"
    
# 状态显示名称映射(用于UI)
STATUS_DISPLAY_NAMES = {
    DocumentStatus.DRAFT: "草稿",
    DocumentStatus.PROOFREADING: "校对中",
    # ...
}
```

**问题3: 业务规则未转换为可执行条件**

**当前状态**:
```
触发条件(全部满足):
1. 文件状态 = APPROVED
2. 所有校对任务 = PASSED
3. 所有审批节点 = APPROVED
```

**建议改进**:
```python
# 将业务规则转换为可执行的验证函数
def can_allocate_official_number(document_id: UUID) -> tuple[bool, str]:
    """
    检查文档是否满足分配正式编号的条件
    
    Returns:
        (是否满足, 不满足原因)
    """
    document = get_document(document_id)
    
    # 条件1: 文档状态必须为APPROVED
    if document.status != DocumentStatus.APPROVED:
        return False, f"文档状态为{document.status},需要为APPROVED"
    
    # 条件2: 所有校对任务必须通过
    proofreading_tasks = get_proofreading_tasks(document_id)
    failed_tasks = [t for t in proofreading_tasks if t.status != "passed"]
    if failed_tasks:
        return False, f"存在{len(failed_tasks)}个未通过的校对任务"
    
    # 条件3: 所有审批节点必须通过
    approval_tasks = get_approval_tasks(document_id)
    pending_tasks = [t for t in approval_tasks if t.status != "approved"]
    if pending_tasks:
        return False, f"存在{len(pending_tasks)}个未完成的审批任务"
    
    return True, ""
```

---

### 3.2 行业标准与合理性检查 (评分: 70/100)

#### ✅ 符合标准的设计:

1. **RBAC权限模型**: 业界标准的基于角色的访问控制
2. **审计日志**: 记录敏感操作,符合合规要求
3. **密码加密**: 使用bcrypt,符合安全最佳实践
4. **JWT认证**: 无状态认证,可扩展性好

#### ❌ 需要改进的地方:

**问题1: 密码策略过于简单**

**当前设计**:
```yaml
password:
  min_length: 8
  require_special_char: true
```

**行业标准要求**:
- 最小长度应为12位(NIST SP 800-63B推荐)
- 应限制常见弱密码
- 应实施密码历史策略(不能重用最近N次密码)
- 应实施账户锁定策略(连续失败N次)
- 应要求定期更换密码或检测密码泄露

**建议改进**:
```yaml
password:
  min_length: 12
  require_uppercase: true
  require_lowercase: true
  require_digit: true
  require_special_char: true
  blocked_patterns: ["password", "123456", "qwerty"]  # 弱密码黑名单
  history_count: 5                # 禁止重用最近5次密码
  max_age_days: 90               # 密码有效期90天
  
account_lock:
  max_failed_attempts: 5         # 最大失败次数
  lockout_duration_minutes: 30   # 锁定时长
  reset_after_minutes: 15        # 失败计数重置时间
```

**问题2: 文档销毁缺少安全网**

**当前流程**:
```
发起销毁申请 → 销毁审批 → 审批通过 → 移动Word到销毁目录
```

**行业最佳实践**:
- 应有"软删除"过渡期(如30天)
- 应要求二次确认(输入文档标题或特定关键词)
- 应发送邮件通知相关人员
- 应保留销毁文档的元数据供审计

**建议改进**:
```
发起销毁申请
  ↓
销毁审批通过
  ↓
标记为"待销毁"状态 + 设置销毁日期(30天后)
  ↓
发送通知给创建人、审批人
  ↓
[30天内可撤销销毁]
  ↓
到期后自动执行销毁
  ↓
移动文件到销毁目录 + 创建DestroyedDocumentMetadata记录
  ↓
记录完整的销毁审计链
```

**问题3: JWT过期时间过长**

**当前配置**:
```yaml
jwt:
  expire_hours: 24
```

**安全风险**:
- 24小时过期时间过长,token被盗风险高
- 缺少刷新token机制
- 缺少token撤销机制

**建议改进**:
```yaml
jwt:
  access_token_expire_minutes: 15   # 访问token 15分钟
  refresh_token_expire_days: 7      # 刷新token 7天
  refresh_rotation: true            # 刷新时轮换token
  
# 添加Token黑名单机制用于主动撤销
redis:
  token_blacklist_ttl: 86400  # 黑名单TTL
```

---

### 3.3 逻辑完整性检查 (评分: 65/100)

#### ❌ 发现的逻辑断点:

**问题1: 编号分配存在竞态条件**

**当前设计**:
```
检查编号池 → 分配正式序号 → 写入Word文档
```

**逻辑缺陷**:
- 两个文档同时进入APPROVED状态
- 两个请求同时读取`current_number = 5`
- 两个请求都分配了编号`6`
- 导致编号重复

**数据流分析**:
```
Time | Thread A              | Thread B              | DB current_number
-----|----------------------|----------------------|------------------
T1   | Read current=5       |                      | 5
T2   |                      | Read current=5       | 5
T3   | Allocate num=6       |                      | 5
T4   |                      | Allocate num=6       | 5
T5   | Update current=6     |                      | 6
T6   |                      | Update current=6     | 6  ❌ 重复!
```

**建议修复**:
```python
# 方案1: 使用数据库行级锁
@transaction.atomic
def allocate_number(document_id: UUID) -> str:
    # SELECT FOR UPDATE 锁定行
    pool = NumberPool.objects.select_for_update().get(
        year=current_year,
        category=document.category
    )
    
    # 原子性递增
    pool.current_number += 1
    allocated_number = f"{pool.prefix}-{pool.year}-{pool.current_number:04d}"
    pool.save()
    
    # 创建编号记录
    NumberRecord.objects.create(
        document_id=document_id,
        official_number=allocated_number,
        status="allocated"
    )
    
    return allocated_number

# 方案2: 使用PostgreSQL序列
CREATE SEQUENCE number_seq_2026 START 1;

def allocate_number(document_id: UUID) -> str:
    next_num = execute_sql("SELECT nextval('number_seq_2026')")
    # 序列保证唯一性
```

**问题2: 审批超时后的状态不明确**

**当前设计**:
```
timeout_days: 30  # 审批超时天数
```

**逻辑断点**:
- 超时后文档处于什么状态?
- 超时后是否自动流转到下一节点?
- 超时后是否可以补救?
- 谁会收到通知?

**建议补充**:
```yaml
approval:
  timeout_days: 30
  timeout_strategy: "escalate"  # auto_approve | auto_reject | escalate | notify_only
  
  # 超时升级策略
  escalation:
    enabled: true
    escalate_to_role: "SYSTEM_ADMIN"  # 升级到系统管理员
    escalate_after_days: 35           # 超时5天后升级
    
  # 超时通知策略
  notification:
    remind_before_days: [7, 3, 1]     # 提前7天、3天、1天提醒
    notify_supervisor: true            # 通知审批人的上级
    send_method: ["email", "sms"]     # 通知方式
```

**完整超时处理流程**:
```
审批任务创建 → 设置截止时间(T+30天)
    ↓
T+23天: 发送第一次提醒
T+27天: 发送第二次提醒
T+29天: 发送最后提醒
    ↓
T+30天: 超时触发
    ↓
根据策略执行:
  - auto_approve: 自动通过,流转到下一节点
  - auto_reject: 自动驳回,返回草稿
  - escalate: 转交给上级/系统管理员
  - notify_only: 仅发送通知,等待人工处理
    ↓
记录审计日志(超时原因、处理方式)
```

**问题3: 并行校对的中止逻辑缺失**

**当前设计**:
```
校对任务A(校对人1) ──┐
校对任务B(校对人2) ──┤
校对任务C(校对人3) ──┼─→ 全部通过 → 进入审批流程
                     └─→ 任一失败 → 返回草稿
```

**逻辑问题**:
- 如果任务A已经PASSED,任务B标记为FAILED
- 任务C的校对人还在进行校对
- 文档已经返回草稿,任务C的工作白费了

**建议补充**:
```python
# 校对失败时的级联处理
def on_proofreading_failed(task_id: UUID):
    task = get_proofreading_task(task_id)
    document = task.document
    
    # 标记文档状态为DRAFT
    document.status = DocumentStatus.DRAFT
    document.save()
    
    # 取消所有其他待处理的校对任务
    other_tasks = ProofreadingTask.objects.filter(
        document=document,
        status="pending"
    ).exclude(id=task_id)
    
    for other_task in other_tasks:
        other_task.status = "cancelled"
        other_task.comment = f"因任务{task.id}失败而自动取消"
        other_task.save()
        
        # 通知被取消任务的校对人
        notify_user(
            other_task.proofreader_id,
            f"文档《{document.title}》的校对任务已取消"
        )
```

**问题4: 编号回收后的追溯链断裂**

**当前设计**:
```python
RecyclePool (编号回收池)
├── official_number: String
├── document_id: UUID (原关联文档)
└── is_available: Boolean
```

**逻辑缺陷**:
- 编号被回收后重新分配给新文档
- 如何追溯这个编号曾经关联过哪些文档?
- 审计时如何查看完整的编号使用历史?

**建议改进**:
```python
# 添加编号使用历史表
class NumberUsageHistory(Base):
    id = Column(UUID, primary_key=True)
    official_number = Column(String)
    document_id = Column(UUID, ForeignKey('documents.id'))
    allocated_at = Column(DateTime)
    recycled_at = Column(DateTime, nullable=True)
    usage_order = Column(Integer)  # 这是该编号的第几次使用
    
# 查询编号完整历史
def get_number_history(official_number: str) -> List[dict]:
    """
    返回编号的完整使用历史
    
    Example:
    [
        {
            "usage_order": 1,
            "document_id": "uuid-1",
            "document_title": "2024年工作报告",
            "allocated_at": "2024-01-15",
            "recycled_at": "2024-12-01",
            "reason": "文档销毁"
        },
        {
            "usage_order": 2,
            "document_id": "uuid-2",
            "document_title": "2025年工作计划",
            "allocated_at": "2025-01-10",
            "recycled_at": null,
            "reason": null
        }
    ]
    """
```

---

### 3.4 边缘情况与异常处理 (评分: 55/100)

#### ❌ 未覆盖的边缘场景:

**场景1: 跨年度编号处理**

**问题**:
- 12月31日 23:59创建的文档,1月1日 00:01审批通过
- 应该分配2024年编号还是2025年编号?
- 编号池何时切换?

**建议方案**:
```yaml
number:
  year_policy: "submission"  # submission | approval | creation
  # submission: 以提交审批时间为准
  # approval: 以审批通过时间为准
  # creation: 以创建时间为准
  
  year_transition:
    auto_create_next_year_pool: true
    advance_days: 30  # 提前30天创建下一年编号池
    previous_year_grace_days: 60  # 允许延迟分配上一年编号的宽限期
```

**场景2: 文档上传失败处理**

**问题**:
- 用户上传50MB的Word文档
- 上传到一半网络中断
- 数据库中已创建了Document记录
- 服务器上有半个文件

**建议处理**:
```python
@transaction.atomic
def upload_document(document_id: UUID, file: UploadFile):
    # 1. 验证文件
    if file.size > MAX_FILE_SIZE:
        raise ValueError(f"文件大小超过限制({MAX_FILE_SIZE}MB)")
    
    if not file.filename.endswith('.docx'):
        raise ValueError("仅支持.docx格式")
    
    # 2. 生成临时文件路径
    temp_path = f"/tmp/upload_{uuid4()}.docx"
    final_path = f"/data/documents/{document_id}.docx"
    
    try:
        # 3. 先写入临时文件
        with open(temp_path, 'wb') as f:
            while chunk := file.read(8192):
                f.write(chunk)
        
        # 4. 验证文件完整性
        if not is_valid_docx(temp_path):
            raise ValueError("文件损坏或格式不正确")
        
        # 5. 移动到最终位置(原子操作)
        os.rename(temp_path, final_path)
        
        # 6. 更新数据库
        document = get_document(document_id)
        document.file_path = final_path
        document.save()
        
    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
    
    return document
```

**场景3: 审批人离职/删除**

**问题**:
- 某文档正在审批节点2,审批人是张三
- 张三离职,账号被禁用
- 文档审批流程卡死

**建议方案**:
```python
# 添加审批任务转移机制
class ApprovalTask(Base):
    # ... existing fields
    original_approver_id = Column(UUID, nullable=True)  # 原审批人
    reassigned_at = Column(DateTime, nullable=True)     # 转移时间
    reassign_reason = Column(String, nullable=True)     # 转移原因

def handle_user_deactivation(user_id: UUID):
    """
    处理用户禁用时的任务转移
    """
    # 查找该用户所有待处理的审批任务
    pending_tasks = ApprovalTask.objects.filter(
        approver_id=user_id,
        status="pending"
    )
    
    for task in pending_tasks:
        # 查找同一审批角色的其他审批人
        approval_role = task.node.approval_role
        alternative_approvers = get_users_with_approval_role(
            approval_role.id
        ).exclude(id=user_id).filter(is_active=True)
        
        if not alternative_approvers:
            # 无可用审批人,升级给系统管理员
            admins = get_system_admins()
            task.approver_id = admins[0].id
            task.reassign_reason = "原审批人离职且无替代人员"
        else:
            # 转移给优先级最高的审批人
            task.approver_id = alternative_approvers[0].id
            task.reassign_reason = "原审批人账号已禁用"
        
        task.original_approver_id = user_id
        task.reassigned_at = datetime.now()
        task.save()
        
        # 发送通知
        notify_user(task.approver_id, f"审批任务已转移给您...")
```

**场景4: 编号池耗尽**

**问题**:
```python
NumberPool:
    start_number: 1
    current_number: 9999
    end_number: 10000
```
- 已经分配到9999
- 新文档审批通过,需要分配10000号
- 编号池已耗尽

**建议处理**:
```python
def allocate_number(document_id: UUID) -> str:
    pool = NumberPool.objects.select_for_update().get(...)
    
    # 检查是否即将耗尽(预警)
    if pool.current_number >= pool.end_number * 0.9:
        notify_admins(f"编号池即将耗尽: {pool.current_number}/{pool.end_number}")
    
    # 检查是否已耗尽
    if pool.current_number >= pool.end_number:
        # 策略1: 自动扩容
        pool.end_number += 10000
        log_audit("编号池自动扩容", {"old_end": pool.end_number - 10000})
        
        # 策略2: 使用备用编号格式
        # FW-2026-0001 → FW-2026-A0001
        pool.prefix = f"{pool.prefix}-A"
        pool.current_number = 0
        
    pool.current_number += 1
    # ...
```

**场景5: 并发提交审批**

**问题**:
- 用户A在前端点击"提交审批"
- 网络延迟,用户A以为没反应,又点了一次
- 两个请求同时到达后端
- 创建了两份审批流程

**建议处理**:
```python
# 添加幂等性检查
class Document(Base):
    # ... existing fields
    submission_token = Column(String, nullable=True)  # 提交令牌

def submit_for_approval(document_id: UUID, token: str) -> dict:
    """
    幂等性提交审批
    
    Args:
        token: 前端生成的唯一令牌(UUID)
    """
    document = get_document(document_id)
    
    # 如果已经提交过,且token相同,直接返回成功
    if document.status == DocumentStatus.APPROVAL:
        if document.submission_token == token:
            return {"status": "already_submitted", "tasks": get_approval_tasks(document_id)}
        else:
            raise ValueError("文档已在审批中")
    
    # 首次提交,保存token
    document.submission_token = token
    document.status = DocumentStatus.APPROVAL
    document.save()
    
    # 创建审批任务...
```

---

### 3.5 UI/UX一致性检查 (评分: 40/100)

#### ❌ 主要问题:

**问题1: 设计文档完全缺少UI/UX描述**

**当前状态**:
- 仅有API端点定义
- 没有页面布局设计
- 没有交互流程图
- 没有前端状态管理说明

**影响**:
- AI无法生成前端代码
- 开发人员不知道界面应该长什么样
- 前后端接口可能不匹配

**建议补充**:

```markdown
## UI/UX 设计规范

### 页面结构

#### 1. 文档列表页

**布局**:
```
+----------------------------------------------------------+
| Header: Logo | 用户: 张三 | 角色: 普通用户 | [登出]      |
+----------------------------------------------------------+
| Sidebar                 | Main Content                    |
| +-----------------+     | +-----------------------------+ |
| | 我的文档        |     | | 筛选: [状态▼] [类型▼] [搜索]| |
| | 待我校对 (3)    |     | +-----------------------------+ |
| | 待我审批 (1)    |     | | 表格:                        | |
| | 编号管理        |     | | □ | 文件号 | 标题 | 状态 |...  | |
| | 系统设置        |     | | ☑ | FW-001 | 报告 | 草稿 |...  | |
| +-----------------+     | +-----------------------------+ |
|                         | | 批量操作: [提交校对] [删除]  | |
+----------------------------------------------------------+
```

**交互流程**:
1. 用户点击"创建文档"按钮
2. 弹出模态框,包含表单:
   - 文档标题 (必填,文本输入)
   - 文档类型 (必填,下拉选择)
   - 上传Word (必填,文件上传组件)
3. 表单验证:
   - 标题不能为空且不超过200字符
   - 文件大小不超过50MB
   - 文件格式必须为.docx
4. 提交后显示加载动画
5. 成功后:
   - 显示Toast提示"创建成功"
   - 跳转到文档详情页

#### 2. 文档详情页

**功能区块**:
```
+----------------------------------------------------------+
| 面包屑: 我的文档 > 2026年工作报告                         |
+----------------------------------------------------------+
| 左侧 (70%)                | 右侧 (30%)                    |
| +----------------------+  | +-----------------------+     |
| | 文档信息             |  | | 操作按钮              |     |
| | 标题: XXX            |  | | [下载Word]            |     |
| | 编号: FW-2026-0001   |  | | [编辑]                |     |
| | 状态: 🟡 审批中      |  | | [提交校对]            |     |
| | 创建人: 张三         |  | | [提交审批]            |     |
| | 创建时间: ...        |  | +-----------------------+     |
| +----------------------+  | | 审批进度              |     |
| | Word预览             |  | | ✅ 校对: 已完成        |     |
| | [嵌入式Word查看器]    |  | | 🔄 审批节点1: 进行中   |     |
| +----------------------+  | |   - 张三: 待审批       |     |
|                           | | ⏸️ 审批节点2: 未开始   |     |
|                           | +-----------------------+     |
+----------------------------------------------------------+
```

**状态颜色规范**:
- 🟢 草稿 (draft): #10B981
- 🟡 校对中 (proofreading): #F59E0B  
- 🔵 审批中 (approval): #3B82F6
- ✅ 已通过 (approved): #22C55E
- ❌ 已驳回 (rejected): #EF4444
- ⚫ 已销毁 (destroyed): #6B7280
```

**问题2: API响应格式与前端需求不匹配**

**当前API设计**:
```python
GET /api/documents/{id}
Response:
{
    "id": "uuid",
    "title": "string",
    "status": "approval",
    ...
}
```

**前端实际需求**:
```javascript
// 前端需要显示审批进度条
// 需要知道:
// - 总共几个审批节点?
// - 当前在第几个节点?
// - 每个节点的审批人是谁?
// - 每个节点的状态是什么?
```

**建议改进API**:
```python
GET /api/documents/{id}
Response:
{
    "id": "uuid",
    "title": "2026年工作报告",
    "status": "approval",
    "status_display": "审批中",
    "status_color": "#3B82F6",
    
    # 前端直接可用的进度信息
    "progress": {
        "proofreading": {
            "status": "completed",
            "passed": 3,
            "total": 3,
            "details": [
                {"proofreader": "李四", "status": "passed", "comment": "无问题"},
                {"proofreader": "王五", "status": "passed", "comment": "格式需调整"}
            ]
        },
        "approval": {
            "status": "in_progress",
            "current_node": 1,
            "total_nodes": 3,
            "nodes": [
                {
                    "sequence": 1,
                    "name": "主任审批",
                    "status": "in_progress",
                    "approvers": [
                        {"name": "张三", "status": "pending", "deadline": "2026-03-01"}
                    ]
                },
                {
                    "sequence": 2,
                    "name": "中心负责人审批",
                    "status": "pending",
                    "approvers": [...]
                }
            ]
        }
    },
    
    # 前端按钮可见性控制
    "available_actions": ["download", "view_history"],
    "disabled_actions": {
        "edit": "文档审批中,无法编辑",
        "delete": "文档审批中,无法删除"
    }
}
```

---

## 4. 优化规范提案

基于以上分析,针对最关键的**编号分配并发问题**,提供优化后的规范:

### 4.1 编号分配模块优化

#### 数据模型优化

```python
# 原模型
class NumberPool(Base):
    id = Column(UUID, primary_key=True)
    year = Column(Integer)
    category = Column(String)
    prefix = Column(String)
    start_number = Column(Integer)
    current_number = Column(Integer)  # ❌ 并发不安全
    end_number = Column(Integer)
    created_at = Column(DateTime)

# 优化后模型
class NumberPool(Base):
    id = Column(UUID, primary_key=True)
    year = Column(Integer)
    category = Column(String)
    prefix = Column(String)
    start_number = Column(Integer)
    end_number = Column(Integer)
    sequence_name = Column(String)  # ✅ PostgreSQL序列名
    created_at = Column(DateTime)
    
    # 添加唯一约束
    __table_args__ = (
        UniqueConstraint('year', 'category', name='uq_year_category'),
    )

class NumberRecord(Base):
    id = Column(UUID, primary_key=True)
    document_id = Column(UUID, ForeignKey('documents.id'))
    pool_id = Column(UUID, ForeignKey('number_pools.id'))
    official_number = Column(String, unique=True)  # ✅ 唯一约束
    sequence_value = Column(Integer)  # 从序列获取的值
    status = Column(Enum("reserved", "allocated", "recycled"))
    allocated_at = Column(DateTime)
    allocated_by = Column(UUID, ForeignKey('users.id'))
    recycled_at = Column(DateTime, nullable=True)
    recycled_by = Column(UUID, ForeignKey('users.id'), nullable=True)
    recycle_reason = Column(String, nullable=True)
```

#### 分配逻辑优化

```python
# app/services/number_service.py

from sqlalchemy import text
from app.core.database import get_db

class NumberService:
    
    @staticmethod
    async def allocate_official_number(document_id: UUID, user_id: UUID) -> str:
        """
        线程安全的编号分配
        
        使用PostgreSQL序列保证并发安全
        """
        async with get_db() as db:
            async with db.begin():  # 事务
                # 1. 获取文档信息
                document = await db.execute(
                    select(Document).where(Document.id == document_id).with_for_update()
                )
                document = document.scalar_one()
                
                # 2. 验证文档状态
                if document.status != DocumentStatus.APPROVED:
                    raise ValueError(f"文档状态为{document.status},不能分配编号")
                
                if document.official_number:
                    raise ValueError("文档已有正式编号")
                
                # 3. 获取编号池
                pool = await db.execute(
                    select(NumberPool).where(
                        NumberPool.year == document.created_at.year,
                        NumberPool.category == document.document_type
                    )
                )
                pool = pool.scalar_one()
                
                # 4. 检查回收池(优先使用回收编号)
                recycled = await db.execute(
                    select(NumberRecord).where(
                        NumberRecord.pool_id == pool.id,
                        NumberRecord.status == "recycled"
                    ).order_by(NumberRecord.sequence_value).limit(1)
                )
                recycled = recycled.scalar_one_or_none()
                
                if recycled:
                    # 使用回收的编号
                    official_number = recycled.official_number
                    recycled.status = "allocated"
                    recycled.document_id = document_id
                    recycled.allocated_at = datetime.now()
                    recycled.allocated_by = user_id
                else:
                    # 从序列获取新编号
                    result = await db.execute(
                        text(f"SELECT nextval('{pool.sequence_name}')")
                    )
                    sequence_value = result.scalar()
                    
                    # 检查是否超出范围
                    if sequence_value > pool.end_number:
                        raise ValueError(f"编号池已耗尽: {sequence_value} > {pool.end_number}")
                    
                    # 格式化编号
                    official_number = f"{pool.prefix}-{pool.year}-{sequence_value:04d}"
                    
                    # 创建编号记录
                    record = NumberRecord(
                        id=uuid4(),
                        document_id=document_id,
                        pool_id=pool.id,
                        official_number=official_number,
                        sequence_value=sequence_value,
                        status="allocated",
                        allocated_at=datetime.now(),
                        allocated_by=user_id
                    )
                    db.add(record)
                
                # 5. 更新文档
                document.official_number = official_number
                
                # 6. 写入审计日志
                await AuditService.log(
                    user_id=user_id,
                    action="allocate_number",
                    resource_type="document",
                    resource_id=str(document_id),
                    details={
                        "official_number": official_number,
                        "from_recycle": recycled is not None
                    }
                )
                
                await db.commit()
                
                return official_number
```

#### 数据库迁移脚本

```python
# alembic/versions/xxx_add_number_sequence.py

from alembic import op
import sqlalchemy as sa

def upgrade():
    # 为每个编号池创建序列
    connection = op.get_bind()
    
    # 获取现有编号池
    pools = connection.execute(
        sa.text("SELECT id, year, category, current_number FROM number_pools")
    ).fetchall()
    
    for pool in pools:
        pool_id, year, category, current = pool
        seq_name = f"number_seq_{category}_{year}"
        
        # 创建序列,从current_number开始
        connection.execute(
            sa.text(f"CREATE SEQUENCE {seq_name} START {current + 1}")
        )
        
        # 更新编号池,添加序列名
        connection.execute(
            sa.text("UPDATE number_pools SET sequence_name = :seq WHERE id = :id"),
            {"seq": seq_name, "id": pool_id}
        )
    
    # 添加唯一约束
    op.create_unique_constraint(
        'uq_number_record_official_number',
        'number_records',
        ['official_number']
    )

def downgrade():
    # 删除序列
    connection = op.get_bind()
    pools = connection.execute(
        sa.text("SELECT sequence_name FROM number_pools WHERE sequence_name IS NOT NULL")
    ).fetchall()
    
    for (seq_name,) in pools:
        connection.execute(sa.text(f"DROP SEQUENCE IF EXISTS {seq_name}"))
    
    op.drop_constraint('uq_number_record_official_number', 'number_records')
```

---

## 5. 修复优先级建议

### 🔴 高优先级 (必须修复,影响系统稳定性)

1. **C-01**: 编号分配并发控制 - 使用数据库序列或行锁
2. **C-02**: 审批超时处理逻辑 - 定义明确的超时策略
3. **C-05**: API Schema定义 - 补充详细的请求/响应格式

### 🟡 中优先级 (建议修复,影响用户体验)

4. **C-03**: 校对中止机制 - 添加任务取消逻辑
5. **C-04**: 编号修改权限 - 明确权限边界和审批流程
6. **C-06**: 销毁文档追溯 - 添加历史记录表
7. **C-07**: 强制解锁二次验证 - 增强安全性

### 🟢 低优先级 (优化项,可延后)

8. **C-08**: 跨年编号策略 - 定义配置项
9. **C-09**: 校对进度可视化 - 改进用户体验
10. **C-10**: 配置项文档化 - 提升可维护性

---

## 6. 总结与行动建议

### 核心问题

这份设计文档在**数据建模**和**权限设计**方面做得很好,但在**并发控制**、**异常处理**和**UI/UX规范**方面存在明显不足。

### 关键风险

1. **数据一致性风险**: 编号分配的并发问题可能导致生产事故
2. **业务连续性风险**: 审批超时、人员变动等场景缺少应对措施
3. **可实施性风险**: 缺少UI/UX规范,AI和开发人员难以生成准确代码

### 行动建议

#### 立即行动 (本周内)
- [ ] 重新设计编号分配逻辑,引入PostgreSQL序列
- [ ] 定义审批超时处理策略并实现定时任务
- [ ] 为核心API补充OpenAPI 3.0规范

#### 短期行动 (2周内)  
- [ ] 添加校对任务取消机制
- [ ] 实现审批人变更转移逻辑
- [ ] 补充UI/UX设计规范文档
- [ ] 设计并实现幂等性保护

#### 长期优化 (1个月内)
- [ ] 完善审计日志和可追溯性
- [ ] 实施全面的异常处理和告警机制
- [ ] 补充前端状态管理设计
- [ ] 编写API集成测试用例

---

**报告生成时间**: 2026-02-15 21:27  
**审查依据**: 公文文件号管理系统设计文档 v1.0  
**下一步**: 建议召开技术评审会议,讨论高优先级问题的修复方案
