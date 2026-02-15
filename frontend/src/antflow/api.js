/**
 * AntFlow API 适配层
 * 将 AntFlow 的 API 调用桥接到公文文件号管理系统后端
 */
import request from '@/utils/request'
import { getApprovalRoles } from '@/api/user'
import { getUsers } from '@/api/user'

// AntFlow 需要的 getEmployees 接口 → 映射到我们的 getUsers
// selectUserDialog.vue 期望: { data: [{userId, userName, email, status}], total }
export const getEmployees = async (params) => {
    const users = await getUsers(params?.userName ? { search: params.userName } : undefined)
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

// AntFlow 需要的 getRoles 接口 → 映射到我们的审批角色（ApprovalRole）
// selectRoleDialog.vue 期望: { data: [{roleId, roleName, description, status}], total }
export const getRoles = async () => {
    const roles = await getApprovalRoles()
    const list = Array.isArray(roles) ? roles : (roles?.data || [])
    return {
        data: list.map(r => ({
            roleId: r.id,
            roleName: r.name,
            description: r.description || `审批等级 ${r.level}`,
            status: '0'
        })),
        total: list.length
    }
}

// AntFlow 需要的 getConditions 接口 → 返回公文系统的条件字段
// 这些条件字段用于流程的条件分支判断
export const getConditions = async () => {
    return {
        data: [
            {
                formId: 0,
                showName: '发起人',
                type: 1,
                showType: '1',
                columnDbname: 'creator',
                columnType: 'String',
                fixedDownBoxValue: '',
            },
            {
                formId: 1,
                showName: '公文文种',
                type: 2,
                showType: '3',
                columnDbname: 'document_type',
                columnType: 'String',
                fieldTypeName: 'select',
                fixedDownBoxValue: JSON.stringify([
                    { key: '通知', value: '通知' },
                    { key: '报告', value: '报告' },
                    { key: '请示', value: '请示' },
                    { key: '批复', value: '批复' },
                    { key: '函', value: '函' },
                    { key: '纪要', value: '纪要' },
                    { key: '决定', value: '决定' },
                    { key: '意见', value: '意见' },
                ]),
            },
        ]
    }
}

// AntFlow 需要的 setWorkFlowData 接口 → 保存流程数据到后端
export const setWorkFlowData = async (data) => {
    console.log('AntFlow workflow data:', JSON.stringify(data))

    // 调用后端API保存流程
    try {
        const response = await request({
            url: '/approval/flows/from-antflow',
            method: 'POST',
            data
        })

        console.log('流程保存成功:', response)
        return { code: 200, data: response }
    } catch (error) {
        console.error('流程保存失败:', error)
        return { code: 500, message: error.message || '保存失败' }
    }
}

