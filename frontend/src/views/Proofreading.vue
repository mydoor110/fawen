<template>
  <div class="proofreading-page">
    <el-card>
      <template #header>
        <h3>我的校对任务</h3>
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
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button 
              v-if="row.status === 'pending'"
              link 
              type="primary" 
              @click="showCompleteDialog(row)"
            >
              完成
            </el-button>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 完成校对对话框 -->
    <el-dialog v-model="dialogVisible" title="完成校对" width="600px">
      <el-form :model="form" ref="formRef" label-width="100px">
        <el-form-item label="结果" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio label="passed">通过</el-radio>
            <el-radio label="failed">不通过</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="意见" prop="comment">
          <el-input 
            v-model="form.comment" 
            type="textarea" 
            :rows="4" 
            placeholder="请输入校对意见"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleComplete" :loading="saving">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getMyProofreadingTasks, completeProofreading } from '@/api/proofreading'
import { getDocuments } from '@/api/document'

const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const tasks = ref([])
const formRef = ref(null)
const currentTask = ref(null)
const documents = ref([])

const form = reactive({
  status: 'passed',
  comment: ''
})

const loadTasks = async () => {
  loading.value = true
  try {
    tasks.value = await getMyProofreadingTasks()
    await loadDocuments()
  } catch (error) {
    console.error('加载校对任务失败:', error)
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

const showCompleteDialog = (task) => {
  currentTask.value = task
  Object.assign(form, {
    status: 'passed',
    comment: ''
  })
  dialogVisible.value = true
}

const handleComplete = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      saving.value = true
      try {
        await completeProofreading(currentTask.value.id, form)
        ElMessage.success('校对完成')
        dialogVisible.value = false
        loadTasks()
      } catch (error) {
        console.error('完成校对失败:', error)
      } finally {
        saving.value = false
      }
    }
  })
}

const getDocumentTitle = (documentId) => {
  const doc = documents.value.find(d => d.id === documentId)
  return doc ? doc.title : documentId
}

const getStatusType = (status) => {
  const types = {
    pending: 'warning',
    passed: 'success',
    failed: 'danger',
    skipped: 'info'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    pending: '待处理',
    passed: '已通过',
    failed: '未通过',
    skipped: '已跳过'
  }
  return texts[status] || status
}

onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
.proofreading-page {
  padding: 20px;
}

.proofreading-page h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}
</style>
