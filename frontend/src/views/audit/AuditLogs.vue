<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listAuditLogs } from '@/api/audit'
import { misapprovalRecords, archiveMisapproval, syncMisapprovalFromStorage, setWarningToLogistics, getUnseenMisapprovalIds, markMisapprovalSeen, type MisapprovalRecord } from '@/stores/demo'
import type { AuditItem } from '@/api/audit'

const activeTab = ref<'all' | 'sensitive' | 'misapproval'>('all')
const loading = ref(false)
const tableData = ref<AuditItem[]>([])
const allTableData = ref<(AuditItem | { _isMisapproval: true; id: string; created_at: string; user_name: string; user_role: string; action: string; target_type: string; target_id: string; detail: string })[]>([])
const actionFilter = ref('')
const targetFilter = ref('')

const actionLabels: Record<string, string> = {
  purchase_create: '采购申请',
  purchase_approve: '审批通过',
  purchase_reject: '驳回申请',
  supplier_confirm: '供应商接单',
  stock_in: '采购入库',
  stock_in_manual: '手工入库',
  stock_out: '出库',
  delivery_create: '创建配送',
  delivery_status_update: '配送状态',
  warning_handle: '预警处置',
  misapproval_approve: '误批审批',
}
const sensitiveActions = ['purchase_reject', 'supplier_confirm', 'warning_handle']

const emailDialogVisible = ref(false)
const emailTarget = ref<MisapprovalRecord | null>(null)
const emailForm = ref({ to: '', subject: '', body: '' })

function openEmailDialog(rec: MisapprovalRecord) {
  emailTarget.value = rec
  emailForm.value = {
    to: rec.operatorName + '@campus.edu',
    subject: `【审计警告】关于申请单 ${rec.orderNo} 的审批异常说明`,
    body: `您好，\n\n经系统审计，您在 ${rec.firstConfirmAt?.slice(0, 19)} 对 AI 标记异常申请单 ${rec.orderNo} 进行了审批通过操作。\n\n相关信息已留痕记录，请关注合规要求。\n\n—— 审计与异常监督中心`,
  }
  emailDialogVisible.value = true
}

function sendWarningEmail() {
  if (emailTarget.value) {
    setWarningToLogistics({
      orderNo: emailTarget.value.orderNo,
      subject: emailForm.value.subject,
      body: emailForm.value.body,
    })
  }
  ElMessage.success('警告邮件已发送至 ' + emailForm.value.to + '，后勤端将收到弹窗提醒')
  emailDialogVisible.value = false
  emailTarget.value = null
}

function doArchive(rec: MisapprovalRecord) {
  archiveMisapproval(rec.id)
  ElMessage.success('已留档')
}

async function fetchData() {
  loading.value = true
  try {
    const params: { action?: string; target_type?: string } = {}
    if (actionFilter.value) params.action = actionFilter.value
    if (targetFilter.value) params.target_type = targetFilter.value
    const res: any = await listAuditLogs(params)
    let rows: AuditItem[] = Array.isArray(res) ? res : res?.data ?? []
    if (activeTab.value === 'sensitive') {
      rows = rows.filter((r: AuditItem) => sensitiveActions.includes(r.action))
      tableData.value = rows
    } else if (activeTab.value === 'all') {
      const misList = misapprovalRecords.value
      const merged: typeof allTableData.value = [
        ...misList.map((m) => ({
          _isMisapproval: true as const,
          id: m.id,
          created_at: m.created_at,
          user_name: m.operatorName,
          user_role: m.operatorRole,
          action: 'misapproval_approve',
          target_type: 'purchase',
          target_id: m.orderNo,
          detail: `误批：${m.orderNo}，${m.goodsSummary}；决策间隔${(m.decisionTimeMs / 1000).toFixed(1)}秒`,
        })),
        ...rows,
      ].sort((a, b) => {
        const ta = a.created_at || ''
        const tb = b.created_at || ''
        return tb.localeCompare(ta)
      })
      allTableData.value = merged
    } else {
      tableData.value = rows
    }
  } catch {
    tableData.value = []
    allTableData.value = []
  } finally {
    loading.value = false
  }
}

function getActionLabel(action: string) {
  return actionLabels[action] || action
}

function isSensitive(action: string) {
  return sensitiveActions.includes(action)
}

onMounted(() => {
  syncMisapprovalFromStorage()
  fetchData()
  const unseen = getUnseenMisapprovalIds()
  if (unseen.length) {
    ElMessageBox.alert(
      `发现 ${unseen.length} 条新的误批审计记录，请及时审查处理。`,
      '异常操作告警',
      { type: 'warning', confirmButtonText: '前往查看' }
    ).then(() => {
      unseen.forEach(markMisapprovalSeen)
    })
  }
})
watch([activeTab, actionFilter, targetFilter, misapprovalRecords], fetchData, { deep: true })
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>审计与异常监督</h2>
      <p class="page-desc">关键操作留痕，敏感动作可重点审查</p>
    </div>
    <div class="tabs-bar">
      <el-radio-group v-model="activeTab" size="default">
        <el-radio-button label="all">全部日志</el-radio-button>
        <el-radio-button label="sensitive">敏感操作（待审查）</el-radio-button>
        <el-radio-button label="misapproval">误批审计</el-radio-button>
      </el-radio-group>
    </div>
    <div class="filter-bar">
      <el-select v-model="actionFilter" placeholder="动作类型" clearable style="width: 140px">
        <el-option
          v-for="(label, key) in actionLabels"
          :key="key"
          :label="label"
          :value="key"
        />
      </el-select>
      <el-input v-model="targetFilter" placeholder="目标类型" clearable style="width: 120px" />
      <el-button type="primary" @click="fetchData">查询</el-button>
    </div>
    <!-- 误批审计 -->
    <div v-if="activeTab === 'misapproval'" class="misapproval-section">
      <div v-for="rec in misapprovalRecords" :key="rec.id" class="misapproval-card" :class="{ archived: rec.archived }">
        <div class="card-header">
          <span class="order-no">{{ rec.orderNo }}</span>
          <el-tag type="danger" size="small">误批</el-tag>
          <el-tag v-if="rec.archived" type="info" size="small">已留档</el-tag>
        </div>
        <div class="card-meta">
          <span>操作人：{{ rec.operatorName }}（{{ rec.operatorRole }}）</span>
          <span>物资：{{ rec.goodsSummary }}</span>
        </div>
        <div class="card-stats">
          <span>首次关闭报告：{{ rec.firstConfirmAt?.slice(0, 19) }}</span>
          <span>二次确认通过：{{ rec.secondConfirmAt?.slice(0, 19) }}</span>
          <span class="highlight">决策间隔：{{ (rec.decisionTimeMs / 1000).toFixed(1) }} 秒</span>
          <span>推测损失：{{ rec.estimatedLoss }}</span>
          <span>故意概率：{{ rec.intentProbability }}</span>
        </div>
        <pre class="card-report">{{ rec.report }}</pre>
        <div v-if="!rec.archived" class="card-actions">
          <el-button type="primary" size="small" @click="doArchive(rec)">留档</el-button>
          <el-button type="warning" size="small" @click="openEmailDialog(rec)">发起警告邮件</el-button>
        </div>
      </div>
      <div v-if="!misapprovalRecords.length" class="empty-hint">暂无误批审计记录</div>
    </div>

    <div v-else class="table-card">
      <el-table :data="activeTab === 'all' ? allTableData : tableData" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">{{ row.created_at ? row.created_at.slice(0, 19) : '-' }}</template>
        </el-table-column>
        <el-table-column prop="user_name" label="操作人" width="100" />
        <el-table-column prop="user_role" label="角色" width="100" />
        <el-table-column prop="action" label="动作" width="140">
          <template #default="{ row }">
            <el-tag :type="(row as any)._isMisapproval ? 'danger' : isSensitive(row.action) ? 'warning' : 'info'" size="small">
              {{ getActionLabel(row.action) }}
            </el-tag>
            <el-tag v-if="(row as any)._isMisapproval || (activeTab === 'sensitive' && isSensitive(row.action))" type="warning" size="small" effect="plain">待审查</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_type" label="对象类型" width="100" />
        <el-table-column prop="target_id" label="对象ID" width="120" />
        <el-table-column prop="detail" label="详情" min-width="200" show-overflow-tooltip />
      </el-table>
    </div>

    <!-- 警告邮件弹窗 -->
    <el-dialog v-model="emailDialogVisible" title="发起警告邮件" width="520px">
      <el-form :model="emailForm" label-width="80px">
        <el-form-item label="收件人">
          <el-input v-model="emailForm.to" />
        </el-form-item>
        <el-form-item label="主题">
          <el-input v-model="emailForm.subject" />
        </el-form-item>
        <el-form-item label="正文">
          <el-input v-model="emailForm.body" type="textarea" :rows="6" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="emailDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="sendWarningEmail">发送</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.page { padding: 0; }
.page-header { margin-bottom: 20px; }
.page-header h2 { margin: 0 0 6px; font-size: 18px; font-weight: 600; }
.page-desc { margin: 0; font-size: 13px; color: var(--text-muted); }
.tabs-bar { margin-bottom: 16px; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; }
.table-card { padding: 20px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-subtle); }

.misapproval-section { display: flex; flex-direction: column; gap: 16px; }
.misapproval-card {
  padding: 20px; background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  border: 1px solid #fca5a5; border-radius: 12px;
  &.archived { opacity: 0.7; background: #f9fafb; border-color: #e5e7eb; }
}
.card-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.order-no { font-weight: 700; font-size: 16px; color: var(--el-color-danger); }
.card-meta { display: flex; flex-wrap: wrap; gap: 16px; font-size: 13px; color: var(--text-secondary); margin-bottom: 10px; }
.card-stats { display: flex; flex-wrap: wrap; gap: 16px; font-size: 12px; margin-bottom: 12px; }
.card-stats .highlight { color: var(--el-color-danger); font-weight: 600; }
.card-report {
  font-size: 11px; background: #1e1e1e; color: #d4d4d4; padding: 12px; border-radius: 8px;
  white-space: pre-wrap; margin: 0 0 12px 0; max-height: 120px; overflow-y: auto;
}
.card-actions { display: flex; gap: 10px; }
.empty-hint { padding: 40px; text-align: center; color: var(--text-muted); }
</style>
