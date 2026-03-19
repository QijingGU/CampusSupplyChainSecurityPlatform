<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import type { UploadFile, UploadRawFile } from 'element-plus'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listGoods } from '@/api/goods'
import { createPurchase } from '@/api/purchase'
import type { GoodsItem } from '@/api/goods'
import request from '@/api/request'

const MAX_SIZE = 5 * 1024 * 1024  // 5MB
const ALLOW_TYPES = [
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/jpg',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]

const router = useRouter()
const goodsList = ref<GoodsItem[]>([])
const loading = ref(false)
const fileList = ref<UploadFile[]>([])
const form = reactive({
  goods_id: null as number | null,
  quantity: 1,
  apply_reason: '',
  destination: '',
  receiver_name: '',
})
const aiSuggestion = ref<string | null>(null)
const aiLoading = ref(false)

onMounted(async () => {
  try {
    const list = await listGoods()
    goodsList.value = Array.isArray(list) ? list : []
  } catch {
    goodsList.value = []
  }
})

function beforeUpload(file: UploadRawFile) {
  if (!ALLOW_TYPES.includes(file.type)) {
    ElMessage.error('仅支持 PDF、Word、JPG、PNG 格式')
    return false
  }
  if (file.size > MAX_SIZE) {
    ElMessage.error('文件不能超过 5MB')
    return false
  }
  return true
}

function handleFileChange(_file: UploadFile, files: UploadFile[]) {
  const valid = files.filter((f) => {
    const raw = f.raw
    if (!raw) return true
    if (!ALLOW_TYPES.includes(raw.type)) {
      ElMessage.error(`"${f.name}" 格式不支持，仅支持 PDF、Word、JPG、PNG`)
      return false
    }
    if (raw.size > MAX_SIZE) {
      ElMessage.error(`"${f.name}" 超过 5MB 限制`)
      return false
    }
    return true
  })
  if (valid.length !== files.length) {
    fileList.value = valid
  }
}

async function fetchAISuggestion() {
  aiLoading.value = true
  aiSuggestion.value = null
  try {
    const res = await request.post('/ai/chat', { message: '现在什么物资可能短缺？请给出补货建议。' })
    const d = (res as any)?.data || res
    aiSuggestion.value = d?.reply || ''
  } catch {
    aiSuggestion.value = '获取 AI 建议失败，请稍后重试。'
  } finally {
    aiLoading.value = false
  }
}

async function handleSubmit() {
  if (!form.goods_id) {
    ElMessage.warning('请选择物资')
    return
  }
  if (form.quantity < 1) {
    ElMessage.warning('采购数量至少为 1')
    return
  }
  loading.value = true
  try {
    await createPurchase({
      goods_id: form.goods_id,
      quantity: form.quantity,
      apply_reason: form.apply_reason,
      destination: form.destination,
      receiver_name: form.receiver_name,
    })
    ElMessage.success('采购申请已提交')
    router.push('/my-applications')
  } catch {
    // error handled by request interceptor
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>采购申请</h2>
      <el-button @click="router.back()">返回</el-button>
    </div>
    <div class="form-card">
      <el-form :model="form" label-width="100px" style="max-width: 560px">
        <el-form-item label="物资">
          <el-select v-model="form.goods_id" placeholder="选择物资" filterable style="width: 100%">
            <el-option
              v-for="g in goodsList"
              :key="g.id"
              :label="`${g.name}${g.spec ? ' ' + g.spec : ''}`"
              :value="g.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="采购数量">
          <el-input-number v-model="form.quantity" :min="1" />
        </el-form-item>
        <el-form-item label="申请理由">
          <el-input v-model="form.apply_reason" type="textarea" :rows="4" placeholder="选填" />
        </el-form-item>
        <el-form-item label="收货地点">
          <el-input v-model="form.destination" placeholder="如：教学楼A栋302、报告厅、机房等" />
        </el-form-item>
        <el-form-item label="收货人">
          <el-input v-model="form.receiver_name" placeholder="默认当前老师，可手动填写" />
        </el-form-item>
        <el-form-item label="附件">
          <el-upload
            v-model:file-list="fileList"
            :auto-upload="false"
            :before-upload="beforeUpload"
            :limit="3"
            multiple
            @change="handleFileChange"
          >
            <el-button type="default">选择文件</el-button>
            <template #tip>
              <div class="upload-tip">支持 PDF、Word、JPG、PNG，单个不超过 5MB，最多 3 个</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSubmit">提交申请</el-button>
          <el-button :loading="aiLoading" @click="fetchAISuggestion">获取 AI 建议</el-button>
        </el-form-item>
      </el-form>
      <div v-if="aiSuggestion" class="ai-box">
        <h4>AI 采购建议（基于本地库存数据）</h4>
        <p>{{ aiSuggestion }}</p>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; margin-bottom: 20px; }
.form-card { padding: 24px; background: var(--bg-card); border-radius: 12px; max-width: 640px; }
.ai-box { margin-top: 24px; padding: 16px; background: var(--primary-muted); border-radius: 8px; }
.ai-box h4 { margin: 0 0 8px; font-size: 14px; color: var(--primary); }
.upload-tip { font-size: 12px; color: var(--text-muted); margin-top: 6px; }
</style>
