/**
 * AntFlow API 适配层
 * 将 AntFlow 的 API 调用桥接到我们的后端
 */
import { getApprovalRoles } from '@/api/user'
import { getUsers } from '@/api/user'

// AntFlow 需要的 getEmployees 接口 → 映射到我们的 getUsers
// selectUserDialog.vue 期望: { data: [{userId, userName, email, status}], total }
export const getEmployees = async (params) => {
    const users = await getUsers(params?.userName ? { search: params.userName } : undefined)
    // getUsers 返回的是数组
    const list = Array.isArray(users) ? users : (users?.data || [])
    return {
        data: list.map(u => ({
            userId: u.id,
            userName: u.real_name || u.username,
            email: u.email || '',
            status: u.is_active !== false ? '0' : '1'
        })),
        total: list.length
    }
}

// AntFlow 需要的 getRoles 接口 → 映射到我们的 getApprovalRoles
// selectRoleDialog.vue 期望: { data: [{roleId, roleName, description, status}], total }
export const getRoles = async () => {
    const roles = await getApprovalRoles()
    const list = Array.isArray(roles) ? roles : (roles?.data || [])
    return {
        data: list.map(r => ({
            roleId: r.id,
            roleName: r.name,
            description: r.description || `等级 ${r.level}`,
            status: '0'
        })),
        total: list.length
    }
}

// AntFlow 需要的 getConditions 接口 → 暂时返回空
export const getConditions = async () => {
    return { data: [] }
}

// AntFlow 需要的 setWorkFlowData 接口 → 我们先返回 mock
export const setWorkFlowData = async (data) => {
    console.log('AntFlow workflow data:', JSON.stringify(data))
    return { code: 200 }
}
