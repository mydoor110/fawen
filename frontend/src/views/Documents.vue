<template>
  <div class="documents-page">
    <el-card>
      <template #header>
        <div class="page-header">
          <h3>文档管理</h3>
          <el-button type="primary" icon="Plus" @click="showCreateDialog">
            新建文档
          </el-button>
        </div>
      </template>
      
      <el-table :data="documents" v-loading="loading" border>
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="document_type" label="类型" width="120" />
        <el-table-column prop="draft_number" label="草稿编号" width="180" />
        <el-table-column prop="official_number" label="正式编号" width="180">
          <template #default="{ row }">
            <span v-if="row.official_number" style="color:#67C23A;font-weight:600">{{ row.official_number }}</span>
            <span v-else style="color:#909399">未分配</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_locked" label="锁定" width="80">
          <template #default="{ row }">
            <el-icon v-if="row.is_locked" color="#E6A23C"><Lock /></el-icon>
            <el-icon v-else color="#67C23A"><Unlock /></el-icon>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewDocument(row.id)">
              查看
            </el-button>
            <el-button 
              link type="primary" 
              @click="editDocument(row)"
              :disabled="!canEdit(row)"
            >
              编辑
            </el-button>
            <el-button 
              link type="warning" 
              @click="showProofreadingDialog(row)"
              :disabled="!canSubmitProofreading(row)"
            >
              提交校对
            </el-button>
            <el-button 
              link type="success" 
              @click="showApprovalDialog(row)"
              :disabled="!canSubmitApproval(row)"
            >
              提交审批
            </el-button>
            <el-button 
              link type="danger" 
              @click="deleteDocument(row.id)"
              :disabled="!canDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 新建/编辑文档对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑文档' : '新建文档'" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入文档标题" />
        </el-form-item>
        <el-form-item label="类型" prop="document_type">
          <el-input v-model="form.document_type" placeholder="请输入文档类型" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 提交校对对话框 -->
    <el-dialog v-model="proofreadingDialogVisible" title="提交校对" width="600px">
      <el-form label-width="100px">
        <el-form-item label="选择校对人">
          <el-select v-model="selectedProofreaders" multiple placeholder="请选择校对人员" style="width:100%">
            <el-option 
              v-for="user in userList" 
              :key="user.id" 
              :label="user.real_name || user.username" 
              :value="user.id" 
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="proofreadingDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitProofreading" :loading="saving"
          :disabled="selectedProofreaders.length === 0">
          提交校对
        </el-button>
      </template>
    </el-dialog>

    <!-- 提交审批对话框 -->
    <el-dialog v-model="approvalDialogVisible" title="提交审批" width="600px">
      <el-form label-width="100px">
        <el-form-item label="审批流程">
          <el-select v-model="selectedFlowId" placeholder="请选择审批流程" style="width:100%">
            <el-option 
              v-for="flow in approvalFlows" 
              :key="flow.id" 
              :label="flow.name" 
              :value="flow.id" 
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approvalDialogVisible = false">取消</el-button>
        <el-button type="success" @click="handleSubmitApproval" :loading="saving"
          :disabled="!selectedFlowId">
          提交审批
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { getDocuments, createDocument, updateDocument, deleteDocument as deleteDocApi, submitProofreading, submitApproval } from '@/api/document'
import { getUsers } from '@/api/user'
import { getApprovalFlows } from '@/api/approval'

const router = useRouter()

const loading = ref(false)
const dialogVisible = ref(false)
const proofreadingDialogVisible = ref(false)
const approvalDialogVisible = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const documents = ref([])
const formRef = ref(null)
const userList = ref([])
const approvalFlows = ref([])
const selectedProofreaders = ref([])
const selectedFlowId = ref('')
const currentDocId = ref(null)

const form = reactive({
  title: '',
  document_type: ''
})

const rules = {
  title: [{ required: true, message: '请输入文档标题', trigger: 'blur' }]
}

const loadDocuments = async () => {
  loading.value = true
  try {
    documents.value = await getDocuments()
  } catch (error) {
    console.error('加载文档失败:', error)
  } finally {
    loading.value = false
  }
}

const loadUsers = async () => {
  try {
    userList.value = await getUsers()
  } catch (error) {
    // 普通用户可能无权限获取用户列表，忽略
    userList.value = []
  }
}

const loadFlows = async () => {
  try {
    approvalFlows.value = await getApprovalFlows()
  } catch (error) {
    approvalFlows.value = []
  }
}

const showCreateDialog = () => {
  isEdit.value = false
  Object.assign(form, { title: '', document_type: '' })
  dialogVisible.value = true
}

const editDocument = (row) => {
  isEdit.value = true
  Object.assign(form, { title: row.title, document_type: row.document_type })
  form.id = row.id
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      saving.value = true
      try {
        if (isEdit.value) {
          await updateDocument(form.id, form)
          ElMessage.success('更新成功')
        } else {
          await createDocument(form)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        loadDocuments()
      } catch (error) {
        console.error('保存失败:', error)
      } finally {
        saving.value = false
      }
    }
  })
}

const viewDocument = (id) => {
  router.push(`/documents/${id}`)
}

// ---- 提交校对 ----
const showProofreadingDialog = (row) => {
  currentDocId.value = row.id
  selectedProofreaders.value = []
  loadUsers()
  proofreadingDialogVisible.value = true
}

const handleSubmitProofreading = async () => {
  saving.value = true
  try {
    await submitProofreading(currentDocId.value, selectedProofreaders.value)
    ElMessage.success('已提交校对')
    proofreadingDialogVisible.value = false
    loadDocuments()
  } catch (error) {
    console.error('提交校对失败:', error)
  } finally {
    saving.value = false
  }
}

// ---- 提交审批 ----
const showApprovalDialog = (row) => {
  currentDocId.value = row.id
  selectedFlowId.value = ''
  loadFlows()
  approvalDialogVisible.value = true
}

const handleSubmitApproval = async () => {
  saving.value = true
  try {
    await submitApproval(currentDocId.value, selectedFlowId.value)
    ElMessage.success('已提交审批')
    approvalDialogVisible.value = false
    loadDocuments()
  } catch (error) {
    console.error('提交审批失败:', error)
  } finally {
    saving.value = false
  }
}

const deleteDocument = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个文档吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteDocApi(id)
    ElMessage.success('删除成功')
    loadDocuments()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

const getStatusType = (status) => {
  const types = { draft: 'info', proofreading: 'warning', approval: '', approved: 'success', rejected: 'danger', destroyed: 'info' }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = { draft: '草稿', proofreading: '校对中', approval: '审批中', approved: '已通过', rejected: '已驳回', destroyed: '已销毁' }
  return texts[status] || status
}

const canEdit = (row) => ['draft', 'rejected'].includes(row.status)
const canSubmitProofreading = (row) => row.status === 'draft'
const canSubmitApproval = (row) => ['draft', 'proofreading'].includes(row.status)
const canDelete = (row) => row.status === 'draft'

onMounted(() => {
  loadDocuments()
})
</script>

<style scoped>
.documents-page { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; }
.page-header h3 { margin: 0; font-size: 18px; color: #333; }
</style>
