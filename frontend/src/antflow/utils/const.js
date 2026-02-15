/**
 * AntFlow 常量配置 - 适配公文文件号管理系统
 */

export let bgColors = ["148.6,212.3,117.1", '87, 106, 149', '121.3, 187.1, 255', '51.2, 126.4, 204', '255, 148, 62', '50, 150, 250', '50, 150, 250']

export let nodeTypeList = ["未知", "发起人", "网关", "条件", "审核人", "抄送人", "抄送人", '审核人'];

// 审批人设置类型 — 只保留我们系统支持的方式
export let setTypes = [
  { value: 1, label: '指定成员' },
  { value: 3, label: '指定审批角色' },
  { value: 5, label: '发起人自己' },
]

// 条件运算符
export let optTypes = [
  { value: '1', label: '小于' },
  { value: '2', label: '大于' },
  { value: '3', label: '小于等于' },
  { value: '4', label: '等于' },
  { value: '5', label: '大于等于' },
  { value: '6', label: '介于两个数之间' },
]

export let opt1s = [
  { value: '<', label: '<' },
  { value: '≤', label: '≤' },
]

// 公文文种选项 — 用于条件节点
export let documentTypes = [
  { key: '通知', value: '通知' },
  { key: '报告', value: '报告' },
  { key: '请示', value: '请示' },
  { key: '批复', value: '批复' },
  { key: '函', value: '函' },
  { key: '纪要', value: '纪要' },
  { key: '决定', value: '决定' },
  { key: '意见', value: '意见' },
]

export let statusColor = {
  0: 'info',
  1: 'primary',  // 提交
  2: 'primary',  // 同意
  3: 'danger',   // 拒绝
  4: 'danger',   // 撤回
  5: 'danger',   // 作废
  6: 'danger',   // 终止
  7: 'primary',
  8: 'danger',   // 打回修改
  9: 'primary',  // 加批
  99: 'success', // 处理中
  100: 'info'
};