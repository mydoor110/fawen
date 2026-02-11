<template>
  <div class="document-detail">
    <el-page-header @back="$router.back()" title="返回" />
    
    <el-card style="margin-top: 20px;">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="标题">{{ document?.title }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ document?.document_type }}</el-descriptions-item>
        <el-descriptions-item label="草稿编号">{{ document?.draft_number }}</el-descriptions-item>
        <el-descriptions-item label="正式编号">
          <span v-if="document?.official_number" style="color:#67C23A;font-weight:600">
            {{ document?.official_number }}
          </span>
          <span v-else style="color:#909399">未分配</span>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(document?.status)">
            {{ getStatusText(document?.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="锁定">
          <el-tag v-if="document?.is_locked" type="warning">已锁定</el-tag>
          <el-tag v-else type="success">未锁定</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(document?.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="通过时间">{{ formatDate(document?.approved_at) }}</el-descriptions-item>
      </el-descriptions>
      
      <el-divider />
      
      <el-space>
        <el-upload 
          v-if="canUpload"
          :action="uploadUrl" 
          :headers="uploadHeaders"
          :on-success="onUploadSuccess"
          :on-error="onUploadError"
          :show-file-list="false"
          accept=".doc,.docx"
        >
          <el-button type="primary" icon="Upload">上传Word</el-button>
        </el-upload>
        <el-button type="warning" @click="submitProofreading" :disabled="!canSubmitProofreading">
          提交校对
        </el-button>
        <el-button type="success" @click="submitApproval" :disabled="!canSubmitApproval">
          提交审批
        </el-button>
      </el-space>
    </el-card>
    
    <!-- 校对任务 -->
    <el-card style="margin-top: 20px;">
      <template #header><h3>校对任务</h3></template>
      <el-empty v-if="!proofreadingTasks.length" description="暂无校对任务" />
      <el-table v-else :data="proofreadingTasks" border>
        <el-table-column prop="proofreader_id" label="校对人" width="200" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getTaskStatusType(row.status)">{{ getTaskStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="comment" label="意见" />
        <el-table-column prop="completed_at" label="完成时间" width="180">
          <template #default="{ row }">{{ formatDate(row.completed_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 审批任务 -->
    <el-card style="margin-top: 20px;">
      <template #header><h3>审批任务</h3></template>
      <el-empty v-if="!approvalTasks.length" description="暂无审批任务" />
      <el-table v-else :data="approvalTasks" border>
        <el-table-column prop="approver_id" label="审批人" width="200" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getTaskStatusType(row.status)">{{ getTaskStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="comment" label="意见" />
        <el-table-column prop="completed_at" label="完成时间" width="180">
          <template #default="{ row }">{{ formatDate(row.completed_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getDocument, getDocumentProofreadingTasks, getDocumentApprovalTasks } from '@/api/document'
import { useUserStore } from '@/store/user'

const route = useRoute()
const userStore = useUserStore()

const document = ref(null)
const proofreadingTasks = ref([])
const approvalTasks = ref([])

const uploadUrl = computed(() => `/api/documents/${route.params.id}/upload`)
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${userStore.token}`
}))

const canUpload = computed(() => 
  document.value && ['draft', 'rejected'].includes(document.value.status)
)
const canSubmitProofreading = computed(() => 
  document.value?.status === 'draft'
)
const canSubmitApproval = computed(() => 
  ['draft', 'proofreading'].includes(document.value?.status)
)

const loadDocument = async () => {
  try {
    document.value = await getDocument(route.params.id)
  } catch (error) {
    console.error('加载文档失败:', error)
  }
}

const loadProofreadingTasks = async () => {
  try {
    proofreadingTasks.value = await getDocumentProofreadingTasks(route.params.id)
  } catch (error) {
    proofreadingTasks.value = []
  }
}

const loadApprovalTasks = async () => {
  try {
    approvalTasks.value = await getDocumentApprovalTasks(route.params.id)
  } catch (error) {
    approvalTasks.value = []
  }
}

const submitProofreading = () => {
  ElMessage.info('请回到文档列表使用"提交校对"按钮')
}
const submitApproval = () => {
  ElMessage.info('请回到文档列表使用"提交审批"按钮')
}

const onUploadSuccess = () => {
  ElMessage.success('文件上传成功')
  loadDocument()
}
const onUploadError = () => {
  ElMessage.error('文件上传失败')
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

const getStatusType = (s) => ({ draft: 'info', proofreading: 'warning', approval: '', approved: 'success', rejected: 'danger', destroyed: 'info' }[s] || 'info')
const getStatusText = (s) => ({ draft: '草稿', proofreading: '校对中', approval: '审批中', approved: '已通过', rejected: '已驳回', destroyed: '已销毁' }[s] || s)
const getTaskStatusType = (s) => ({ pending: 'warning', passed: 'success', approved: 'success', failed: 'danger', rejected: 'danger', skipped: 'info' }[s] || 'info')
const getTaskStatusText = (s) => ({ pending: '待处理', passed: '已通过', approved: '已通过', failed: '未通过', rejected: '已驳回', skipped: '已跳过' }[s] || s)

onMounted(() => {
  loadDocument()
  loadProofreadingTasks()
  loadApprovalTasks()
})
</script>

<style scoped>
.document-detail { padding: 20px; }
</style>
