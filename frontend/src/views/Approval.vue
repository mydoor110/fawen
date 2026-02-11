<template>
  <div class="approval-page">
    <el-card>
      <template #header>
        <h3>我的审批任务</h3>
      </template>
      
      <el-table :data="tasks" v-loading="loading" border>
        <el-table-column label="文档标题" min-width="200">
          <template #default="{ row }">
            {{ getDocumentTitle(row.document_id) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="comment" label="意见" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button 
              v-if="row.status === 'pending'"
              link 
              type="success" 
              @click="showApproveDialog(row)"
            >
              通过
            </el-button>
            <el-button 
              v-if="row.status === 'pending'"
              link 
              type="danger" 
              @click="showRejectDialog(row)"
            >
              驳回
            </el-button>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 审批对话框 -->
    <el-dialog v-model="dialogVisible" title="审批" width="600px">
      <el-form :model="form" ref="formRef" label-width="100px">
        <el-form-item label="意见" prop="comment">
          <el-input 
            v-model="form.comment" 
            type="textarea" 
            :rows="4" 
            placeholder="请输入审批意见"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button 
          v-if="action === 'approve'"
          type="success" 
          @click="handleAction"
          :loading="saving"
        >
          通过
        </el-button>
        <el-button 
          v-if="action === 'reject'"
          type="danger" 
          @click="handleAction"
          :loading="saving"
        >
          驳回
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getMyApprovalTasks, approveTask, rejectTask } from '@/api/approval'
import { getDocuments } from '@/api/document'

const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const tasks = ref([])
const formRef = ref(null)
const currentTask = ref(null)
const action = ref('approve')
const documents = ref([])

const form = reactive({
  comment: ''
})

const loadTasks = async () => {
  loading.value = true
  try {
    tasks.value = await getMyApprovalTasks()
    await loadDocuments()
  } catch (error) {
    console.error('加载审批任务失败:', error)
  } finally {
    loading.value = false
  }
}

const loadDocuments = async () => {
  try {
    documents.value = await getDocuments()
  } catch (error) {
    console.error('加载文档失败:', error)
  }
}

const showApproveDialog = (task) => {
  currentTask.value = task
  action.value = 'approve'
  form.comment = ''
  dialogVisible.value = true
}

const showRejectDialog = (task) => {
  currentTask.value = task
  action.value = 'reject'
  form.comment = ''
  dialogVisible.value = true
}

const handleAction = async () => {
  saving.value = true
  try {
    if (action.value === 'approve') {
      await approveTask(currentTask.value.id, form.comment)
      ElMessage.success('审批通过')
    } else {
      await rejectTask(currentTask.value.id, form.comment)
      ElMessage.success('审批驳回')
    }
    dialogVisible.value = false
    loadTasks()
  } catch (error) {
    console.error('审批失败:', error)
  } finally {
    saving.value = false
  }
}

const getDocumentTitle = (documentId) => {
  const doc = documents.value.find(d => d.id === documentId)
  return doc ? doc.title : documentId
}

const getStatusType = (status) => {
  const types = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
    skipped: 'info'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    pending: '待处理',
    approved: '已通过',
    rejected: '已驳回',
    skipped: '已跳过'
  }
  return texts[status] || status
}

onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
.approval-page {
  padding: 20px;
}

.approval-page h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}
</style>
