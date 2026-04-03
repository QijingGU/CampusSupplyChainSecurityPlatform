<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { listAuditLogs, type AuditItem, type AuditListParams, type AuditSummary } from '@/api/audit'

type IdsDomain = 'source_sync' | 'source_package' | 'rulepack'
type IdsOutcome = 'success' | 'rejected' | 'failed' | 'skipped'

const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const tableData = ref<AuditItem[]>([])

const actionFilter = ref('')
const targetTypeFilter = ref('')
const userFilter = ref('')
const keywordFilter = ref('')
const idsDomainFilter = ref<IdsDomain | ''>('')
const idsOutcomeFilter = ref<IdsOutcome | ''>('')
const timeRange = ref<[string, string] | []>([])

const actionOptions = ref<string[]>([])
const targetTypeOptions = ref<string[]>([])
const idsDomainOptions = ref<IdsDomain[]>(['source_sync', 'source_package', 'rulepack'])
const idsOutcomeOptions = ref<IdsOutcome[]>(['success', 'rejected', 'failed', 'skipped'])

const summary = ref<AuditSummary>({
  total: 0,
  ids_count: 0,
  sensitive_count: 0,
  today_count: 0,
  by_action: [],
  by_user: [],
  by_target_type: [],
  ids_by_domain: [],
  ids_by_outcome: [],
})

const actionLabels: Record<string, string> = {
  ids_source_sync: '规则源同步',
  ids_source_package_preview: '规则包预览',
  ids_source_package_preview_rejected: '规则包预览被拒绝',
  ids_source_package_activate: '规则包激活',
  ids_source_package_activate_rejected: '规则包激活被拒绝',
  ids_rulepack_activate: '运行规则包激活',
  ids_rulepack_activate_rejected: '运行规则包激活被拒绝',
  ids_rulepack_activate_failed: '运行规则包激活失败',
}

const idsDomainLabels: Record<IdsDomain, string> = {
  source_sync: '规则源同步',
  source_package: '规则包管理',
  rulepack: '运行规则包',
}

const idsOutcomeLabels: Record<IdsOutcome, string> = {
  success: '成功',
  rejected: '被拒绝',
  failed: '失败',
  skipped: '跳过',
}

function getActionLabel(action: string) {
  return actionLabels[action] || action
}

function getDomainLabel(domain: string | null | undefined) {
  if (!domain) return '-'
  return idsDomainLabels[domain as IdsDomain] || domain
}

function getOutcomeLabel(outcome: string | null | undefined) {
  if (!outcome) return '-'
  return idsOutcomeLabels[outcome as IdsOutcome] || outcome
}

function outcomeType(outcome: string | null | undefined): 'success' | 'warning' | 'danger' | 'info' {
  if (outcome === 'success') return 'success'
  if (outcome === 'rejected') return 'warning'
  if (outcome === 'failed') return 'danger'
  return 'info'
}

function summaryCountFrom(buckets: Array<{ name: string; count: number }> | undefined, name: string) {
  return buckets?.find((x) => x.name === name)?.count || 0
}

const idsSuccessCount = computed(() => summaryCountFrom(summary.value.ids_by_outcome, 'success'))
const idsRejectedCount = computed(() => summaryCountFrom(summary.value.ids_by_outcome, 'rejected'))
const idsFailedCount = computed(() => summaryCountFrom(summary.value.ids_by_outcome, 'failed'))
const idsSkippedCount = computed(() => summaryCountFrom(summary.value.ids_by_outcome, 'skipped'))

function buildParams(): AuditListParams {
  const params: AuditListParams = {
    ids_only: 1,
    page: page.value,
    page_size: pageSize.value,
  }
  if (actionFilter.value) params.action = actionFilter.value
  if (targetTypeFilter.value) params.target_type = targetTypeFilter.value
  if (userFilter.value) params.user_name = userFilter.value
  if (keywordFilter.value) params.keyword = keywordFilter.value
  if (idsDomainFilter.value) params.ids_domain = idsDomainFilter.value
  if (idsOutcomeFilter.value) params.ids_outcome = idsOutcomeFilter.value
  if (timeRange.value.length === 2) {
    params.start_at = timeRange.value[0]
    params.end_at = timeRange.value[1]
  }
  return params
}

function normalizePayload(res: any) {
  if (Array.isArray(res)) {
    const items = (res as AuditItem[]).filter((x) => x.is_ids)
    return {
      total: items.length,
      page: page.value,
      page_size: pageSize.value,
      items,
      summary: {
        total: items.length,
        ids_count: items.length,
        sensitive_count: items.filter((x) => x.is_sensitive).length,
        today_count: items.length,
        by_action: [],
        by_user: [],
        by_target_type: [],
        ids_by_domain: [],
        ids_by_outcome: [],
      } as AuditSummary,
      filters: {
        action_options: Object.keys(actionLabels),
        target_type_options: [],
        ids_domain_options: ['source_sync', 'source_package', 'rulepack'],
        ids_outcome_options: ['success', 'rejected', 'failed', 'skipped'],
      },
    }
  }
  return res
}

async function fetchData() {
  loading.value = true
  try {
    const raw: any = await listAuditLogs(buildParams())
    const payload = normalizePayload(raw?.data ?? raw)
    tableData.value = payload?.items ?? []
    total.value = Number(payload?.total || 0)
    summary.value = payload?.summary || summary.value
    actionOptions.value = payload?.filters?.action_options || []
    targetTypeOptions.value = payload?.filters?.target_type_options || []
    idsDomainOptions.value = payload?.filters?.ids_domain_options || idsDomainOptions.value
    idsOutcomeOptions.value = payload?.filters?.ids_outcome_options || idsOutcomeOptions.value
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  fetchData()
}

function setRangeByDays(days: number) {
  const end = new Date()
  const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000)
  const format = (d: Date) => {
    const p = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
  }
  timeRange.value = [format(start), format(end)]
  search()
}

function resetFilters() {
  actionFilter.value = ''
  targetTypeFilter.value = ''
  userFilter.value = ''
  keywordFilter.value = ''
  idsDomainFilter.value = ''
  idsOutcomeFilter.value = ''
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

onMounted(fetchData)
</script>

<template>
  <div class="security-audit-page">
    <header class="sec-header">
      <div class="sec-hud-rail" aria-hidden="true">
        <span class="sec-hud-rail__dot" />
        <span class="sec-hud-rail__brand">安全运营审计 · IDS操作留痕 · 可追溯闭环</span>
      </div>
      <h1 class="sec-title">IDS 审计追踪</h1>
      <div class="sec-subtitle">这里专门看 IDS 的操作记录、结果归类和追溯链路，不与日常业务审计混在一起。</div>
    </header>

    <main class="sec-main">
      <div class="summary-grid">
        <div class="summary-card">
          <span class="summary-label">IDS日志总量</span>
          <span class="summary-value">{{ summary.ids_count }}</span>
        </div>
        <div class="summary-card summary-card--ok">
          <span class="summary-label">成功</span>
          <span class="summary-value">{{ idsSuccessCount }}</span>
        </div>
        <div class="summary-card summary-card--warn">
          <span class="summary-label">被拒绝</span>
          <span class="summary-value">{{ idsRejectedCount }}</span>
        </div>
        <div class="summary-card summary-card--danger">
          <span class="summary-label">失败</span>
          <span class="summary-value">{{ idsFailedCount }}</span>
        </div>
      </div>
      <div class="summary-mini">
        <el-tag type="info">跳过 {{ idsSkippedCount }}</el-tag>
      </div>

      <div class="filter-card">
        <div class="filter-row">
          <el-select v-model="actionFilter" placeholder="动作类型" clearable class="sec-select">
            <el-option v-for="item in actionOptions" :key="item" :label="getActionLabel(item)" :value="item" />
          </el-select>
          <el-select v-model="idsDomainFilter" placeholder="IDS模块" clearable class="sec-select">
            <el-option v-for="item in idsDomainOptions" :key="item" :label="getDomainLabel(item)" :value="item" />
          </el-select>
          <el-select v-model="idsOutcomeFilter" placeholder="处理结果" clearable class="sec-select">
            <el-option v-for="item in idsOutcomeOptions" :key="item" :label="getOutcomeLabel(item)" :value="item" />
          </el-select>
          <el-select v-model="targetTypeFilter" placeholder="对象类型" clearable class="sec-select">
            <el-option v-for="item in targetTypeOptions" :key="item" :label="item" :value="item" />
          </el-select>
          <el-input v-model="userFilter" placeholder="操作人" clearable class="sec-input" />
          <el-input v-model="keywordFilter" placeholder="关键词（详情/对象ID）" clearable class="sec-input sec-input-wide" />
          <el-date-picker
            v-model="timeRange"
            type="datetimerange"
            value-format="YYYY-MM-DDTHH:mm:ss"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            class="sec-date"
          />
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </div>
        <div class="quick-row">
          <el-button text @click="setRangeByDays(1)">近24小时</el-button>
          <el-button text @click="setRangeByDays(3)">近3天</el-button>
          <el-button text @click="setRangeByDays(7)">近7天</el-button>
        </div>
      </div>

      <div class="table-card">
        <el-table :data="tableData" v-loading="loading" class="sec-table" stripe>
          <el-table-column prop="created_at" label="时间" width="184">
            <template #default="{ row }">{{ row.created_at ? row.created_at.slice(0, 19).replace('T', ' ') : '-' }}</template>
          </el-table-column>
          <el-table-column prop="user_name" label="操作人" width="130" />
          <el-table-column prop="action" label="动作" width="220">
            <template #default="{ row }">
              <el-tag size="small" type="success">{{ getActionLabel(row.action) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="IDS模块" width="130">
            <template #default="{ row }">{{ getDomainLabel(row.ids_domain) }}</template>
          </el-table-column>
          <el-table-column label="处理结果" width="110">
            <template #default="{ row }">
              <el-tag size="small" :type="outcomeType(row.ids_outcome)">{{ getOutcomeLabel(row.ids_outcome) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="target_type" label="对象类型" width="120" />
          <el-table-column prop="target_id" label="对象ID" width="180" show-overflow-tooltip />
          <el-table-column prop="detail" label="详情" min-width="320" show-overflow-tooltip />
        </el-table>
        <el-pagination
          background
          class="sec-pagination"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          :current-page="page"
          :page-size="pageSize"
          :page-sizes="[20, 50, 100, 200]"
          @update:current-page="onPageChange"
          @update:page-size="onPageSizeChange"
        />
      </div>
    </main>
  </div>
</template>

<style scoped>
.security-audit-page {
  padding: 18px 22px 20px;
  min-height: 100%;
  background:
    radial-gradient(circle at 10% 10%, rgba(56, 189, 248, 0.14), transparent 35%),
    radial-gradient(circle at 90% 0%, rgba(37, 99, 235, 0.12), transparent 35%),
    #05070f;
  color: #dbeafe;
}

.sec-header {
  margin-bottom: 16px;
}

.sec-hud-rail {
  display: flex;
  align-items: center;
  gap: 10px;
  color: rgba(125, 211, 252, 0.9);
  font-size: 12px;
  letter-spacing: 0.08em;
  margin-bottom: 8px;
}

.sec-hud-rail__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22d3ee;
}

.sec-title {
  margin: 0;
  font-size: 34px;
  font-weight: 800;
  color: #e0f2fe;
}

.sec-subtitle {
  margin-top: 6px;
  color: rgba(191, 219, 254, 0.85);
  font-size: 13px;
}

.sec-main {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.summary-mini {
  margin-top: -4px;
}

.summary-card {
  padding: 14px 14px;
  border-radius: 12px;
  border: 1px solid rgba(56, 189, 248, 0.24);
  background: rgba(12, 22, 42, 0.72);
}

.summary-card--ok {
  border-color: rgba(16, 185, 129, 0.35);
}

.summary-card--warn {
  border-color: rgba(245, 158, 11, 0.35);
}

.summary-card--danger {
  border-color: rgba(239, 68, 68, 0.35);
}

.summary-label {
  color: rgba(191, 219, 254, 0.84);
  font-size: 12px;
}

.summary-value {
  display: block;
  margin-top: 8px;
  font-size: 26px;
  line-height: 1;
  font-weight: 800;
  color: #f8fafc;
}

.filter-card,
.table-card {
  border-radius: 12px;
  border: 1px solid rgba(56, 189, 248, 0.2);
  background: rgba(8, 16, 32, 0.82);
  padding: 12px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.quick-row {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}

.sec-select,
.sec-input {
  width: 150px;
}

.sec-input-wide {
  width: 240px;
}

.sec-date {
  width: 350px;
}

.sec-table :deep(.el-table),
.sec-table :deep(.el-table__inner-wrapper),
.sec-table :deep(.el-table__header-wrapper),
.sec-table :deep(.el-table__body-wrapper) {
  background: transparent;
}

.sec-table :deep(th.el-table__cell) {
  background: rgba(15, 23, 42, 0.78);
  color: #c7d2fe;
}

.sec-table :deep(td.el-table__cell) {
  background: rgba(2, 8, 23, 0.52);
  color: #e2e8f0;
}

.sec-pagination {
  margin-top: 12px;
  justify-content: flex-end;
}

@media (max-width: 1024px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .sec-date {
    width: 100%;
  }
}
</style>
