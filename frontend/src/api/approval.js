import request from '@/utils/request'

// 获取我的审批任务
export const getMyApprovalTasks = () => {
  return request({
    url: '/approval/tasks',
    method: 'GET'
  })
}

// 获取文档的审批任务
export const getDocumentApprovalTasks = (documentId) => {
  return request({
    url: `/approval/document/${documentId}/tasks`,
    method: 'GET'
  })
}

// 审批通过
export const approveTask = (taskId, comment) => {
  return request({
    url: `/approval/task/${taskId}/approve`,
    method: 'POST',
    data: { comment }
  })
}

// 审批驳回
export const rejectTask = (taskId, comment) => {
  return request({
    url: `/approval/task/${taskId}/reject`,
    method: 'POST',
    data: { comment }
  })
}

// ===== 审批流程管理 =====
export const getApprovalFlows = () => {
  return request({ url: '/approval/flows', method: 'GET' })
}

export const createApprovalFlow = (data) => {
  return request({ url: '/approval/flows', method: 'POST', data })
}

export const updateApprovalFlow = (flowId, data) => {
  return request({ url: `/approval/flows/${flowId}`, method: 'PUT', data })
}

export const deleteApprovalFlow = (flowId) => {
  return request({ url: `/approval/flows/${flowId}`, method: 'DELETE' })
}

// ===== 审批节点管理 =====
export const getFlowNodes = (flowId) => {
  return request({ url: `/approval/flows/${flowId}/nodes`, method: 'GET' })
}

// 别名导出（供其他组件使用）
export const listFlowNodes = getFlowNodes

export const createFlowNode = (flowId, data) => {
  return request({ url: `/approval/flows/${flowId}/nodes`, method: 'POST', data })
}

export const updateFlowNode = (flowId, nodeId, data) => {
  return request({ url: `/approval/flows/${flowId}/nodes/${nodeId}`, method: 'PUT', data })
}

export const deleteFlowNode = (flowId, nodeId) => {
  return request({ url: `/approval/flows/${flowId}/nodes/${nodeId}`, method: 'DELETE' })
}
