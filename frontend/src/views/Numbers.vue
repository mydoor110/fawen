<template>
  <div class="numbers-page">
    <el-card>
      <template #header>
        <h3>编号管理</h3>
      </template>
      
      <el-tabs v-model="activeTab">
        <el-tab-pane label="编号池" name="pools">
          <el-table :data="pools" v-loading="loading" border>
            <el-table-column prop="year" label="年份" width="100" />
            <el-table-column prop="category" label="类别" width="120" />
            <el-table-column prop="prefix" label="前缀" width="100" />
            <el-table-column prop="start_number" label="起始号" width="100" />
            <el-table-column prop="current_number" label="当前号" width="100" />
            <el-table-column prop="end_number" label="结束号" width="100" />
          </el-table>
        </el-tab-pane>
        
        <el-tab-pane label="编号记录" name="records">
          <el-table :data="records" v-loading="loading" border>
            <el-table-column prop="official_number" label="正式编号" width="180" />
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="分配时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.allocated_at) }}
              </template>
            </el-table-column>
            <el-table-column prop="manual_adjustment" label="手动调整" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.manual_adjustment" type="warning">是</el-tag>
                <span v-else>否</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        
        <el-tab-pane label="回收池" name="recycle">
          <el-table :data="recyclePool" v-loading="loading" border>
            <el-table-column prop="official_number" label="正式编号" width="180" />
            <el-table-column prop="reason" label="回收原因" />
            <el-table-column label="回收时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.recycled_at) }}
              </template>
            </el-table-column>
            <el-table-column prop="is_available" label="可用" width="100">
              <template #default="{ row }">
                <el-tag :type="row.is_available ? 'success' : 'info'">
                  {{ row.is_available ? '可用' : '已用' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getNumberPools, getNumberRecords, getRecyclePool } from '@/api/number'

const activeTab = ref('pools')
const loading = ref(false)
const pools = ref([])
const records = ref([])
const recyclePool = ref([])

const loadData = async () => {
  loading.value = true
  try {
    const [poolsData, recordsData, recycleData] = await Promise.all([
      getNumberPools(),
      getNumberRecords(),
      getRecyclePool()
    ])
    pools.value = poolsData
    records.value = recordsData
    recyclePool.value = recycleData
  } catch (error) {
    console.error('加载编号数据失败:', error)
  } finally {
    loading.value = false
  }
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

const getStatusType = (status) => {
  const types = {
    reserved: 'info',
    allocated: 'success',
    recycled: 'warning'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    reserved: '已预留',
    allocated: '已分配',
    recycled: '已回收'
  }
  return texts[status] || status
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.numbers-page {
  padding: 20px;
}

.numbers-page h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}
</style>
