<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <el-statistic title="我的文档" :value="statistics.myDocuments">
            <template #suffix>
              <el-icon style="vertical-align: -0.125em"><Document /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <el-statistic title="校对任务" :value="statistics.proofreadingTasks">
            <template #suffix>
              <el-icon style="vertical-align: -0.125em"><View /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <el-statistic title="审批任务" :value="statistics.approvalTasks">
            <template #suffix>
              <el-icon style="vertical-align: -0.125em"><CircleCheck /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <el-statistic title="已完成" :value="statistics.completed">
            <template #suffix>
              <el-icon style="vertical-align: -0.125em"><CircleCheckFilled /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <h3>欢迎回来</h3>
            </div>
          </template>
          <p>欢迎来到公文文件号管理系统</p>
          <p>您是：<strong>{{ userInfo?.real_name }}</strong></p>
          <p>所属部门：<strong>{{ userInfo?.department }}</strong></p>
          <p>当前角色：<el-tag v-for="role in userInfo?.roles" :key="role">{{ role }}</el-tag></p>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <h3>快速操作</h3>
            </div>
          </template>
          <el-space direction="vertical" style="width: 100%">
            <el-button type="primary" @click="$router.push('/documents')" icon="Plus">
              创建新文档
            </el-button>
            <el-button @click="$router.push('/proofreading')" icon="View">
              查看校对任务
            </el-button>
            <el-button @click="$router.push('/approval')" icon="CircleCheck">
              查看审批任务
            </el-button>
          </el-space>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()

const userInfo = computed(() => userStore.userInfo)

const statistics = ref({
  myDocuments: 0,
  proofreadingTasks: 0,
  approvalTasks: 0,
  completed: 0
})

onMounted(() => {
  // TODO: 加载统计数据
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.stat-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

.stat-card :deep(.el-statistic__head) {
  color: #fff;
}

.stat-card :deep(.el-statistic__content) {
  color: #fff;
}

.stat-card :deep(.el-statistic__number) {
  color: #fff;
  font-size: 32px;
  font-weight: 700;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}
</style>
