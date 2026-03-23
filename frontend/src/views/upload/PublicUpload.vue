<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import { publicUpload } from '@/api/upload'
import type { UploadResult } from '@/api/upload'

const loading = ref(false)
const fileList = ref<File[]>([])
const lastResult = ref<UploadResult | null>(null)

function onFileChange(files: FileList | null) {
  fileList.value = files ? Array.from(files) : []
}

async function handleUpload() {
  if (fileList.value.length === 0) {
    ElMessage.warning('请选择文件')
    return
  }
  const file = fileList.value[0]
  loading.value = true
  lastResult.value = null
  try {
    const data: any = await publicUpload(file)
    if (data?.ok) {
      lastResult.value = data
      ElMessage.success(`上传成功：${data.filename}`)
    } else {
      ElMessage.error(data?.detail || '上传失败')
    }
  } catch {
    // error handled by request interceptor
  } finally {
    loading.value = false
  }
}

function clearAll() {
  fileList.value = []
  lastResult.value = null
}
</script>

<template>
  <div class="upload-page">
    <div class="upload-bg" />
    <div class="upload-card">
      <div class="card-header">
        <h2>匿名举报 / 反馈材料上传</h2>
        <p>如发现平台违规问题，可匿名上传相关材料，我们将核实处理</p>
      </div>

      <div class="upload-form">
        <div class="file-input-wrap">
          <input
            type="file"
            id="fileInput"
            class="file-input"
            @change="(e: Event) => onFileChange((e.target as HTMLInputElement)?.files)"
          />
          <label for="fileInput" class="file-label">
            <el-icon :size="24"><Upload /></el-icon>
            <span>选择文件</span>
          </label>
        </div>
        <p v-if="fileList.length" class="selected-file">{{ fileList[0]?.name }}（{{ ((fileList[0]?.size || 0) / 1024).toFixed(1) }} KB）</p>

        <div class="actions">
          <el-button type="primary" :loading="loading" @click="handleUpload">上传</el-button>
          <el-button @click="clearAll">清空</el-button>
        </div>
      </div>

      <div v-if="lastResult" class="result-box">
        <h4>上传结果</h4>
        <p>文件名：{{ lastResult.filename }}</p>
        <p>保存为：{{ lastResult.saved_as }}</p>
        <p>大小：{{ lastResult.size }} 字节</p>
        <a v-if="lastResult.url" :href="lastResult.url" target="_blank" rel="noopener">访问文件</a>
      </div>

      <p class="hint">无需登录即可上传 · 支持任意格式</p>
    </div>

    <router-link to="/login" class="back-link">返回登录</router-link>
  </div>
</template>

<style lang="scss" scoped>
.upload-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  position: relative;
}

.upload-bg {
  position: fixed;
  inset: 0;
  background: linear-gradient(135deg, #fafaf9 0%, #f0f4f8 100%);
  z-index: 0;
}

.upload-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  padding: 32px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
}

.card-header {
  text-align: center;
  margin-bottom: 28px;

  h2 {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 8px;
  }

  p {
    font-size: 13px;
    color: var(--text-muted);
    margin: 0;
  }
}

.file-input-wrap {
  position: relative;
}

.file-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  overflow: hidden;
}

.file-label {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px 24px;
  border: 2px dashed var(--border-color, #dcdfe6);
  border-radius: 12px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;

  &:hover {
    border-color: var(--primary);
    color: var(--primary);
  }
}

.selected-file {
  font-size: 13px;
  color: var(--text-muted);
  margin: 12px 0 0;
}

.actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.result-box {
  margin-top: 24px;
  padding: 16px;
  background: var(--primary-muted, #f0f4ff);
  border-radius: 10px;

  h4 {
    margin: 0 0 8px;
    font-size: 14px;
  }

  p {
    margin: 4px 0;
    font-size: 13px;
  }

  a {
    display: inline-block;
    margin-top: 8px;
    color: var(--primary);
    font-size: 13px;
  }
}

.hint {
  margin-top: 20px;
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
}

.back-link {
  position: relative;
  z-index: 1;
  margin-top: 20px;
  font-size: 14px;
  color: var(--primary);
}
</style>
