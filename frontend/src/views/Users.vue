<template>
  <div class="users-page">
    <el-card>
      <template #header>
        <div class="page-header">
          <h3>用户管理</h3>
          <el-button type="primary" icon="Plus" @click="openCreateDialog">新建用户</el-button>
        </div>
      </template>
      <el-table :data="users" v-loading="loading" border stripe>
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="real_name" label="姓名" width="100" />
        <el-table-column prop="department" label="部门" width="120" />
        <el-table-column label="系统角色" min-width="160">
          <template #default="{ row }">
            <el-tag v-for="r in row.roles" :key="r" size="small" style="margin-right: 4px; margin-bottom: 2px;">
              {{ roleLabel(r) }}
            </el-tag>
            <span v-if="!row.roles || !row.roles.length" style="color: #999;">无</span>
          </template>
        </el-table-column>
        <el-table-column label="审批角色" min-width="180">
          <template #default="{ row }">
            <template v-if="row.approval_roles && row.approval_roles.length">
              <el-tag 
                v-for="ar in row.approval_roles" 
                :key="ar.id"
                type="warning"
                size="small" 
                closable
                style="margin-right: 4px; margin-bottom: 2px;"
                @close="handleRemoveApprovalRole(row, ar)"
              >
                {{ ar.name }}（{{ ar.level }}级）
              </el-tag>
            </template>
            <span v-else style="color: #999;">未分配</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="primary" @click="openRoleDialog(row)">系统角色</el-button>
            <el-button link type="warning" @click="openApprovalRoleDialog(row)">审批角色</el-button>
            <el-popconfirm
              title="确定要删除该用户吗？"
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

    <!-- 新建用户 -->
    <el-dialog v-model="createDialogVisible" title="新建用户" width="480px" destroy-on-close>
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="createForm.real_name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="部门" prop="department">
          <el-input v-model="createForm.department" placeholder="请输入部门" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="createForm.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>

    <!-- 编辑用户 -->
    <el-dialog v-model="editDialogVisible" title="编辑用户" width="480px" destroy-on-close>
      <el-form :model="editForm" :rules="editRules" ref="editFormRef" label-width="80px">
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="editForm.real_name" />
        </el-form-item>
        <el-form-item label="部门" prop="department">
          <el-input v-model="editForm.department" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="editForm.is_active" active-text="正常" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleEdit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 分配系统角色 -->
    <el-dialog v-model="roleDialogVisible" title="分配系统角色" width="480px" destroy-on-close>
      <p style="margin-bottom: 12px; color: #666;">
        用户：<strong>{{ roleTarget.real_name || roleTarget.username }}</strong>
      </p>
      <el-checkbox-group v-model="selectedRoles" v-loading="rolesLoading">
        <el-checkbox 
          v-for="role in allRoles" 
          :key="role.name" 
          :value="role.name"
          style="display: block; margin-bottom: 10px;"
        >
          {{ role.name }}
          <span v-if="role.description" style="color: #999; margin-left: 8px;">
            ({{ role.description }})
          </span>
        </el-checkbox>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleAssignRoles">确定</el-button>
      </template>
    </el-dialog>

    <!-- 指派审批角色 -->
    <el-dialog v-model="approvalRoleDialogVisible" title="指派审批角色" width="480px" destroy-on-close>
      <p style="margin-bottom: 12px; color: #666;">
        为用户 <strong>{{ approvalRoleTarget.real_name || approvalRoleTarget.username }}</strong> 添加审批角色
      </p>
      <div v-if="approvalRoleTarget.approval_roles && approvalRoleTarget.approval_roles.length" style="margin-bottom: 16px;">
        <span style="color: #606266; font-size: 13px;">当前审批角色：</span>
        <el-tag 
          v-for="ar in approvalRoleTarget.approval_roles" 
          :key="ar.id" 
          type="warning" 
          size="small" 
          style="margin-right: 4px;"
        >
          {{ ar.name }}
        </el-tag>
      </div>
      <el-select
        v-model="selectedApprovalRoleId"
        placeholder="选择要添加的审批角色"
        style="width: 100%;"
        v-loading="approvalRolesLoading"
      >
        <el-option
          v-for="role in availableApprovalRoles"
          :key="role.id"
          :label="`${role.name}（等级 ${role.level}）`"
          :value="role.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="approvalRoleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleAssignApprovalRole">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  getUsers, createUser, updateUser, deleteUser,
  assignRoles, getRoles,
  getApprovalRoles, assignApprovalRole, removeUserApprovalRole 
} from '@/api/user'

const loading = ref(false)
const submitLoading = ref(false)
const rolesLoading = ref(false)
const approvalRolesLoading = ref(false)
const users = ref([])

const ROLE_LABELS = {
  SYSTEM_ADMIN: '系统管理员',
  USER: '普通用户',
  NUMBER_ADMIN: '文号管理员',
  APPROVER: '审批人员',
}
const roleLabel = (name) => ROLE_LABELS[name] || name

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const loadUsers = async () => {
  loading.value = true
  try {
    users.value = await getUsers()
  } catch (error) {
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

// ===== 新建用户 =====
const createDialogVisible = ref(false)
const createFormRef = ref(null)
const createForm = ref({ username: '', real_name: '', department: '', password: '' })
const createRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ]
}

const openCreateDialog = () => {
  createForm.value = { username: '', real_name: '', department: '', password: '' }
  createDialogVisible.value = true
}

const handleCreate = async () => {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  submitLoading.value = true
  try {
    await createUser(createForm.value)
    ElMessage.success('用户创建成功')
    createDialogVisible.value = false
    loadUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '创建失败')
  } finally {
    submitLoading.value = false
  }
}

// ===== 编辑用户 =====
const editDialogVisible = ref(false)
const editFormRef = ref(null)
const editUserId = ref(null)
const editForm = ref({ real_name: '', department: '', is_active: true })
const editRules = {
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }]
}

const openEditDialog = (row) => {
  editUserId.value = row.id
  editForm.value = {
    real_name: row.real_name,
    department: row.department || '',
    is_active: row.is_active
  }
  editDialogVisible.value = true
}

const handleEdit = async () => {
  const valid = await editFormRef.value?.validate().catch(() => false)
  if (!valid) return
  submitLoading.value = true
  try {
    await updateUser(editUserId.value, editForm.value)
    ElMessage.success('用户更新成功')
    editDialogVisible.value = false
    loadUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '更新失败')
  } finally {
    submitLoading.value = false
  }
}

// ===== 系统角色 =====
const roleDialogVisible = ref(false)
const roleTarget = ref({})
const selectedRoles = ref([])
const allRoles = ref([])

const openRoleDialog = async (row) => {
  roleTarget.value = row
  selectedRoles.value = [...(row.roles || [])]
  roleDialogVisible.value = true
  rolesLoading.value = true
  try {
    allRoles.value = await getRoles()
  } catch (error) {
    ElMessage.error('获取角色列表失败')
  } finally {
    rolesLoading.value = false
  }
}

const handleAssignRoles = async () => {
  submitLoading.value = true
  try {
    await assignRoles(roleTarget.value.id, selectedRoles.value)
    ElMessage.success('角色分配成功')
    roleDialogVisible.value = false
    loadUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '角色分配失败')
  } finally {
    submitLoading.value = false
  }
}

// ===== 审批角色 =====
const approvalRoleDialogVisible = ref(false)
const approvalRoleTarget = ref({})
const selectedApprovalRoleId = ref('')
const allApprovalRoles = ref([])

const availableApprovalRoles = computed(() => {
  const existingIds = (approvalRoleTarget.value.approval_roles || []).map(r => r.id)
  return allApprovalRoles.value.filter(r => !existingIds.includes(r.id))
})

const openApprovalRoleDialog = async (row) => {
  approvalRoleTarget.value = row
  selectedApprovalRoleId.value = ''
  approvalRoleDialogVisible.value = true
  approvalRolesLoading.value = true
  try {
    allApprovalRoles.value = await getApprovalRoles()
  } catch (error) {
    ElMessage.error('获取审批角色失败')
  } finally {
    approvalRolesLoading.value = false
  }
}

const handleAssignApprovalRole = async () => {
  if (!selectedApprovalRoleId.value) {
    ElMessage.warning('请选择审批角色')
    return
  }
  submitLoading.value = true
  try {
    await assignApprovalRole(approvalRoleTarget.value.id, selectedApprovalRoleId.value)
    ElMessage.success('审批角色指派成功')
    approvalRoleDialogVisible.value = false
    loadUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '指派失败')
  } finally {
    submitLoading.value = false
  }
}

const handleRemoveApprovalRole = async (user, approvalRole) => {
  try {
    await removeUserApprovalRole(user.id, approvalRole.id)
    ElMessage.success(`已移除 ${approvalRole.name}`)
    loadUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '移除失败')
  }
}

// ===== 删除用户 =====
const handleDelete = async (row) => {
  try {
    await deleteUser(row.id)
    ElMessage.success('用户删除成功')
    loadUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  }
}

onMounted(loadUsers)
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
