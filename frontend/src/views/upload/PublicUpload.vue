<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheckFilled, Clock, Lock, Upload } from '@element-plus/icons-vue'
import {
  getUploadAuditRuntime,
  resolvePublicUploadURL,
  type UploadAuditMode,
  type UploadAuditResult,
  type UploadResult,
} from '@/api/upload'

type UploadPhase = 'idle' | 'uploading' | 'auditing' | 'released' | 'quarantined' | 'rejected'

const loading = ref(false)
const runtimeLoading = ref(false)
const fileList = ref<File[]>([])
const lastResult = ref<UploadResult | null>(null)
const phase = ref<UploadPhase>('idle')
const errorMessage = ref('')
const runtimeMode = ref<UploadAuditMode>('static_only')
const runtimeMessage = ref('当前未读取到后端审计状态。')

function sleep(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

function onFileChange(files: FileList | null) {
  fileList.value = files ? Array.from(files) : []
}

function auditModeLabel(mode?: string | null) {
  return mode === 'llm_assisted' ? 'AI 审计' : '静态审计'
}

function auditVerdictLabel(audit?: UploadAuditResult | null) {
  if (audit?.verdict === 'quarantine') return '已扣留'
  if (audit?.verdict === 'review') return '待复核'
  return '已放行'
}

function auditRiskLabel(audit?: UploadAuditResult | null) {
  if (audit?.risk_level === 'high') return '高风险'
  if (audit?.risk_level === 'medium') return '中风险'
  if (audit?.risk_level === 'low') return '低风险'
  return '未知'
}

function auditProviderText(audit?: UploadAuditResult | null) {
  const provider = audit?.provider || audit?.engine || audit?.analysis_mode || '--'
  if (provider === 'static-rules' || provider === 'static_upload_ruleset') return '静态规则引擎'
  return provider
}

const currentMode = computed<UploadAuditMode>(() => {
  const auditMode = lastResult.value?.audit?.analysis_mode as UploadAuditMode | undefined
  return auditMode || runtimeMode.value
})

const phaseSteps = computed(() => [
  { key: 'uploading', label: '文件接收' },
  { key: 'auditing', label: auditModeLabel(currentMode.value) },
  { key: 'released', label: '处置决策' },
] as const)

const phaseTitle = computed(() => {
  if (phase.value === 'uploading') return '文件正在接收'
  if (phase.value === 'auditing') return `${auditModeLabel(currentMode.value)}正在执行`
  if (phase.value === 'released') return '审计通过，文件已放行'
  if (phase.value === 'quarantined') return '审计未通过，文件已扣留到安全沙箱'
  if (phase.value === 'rejected') return '上传审计执行失败'
  return `${auditModeLabel(currentMode.value)}已就绪`
})

const phaseDescription = computed(() => {
  if (phase.value === 'uploading') return '系统正在固化原始文件并计算基础指纹。'
  if (phase.value === 'auditing') {
    return currentMode.value === 'llm_assisted'
      ? '后端会先做静态预检，再追加模型裁决。'
      : '后端会按扩展名、哈希、内容预览和命中特征执行静态审计。'
  }
  if (phase.value === 'released') return '文件已经通过审计，可以进入公开目录。'
  if (phase.value === 'quarantined') return '文件不会进入公开目录，只会进入安全沙箱等待复核。'
  if (phase.value === 'rejected') return '本次调用没有产出可落账的审计结果，文件未被放行。'
  return runtimeMessage.value
})

const progressValue = computed(() => {
  if (phase.value === 'uploading') return 24
  if (phase.value === 'auditing') return 68
  if (phase.value === 'released' || phase.value === 'quarantined' || phase.value === 'rejected') return 100
  return 0
})

const runtimeBadgeText = computed(() => {
  return currentMode.value === 'llm_assisted' ? 'AI 审计已启用' : '静态审计运行中'
})

const auditBadgeClass = computed(() => {
  const verdict = lastResult.value?.audit?.verdict
  if (verdict === 'quarantine') return 'audit-badge audit-badge--danger'
  if (verdict === 'review') return 'audit-badge audit-badge--warn'
  return 'audit-badge audit-badge--safe'
})

const rejectedHint = computed(() => {
  if (currentMode.value === 'llm_assisted') {
    return '请检查当前 AI 服务连接、模型地址或密钥配置，然后重新上传。'
  }
  return '当前可以直接以静态审计模式继续使用；如果要启用 AI 审计，请在后端启动时输入密钥或补齐 LLM 配置。'
})

async function refreshRuntimeStatus() {
  runtimeLoading.value = true
  try {
    const status = await getUploadAuditRuntime()
    runtimeMode.value = status.ids_upload_audit_mode || 'static_only'
    runtimeMessage.value = status.ids_upload_audit_message || '后端未返回审计状态说明。'
  } catch {
    runtimeMode.value = 'static_only'
    runtimeMessage.value = '未能读取后端审计状态，请确认后端已启动。'
  } finally {
    runtimeLoading.value = false
  }
}

async function showAuditDialog(message: string, title: string, confirmButtonText = '我知道了') {
  try {
    await ElMessageBox.alert(message, title, {
      type: 'error',
      confirmButtonText,
      customClass: 'public-upload-malware-dialog',
    })
  } catch {
    // Ignore manual close so dialog interaction does not rewrite the upload result state.
  }
}

async function handleUpload() {
  if (fileList.value.length === 0) {
    ElMessage.warning('请选择文件')
    return
  }

  const file = fileList.value[0]
  loading.value = true
  lastResult.value = null
  errorMessage.value = ''
  phase.value = 'uploading'

  try {
    const form = new FormData()
    form.append('file', file)

    await sleep(150)
    phase.value = 'auditing'

    const response = await fetch(await resolvePublicUploadURL(), {
      method: 'POST',
      body: form,
      credentials: 'include',
    })

    const payload = (await response.json().catch(() => ({}))) as UploadResult & { detail?: string }
    if (!response.ok) {
      lastResult.value = null
      phase.value = 'rejected'
      errorMessage.value = typeof payload.detail === 'string'
        ? payload.detail
        : `上传审计失败 (${response.status})`
      await showAuditDialog(errorMessage.value, '上传审计失败')
      await refreshRuntimeStatus()
      return
    }

    lastResult.value = payload
    runtimeMode.value = (payload.audit?.analysis_mode as UploadAuditMode | undefined) || runtimeMode.value
    phase.value = payload.quarantined ? 'quarantined' : 'released'

    if (payload.quarantined) {
      const body = [
        payload.security_alert?.message || payload.audit?.summary,
        payload.security_alert?.detail,
        `审计结论：${auditVerdictLabel(payload.audit)} / ${auditRiskLabel(payload.audit)} / 置信度 ${payload.audit?.confidence ?? 0}`,
      ]
        .filter(Boolean)
        .join('\n\n')
      await showAuditDialog(body, payload.security_alert?.title || '上传审计未通过', '查看沙箱')
      return
    }

    ElMessage.success(`${auditModeLabel(payload.audit?.analysis_mode)}通过，文件已放行：${payload.filename || ''}`)
  } catch (error: any) {
    lastResult.value = null
    phase.value = 'rejected'
    errorMessage.value = error?.message || '网络错误'
    ElMessage.error(errorMessage.value)
  } finally {
    loading.value = false
  }
}

function clearAll() {
  fileList.value = []
  lastResult.value = null
  errorMessage.value = ''
  phase.value = 'idle'
}

onMounted(() => {
  void refreshRuntimeStatus()
})
</script>

<template>
  <div class="upload-page">
    <div class="upload-bg" />
    <div class="upload-card">
      <div class="card-header">
        <div class="header-badge">
          <el-icon><Lock /></el-icon>
          <span>{{ runtimeBadgeText }}</span>
        </div>
        <h2>匿名举报 / 反馈材料上传</h2>
        <p>{{ runtimeMessage }}</p>
        <div class="runtime-strip">
          <span>当前模式：{{ auditModeLabel(currentMode) }}</span>
          <span>{{ runtimeLoading ? '正在读取后端状态…' : '后端状态已同步' }}</span>
        </div>
      </div>

      <section class="status-panel">
        <div class="status-panel__head">
          <div>
            <h3>{{ phaseTitle }}</h3>
            <p>{{ phaseDescription }}</p>
          </div>
          <div class="status-panel__meter">
            <span>{{ progressValue }}%</span>
          </div>
        </div>
        <div class="status-progress">
          <div class="status-progress__bar" :style="{ width: `${progressValue}%` }" />
        </div>
        <div class="status-steps">
          <div
            v-for="(step, index) in phaseSteps"
            :key="step.key"
            class="status-step"
            :class="{
              active:
                (phase === 'uploading' && index === 0) ||
                (phase === 'auditing' && index <= 1) ||
                ((phase === 'released' || phase === 'quarantined' || phase === 'rejected') && index <= 2),
              done:
                (phase === 'auditing' && index === 0) ||
                ((phase === 'released' || phase === 'quarantined' || phase === 'rejected') && index <= 1),
            }"
          >
            <span class="status-step__dot">
              <el-icon v-if="phase === 'released' && index === 2"><CircleCheckFilled /></el-icon>
              <el-icon v-else-if="phase === 'quarantined' && index === 2"><Lock /></el-icon>
              <el-icon v-else><Clock /></el-icon>
            </span>
            <span>{{ step.label }}</span>
          </div>
        </div>
      </section>

      <div class="upload-form">
        <div class="file-input-wrap">
          <input
            id="fileInput"
            class="file-input"
            type="file"
            @change="(e: Event) => onFileChange((e.target as HTMLInputElement)?.files)"
          />
          <label for="fileInput" class="file-label">
            <el-icon :size="24"><Upload /></el-icon>
            <span>选择文件</span>
          </label>
        </div>
        <p v-if="fileList.length" class="selected-file">
          {{ fileList[0]?.name }}，{{ ((fileList[0]?.size || 0) / 1024).toFixed(1) }} KB
        </p>

        <div class="actions">
          <el-button type="primary" :loading="loading" @click="handleUpload">开始上传</el-button>
          <el-button @click="clearAll">清空</el-button>
        </div>
      </div>

      <div v-if="phase === 'rejected' && errorMessage" class="result-box result-box--danger">
        <div class="result-head">
          <h4>上传审计未完成，本次请求未放行</h4>
          <span class="audit-badge audit-badge--danger">已拒绝</span>
        </div>
        <p class="result-summary">{{ errorMessage }}</p>
        <p class="result-note">{{ rejectedHint }}</p>
      </div>

      <div
        v-if="lastResult?.ok && lastResult.saved_as"
        class="result-box"
        :class="{
          'result-box--warn': lastResult.quarantined,
          'result-box--safe': !lastResult.quarantined,
        }"
      >
        <div class="result-head">
          <h4>{{ lastResult.quarantined ? '文件已扣留到安全沙箱' : `文件已通过${auditModeLabel(lastResult.audit?.analysis_mode)}` }}</h4>
          <span :class="auditBadgeClass">{{ auditVerdictLabel(lastResult.audit) }}</span>
        </div>
        <p>文件名：{{ lastResult.filename }}</p>
        <p>保存名：{{ lastResult.saved_as }}</p>
        <p>大小：{{ lastResult.size }} 字节</p>
        <p>审计模式：{{ auditModeLabel(lastResult.audit?.analysis_mode) }}</p>
        <p>风险等级：{{ auditRiskLabel(lastResult.audit) }}</p>
        <p>审计引擎：{{ auditProviderText(lastResult.audit) }}</p>
        <p>审计置信度：{{ lastResult.audit.confidence }}</p>
        <p class="result-summary">{{ lastResult.audit.summary }}</p>
        <a v-if="lastResult.url" :href="lastResult.url" target="_blank" rel="noopener">访问已放行文件</a>
        <p v-if="lastResult.quarantined" class="result-note">
          管理员可在安全中心的“安全沙箱”和“IDS 日志审计”中查看这次扣留、分析和处置留痕。
        </p>
      </div>

      <p class="hint">
        未配置密钥时系统按静态审计模式运行；配置后会自动启用 AI 审计增强。局域网演示时请用本机 IP 打开前端页面，不要用 127.0.0.1 代替另一台电脑。
      </p>
    </div>

    <router-link to="/login" class="back-link">返回登录</router-link>
  </div>
</template>

<style lang="scss">
.el-overlay-dialog .public-upload-malware-dialog.el-message-box {
  border: 1px solid #fecaca;
  background: linear-gradient(180deg, #fff5f5 0%, #ffffff 100%);
}

.el-overlay-dialog .public-upload-malware-dialog .el-message-box__title {
  color: #b91c1c;
  font-weight: 700;
}

.el-overlay-dialog .public-upload-malware-dialog .el-message-box__message {
  color: #7f1d1d;
  white-space: pre-wrap;
  line-height: 1.6;
}
</style>

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
  background:
    radial-gradient(circle at top left, rgba(14, 165, 233, 0.14), transparent 28%),
    radial-gradient(circle at bottom right, rgba(239, 68, 68, 0.12), transparent 24%),
    linear-gradient(135deg, #0b1220 0%, #111827 48%, #172554 100%);
  z-index: 0;
}

.upload-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 560px;
  padding: 32px;
  background: rgba(7, 13, 24, 0.9);
  border-radius: 24px;
  box-shadow: 0 24px 80px rgba(2, 6, 23, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.18);
  color: #f8fafc;
}

.card-header {
  margin-bottom: 24px;

  h2 {
    margin: 12px 0 10px;
    font-size: 26px;
    font-weight: 800;
    letter-spacing: 0.02em;
  }

  p {
    margin: 0;
    color: rgba(226, 232, 240, 0.76);
    line-height: 1.7;
    font-size: 14px;
  }
}

.header-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(14, 165, 233, 0.12);
  color: #67e8f9;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.runtime-strip {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;

  span {
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(15, 23, 42, 0.72);
    color: rgba(226, 232, 240, 0.82);
    font-size: 12px;
  }
}

.status-panel {
  padding: 18px 18px 16px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.76);
  border: 1px solid rgba(148, 163, 184, 0.14);
  margin-bottom: 24px;
}

.status-panel__head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;

  h3 {
    margin: 0 0 6px;
    font-size: 18px;
    font-weight: 700;
  }

  p {
    margin: 0;
    font-size: 13px;
    line-height: 1.6;
    color: rgba(226, 232, 240, 0.72);
  }
}

.status-panel__meter {
  min-width: 70px;
  text-align: right;
  font-size: 20px;
  font-weight: 800;
  color: #67e8f9;
}

.status-progress {
  margin: 16px 0 14px;
  height: 10px;
  border-radius: 999px;
  background: rgba(30, 41, 59, 0.85);
  overflow: hidden;
}

.status-progress__bar {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #06b6d4 0%, #3b82f6 55%, #22c55e 100%);
  transition: width 0.25s ease;
}

.status-steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.status-step {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.48);
  border: 1px solid transparent;
  color: rgba(203, 213, 225, 0.68);
  font-size: 13px;
  transition: all 0.2s ease;

  &.active {
    border-color: rgba(34, 211, 238, 0.4);
    color: #f8fafc;
  }

  &.done {
    background: rgba(8, 47, 73, 0.45);
  }
}

.status-step__dot {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(30, 41, 59, 0.9);
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
  gap: 10px;
  padding: 18px 24px;
  border: 2px dashed rgba(148, 163, 184, 0.35);
  border-radius: 16px;
  cursor: pointer;
  color: rgba(226, 232, 240, 0.84);
  background: rgba(15, 23, 42, 0.42);
  transition: all 0.2s ease;

  &:hover {
    border-color: rgba(34, 211, 238, 0.76);
    color: #67e8f9;
  }
}

.selected-file {
  font-size: 13px;
  color: rgba(226, 232, 240, 0.72);
  margin: 12px 0 0;
}

.actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.result-box {
  margin-top: 24px;
  padding: 18px;
  border-radius: 18px;
  border: 1px solid rgba(59, 130, 246, 0.22);

  p {
    margin: 6px 0;
    font-size: 13px;
    color: #e2e8f0;
  }

  a {
    display: inline-block;
    margin-top: 8px;
    color: #67e8f9;
    font-size: 13px;
    font-weight: 700;
  }
}

.result-box--safe {
  background: rgba(22, 101, 52, 0.16);
}

.result-box--warn {
  background: rgba(120, 53, 15, 0.18);
  border-color: rgba(245, 158, 11, 0.34);
}

.result-box--danger {
  background: rgba(127, 29, 29, 0.18);
  border-color: rgba(239, 68, 68, 0.34);
}

.result-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;

  h4 {
    margin: 0;
    font-size: 16px;
  }
}

.audit-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.audit-badge--safe {
  background: rgba(34, 197, 94, 0.18);
  color: #86efac;
}

.audit-badge--warn {
  background: rgba(245, 158, 11, 0.18);
  color: #fcd34d;
}

.audit-badge--danger {
  background: rgba(239, 68, 68, 0.18);
  color: #fca5a5;
}

.result-summary {
  margin-top: 10px !important;
  line-height: 1.7;
}

.result-note {
  margin-top: 10px !important;
  color: #fcd34d !important;
  line-height: 1.6;
}

.hint {
  margin-top: 20px;
  font-size: 12px;
  color: rgba(203, 213, 225, 0.62);
  text-align: center;
  line-height: 1.6;
}

.back-link {
  position: relative;
  z-index: 1;
  margin-top: 20px;
  font-size: 14px;
  color: #67e8f9;
}

@media (max-width: 640px) {
  .upload-card {
    padding: 22px;
  }

  .status-panel__head {
    flex-direction: column;
  }

  .status-panel__meter {
    text-align: left;
  }

  .status-steps {
    grid-template-columns: 1fr;
  }

  .actions {
    flex-direction: column;
  }
}
</style>
