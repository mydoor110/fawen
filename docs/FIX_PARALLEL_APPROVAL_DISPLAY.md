# 并行审批节点显示问题修复

**问题描述**: 在AntFlow审批流程设计器中，选择并行审批节点的人员后，节点上没有显示已选择的人员信息。

**修复时间**: 2026-02-16 06:30  
**影响范围**: 前端审批流程设计器  

---

## 问题根因

### 1. 数据传递错误
在 `nodeWrap.vue` 的 `setNodeInfo` 函数中，当点击并行审批节点(nodeType=7)时：
- **错误做法**: 传递整个 `nodeConfig` 给审批人选择器
- **问题**: `nodeConfig` 包含了整个并行分支的所有节点，而不是单个并行节点的数据

### 2. 数据更新错误
在 `watch(approverConfig1)` 中，当用户选择完人员后：
- **错误做法**: 直接用返回的数据替换整个 `nodeConfig`
- **问题**: 这会覆盖整个并行分支结构，导致数据丢失

---

## 修复方案

### 修复1: 正确传递并行节点数据

**文件**: `frontend/src/antflow/components/nodeWrap.vue`  
**位置**: 第441-455行 (setNodeInfo函数的nodeType=7分支)

```javascript
// 修复前
7: () => {
    setApprover(true);
    setApproverConfig({
        value: {
            ...JSON.parse(JSON.stringify(props.nodeConfig)),  // ❌ 传递整个nodeConfig
            index: index,
        },
        flag: false,
        id: _uid,
    });
},

// 修复后
7: () => {
    setApprover(true);
    // 获取对应索引的并行节点数据
    const parallelNode = props.nodeConfig.parallelNodes && props.nodeConfig.parallelNodes[index] 
        ? props.nodeConfig.parallelNodes[index] 
        : {};
    setApproverConfig({
        value: {
            ...JSON.parse(JSON.stringify(parallelNode)),  // ✅ 只传递对应的并行节点
            index: index,  // 传递索引以便保存时能找到对应节点
            setType: parallelNode.setType ? parallelNode.setType : 1,
        },
        flag: false,
        id: _uid,
    });
},
```

---

### 修复2: 正确更新并行节点数据

**文件**: `frontend/src/antflow/components/nodeWrap.vue`  
**位置**: 第189-220行 (watch approverConfig1)

```javascript
// 修复前
watch(approverConfig1, (approver) => {
    if (approver.flag && approver.id === _uid) {
        emits("update:nodeConfig", approver.value);  // ❌ 直接替换整个nodeConfig
    }
});

// 修复后
watch(approverConfig1, (approver) => {
    if (approver.flag && approver.id === _uid) {
        // 特别处理并行审批节点 (nodeType==7)
        if (props.nodeConfig.nodeType == 7 && approver.value.index !== undefined) {
            // 并行审批节点，更新指定索引的parallelNodes
            const index = approver.value.index;
            if (props.nodeConfig.parallelNodes && props.nodeConfig.parallelNodes[index]) {
                // ✅ 只更新指定索引的节点数据
                props.nodeConfig.parallelNodes[index].nodeApproveList = approver.value.nodeApproveList;
                props.nodeConfig.parallelNodes[index].setType = approver.value.setType;
                props.nodeConfig.parallelNodes[index].signType = approver.value.signType;
                props.nodeConfig.parallelNodes[index].noHeaderAction = approver.value.noHeaderAction;
                
                // 重新计算显示名称
                const displayName = $func.setApproverStr(props.nodeConfig.parallelNodes[index]);
                props.nodeConfig.parallelNodes[index].nodeDisplayName = displayName;
                props.nodeConfig.parallelNodes[index].error = !displayName;
                
                console.log('[NodeWrap] Updated parallelNodes[' + index + '] with displayName:', displayName);
                
                // 发出整个nodeConfig的更新
                emits("update:nodeConfig", props.nodeConfig);
            }
        } else {
            // 普通审批节点 (nodeType==4)
            emits("update:nodeConfig", approver.value);
        }
    }
});
```

---

## 数据流说明

### 正确的数据流

```
用户点击并行节点
↓
setNodeInfo(index) 被调用
↓
从 parallelNodes[index] 获取单个节点数据
↓
打开审批人选择器，显示该节点的已选人员
↓
用户选择/修改人员
↓
approverDrawer 保存数据
↓
watch(approverConfig1) 触发
↓
更新 parallelNodes[index] 的数据
↓
调用 setApproverStr 生成显示文本
↓
更新 parallelNodes[index].nodeDisplayName
↓
界面显示更新 ✅
```

---

## 测试验证

### 测试步骤

1. **创建并行审批流程**
   - 打开审批流程设计器
   - 添加"并行审批"节点
   - 默认会有2个并行审批人节点

2. **选择第一个并行审批人**
   - 点击第一个并行节点
   - 选择"指定成员"或"审批角色"
   - 选择具体人员/角色
   - 点击确定

3. **验证显示**
   - ✅ 第一个并行节点应显示已选人员信息
   - ✅ 显示格式: "张三" 或 "副主任" 等

4. **选择第二个并行审批人**
   - 点击第二个并行节点
   - 选择人员/角色
   - 点击确定

5. **验证独立性**
   - ✅ 第二个节点显示正确
   - ✅ 第一个节点的数据没有被覆盖
   - ✅ 两个节点各自独立显示

6. **保存流程**
   - 点击保存流程
   - ✅ 后端应收到完整的并行节点数据

---

## 预期效果

### 修复前
```
┌─────────────────┐
│  并行审批分支   │
├─────────────────┤
│ 并行审批人1     │  ← 点击选择人员后
│ [请选择审批人]  │  ← ❌ 仍然显示"请选择"
├─────────────────┤
│ 并行审批人2     │
│ [请选择审批人]  │
└─────────────────┘
```

### 修复后
```
┌─────────────────┐
│  并行审批分支   │
├─────────────────┤
│ 并行审批人1     │  ← 点击选择人员后
│ 🙍‍♂️ 张三        │  ← ✅ 正确显示已选人员
├─────────────────┤
│ 并行审批人2     │
│ 副主任          │  ← ✅ 显示已选角色
└─────────────────┘
```

---

## 相关文件

**修改的文件**:
- `frontend/src/antflow/components/nodeWrap.vue` - 主要修复

**相关文件** (无需修改):
- `frontend/src/antflow/components/drawer/approverDrawer.vue` - 审批人选择器
- `frontend/src/antflow/utils/index.js` - setApproverStr函数
- `frontend/src/antflow/store.js` - 状态管理

---

## 注意事项

1. **索引传递**: 并行节点必须传递 `index` 参数，用于识别具体是哪个并行节点
2. **数据隔离**: 每个并行节点的数据是独立的，保存在 `parallelNodes[index]` 中
3. **显示名称**: `nodeDisplayName` 字段用于界面显示，由 `setApproverStr` 函数生成
4. **错误状态**: `error` 字段表示节点是否配置完整

---

## 提交信息

```
fix: 修复并行审批节点选择人员后不显示的问题

- 修复setNodeInfo函数，传递正确的并行节点数据而非整个nodeConfig
- 修复approverConfig1的watch，正确更新parallelNodes数组中的对应节点
- 添加详细的console.log用于调试

影响: 前端审批流程设计器
文件: frontend/src/antflow/components/nodeWrap.vue
```

---

**状态**: ✅ 已修复  
**测试**: 待用户验证  
**版本**: 2026-02-16
