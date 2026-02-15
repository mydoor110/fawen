import request from '@/utils/request'

// 获取用户列表
export const getUsers = (params) => {
  return request({
    url: '/admin/users',
    method: 'GET',
    params
  })
}

// 创建用户
export const createUser = (data) => {
  return request({
    url: '/admin/users',
    method: 'POST',
    data
  })
}

// 获取用户详情
export const getUser = (id) => {
  return request({
    url: `/admin/users/${id}`,
    method: 'GET'
  })
}

// 更新用户
export const updateUser = (id, data) => {
  return request({
    url: `/admin/users/${id}`,
    method: 'PUT',
    data
  })
}

// 删除用户
export const deleteUser = (id) => {
  return request({
    url: `/admin/users/${id}`,
    method: 'DELETE'
  })
}

// 分配角色
export const assignRoles = (userId, roleNames) => {
  return request({
    url: `/admin/users/${userId}/roles`,
    method: 'POST',
    data: { role_names: roleNames }
  })
}

// 获取角色列表
export const getRoles = () => {
  return request({
    url: '/admin/roles',
    method: 'GET'
  })
}

// 获取审批角色
export const getApprovalRoles = () => {
  return request({
    url: '/admin/approval-roles',
    method: 'GET'
  })
}

// 指派审批角色
export const assignApprovalRole = (userId, approvalRoleId) => {
  return request({
    url: `/admin/approval-roles/${userId}`,
    method: 'POST',
    params: { approval_role_id: approvalRoleId }
  })
}

// 移除用户审批角色
export const removeUserApprovalRole = (userId, approvalRoleId) => {
  return request({
    url: `/admin/users/${userId}/approval-roles/${approvalRoleId}`,
    method: 'DELETE'
  })
}

// ===== 审批角色 CRUD =====
export const createApprovalRole = (data) => {
  return request({ url: '/admin/approval-roles', method: 'POST', data })
}

export const updateApprovalRole = (roleId, data) => {
  return request({ url: `/admin/approval-roles/${roleId}`, method: 'PUT', data })
}

export const deleteApprovalRole = (roleId) => {
  return request({ url: `/admin/approval-roles/${roleId}`, method: 'DELETE' })
}

// ===== 审计日志 =====
export const getAuditLogs = (params) => {
  return request({ url: '/admin/audit-logs', method: 'GET', params })
}

// ===== 系统配置 =====
export const getSystemConfigs = () => {
  return request({ url: '/admin/config', method: 'GET' })
}

export const updateSystemConfig = (data) => {
  return request({ url: '/admin/config', method: 'POST', data })
}

export const deleteSystemConfig = (configKey) => {
  return request({ url: `/admin/config/${configKey}`, method: 'DELETE' })
}

// ===== 编号池管理 =====
export const getAdminNumberPools = () => {
  return request({ url: '/admin/number-pools', method: 'GET' })
}

export const createNumberPool = (data) => {
  return request({ url: '/admin/number-pools', method: 'POST', data })
}

export const updateNumberPool = (poolId, data) => {
  return request({ url: `/admin/number-pools/${poolId}`, method: 'PUT', data })
}

export const deleteNumberPool = (poolId) => {
  return request({ url: `/admin/number-pools/${poolId}`, method: 'DELETE' })
}
