<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listAuditLogs, type AuditItem, type AuditListParams, type AuditSummary } from '@/api/audit'
import {
  archiveMisapproval,
  getUnseenMisapprovalIds,
  markMisapprovalSeen,
  misapprovalRecords,
  setWarningToLogistics,
  syncMisapprovalFromStorage,
  type MisapprovalRecord,
} from '@/stores/demo'

type ActiveTab = 'all' | 'ids' | 'sensitive' | 'misapproval'

interface MisapprovalAuditRow {
  _isMisapproval: true
  id: string
  user_name: string
  user_role: string
  action: string
  target_type: string
  target_id: string
  detail: string
  is_ids: false
  is_sensitive: true
  created_at: string | null
}

type MixedAuditRow = AuditItem | MisapprovalAuditRow

const activeTab = ref<ActiveTab>('all')
const loading = ref(false)
const tableData = ref<AuditItem[]>([])
const mergedTableData = ref<MixedAuditRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const actionFilter = ref('')
const targetFilter = ref('')
const userFilter = ref('')
const keywordFilter = ref('')
const timeRange = ref<[string, string] | []>([])

const actionOptions = ref<string[]>([])
const targetTypeOptions = ref<string[]>([])
const summary = ref<AuditSummary>({
  total: 0,
  ids_count: 0,
  sensitive_count: 0,
  today_count: 0,
  by_action: [],
  by_user: [],
  by_target_type: [],
})

const emailDialogVisible = ref(false)
const emailTarget = ref<MisapprovalRecord | null>(null)
const emailForm = ref({ to: '', subject: '', body: '' })

const actionLabels: Record<string, string> = {
  purchase_create: '采购申请',
  purchase_approve: '采购审批通过',
  purchase_reject: '采购审批驳回',
  supplier_confirm: '供应商确认',
  stock_in: '采购入库',
  stock_in_manual: '手工入库',
  stock_out: '出库',
  delivery_create: '创建配送',
  delivery_status_update: '配送状态更新',
  warning_handle: '预警处置',
  misapproval_approve: '误批审计',
  ids_source_sync: 'IDS 源同步',
  ids_source_package_preview: 'IDS 包预览',
  ids_source_package_preview_rejected: 'IDS 包预览拒绝',
  ids_source_package_activate: 'IDS 包激活',
  ids_source_package_activate_rejected: 'IDS 包激活拒绝',
  ids_rulepack_activate: 'IDS 规则包激活',
  ids_rulepack_activate_rejected: 'IDS 规则包激活拒绝',
  ids_rulepack_activate_failed: 'IDS 规则包激活失败',
}

const showTableData = computed(() => (activeTab.value === 'all' ? mergedTableData.value : tableData.value))
const showPagination = computed(() => activeTab.value !== 'misapproval')

function getActionLabel(action: string) {
  return actionLabels[action] || action
}

function isMisapprovalRow(row: MixedAuditRow): row is MisapprovalAuditRow {
  return (row as MisapprovalAuditRow)._isMisapproval === true
}

function toMixedRow(rec: MisapprovalRecord): MisapprovalAuditRow {
  return {
    _isMisapproval: true,
    id: rec.id,
    created_at: rec.created_at,
    user_name: rec.operatorName,
    user_role: rec.operatorRole,
    action: 'misapproval_approve',
    target_type: 'purchase',
    target_id: rec.orderNo,
    detail: `误批订单 ${rec.orderNo}，物资 ${rec.goodsSummary}，决策间隔 ${(rec.decisionTimeMs / 1000).toFixed(1)} 秒`,
    is_ids: false,
    is_sensitive: true,
  }
}

function mergeAllRows(auditRows: AuditItem[]) {
  const misRows = misapprovalRecords.value.map(toMixedRow)
  mergedTableData.value = [...misRows, ...auditRows].sort((a, b) => {
    const ta = a.created_at || ''
    const tb = b.created_at || ''
    return tb.localeCompare(ta)
  })
}

function buildParams(): AuditListParams {
  const params: AuditListParams = {
    page: page.value,
    page_size: pageSize.value,
  }
  if (actionFilter.value) params.action = actionFilter.value
  if (targetFilter.value) params.target_type = targetFilter.value
  if (userFilter.value) params.user_name = userFilter.value
  if (keywordFilter.value) params.keyword = keywordFilter.value
  if (timeRange.value.length === 2) {
    params.start_at = timeRange.value[0]
    params.end_at = timeRange.value[1]
  }
  if (activeTab.value === 'ids') params.ids_only = 1
  if (activeTab.value === 'sensitive') params.sensitive_only = 1
  return params
}

function normalizePayload(res: any) {
  if (Array.isArray(res)) {
    const items = res as AuditItem[]
    return {
      total: items.length,
      page: page.value,
      page_size: pageSize.value,
      items,
      summary: {
        total: items.length,
        ids_count: items.filter((x) => x.action?.startsWith('ids_')).length,
        sensitive_count: items.filter((x) => x.action === 'purchase_reject' || x.action === 'supplier_confirm' || x.action === 'warning_handle').length,
        today_count: items.length,
        by_action: [],
        by_user: [],
        by_target_type: [],
      } as AuditSummary,
      filters: {
        action_options: Object.keys(actionLabels),
        target_type_options: [],
      },
    }
  }
  return res
}

async function fetchData() {
  if (activeTab.value === 'misapproval') {
    return
  }
  loading.value = true
  try {
    const raw: any = await listAuditLogs(buildParams())
    const payload = normalizePayload(raw?.data ?? raw)

    tableData.value = payload?.items ?? []
    total.value = Number(payload?.total || 0)
    summary.value = payload?.summary || summary.value
    actionOptions.value = payload?.filters?.action_options || []
    targetTypeOptions.value = payload?.filters?.target_type_options || []
    if (activeTab.value === 'all') {
      mergeAllRows(tableData.value)
    }
  } catch {
    tableData.value = []
    mergedTableData.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  fetchData()
}

function resetFilters() {
  actionFilter.value = ''
  targetFilter.value = ''
  userFilter.value = ''
  keywordFilter.value = ''
  timeRange.value = []
  page.value = 1
  fetchData()
}

function onPageChange(nextPage: number) {
  page.value = nextPage
  fetchData()
}

function onPageSizeChange(nextSize: number) {
  pageSize.value = nextSize
  page.value = 1
  fetchData()
}

function openEmailDialog(rec: MisapprovalRecord) {
  emailTarget.value = rec
  emailForm.value = {
    to: `${rec.operatorName}@campus.edu`,
    subject: `【审计提醒】关于申请单 ${rec.orderNo} 的误批复核`,
    body: [
      '您好，',
      '',
      `系统审计发现您对异常申请单 ${rec.orderNo} 进行了通过操作。`,
      `首次确认时间：${rec.firstConfirmAt?.slice(0, 19) || '-'}`,
      '请及时完成复核并补充说明，避免后续风险。',
      '',
      '审计中心',
    ].join('\n'),
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
    ElMessage.success(`已发送提醒邮件：${emailForm.value.to}`)
  }
  emailDialogVisible.value = false
  emailTarget.value = null
}

function doArchive(rec: MisapprovalRecord) {
  archiveMisapproval(rec.id)
  ElMessage.success('已归档该误批记录')
}

onMounted(() => {
  syncMisapprovalFromStorage()
  fetchData()
  const unseen = getUnseenMisapprovalIds()
  if (unseen.length) {
    ElMessageBox.alert(
      `发现 ${unseen.length} 条新的误批审计记录，请尽快处理。`,
      '审计提醒',
      { type: 'warning', confirmButtonText: '我知道了' }
    ).then(() => {
      unseen.forEach(markMisapprovalSeen)
    })
  }
})

watch(activeTab, () => {
  page.value = 1
  if (activeTab.value === 'all') {
    mergeAllRows(tableData.value)
  }
  fetchData()
})

watch(misapprovalRecords, () => {
  if (activeTab.value === 'all') {
    mergeAllRows(tableData.value)
  }
}, { deep: true })
</script>

<template>
  <div class="audit-page">
    <div class="page-header">
      <h2>日志审计中心</h2>
      <p>统一查看系统日志、IDS 操作日志和敏感操作，支持快速筛选与追溯。</p>
    </div>

    <div class="summary-grid">
      <div class="summary-card">
        <div class="summary-label">日志总量</div>
        <div class="summary-value">{{ summary.total }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">IDS 审计</div>
        <div class="summary-value">{{ summary.ids_count }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">敏感操作</div>
        <div class="summary-value warning">{{ summary.sensitive_count }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">今日新增</div>
        <div class="summary-value">{{ summary.today_count }}</div>
      </div>
    </div>

    <div class="tabs-row">
      <el-radio-group v-model="activeTab">
        <el-radio-button label="all">全部日志</el-radio-button>
        <el-radio-button label="ids">IDS 审计</el-radio-button>
        <el-radio-button label="sensitive">敏感操作</el-radio-button>
        <el-radio-button label="misapproval">误批审计</el-radio-button>
      </el-radio-group>
    </div>

    <div v-if="activeTab !== 'misapproval'" class="filter-row">
      <el-select v-model="actionFilter" placeholder="动作类型" clearable style="width: 180px">
        <el-option v-for="item in actionOptions" :key="item" :label="getActionLabel(item)" :value="item" />
      </el-select>
      <el-select v-model="targetFilter" placeholder="对象类型" clearable style="width: 140px">
        <el-option v-for="item in targetTypeOptions" :key="item" :label="item" :value="item" />
      </el-select>
      <el-input v-model="userFilter" placeholder="操作人" clearable style="width: 140px" />
      <el-input v-model="keywordFilter" placeholder="关键词（详情/ID）" clearable style="width: 220px" />
      <el-date-picker
        v-model="timeRange"
        type="datetimerange"
        value-format="YYYY-MM-DDTHH:mm:ss"
        range-separator="至"
        start-placeholder="开始时间"
        end-placeholder="结束时间"
        style="width: 380px"
      />
      <el-button type="primary" @click="search">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </div>

    <div v-if="activeTab === 'misapproval'" class="misapproval-section">
      <div v-for="rec in misapprovalRecords" :key="rec.id" class="misapproval-card" :class="{ archived: rec.archived }">
        <div class="mis-header">
          <span class="order-no">{{ rec.orderNo }}</span>
          <el-tag type="danger" size="small">误批</el-tag>
          <el-tag v-if="rec.archived" type="info" size="small">已归档</el-tag>
        </div>
        <div class="mis-meta">
          <span>操作人：{{ rec.operatorName }}（{{ rec.operatorRole }}）</span>
          <span>物资：{{ rec.goodsSummary }}</span>
        </div>
        <div class="mis-meta">
          <span>首次确认：{{ rec.firstConfirmAt?.slice(0, 19) || '-' }}</span>
          <span>二次确认：{{ rec.secondConfirmAt?.slice(0, 19) || '-' }}</span>
          <span class="danger">决策间隔：{{ (rec.decisionTimeMs / 1000).toFixed(1) }} 秒</span>
        </div>
        <pre class="mis-report">{{ rec.report }}</pre>
        <div v-if="!rec.archived" class="mis-actions">
          <el-button type="primary" size="small" @click="doArchive(rec)">归档</el-button>
          <el-button type="warning" size="small" @click="openEmailDialog(rec)">发送提醒</el-button>
        </div>
      </div>
      <div v-if="!misapprovalRecords.length" class="empty-hint">暂无误批审计记录</div>
    </div>

    <div v-else class="table-card">
      <el-table :data="showTableData" v-loading="loading" stripe>
        <el-table-column prop="created_at" label="时间" width="185">
          <template #default="{ row }">{{ row.created_at ? row.created_at.slice(0, 19).replace('T', ' ') : '-' }}</template>
        </el-table-column>
        <el-table-column prop="user_name" label="操作人" width="120" />
        <el-table-column prop="user_role" label="角色" width="130" />
        <el-table-column prop="action" label="动作" width="180">
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="isMisapprovalRow(row) ? 'danger' : row.is_sensitive ? 'warning' : row.is_ids ? 'success' : 'info'"
            >
              {{ getActionLabel(row.action) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_type" label="对象类型" width="120" />
        <el-table-column prop="target_id" label="对象ID" width="160" show-overflow-tooltip />
        <el-table-column prop="detail" label="详情" min-width="280" show-overflow-tooltip />
      </el-table>

      <div v-if="showPagination" class="pager">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          :current-page="page"
          :page-size="pageSize"
          :page-sizes="[20, 50, 100, 200]"
          @update:current-page="onPageChange"
          @update:page-size="onPageSizeChange"
        />
      </div>
    </div>

    <el-dialog v-model="emailDialogVisible" title="发送审计提醒" width="560px">
      <el-form :model="emailForm" label-width="80px">
        <el-form-item label="收件人">
          <el-input v-model="emailForm.to" />
        </el-form-item>
        <el-form-item label="主题">
          <el-input v-model="emailForm.subject" />
        </el-form-item>
        <el-form-item label="正文">
          <el-input v-model="emailForm.body" type="textarea" :rows="7" />
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
.audit-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  h2 {
    margin: 0 0 6px 0;
    font-size: 22px;
    font-weight: 700;
    color: #12324f;
  }

  p {
    margin: 0;
    color: #4e6278;
    font-size: 14px;
  }
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(140px, 1fr));
  gap: 12px;
}

.summary-card {
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid #d8e6f2;
  background: linear-gradient(135deg, #f8fcff 0%, #eef6ff 100%);
}

.summary-label {
  color: #5b7390;
  font-size: 12px;
}

.summary-value {
  margin-top: 6px;
  font-size: 24px;
  line-height: 1.1;
  font-weight: 700;
  color: #173e63;
}

.summary-value.warning {
  color: #d35400;
}

.tabs-row {
  display: flex;
  justify-content: flex-start;
}

.filter-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.table-card {
  background: #fff;
  border: 1px solid #dbe6f0;
  border-radius: 12px;
  padding: 12px;
}

.pager {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}

.misapproval-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.misapproval-card {
  border: 1px solid #f2c0c0;
  border-radius: 12px;
  padding: 16px;
  background: linear-gradient(135deg, #fff6f6 0%, #ffeaea 100%);

  &.archived {
    opacity: 0.72;
    background: #f8f9fb;
    border-color: #d9dee7;
  }
}

.mis-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.order-no {
  font-size: 16px;
  font-weight: 700;
  color: #c0392b;
}

.mis-meta {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  color: #485b6d;
  font-size: 13px;
}

.mis-meta .danger {
  color: #c0392b;
  font-weight: 600;
}

.mis-report {
  margin: 10px 0;
  font-size: 12px;
  color: #e5e7eb;
  background: #1f2937;
  border-radius: 8px;
  padding: 10px;
  white-space: pre-wrap;
}

.mis-actions {
  display: flex;
  gap: 10px;
}

.empty-hint {
  padding: 30px 0;
  text-align: center;
  color: #8a99aa;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(120px, 1fr));
  }
}
</style>
