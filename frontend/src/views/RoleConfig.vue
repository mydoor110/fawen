<template>
  <div class="role-config">
    <el-card>
      <template #header>
        <div class="page-header">
          <h3>审批角色配置</h3>
          <el-button type="primary" icon="Plus" @click="openDialog()">新建角色</el-button>
        </div>
      </template>
      <el-table :data="roles" v-loading="loading" border stripe>
        <el-table-column prop="name" label="角色名称" min-width="140" />
        <el-table-column prop="level" label="审批等级" width="100" sortable>
          <template #default="{ row }">
            <el-tag :type="levelTagType(row.level)">{{ row.level }} 级</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column label="关联用户" min-width="200">
          <template #default="{ row }">
            <span v-if="row.users && row.users.length">
              <el-tag v-for="u in row.users" :key="u" size="small" style="margin-right: 4px;">{{ u }}</el-tag>
            </span>
            <span v-else style="color: #999;">暂无</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm
              title="删除后，关联该角色的用户和审批节点将受影响，确定删除？"
              confirm-button-text="确定"
              cancel-button-text="取消"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑审批角色' : '新建审批角色'" width="480px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="form.name" placeholder="如：科长审批" />
        </el-form-item>
        <el-form-item label="审批等级" prop="level">
          <el-input-number v-model="form.level" :min="1" :max="99" />
          <span style="margin-left: 12px; color: #999; font-size: 12px;">等级越高，审批权限越大</span>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="角色职责描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getApprovalRoles,
  createApprovalRole,
  updateApprovalRole,
  deleteApprovalRole
} from '@/api/user'

const loading = ref(false)
const submitLoading = ref(false)
const roles = ref([])

const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const formRef = ref(null)
const form = ref({ name: '', level: 1, description: '' })
const rules = {
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  level: [{ required: true, message: '请设置审批等级', trigger: 'change' }]
}

const levelTagType = (level) => {
  if (level <= 1) return 'info'
  if (level <= 2) return 'success'
  if (level <= 3) return 'warning'
  return 'danger'
}

const loadRoles = async () => {
  loading.value = true
  try {
    roles.value = await getApprovalRoles()
  } catch (error) {
    ElMessage.error('加载审批角色失败')
  } finally {
    loading.value = false
  }
}

const openDialog = (row = null) => {
  if (row) {
    isEdit.value = true
    editId.value = row.id
    form.value = { name: row.name, level: row.level, description: row.description || '' }
  } else {
    isEdit.value = false
    editId.value = null
    form.value = { name: '', level: 1, description: '' }
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    if (isEdit.value) {
      await updateApprovalRole(editId.value, form.value)
      ElMessage.success('审批角色更新成功')
    } else {
      await createApprovalRole(form.value)
      ElMessage.success('审批角色创建成功')
    }
    dialogVisible.value = false
    loadRoles()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await deleteApprovalRole(row.id)
    ElMessage.success('审批角色删除成功')
    loadRoles()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  }
}

onMounted(loadRoles)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.page-header h3 {
  margin: 0;
}
</style>
