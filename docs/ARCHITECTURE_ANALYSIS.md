# 公文文件号管理系统 - 架构分析与优化建议

**分析日期**: 2026-02-15  
**分析对象**: 用户自定义审批流程的可行性分析

---

## 📋 用户需求流程

```
┌─────────────────────────────────────────────────────────────┐
│                    用户期望的业务流程                          │
└─────────────────────────────────────────────────────────────┘

1. 用户提交文档并上传
   ↓
2. 并行校对（多人同时校对）
   ↓
3. 副主任审批
   ↓
4. 主任审批
   ↓
5. 文件管理员审批
   ↓
6. 自动发号 + 自动盖章
   ↓
7. 文件管理员可手动调整文件号（需系统校验合规性）
```

---

## ✅ 当前系统支持情况分析

### 1. 用户提交文档并上传 ✅ **完全支持**

**现状**:
- ✅ API: `POST /documents` - 创建文档
- ✅ API: `POST /documents/{id}/upload` - 上传Word文档
- ✅ 支持文件格式验证（仅允许.docx）
- ✅ 支持文件大小限制（默认50MB）
- ✅ 草稿自动编号生成（格式：D-YYYYMMDD-随机码）

**代码位置**:
- `app/api/document.py` (line 36-57, 127-172)
- `app/models/document.py` (line 16-36)

---

### 2. 并行校对 ✅ **完全支持**

**现状**:
- ✅ API: `POST /documents/{id}/submit-proofreading`
- ✅ 支持同时指定多个校对人员
- ✅ 校对任务并行执行
- ✅ 支持两种通过模式：
  - `all_pass`: 所有校对人都通过（默认）
  - `majority_pass`: 超过50%通过即可
- ✅ 校对时自动锁定编号字段

**代码位置**:
- `app/services/document_service.py` (line 56-106)
- `app/api/proofreading.py` (line 38-93)
- `config.yaml` - proofreading.mode 配置

**配置示例**:
```yaml
proofreading:
  mode: "all_pass"
  timeout_days: 7
  can_skip: false
  require_comment: true
```

---

### 3. 串行审批（副主任 → 主任 → 文件管理员）✅ **完全支持**

**现状**:
- ✅ 基于 ApprovalFlow（审批流程）和 ApprovalNode（审批节点）
- ✅ 支持按 sequence 字段串行推进
- ✅ 支持审批角色系统（ApprovalRole）
- ✅ 支持每个节点的 AND/OR 模式：
  - AND: 该节点所有审批人都通过才推进
  - OR: 该节点任一审批人通过即推进

**数据模型**:
```
ApprovalFlow (审批流程)
  ├── ApprovalNode (sequence=1) → 副主任角色
  ├── ApprovalNode (sequence=2) → 主任角色
  └── ApprovalNode (sequence=3) → 文件管理员角色

每个节点关联一个 ApprovalRole（审批角色）
每个角色可以分配给多个 User（用户）
```

**代码位置**:
- `app/models/approval.py` (line 11-34)
- `app/services/document_service.py` (line 148-241)
- `app/api/approval.py` (line 337-379 - _advance_to_next_node 函数)

**如何配置您的流程**:
```python
# 1. 创建三个审批角色
POST /admin/approval-roles
{
  "name": "副主任",
  "level": 1,
  "description": "副主任审批层级"
}

POST /admin/approval-roles
{
  "name": "主任",
  "level": 2,
  "description": "主任审批层级"
}

POST /admin/approval-roles
{
  "name": "文件管理员",
  "level": 3,
  "description": "文件管理员审批层级"
}

# 2. 创建审批流程
POST /approval/flows
{
  "name": "标准公文审批流程",
  "description": "副主任→主任→文件管理员"
}

# 3. 为流程添加三个节点
POST /approval/flows/{flow_id}/nodes
{
  "approval_role_id": "{副主任角色ID}",
  "sequence": 1,
  "node_type": "and",
  "timeout_days": 7
}

POST /approval/flows/{flow_id}/nodes
{
  "approval_role_id": "{主任角色ID}",
  "sequence": 2,
  "node_type": "and",
  "timeout_days": 7
}

POST /approval/flows/{flow_id}/nodes
{
  "approval_role_id": "{文件管理员角色ID}",
  "sequence": 3,
  "node_type": "and",
  "timeout_days": 7
}

# 4. 将具体用户分配到审批角色
POST /admin/approval-roles/{user_id}?approval_role_id={副主任角色ID}&priority=0
POST /admin/approval-roles/{user_id}?approval_role_id={主任角色ID}&priority=0
POST /admin/approval-roles/{user_id}?approval_role_id={文件管理员角色ID}&priority=0
```

---

### 4. 自动发号 ✅ **完全支持**

**现状**:
- ✅ 在最后一个审批节点通过后**自动触发**
- ✅ 支持编号池管理（NumberPool）
- ✅ 支持编号回收复用（RecyclePool）
- ✅ 编号格式可配置（前缀、年份、序号）

**自动发号逻辑**:
```python
# app/api/approval.py (line 367-375)
if next_node:
    # 推进到下一个节点
    ...
else:
    # 最终节点通过 → 审批完成
    document.status = DocumentStatus.APPROVED
    document.approved_at = datetime.utcnow()
    
    # 🔥 自动分配正式文件号
    allocate_official_number(db, document, user)
    
    unlock_document(db, document, user, "审批全部通过，自动解锁")
```

**编号生成规则**:
```python
# app/services/document_service.py (line 244-313)
1. 优先从回收池获取（如果配置 recycle_first=true）
2. 否则从编号池分配当前序号
3. 格式: {prefix}-{year}-{序号(4位)}
   例如: GW-2026-0001
```

**配置示例**:
```yaml
number:
  pool:
    auto_allocate: true
    recycle_first: true
  format:
    prefix: "GW"
    year_length: 4
    number_length: 4
    separator: "-"
```

**代码位置**:
- `app/services/document_service.py` (line 244-313)
- `app/api/approval.py` (line 374)

---

### 5. 自动盖章 ❌ **未实现 - 需要补充**

**现状**: 
- ❌ 系统中**没有**自动盖章功能的实现
- ❌ 没有电子印章管理模块
- ❌ 没有Word文档签章处理逻辑

**需要补充的功能**:
1. 电子印章图片管理
2. Word文档签章位置定位
3. python-docx 或其他库进行图片插入
4. 签章记录和验证

**建议实现方案**:

#### 方案A: 使用 python-docx 插入图片印章
```python
from docx import Document
from docx.shared import Inches

def add_seal_to_document(file_path: str, seal_image_path: str):
    """
    在Word文档指定位置添加电子印章
    """
    doc = Document(file_path)
    
    # 在文档末尾添加印章
    paragraph = doc.add_paragraph()
    run = paragraph.add_run()
    run.add_picture(seal_image_path, width=Inches(1.5))
    
    doc.save(file_path)
```

#### 方案B: 使用专业的电子签章服务
- 集成第三方电子签章服务（如e签宝、上上签）
- 符合国家电子签章标准
- 具有法律效力

**建议的实现位置**:
```python
# 在 app/services/document_service.py 中添加
def add_electronic_seal(db: Session, document: Document, user: User):
    """
    为文档添加电子印章
    """
    if not document.file_path or not os.path.exists(document.file_path):
        raise Exception("文档文件不存在")
    
    # 获取印章配置
    seal_config = db.query(SystemConfig).filter(
        SystemConfig.config_key == "electronic_seal"
    ).first()
    
    if not seal_config:
        raise Exception("未配置电子印章")
    
    seal_image_path = seal_config.config_value.get("image_path")
    
    # 调用盖章函数
    add_seal_to_document(document.file_path, seal_image_path)
    
    # 记录盖章日志
    log_audit(db, user, AuditEvent.DOCUMENT_SEAL,
              "Document", str(document.id),
              {"seal_time": datetime.utcnow().isoformat()})

# 在自动发号后调用
# app/api/approval.py (line 374后添加)
allocate_official_number(db, document, user)
add_electronic_seal(db, document, user)  # 新增
```

---

### 6. 文件管理员手动调整文件号 ✅ **部分支持 - 需要优化**

**现状**:
- ✅ API: `POST /numbers/records/{record_id}/adjust`
- ✅ 要求填写调整原因
- ✅ 自动记录审计日志
- ✅ 权限检查（需要 `number.adjust` 权限）
- ⚠️ 配置控制是否允许审批中调整

**当前限制**:
```python
# app/api/number.py (line 88-92)
if record.status == NumberRecordStatus.ALLOCATED:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="已分配的编号不可直接调整"
    )
```

**问题**: 已分配的编号不允许调整！

**需要优化的地方**:
为了满足"文件管理员可以手动调整"的需求，建议修改逻辑：

```python
# 修改后的逻辑（建议）
if record.status == NumberRecordStatus.ALLOCATED:
    # 检查是否有 number.force_adjust 权限（文件管理员专属）
    if not has_permission("number.force_adjust", current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅文件管理员可调整已分配的编号"
        )
    
    # 强制要求填写原因
    if not request.reason or len(request.reason.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="调整已分配编号需要详细说明原因（至少10字符）"
        )
```

---

### 7. 文件号合规性校验 ⚠️ **基础支持 - 需要增强**

**现状**:
- ✅ 编号唯一性约束（数据库层面）
- ⚠️ 格式校验较弱

**需要增强的校验**:
1. 编号格式校验（正则表达式）
2. 年份合法性校验
3. 序号范围校验
4. 前缀合法性校验

**建议实现**:

```python
# 新增文件: app/utils/number_validator.py
import re
from datetime import datetime

class NumberValidator:
    """文件号合规性校验器"""
    
    @staticmethod
    def validate_format(number: str, pattern: str = None) -> tuple[bool, str]:
        """
        校验文件号格式
        默认格式: {前缀}-{年份}-{序号}
        """
        if not pattern:
            pattern = r'^[A-Z]{2,5}-\d{4}-\d{4,6}$'
        
        if not re.match(pattern, number):
            return False, f"文件号格式不符合规范: {pattern}"
        
        return True, "格式正确"
    
    @staticmethod
    def validate_year(number: str) -> tuple[bool, str]:
        """校验年份是否合理"""
        parts = number.split('-')
        if len(parts) < 2:
            return False, "无法解析年份"
        
        try:
            year = int(parts[1])
            current_year = datetime.now().year
            
            if year < 2000 or year > current_year + 1:
                return False, f"年份不合理: {year}"
            
            return True, "年份正确"
        except ValueError:
            return False, "年份格式错误"
    
    @staticmethod
    def validate_sequence(number: str, max_sequence: int = 9999) -> tuple[bool, str]:
        """校验序号范围"""
        parts = number.split('-')
        if len(parts) < 3:
            return False, "无法解析序号"
        
        try:
            seq = int(parts[2])
            if seq < 1 or seq > max_sequence:
                return False, f"序号超出范围: 1-{max_sequence}"
            
            return True, "序号正确"
        except ValueError:
            return False, "序号格式错误"
    
    @staticmethod
    def validate_all(number: str) -> tuple[bool, list[str]]:
        """
        执行所有校验
        返回: (是否通过, 错误信息列表)
        """
        errors = []
        
        valid, msg = NumberValidator.validate_format(number)
        if not valid:
            errors.append(msg)
        
        valid, msg = NumberValidator.validate_year(number)
        if not valid:
            errors.append(msg)
        
        valid, msg = NumberValidator.validate_sequence(number)
        if not valid:
            errors.append(msg)
        
        return len(errors) == 0, errors

# 在调整编号时调用
# app/api/number.py (line 100前添加)
from app.utils.number_validator import NumberValidator

# 校验新编号的合规性
is_valid, errors = NumberValidator.validate_all(request.new_number)
if not is_valid:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"文件号不合规: {'; '.join(errors)}"
    )
```

---

## 🎯 自定义流程设置

### 方式一: 通过API手动配置（当前支持）

**步骤**:
1. 创建审批角色: `POST /admin/approval-roles`
2. 创建审批流程: `POST /approval/flows`
3. 添加审批节点: `POST /approval/flows/{flow_id}/nodes`
4. 分配用户到角色: `POST /admin/approval-roles/{user_id}`

**优点**: 灵活、精确控制  
**缺点**: 需要编写代码调用API

---

### 方式二: 使用AntFlow可视化设计器（前端已集成）

**现状**:
- ✅ 前端已集成AntFlow组件
- ✅ 有FlowDesigner.vue可视化设计器
- ⚠️ 但流程数据保存后**未与后端审批逻辑关联**

**问题**:
```javascript
// frontend/src/antflow/api.js (line 78-81)
export const setWorkFlowData = async (data) => {
    console.log('AntFlow workflow data:', JSON.stringify(data))
    return { code: 200 }  // ⚠️ 仅打印，未保存到数据库！
}
```

**需要实现的功能**:
1. 将AntFlow的JSON数据保存到 `ApprovalFlow.flow_data` 字段
2. 解析AntFlow数据并生成 `ApprovalNode` 记录
3. 将用户/角色选择映射到 `approval_role_id`

**建议实现方案**:

```python
# 新增文件: app/services/antflow_parser.py
import json
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.approval import ApprovalFlow, ApprovalNode, NodeApprovalType
import uuid

class AntFlowParser:
    """AntFlow数据解析器"""
    
    @staticmethod
    def parse_and_create_flow(db: Session, flow_data: dict) -> ApprovalFlow:
        """
        解析AntFlow数据并创建审批流程
        
        flow_data 示例:
        {
          "bpmnName": "标准公文审批流程",
          "nodeConfig": {
            "nodeType": "ROOT",
            "childNode": {
              "nodeType": "APPROVAL",
              "nodeName": "副主任审批",
              "nodeUserList": [{"type": 3, "targetId": "role_id", "name": "副主任"}],
              "childNode": {
                "nodeType": "APPROVAL",
                "nodeName": "主任审批",
                ...
              }
            }
          }
        }
        """
        # 1. 创建审批流程
        flow = ApprovalFlow(
            name=flow_data.get("bpmnName", "未命名流程"),
            description=flow_data.get("description", ""),
            flow_data=json.dumps(flow_data)  # 保存原始数据
        )
        db.add(flow)
        db.flush()
        
        # 2. 递归解析节点
        node_config = flow_data.get("nodeConfig", {})
        sequence = 1
        
        AntFlowParser._parse_node_recursive(
            db, flow.id, node_config, sequence
        )
        
        return flow
    
    @staticmethod
    def _parse_node_recursive(
        db: Session, 
        flow_id: uuid.UUID, 
        node_data: dict, 
        sequence: int
    ) -> int:
        """递归解析节点"""
        child_node = node_data.get("childNode")
        
        if not child_node:
            return sequence
        
        node_type = child_node.get("nodeType")
        
        # 仅处理审批节点
        if node_type == "APPROVAL":
            # 获取审批人配置
            node_user_list = child_node.get("nodeUserList", [])
            
            # 提取角色ID（假设type=3表示角色）
            role_ids = [
                uuid.UUID(user["targetId"]) 
                for user in node_user_list 
                if user.get("type") == 3
            ]
            
            if role_ids:
                # 为每个角色创建一个节点（或使用第一个角色）
                approval_role_id = role_ids[0]
                
                # 判断是AND还是OR模式
                # AntFlow中可能有配置，这里默认AND
                node_type_enum = NodeApprovalType.AND
                if child_node.get("selectMode") == "OR":
                    node_type_enum = NodeApprovalType.OR
                
                node = ApprovalNode(
                    flow_id=flow_id,
                    approval_role_id=approval_role_id,
                    sequence=sequence,
                    node_type=node_type_enum,
                    timeout_days=child_node.get("timeoutDays", 7)
                )
                db.add(node)
                sequence += 1
        
        # 递归处理子节点
        if child_node.get("childNode"):
            sequence = AntFlowParser._parse_node_recursive(
                db, flow_id, child_node, sequence
            )
        
        return sequence

# 更新API: app/api/approval.py
@router.post("/flows/from-antflow", response_model=ApprovalFlowResponse)
def create_flow_from_antflow(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """从AntFlow数据创建审批流程"""
    check_permission("approval.create_flow", current_user, db)
    
    from app.services.antflow_parser import AntFlowParser
    
    flow = AntFlowParser.parse_and_create_flow(db, data)
    db.commit()
    db.refresh(flow)
    
    return flow

# 更新前端API: frontend/src/antflow/api.js
export const setWorkFlowData = async (data) => {
    console.log('AntFlow workflow data:', JSON.stringify(data))
    
    // 调用后端保存流程
    const response = await request({
        url: '/approval/flows/from-antflow',
        method: 'POST',
        data
    })
    
    return { code: 200, data: response }
}
```

---

## 🚨 发现的问题总结

| # | 问题 | 严重程度 | 现状 |
|---|------|---------|------|
| 1 | 自动盖章功能缺失 | 🔴 高 | 未实现 |
| 2 | 已分配编号无法调整 | 🟡 中 | 需要优化权限逻辑 |
| 3 | 文件号合规性校验不完善 | 🟡 中 | 需要增强校验规则 |
| 4 | AntFlow数据未与后端关联 | 🟡 中 | 流程设计器数据未保存 |
| 5 | Document缺少approval_flow_id | 🟢 低 | 已修复 |

---

## ✨ 优化建议

### 立即需要实现（高优先级）

1. **实现自动盖章功能**
   - 添加电子印章管理模块
   - 在自动发号后自动盖章
   - 记录盖章时间和操作人

2. **完善文件号调整权限**
   - 允许文件管理员调整已分配编号
   - 强化原因必填和审计记录
   - 添加二次确认机制

3. **增强文件号合规性校验**
   - 实现NumberValidator校验器
   - 在手动调整时强制校验
   - 提供友好的错误提示

---

### 建议实现（中优先级）

4. **打通AntFlow与后端流程**
   - 实现AntFlowParser解析器
   - 添加 `/approval/flows/from-antflow` API
   - 前端调用该API保存流程

5. **优化审批流程可视化**
   - 在文档详情页显示当前审批进度
   - 显示每个节点的审批人和状态
   - 支持流程图可视化展示

---

### 长期优化（低优先级）

6. **增加流程模板**
   - 预设常用审批流程模板
   - 支持流程克隆和导入导出
   - 流程版本控制

7. **优化用户体验**
   - 审批任务邮件/消息提醒
   - 移动端审批支持
   - 批量审批功能

---

## 🎉 结论

**您的流程需求是否可以实现？**

✅ **完全可以实现！** 

当前系统架构**已经支持**您描述的全部流程，只需要：

### 必须立即完成的（影响核心功能）:
1. ✅ 配置三个审批角色（副主任、主任、文件管理员）
2. ✅ 创建审批流程并添加三个串行节点
3. ✅ 分配具体用户到这三个角色
4. 🔧 **实现自动盖章功能**（当前缺失）
5. 🔧 **修改编号调整权限**（允许文件管理员调整已分配编号）
6. 🔧 **实现文件号校验器**（确保调整的编号合规）

### 可选优化（提升用户体验）:
7. 打通AntFlow可视化设计器与后端（如果希望用户通过界面配置流程）
8. 增加审批进度可视化
9. 添加消息提醒功能

---

## 📝 快速配置指南

### 方案A: 通过API配置（立即可用）

```bash
# 1. 创建三个审批角色
curl -X POST http://localhost:8000/admin/approval-roles \
  -H "Authorization: Bearer {token}" \
  -d '{"name":"副主任","level":1,"description":"副主任审批"}'

curl -X POST http://localhost:8000/admin/approval-roles \
  -H "Authorization: Bearer {token}" \
  -d '{"name":"主任","level":2,"description":"主任审批"}'

curl -X POST http://localhost:8000/admin/approval-roles \
  -H "Authorization: Bearer {token}" \
  -d '{"name":"文件管理员","level":3,"description":"文件管理员审批"}'

# 2. 创建审批流程
curl -X POST http://localhost:8000/approval/flows \
  -H "Authorization: Bearer {token}" \
  -d '{"name":"标准公文审批流程","description":"副主任→主任→文件管理员"}'

# 3. 添加三个审批节点（使用上步返回的flow_id和角色IDs）
curl -X POST http://localhost:8000/approval/flows/{flow_id}/nodes \
  -H "Authorization: Bearer {token}" \
  -d '{"approval_role_id":"{副主任ID}","sequence":1,"node_type":"and","timeout_days":7}'

curl -X POST http://localhost:8000/approval/flows/{flow_id}/nodes \
  -H "Authorization: Bearer {token}" \
  -d '{"approval_role_id":"{主任ID}","sequence":2,"node_type":"and","timeout_days":7}'

curl -X POST http://localhost:8000/approval/flows/{flow_id}/nodes \
  -H "Authorization: Bearer {token}" \
  -d '{"approval_role_id":"{文件管理员ID}","sequence":3,"node_type":"and","timeout_days":7}'

# 4. 分配用户到角色
curl -X POST http://localhost:8000/admin/approval-roles/{user_id} \
  -H "Authorization: Bearer {token}" \
  -d '{"approval_role_id":"{副主任ID}","priority":0}'
```

### 方案B: 使用AntFlow可视化设计（需要先实现Parser）

在前端FlowDesigner中设计流程 → 保存时自动生成ApprovalNode

---

**需要我帮您实现哪部分功能？**
