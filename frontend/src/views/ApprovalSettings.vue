<template>
  <div class="approval-settings">
    <!-- 顶部操作栏 -->
    <div class="top-bar">
      <div class="top-bar-left">
        <el-select v-model="currentFlowId" placeholder="选择审批流程" style="width: 260px;" @change="onFlowChange">
          <el-option v-for="flow in flows" :key="flow.id" :label="flow.name" :value="flow.id">
            <span>{{ flow.name }}</span>
            <el-tag :type="flow.is_active ? 'success' : 'info'" size="small" style="margin-left: 8px;">
              {{ flow.is_active ? '启用' : '停用' }}
            </el-tag>
          </el-option>
        </el-select>
        <el-button type="primary" icon="Plus" @click="openFlowDialog()">新建流程</el-button>
        <el-button v-if="currentFlowId" icon="Edit" @click="openFlowDialog(currentFlowObj)">编辑</el-button>
        <el-button v-if="currentFlowId" :type="currentFlowObj?.is_active ? 'warning' : 'success'"
          @click="toggleFlowActive">
          {{ currentFlowObj?.is_active ? '停用' : '启用' }}
        </el-button>
        <el-popconfirm v-if="currentFlowId" title="删除此流程？" @confirm="handleDeleteFlow">
          <template #reference>
            <el-button type="danger" icon="Delete">删除</el-button>
          </template>
        </el-popconfirm>
      </div>
      <div class="top-bar-right">
        <el-button type="primary" icon="Check" @click="handlePublish" :loading="saving">
          保存流程
        </el-button>
      </div>
    </div>

    <!-- AntFlow 流程设计器（核心） -->
    <div v-if="nodeConfig" class="designer-container">
      <Process ref="processRef" :processData="nodeConfig" />
    </div>

    <!-- 未选择流程时的引导 -->
    <div v-else class="empty-state">
      <el-empty description="请选择或新建一个审批流程" :image-size="160">
        <el-button type="primary" @click="openFlowDialog()">新建审批流程</el-button>
      </el-empty>
    </div>

    <!-- 新建/编辑流程对话框 -->
    <el-dialog v-model="flowDialogVisible" :title="flowForm.id ? '编辑流程' : '新建流程'" width="500px" destroy-on-close>
      <el-form :model="flowForm" :rules="flowRules" ref="flowFormRef" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="flowForm.name" placeholder="如：标准公文审批流程" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="flowForm.description" type="textarea" :rows="3" placeholder="流程用途说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="flowDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveFlow">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import Process from '@/antflow/components/Process/index.vue'
import { NodeUtils } from '@/antflow/utils/nodeUtils'
import { FormatDisplayUtils } from '@/antflow/utils/formatdisplay_data'
import { FormatUtils } from '@/antflow/utils/formatcommit_data'
import {
  getApprovalFlows,
  createApprovalFlow,
  updateApprovalFlow,
  deleteApprovalFlow
} from '@/api/approval'

const processRef = ref(null)
const loading = ref(false)
const saving = ref(false)
const flows = ref([])
const currentFlowId = ref(null)
const nodeConfig = ref(null)

const currentFlowObj = computed(() => flows.value.find(f => f.id === currentFlowId.value))

// ===== 流程列表 =====
const loadFlows = async () => {
  loading.value = true
  try {
    flows.value = await getApprovalFlows()
  } catch (e) {
    ElMessage.error('加载流程失败')
  } finally {
    loading.value = false
  }
}

const onFlowChange = (flowId) => {
  const flow = flows.value.find(f => f.id === flowId)
  if (flow && flow.flow_data) {
    // 从后端加载已保存的流程 JSON
    try {
      const data = typeof flow.flow_data === 'string' ? JSON.parse(flow.flow_data) : flow.flow_data
      nodeConfig.value = data
    } catch (e) {
      console.error('解析流程数据失败:', e)
      initNewFlow()
    }
  } else {
    initNewFlow()
  }
}

const initNewFlow = () => {
  // 创建 AntFlow 默认起始节点
  let mockjson = NodeUtils.createStartNode()
  let data = FormatDisplayUtils.getToTree(mockjson.data)
  nodeConfig.value = data.nodeConfig
}

// ===== 流程 CRUD =====
const flowDialogVisible = ref(false)
const flowFormRef = ref(null)
const flowForm = ref({ id: null, name: '', description: '' })
const flowRules = { name: [{ required: true, message: '请输入流程名称', trigger: 'blur' }] }

const openFlowDialog = (row = null) => {
  flowForm.value = row
    ? { id: row.id, name: row.name, description: row.description || '' }
    : { id: null, name: '', description: '' }
  flowDialogVisible.value = true
}

const handleSaveFlow = async () => {
  const valid = await flowFormRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (flowForm.value.id) {
      await updateApprovalFlow(flowForm.value.id, {
        name: flowForm.value.name,
        description: flowForm.value.description
      })
      ElMessage.success('流程更新成功')
    } else {
      const res = await createApprovalFlow({
        name: flowForm.value.name,
        description: flowForm.value.description
      })
      // 自动选中新建的流程
      if (res && res.id) {
        currentFlowId.value = res.id
        initNewFlow()
      }
      ElMessage.success('流程创建成功')
    }
    flowDialogVisible.value = false
    loadFlows()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

const toggleFlowActive = async () => {
  const flow = currentFlowObj.value
  if (!flow) return
  try {
    await updateApprovalFlow(flow.id, { is_active: !flow.is_active })
    ElMessage.success(flow.is_active ? '已停用' : '已启用')
    loadFlows()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleDeleteFlow = async () => {
  try {
    await deleteApprovalFlow(currentFlowId.value)
    ElMessage.success('流程已删除')
    currentFlowId.value = null
    nodeConfig.value = null
    loadFlows()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

// ===== 发布/保存 =====
const handlePublish = async () => {
  if (!currentFlowId.value) {
    ElMessage.warning('请先选择或创建一个流程')
    return
  }
  saving.value = true
  try {
    // 获取流程设计器数据
    const processData = await processRef.value.getData().catch(() => null)
    if (!processData || !processData.formData) {
      ElMessage.error('流程数据校验失败，请检查节点配置')
      saving.value = false
      return
    }

    // 将流程 JSON 保存到后端
    await updateApprovalFlow(currentFlowId.value, {
      flow_data: JSON.stringify(processData.formData)
    })
    ElMessage.success('流程保存成功')
    loadFlows()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadFlows()
})
</script>

<style>
/* AntFlow 流程设计器样式（非scoped，仅在此页面加载） */
@import '@/antflow/assets/css/workflow.css';
@import '@/antflow/assets/css/override-element-ui.css';
</style>

<style scoped>
.approval-settings {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px);
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  z-index: 10;
}

.top-bar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.designer-container {
  flex: 1;
  overflow: auto;
  background: #f5f5f7;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f7;
}
</style>
