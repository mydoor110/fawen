import request from '@/utils/request'

// 获取编号池
export const getNumberPools = () => {
  return request({
    url: '/numbers/pools',
    method: 'GET'
  })
}

// 获取编号记录
export const getNumberRecords = (params) => {
  return request({
    url: '/numbers/records',
    method: 'GET',
    params
  })
}

// 分配编号
export const allocateNumber = (documentId) => {
  return request({
    url: '/numbers/allocate',
    method: 'POST',
    data: { document_id: documentId }
  })
}

// 获取回收池
export const getRecyclePool = () => {
  return request({
    url: '/numbers/recycle-pool',
    method: 'GET'
  })
}

// 手动调整编号
export const adjustNumber = (recordId, data) => {
  return request({
    url: `/numbers/records/${recordId}/adjust`,
    method: 'POST',
    data
  })
}
