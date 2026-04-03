<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
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

const emptySummary: AuditSummary = {
  total: 0,
  ids_count: 0,
  sensitive_count: 0,
  today_count: 0,
  by_action: [],
  by_user: [],
  by_target_type: [],
  ids_by_domain: [],
  ids_by_outcome: [],
}
const summary = ref<AuditSummary>(emptySummary)

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

function summaryCountFrom(buckets: Array<{ name: string; count: number }> | undefined, name: string): number {
  return buckets?.find((bucket) => bucket.name === name)?.count || 0
}

const idsSuccessCount = computed(() => summaryCountFrom(summary.value.ids_by_outcome, 'success'))
const idsRejectedCount = computed(() => summaryCountFrom(summary.value.ids_by_outcome, 'rejected'))
const idsFailedCount = computed(() => summaryCountFrom(summary.value.ids_by_outcome, 'failed'))
const idsSkippedCount = computed(() => summaryCountFrom(summary.value.ids_by_outcome, 'skipped'))

function getActionLabel(action: string): string {
  return actionLabels[action] || action
}

function getDomainLabel(domain: string | null | undefined): string {
  if (!domain) return '-'
  return idsDomainLabels[domain as IdsDomain] || domain
}

function getOutcomeLabel(outcome: string | null | undefined): string {
  if (!outcome) return '-'
  return idsOutcomeLabels[outcome as IdsOutcome] || outcome
}

function outcomeType(outcome: string | null | undefined): 'success' | 'warning' | 'danger' | 'info' {
  if (outcome === 'success') return 'success'
  if (outcome === 'rejected') return 'warning'
  if (outcome === 'failed') return 'danger'
  return 'info'
}

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
    const items = (res as AuditItem[]).filter((item) => item.is_ids)
    return {
      total: items.length,
      page: page.value,
      page_size: pageSize.value,
      items,
      summary: {
        total: items.length,
        ids_count: items.length,
        sensitive_count: items.filter((item) => item.is_sensitive).length,
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

let fetchSeq = 0

async function fetchData(showError = false) {
  const currentSeq = ++fetchSeq
  loading.value = true
  try {
    const raw: any = await Promise.race([
      listAuditLogs(buildParams()),
      new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 12000)),
    ])
    if (currentSeq !== fetchSeq) return
    const payload = normalizePayload(raw?.data ?? raw)
    tableData.value = payload?.items ?? []
    total.value = Number(payload?.total || 0)
    summary.value = payload?.summary || emptySummary
    actionOptions.value = payload?.filters?.action_options || Object.keys(actionLabels)
    targetTypeOptions.value = payload?.filters?.target_type_options || []
    idsDomainOptions.value = payload?.filters?.ids_domain_options || idsDomainOptions.value
    idsOutcomeOptions.value = payload?.filters?.ids_outcome_options || idsOutcomeOptions.value
  } catch {
    if (currentSeq !== fetchSeq) return
    tableData.value = []
    total.value = 0
    summary.value = emptySummary
    if (showError) ElMessage.error('IDS 审计数据加载失败，请重试')
  } finally {
    if (currentSeq === fetchSeq) loading.value = false
  }
}

function search() {
  page.value = 1
  void fetchData(true)
}

function refresh() {
  void fetchData(true)
}

function setRangeByDays(days: number) {
  const end = new Date()
  const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000)
  const format = (value: Date) => {
    const pad = (num: number) => String(num).padStart(2, '0')
    return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}T${pad(value.getHours())}:${pad(value.getMinutes())}:${pad(value.getSeconds())}`
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
  void fetchData(true)
}

function onPageChange(nextPage: number) {
  page.value = nextPage
  void fetchData()
}

function onPageSizeChange(nextSize: number) {
  pageSize.value = nextSize
  page.value = 1
  void fetchData()
}

onMounted(() => {
  void fetchData(true)
})
</script>

<template>
  <div class="security-audit-page">
    <header class="audit-header">
      <div class="header-chip">安全中心 / IDS 审计追踪</div>
      <h1 class="header-title">IDS 审计追踪</h1>
      <p class="header-subtitle">专门追踪规则源、规则包和运行规则包的关键操作，不与业务日常审计混在一起。</p>
    </header>

    <main class="audit-main">
      <section class="summary-grid">
        <article class="summary-card">
          <span class="summary-label">IDS 日志总量</span>
          <span class="summary-value">{{ summary.ids_count }}</span>
        </article>
        <article class="summary-card summary-card--ok">
          <span class="summary-label">成功</span>
          <span class="summary-value">{{ idsSuccessCount }}</span>
        </article>
        <article class="summary-card summary-card--warn">
          <span class="summary-label">被拒绝</span>
          <span class="summary-value">{{ idsRejectedCount }}</span>
        </article>
        <article class="summary-card summary-card--danger">
          <span class="summary-label">失败</span>
          <span class="summary-value">{{ idsFailedCount }}</span>
        </article>
        <article class="summary-card summary-card--neutral">
          <span class="summary-label">跳过</span>
          <span class="summary-value">{{ idsSkippedCount }}</span>
        </article>
      </section>

      <section class="filter-panel">
        <div class="filter-row">
          <el-select v-model="actionFilter" placeholder="动作类型" clearable class="field-sm">
            <el-option v-for="item in actionOptions" :key="item" :label="getActionLabel(item)" :value="item" />
          </el-select>
          <el-select v-model="idsDomainFilter" placeholder="IDS 模块" clearable class="field-sm">
            <el-option v-for="item in idsDomainOptions" :key="item" :label="getDomainLabel(item)" :value="item" />
          </el-select>
          <el-select v-model="idsOutcomeFilter" placeholder="处理结果" clearable class="field-sm">
            <el-option v-for="item in idsOutcomeOptions" :key="item" :label="getOutcomeLabel(item)" :value="item" />
          </el-select>
          <el-select v-model="targetTypeFilter" placeholder="对象类型" clearable class="field-sm">
            <el-option v-for="item in targetTypeOptions" :key="item" :label="item" :value="item" />
          </el-select>
          <el-input v-model="userFilter" placeholder="操作人" clearable class="field-sm" />
          <el-input v-model="keywordFilter" placeholder="关键词（详情/对象ID）" clearable class="field-lg" />
          <el-date-picker
            v-model="timeRange"
            type="datetimerange"
            value-format="YYYY-MM-DDTHH:mm:ss"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            class="field-date"
          />
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-button @click="refresh">刷新</el-button>
        </div>
        <div class="quick-row">
          <el-button text @click="setRangeByDays(1)">近 24 小时</el-button>
          <el-button text @click="setRangeByDays(3)">近 3 天</el-button>
          <el-button text @click="setRangeByDays(7)">近 7 天</el-button>
        </div>
      </section>

      <section class="table-panel">
        <el-table :data="tableData" v-loading="loading" class="audit-table" stripe>
          <el-table-column prop="created_at" label="时间" width="188">
            <template #default="{ row }">{{ row.created_at ? row.created_at.slice(0, 19).replace('T', ' ') : '-' }}</template>
          </el-table-column>
          <el-table-column prop="user_name" label="操作人" width="132" />
          <el-table-column prop="action" label="动作" width="230">
            <template #default="{ row }">
              <el-tag size="small" type="success">{{ getActionLabel(row.action) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="IDS 模块" width="132">
            <template #default="{ row }">{{ getDomainLabel(row.ids_domain) }}</template>
          </el-table-column>
          <el-table-column label="处理结果" width="112">
            <template #default="{ row }">
              <el-tag size="small" :type="outcomeType(row.ids_outcome)">{{ getOutcomeLabel(row.ids_outcome) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="target_type" label="对象类型" width="122" />
          <el-table-column prop="target_id" label="对象 ID" width="180" show-overflow-tooltip />
          <el-table-column prop="detail" label="详情" min-width="340" show-overflow-tooltip />
        </el-table>

        <div v-if="!loading && tableData.length === 0" class="empty-state">
          当前筛选条件下没有 IDS 审计记录
        </div>

        <el-pagination
          background
          class="pager"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          :current-page="page"
          :page-size="pageSize"
          :page-sizes="[20, 50, 100, 200]"
          @update:current-page="onPageChange"
          @update:page-size="onPageSizeChange"
        />
      </section>
    </main>
  </div>
</template>

<style scoped>
.security-audit-page {
  --bg-0: #060b1b;
  --bg-1: #0b1530;
  --panel: rgba(9, 20, 42, 0.9);
  --panel-border: rgba(94, 168, 255, 0.26);
  --text-main: #f3f7ff;
  --text-sub: #c8d8f0;
  --text-muted: #97abcd;
  --accent: #4da3ff;
  --ok: #34d399;
  --warn: #f59e0b;
  --danger: #ef4444;
  --font-cn: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;

  min-height: 100%;
  padding: 22px;
  background:
    radial-gradient(circle at 8% 8%, rgba(77, 163, 255, 0.22), transparent 36%),
    radial-gradient(circle at 96% 0%, rgba(56, 189, 248, 0.14), transparent 34%),
    linear-gradient(180deg, var(--bg-1) 0%, var(--bg-0) 100%);
  color: var(--text-main);
  font-family: var(--font-cn);
}

.audit-header {
  margin-bottom: 16px;
}

.header-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(77, 163, 255, 0.45);
  background: rgba(77, 163, 255, 0.12);
  color: #bfdbfe;
  font-size: 12px;
  letter-spacing: 0.03em;
}

.header-title {
  margin: 10px 0 4px;
  font-size: 34px;
  line-height: 1.12;
  font-weight: 800;
  color: var(--text-main);
}

.header-subtitle {
  margin: 0;
  color: var(--text-sub);
  font-size: 14px;
  line-height: 1.6;
}

.audit-main {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.summary-card {
  border: 1px solid var(--panel-border);
  border-radius: 12px;
  background: var(--panel);
  padding: 14px;
}

.summary-card--ok {
  border-color: rgba(52, 211, 153, 0.48);
}

.summary-card--warn {
  border-color: rgba(245, 158, 11, 0.48);
}

.summary-card--danger {
  border-color: rgba(239, 68, 68, 0.48);
}

.summary-card--neutral {
  border-color: rgba(148, 163, 184, 0.44);
}

.summary-label {
  display: block;
  color: var(--text-sub);
  font-size: 12px;
}

.summary-value {
  display: block;
  margin-top: 8px;
  font-size: 28px;
  line-height: 1;
  font-weight: 800;
  color: #ffffff;
}

.filter-panel,
.table-panel {
  border: 1px solid var(--panel-border);
  border-radius: 12px;
  background: var(--panel);
  padding: 12px;
}

.filter-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.quick-row {
  margin-top: 6px;
  display: flex;
  gap: 8px;
}

.field-sm {
  width: 154px;
}

.field-lg {
  width: 240px;
}

.field-date {
  width: 350px;
}

.audit-table :deep(.el-table),
.audit-table :deep(.el-table__inner-wrapper),
.audit-table :deep(.el-table__header-wrapper),
.audit-table :deep(.el-table__body-wrapper) {
  background: transparent;
}

.audit-table :deep(th.el-table__cell) {
  background: rgba(17, 31, 62, 0.92);
  color: #dbeafe;
  font-weight: 600;
}

.audit-table :deep(td.el-table__cell) {
  background: rgba(8, 16, 34, 0.76);
  color: #eef4ff;
}

.empty-state {
  margin-top: 10px;
  color: var(--text-muted);
  text-align: center;
  font-size: 13px;
}

.pager {
  margin-top: 12px;
  justify-content: flex-end;
}

.security-audit-page :deep(.el-input__wrapper),
.security-audit-page :deep(.el-select__wrapper),
.security-audit-page :deep(.el-range-editor.el-input__wrapper) {
  background: rgba(7, 16, 34, 0.92);
  box-shadow: 0 0 0 1px rgba(129, 169, 232, 0.24) inset;
}

.security-audit-page :deep(.el-input__inner),
.security-audit-page :deep(.el-select__placeholder),
.security-audit-page :deep(.el-select__selected-item),
.security-audit-page :deep(.el-range-input) {
  color: #eef4ff;
}

.security-audit-page :deep(.el-input__inner::placeholder),
.security-audit-page :deep(.el-range-input::placeholder) {
  color: #9fb5d8;
}

@media (max-width: 1360px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1024px) {
  .security-audit-page {
    padding: 16px;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .field-date,
  .field-sm,
  .field-lg {
    width: 100%;
  }
}
</style>
