<template>
  <div class="seal-management">
    <el-page-header @back="goBack" content="电子印章管理" />
    
    <el-card class="config-card" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>印章配置</span>
          <el-button v-if="sealConfig.enabled" type="primary" @click="handleUpload">
            更换印章图片
          </el-button>
        </div>
      </template>

      <el-form v-if="sealConfig" :model="sealConfig" label-width="120px">
        <el-form-item label="启用自动盖章">
          <el-switch v-model="sealConfig.enabled" @change="handleSaveConfig" />
          <span class="form-tip">审批通过后自动在文档中添加电子印章</span>
        </el-form-item>

        <template v-if="sealConfig.enabled">
          <el-form-item label="印章图片">
            <div v-if="sealConfig.image_path" class="seal-preview">
              <img :src="getSealImageUrl()" alt="印章预览" class="seal-image" />
              <div class="seal-path">{{ sealConfig.image_path }}</div>
            </div>
            <el-upload
              v-else
              class="seal-uploader"
              :action="uploadUrl"
              :headers="uploadHeaders"
              :show-file-list="false"
              :on-success="handleUploadSuccess"
              :on-error="handleUploadError"
              :before-upload="beforeUpload"
              accept="image/png,image/jpeg"
            >
              <el-button type="primary">
                <el-icon><Upload /></el-icon>
                上传印章图片
              </el-button>
              <template #tip>
                <div class="el-upload__tip">
                  只能上传 PNG 或 JPG 文件，建议使用PNG格式的透明背景图片，大小不超过2MB
                </div>
              </template>
            </el-upload>
          </el-form-item>

          <el-form-item label="印章位置">
            <el-radio-group v-model="sealConfig.position" @change="handleSaveConfig">
              <el-radio label="end">文档末尾</el-radio>
              <el-radio label="custom" disabled>自定义位置（暂不支持）</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="印章大小（英寸）">
            <el-input-number 
              v-model="sealConfig.width_inches" 
              :min="0.5" 
              :max="3" 
              :step="0.1"
              @change="handleSaveConfig"
            />
            <span class="form-tip">建议范围: 1.0 - 2.0 英寸</span>
          </el-form-item>

          <el-form-item label="预览效果">
            <div class="seal-size-preview">
              <div class="size-demo" :style="{ width: sealConfig.width_inches * 96 + 'px' }">
                <img v-if="sealConfig.image_path" :src="getSealImageUrl()" alt="印章" />
                <div v-else class="placeholder">印章预览</div>
              </div>
              <div class="size-info">
                实际大小约: {{ Math.round(sealConfig.width_inches * 2.54 * 10) / 10 }} 厘米
              </div>
            </div>
          </el-form-item>
        </template>
      </el-form>
    </el-card>

    <!-- 上传对话框 -->
    <el-dialog v-model="uploadDialogVisible" title="上传印章图片" width="500px">
      <el-upload
        class="seal-uploader"
        drag
        :action="uploadUrl"
        :headers="uploadHeaders"
        :show-file-list="false"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        :before-upload="beforeUpload"
        accept="image/png,image/jpeg"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            只能上传 PNG 或 JPG 文件，建议使用PNG格式的透明背景图片，大小不超过2MB
          </div>
        </template>
      </el-upload>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, UploadFilled } from '@element-plus/icons-vue'
import { getSystemConfig, updateSystemConfig } from '@/api/admin'
import { uploadSealImage } from '@/api/seal'
import { useRouter } from 'vue-router'
import { getToken } from '@/utils/auth'

const router = useRouter()
const uploadDialogVisible = ref(false)

const sealConfig = reactive({
  enabled: false,
  image_path: null,
  position: 'end',
  width_inches: 1.5
})

const uploadUrl = computed(() => {
  return `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/admin/upload-seal`
})

const uploadHeaders = computed(() => {
  return {
    'Authorization': `Bearer ${getToken()}`
  }
})

// 加载配置
onMounted(async () => {
  try {
    const config = await getSystemConfig('electronic_seal')
    if (config && config.config_value) {
      Object.assign(sealConfig, config.config_value)
    }
  } catch (error) {
    console.error('加载印章配置失败:', error)
  }
})

// 保存配置
const handleSaveConfig = async () => {
  try {
    await updateSystemConfig('electronic_seal', {
      config_key: 'electronic_seal',
      config_value: { ...sealConfig },
      description: '电子印章配置'
    })
    ElMessage.success('配置已保存')
  } catch (error) {
    ElMessage.error('保存失败: ' + (error.message || '未知错误'))
  }
}

// 上传前检查
const beforeUpload = (file) => {
  const isImage = file.type === 'image/png' || file.type === 'image/jpeg'
  const isLt2M = file.size / 1024 / 1024 < 2

  if (!isImage) {
    ElMessage.error('只能上传 PNG 或 JPG 格式的图片!')
    return false
  }
  if (!isLt2M) {
    ElMessage.error('图片大小不能超过 2MB!')
    return false
  }
  return true
}

// 上传成功
const handleUploadSuccess = (response) => {
  if (response.file_path) {
    sealConfig.image_path = response.file_path
    sealConfig.enabled = true  // 上传后自动启用
    handleSaveConfig()
    ElMessage.success('印章图片上传成功')
    uploadDialogVisible.value = false
  } else {
    ElMessage.error('上传失败')
  }
}

// 上传失败
const handleUploadError = (error) => {
  console.error('上传失败:', error)
  ElMessage.error('上传失败: ' + (error.message || '未知错误'))
}

// 打开上传对话框
const handleUpload = () => {
  uploadDialogVisible.value = true
}

// 获取印章图片URL
const getSealImageUrl = () => {
  if (!sealConfig.image_path) return ''
  // 如果是相对路径，拼接Base URL
  if (sealConfig.image_path.startsWith('http')) {
    return sealConfig.image_path
  }
  return `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/static/${sealConfig.image_path}`
}

// 返回
const goBack = () => {
  router.back()
}
</script>

<style scoped>
.seal-management {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-card {
  max-width: 800px;
}

.form-tip {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.seal-preview {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.seal-image {
  max-width: 200px;
  max-height: 200px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
  background: #f5f7fa;
}

.seal-path {
  color: #606266;
  font-size: 13px;
  word-break: break-all;
}

.seal-uploader {
  width: 100%;
}

.seal-size-preview {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.size-demo {
  border: 2px dashed #dcdfe6;
  border-radius: 4px;
  padding: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #fafafa;
}

.size-demo img {
  width: 100%;
  height: auto;
}

.size-demo .placeholder {
  color: #909399;
  font-size: 14px;
}

.size-info {
  color: #606266;
  font-size: 13px;
}
</style>
