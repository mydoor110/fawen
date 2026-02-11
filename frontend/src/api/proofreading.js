import request from '@/utils/request'

// 获取我的校对任务
export const getMyProofreadingTasks = () => {
  return request({
    url: '/proofreading/tasks',
    method: 'GET'
  })
}

// 获取文档的校对任务
export const getDocumentProofreadingTasks = (documentId) => {
  return request({
    url: `/proofreading/document/${documentId}/tasks`,
    method: 'GET'
  })
}

// 完成校对
export const completeProofreading = (taskId, data) => {
  return request({
    url: `/proofreading/task/${taskId}/complete`,
    method: 'POST',
    data
  })
}
