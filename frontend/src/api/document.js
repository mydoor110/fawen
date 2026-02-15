import request from '@/utils/request'

// 获取文档列表
export const getDocuments = (params) => {
  return request({ url: '/documents', method: 'GET', params })
}

// 创建文档
export const createDocument = (data) => {
  return request({ url: '/documents', method: 'POST', data })
}

// 获取文档详情
export const getDocument = (id) => {
  return request({ url: `/documents/${id}`, method: 'GET' })
}

// 更新文档
export const updateDocument = (id, data) => {
  return request({ url: `/documents/${id}`, method: 'PUT', data })
}

// 删除文档
export const deleteDocument = (id) => {
  return request({ url: `/documents/${id}`, method: 'DELETE' })
}

// 上传文档
export const uploadDocument = (id, file) => {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: `/documents/${id}/upload`,
    method: 'POST',
    headers: { 'Content-Type': 'multipart/form-data' },
    data: formData
  })
}

// 提交校对
export const submitProofreading = (id, proofreaderIds) => {
  return request({
    url: `/documents/${id}/submit-proofreading`,
    method: 'POST',
    data: { proofreader_ids: proofreaderIds }
  })
}

// 提交审批
export const submitApproval = (id, flowId) => {
  return request({
    url: `/documents/${id}/submit-approval`,
    method: 'POST',
    data: { flow_id: flowId }
  })
}

// 获取文档校对任务
export const getDocumentProofreadingTasks = (id) => {
  return request({ url: `/documents/${id}/proofreading-tasks`, method: 'GET' })
}

// 获取文档审批任务
export const getDocumentApprovalTasks = (id) => {
  return request({ url: `/documents/${id}/approval-tasks`, method: 'GET' })
}

// 强制解锁
export const forceUnlockDocument = (id, reason) => {
  return request({
    url: `/documents/${id}/force-unlock`,
    method: 'POST',
    params: { reason }
  })
}

// 获取文档锁定详情
export const getDocumentLocks = (id) => {
  return request({ url: `/documents/${id}/locks`, method: 'GET' })
}

// 重新提交（驳回后回到草稿）
export const resubmitDocument = (id) => {
  return request({ url: `/documents/${id}/resubmit`, method: 'POST' })
}

// 发起销毁申请
export const requestDestroy = (id, reason) => {
  return request({
    url: `/destroy/documents/${id}/request`,
    method: 'POST',
    data: { reason }
  })
}

// 审批销毁
export const approveDestroy = (id, data) => {
  return request({
    url: `/destroy/documents/${id}/approve`,
    method: 'POST',
    data
  })
}
