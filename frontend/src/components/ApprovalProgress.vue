<template>
  <div class="approval-progress">
    <div class="progress-header">
      <h3>审批进度</h3>
      <el-tag :type="getStatusType(document.status)">
        {{ getStatusText(document.status) }}
      </el-tag>
    </div>

    <el-timeline class="progress-timeline">
      <!-- 创建文档 -->
      <el-timeline-item
        timestamp="文档创建"
        :icon="Document"
        color="#67c23a"
      >
        <div class="timeline-content">
          <p><strong>创建人：</strong>{{ document.creator_name || '未知' }}</p>
          <p><strong>创建时间：</strong>{{ formatTime(document.created_at) }}</p>
        </div>
      </el-timeline-item>

      <!-- 校对阶段 -->
      <el-timeline-item
        v-if="proofreadingTasks && proofreadingTasks.length > 0"
        timestamp="校对阶段"
        :icon="Edit"
        :color="getProofreadingColor()"
      >
        <div class="task-list">
          <div
            v-for="task in proofreadingTasks"
            :key="task.id"
            class="task-item"
          >
            <el-tag :type="getTaskStatusType(task.status)" size="small">
              {{ getTaskStatusText(task.status) }}
            </el-tag>
            <span class="task-user">{{ task.proofreader_name }}</span>
            <span v-if="task.comment" class="task-comment">{{ task.comment }}</span>
            <span v-if="task.completed_at" class="task-time">
              {{ formatTime(task.completed_at) }}
            </span>
          </div>
        </div>
      </el-timeline-item>

      <!-- 审批阶段 -->
      <template v-if="approvalNodes && approvalNodes.length > 0">
        <el-timeline-item
          v-for="(node, index) in approvalNodes"
          :key="node.id"
          :timestamp="`审批节点 ${index + 1}: ${node.role_name}`"
          :icon="Checked"
          :color="getNodeColor(node)"
        >
          <div class="task-list">
            <div
              v-for="task in getNodeTasks(node.id)"
              :key="task.id"
              class="task-item"
            >
              <el-tag :type="getTaskStatusType(task.status)" size="small">
                {{ getTaskStatusText(task.status) }}
              </el-tag>
              <span class="task-user">{{ task.approver_name }}</span>
              <span v-if="task.comment" class="task-comment">{{ task.comment }}</span>
              <span v-if="task.completed_at" class="task-time">
                {{ formatTime(task.completed_at) }}
              </span>
            </div>
            <div v-if="getNodeTasks(node.id).length === 0" class="task-item pending">
              <el-icon><Clock /></el-icon>
              <span>等待审批</span>
            </div>
          </div>
        </el-timeline-item>
      </template>

      <!-- 发号盖章 -->
      <el-timeline-item
        v-if="document.status === 'approved' && document.official_number"
        timestamp="发号盖章"
        :icon="Stamp"
        color="#67c23a"
      >
        <div class="timeline-content">
          <p><strong>文件号：</strong>{{ document.official_number }}</p>
          <p><strong>完成时间：</strong>{{ formatTime(document.approved_at) }}</p>
        </div>
      </el-timeline-item>
    </el-timeline>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Document, Edit, Checked, Clock, Stamp } from '@element-plus/icons-vue'
import { getDocumentProofreadingTasks, getDocumentApprovalTasks } from '@/api/document'
import { listFlowNodes } from '@/api/approval'

const props = defineProps({
  document: {
    type: Object,
    required: true
  }
})

const proofreadingTasks = ref([])
const approvalTasks = ref([])
const approvalNodes = ref([])

// 加载数据
onMounted(async () => {
  try {
    // 加载校对任务
    proofreadingTasks.value = await getDocumentProofreadingTasks(props.document.id)
    
    // 加载审批任务
    approvalTasks.value = await getDocumentApprovalTasks(props.document.id)
    
    // 如果有审批流程，加载流程节点
    if (props.document.approval_flow_id) {
      approvalNodes.value = await listFlowNodes(props.document.approval_flow_id)
    }
  } catch (error) {
    console.error('加载审批进度失败:', error)
  }
})

// 获取节点的任务
const getNodeTasks = (nodeId) => {
  return approvalTasks.value.filter(task => task.node_id === nodeId)
}

// 获取节点颜色
const getNodeColor = (node) => {
  const tasks = getNodeTasks(node.id)
  if (tasks.length === 0) return '#909399' // 灰色 - 未开始
  
  const allCompleted = tasks.every(t => t.status !== 'pending')
  const anyApproved = tasks.some(t => t.status === 'approved')
  const anyRejected = tasks.some(t => t.status === 'rejected')
  
  if (anyRejected) return '#f56c6c' // 红色 - 驳回
  if (anyApproved && allCompleted) return '#67c23a' // 绿色 - 完成
  if (anyApproved) return '#e6a23c' // 橙色 - 进行中
  
  return '#909399' // 灰色 - 等待中
}

// 获取校对阶段颜色
const getProofreadingColor = () => {
  if (!proofreadingTasks.value || proofreadingTasks.value.length === 0) {
    return '#909399'
  }
  
  const allCompleted = proofreadingTasks.value.every(t => t.status !== 'pending')
  const anyFailed = proofreadingTasks.value.some(t => t.status === 'failed')
  const allPassed = proofreadingTasks.value.every(t => t.status === 'passed')
  
  if (anyFailed) return '#f56c6c'
  if (allPassed) return '#67c23a'
  if (allCompleted) return '#e6a23c'
  
  return '#409eff'
}

// 获取状态颜色类型
const getStatusType = (status) => {
  const types = {
    draft: 'info',
    proofreading: 'warning',
    approval: 'primary',
    approved: 'success',
    rejected: 'danger',
    destroyed: 'info'
  }
  return types[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const texts = {
    draft: '草稿',
    proofreading: '校对中',
    approval: '审批中',
    approved: '已通过',
    rejected: '已驳回',
    destroyed: '已销毁'
  }
  return texts[status] || status
}

// 获取任务状态类型
const getTaskStatusType = (status) => {
  const types = {
    pending: 'info',
    passed: 'success',
    failed: 'danger',
    approved: 'success',
    rejected: 'danger',
    skipped: 'info'
  }
  return types[status] || 'info'
}

// 获取任务状态文本
const getTaskStatusText = (status) => {
  const texts = {
    pending: '待处理',
    passed: '通过',
    failed: '未通过',
    approved: '已批准',
    rejected: '已驳回',
    skipped: '已跳过'
  }
  return texts[status] || status
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.approval-progress {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}

.progress-header h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.progress-timeline {
  padding-left: 10px;
}

.timeline-content {
  padding: 10px 0;
}

.timeline-content p {
  margin: 5px 0;
  color: #606266;
  font-size: 14px;
}

.task-list {
  padding: 10px 0;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  margin: 5px 0;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 14px;
}

.task-item.pending {
  color: #909399;
}

.task-user {
  font-weight: 500;
  color: #303133;
}

.task-comment {
  flex: 1;
  color: #606266;
  font-style: italic;
}

.task-time {
  color: #909399;
  font-size: 12px;
}
</style>
