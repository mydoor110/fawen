<template>
  <div class="audit-logs">
    <h2>审计日志</h2>
    <p class="page-desc">系统操作审计记录，仅系统管理员可查看</p>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <select v-model="filterAction" @change="loadLogs">
        <option value="">全部操作类型</option>
        <option value="number.adjust">编号调整</option>
        <option value="number.lock">编号锁定</option>
        <option value="number.unlock">编号解锁</option>
        <option value="number.force_unlock">强制解锁</option>
        <option value="number.allocate">编号分配</option>
        <option value="number.recycle">编号回收</option>
        <option value="approval.approve">审批通过</option>
        <option value="approval.reject">审批驳回</option>
        <option value="proofread.submit">校对提交</option>
        <option value="proofread.complete">校对完成</option>
        <option value="document.destroy">文档销毁</option>
        <option value="permission.denied">权限拒绝</option>
      </select>

      <select v-model="filterResourceType" @change="loadLogs">
        <option value="">全部资源类型</option>
        <option value="Document">文档</option>
        <option value="NumberRecord">编号记录</option>
        <option value="ApprovalTask">审批任务</option>
        <option value="ProofreadingTask">校对任务</option>
        <option value="Permission">权限</option>
      </select>

      <button class="btn btn-secondary" @click="resetFilters">重置筛选</button>
    </div>

    <!-- 日志表格 -->
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>操作类型</th>
            <th>资源类型</th>
            <th>资源ID</th>
            <th>操作人</th>
            <th>IP地址</th>
            <th>详情</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id">
            <td>{{ formatTime(log.created_at) }}</td>
            <td><span class="action-tag" :class="getActionClass(log.action)">{{ getActionLabel(log.action) }}</span></td>
            <td>{{ log.resource_type }}</td>
            <td class="mono">{{ log.resource_id?.substring(0, 8) }}...</td>
            <td>{{ log.user_id?.substring(0, 8) }}...</td>
            <td>{{ log.ip_address || '-' }}</td>
            <td>
              <button class="btn btn-sm" @click="showDetails(log)">查看</button>
            </td>
          </tr>
          <tr v-if="logs.length === 0">
            <td colspan="7" class="empty">暂无审计日志</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div class="pagination" v-if="total > pageSize">
      <button :disabled="currentPage <= 1" @click="changePage(currentPage - 1)">上一页</button>
      <span>第 {{ currentPage }} / {{ totalPages }} 页 (共 {{ total }} 条)</span>
      <button :disabled="currentPage >= totalPages" @click="changePage(currentPage + 1)">下一页</button>
    </div>

    <!-- 详情弹窗 -->
    <div class="modal-overlay" v-if="detailLog" @click.self="detailLog = null">
      <div class="modal-content">
        <h3>日志详情</h3>
        <pre>{{ JSON.stringify(detailLog.details, null, 2) }}</pre>
        <button class="btn" @click="detailLog = null">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { getAuditLogs } from '@/api/user'

const logs = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 50
const filterAction = ref('')
const filterResourceType = ref('')
const detailLog = ref(null)

const totalPages = computed(() => Math.ceil(total.value / pageSize))

const loadLogs = async () => {
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize,
      limit: pageSize
    }
    if (filterAction.value) params.action = filterAction.value
    if (filterResourceType.value) params.resource_type = filterResourceType.value

    const res = await getAuditLogs(params)
    logs.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    console.error('加载审计日志失败', e)
  }
}

const changePage = (page) => {
  currentPage.value = page
  loadLogs()
}

const resetFilters = () => {
  filterAction.value = ''
  filterResourceType.value = ''
  currentPage.value = 1
  loadLogs()
}

const showDetails = (log) => {
  detailLog.value = log
}

const formatTime = (iso) => {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

const ACTION_LABELS = {
  'number.adjust': '编号调整',
  'number.lock': '编号锁定',
  'number.unlock': '编号解锁',
  'number.force_unlock': '强制解锁',
  'number.allocate': '编号分配',
  'number.recycle': '编号回收',
  'approval.approve': '审批通过',
  'approval.reject': '审批驳回',
  'proofread.submit': '校对提交',
  'proofread.complete': '校对完成',
  'document.destroy': '文档销毁',
  'permission.denied': '权限拒绝',
}

const getActionLabel = (action) => ACTION_LABELS[action] || action
const getActionClass = (action) => {
  if (action.includes('reject') || action.includes('denied') || action.includes('destroy')) return 'danger'
  if (action.includes('approve') || action.includes('allocate')) return 'success'
  if (action.includes('lock')) return 'warning'
  return 'info'
}

onMounted(loadLogs)
</script>

<style scoped>
.audit-logs { padding: 20px; }
.page-desc { color: #888; margin-bottom: 16px; }

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}
.filter-bar select {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
}

.table-container { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; font-size: 14px; }
th { background: #f8f9fa; font-weight: 600; }
.mono { font-family: monospace; font-size: 12px; }
.empty { text-align: center; color: #aaa; padding: 40px; }

.action-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}
.action-tag.danger { background: #fee; color: #d00; }
.action-tag.success { background: #efe; color: #080; }
.action-tag.warning { background: #ffd; color: #880; }
.action-tag.info { background: #eef; color: #008; }

.btn { padding: 6px 14px; border: none; border-radius: 6px; cursor: pointer; background: #4a90d9; color: #fff; }
.btn-sm { padding: 3px 8px; font-size: 12px; }
.btn-secondary { background: #6c757d; color: #fff; }

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}
.pagination button { padding: 6px 14px; border: 1px solid #ddd; border-radius: 6px; background: #fff; cursor: pointer; }
.pagination button:disabled { opacity: 0.5; cursor: not-allowed; }

.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal-content {
  background: #fff; border-radius: 12px; padding: 24px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto;
}
.modal-content pre {
  background: #f8f9fa; padding: 12px; border-radius: 6px; font-size: 13px; overflow-x: auto;
}
</style>
