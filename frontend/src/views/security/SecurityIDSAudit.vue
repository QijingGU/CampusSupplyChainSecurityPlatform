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
const sourceSyncCount = computed(() => summaryCountFrom(summary.value.ids_by_domain, 'source_sync'))
const sourcePackageCount = computed(() => summaryCountFrom(summary.value.ids_by_domain, 'source_package'))
const rulepackCount = computed(() => summaryCountFrom(summary.value.ids_by_domain, 'rulepack'))

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
    if (showError) ElMessage.error('IDS 审计数据加载失败，请检查服务后重试')
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
  <div class="ids-audit-page">
    <header class="audit-hero">
      <div class="audit-hero__meta">
        <span class="meta-dot" />
        <span class="meta-text">安全中心 / IDS 审计追踪</span>
        <span class="meta-badge">仅 IDS 关键操作</span>
      </div>
      <h1 class="audit-hero__title">IDS 审计追踪</h1>
      <p class="audit-hero__desc">用于追溯规则源、规则包、运行规则包相关操作，帮助定位“谁在什么时候做了什么”。</p>
    </header>

    <section class="summary-grid">
      <article class="summary-card">
        <span class="summary-label">日志总量</span>
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

    <section class="sec-panel">
      <div class="sec-panel__head">
        <span class="sec-panel__title">筛选条件</span>
        <div class="sec-panel__actions">
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-button @click="refresh">刷新</el-button>
        </div>
      </div>

      <div class="filter-grid">
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
      </div>

      <div class="quick-row">
        <el-button text @click="setRangeByDays(1)">近 24 小时</el-button>
        <el-button text @click="setRangeByDays(3)">近 3 天</el-button>
        <el-button text @click="setRangeByDays(7)">近 7 天</el-button>
      </div>
    </section>

    <section class="sec-panel table-panel">
      <div class="sec-panel__head">
        <span class="sec-panel__title">审计记录</span>
        <div class="domain-strip">
          <span class="domain-strip__item">规则源同步 {{ sourceSyncCount }}</span>
          <span class="domain-strip__item">规则包管理 {{ sourcePackageCount }}</span>
          <span class="domain-strip__item">运行规则包 {{ rulepackCount }}</span>
        </div>
      </div>

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

      <div v-if="!loading && tableData.length === 0" class="empty-state">当前筛选条件下没有 IDS 审计记录</div>

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
  </div>
</template>

<style scoped>
.ids-audit-page {
  --bg-base: #040b16;
  --bg-panel: rgba(6, 18, 39, 0.92);
  --bg-panel-top: rgba(8, 34, 68, 0.6);
  --line-main: rgba(65, 157, 255, 0.32);
  --line-soft: rgba(55, 124, 203, 0.24);
  --text-main: #f2f8ff;
  --text-sub: #c2d4ed;
  --text-muted: #8ea7c5;
  --brand: #61b6ff;
  --ok: #22c55e;
  --warn: #f59e0b;
  --danger: #ef4444;
  --font-cn: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif;

  min-height: 100%;
  padding: 16px 18px 18px;
  font-family: var(--font-cn);
  color: var(--text-main);
  background:
    radial-gradient(circle at 0 0, rgba(16, 78, 147, 0.28), transparent 38%),
    radial-gradient(circle at 100% 0, rgba(11, 103, 172, 0.18), transparent 36%),
    var(--bg-base);
}

.audit-hero {
  border: 1px solid var(--line-main);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(9, 28, 55, 0.9), rgba(5, 18, 37, 0.9));
  padding: 14px 16px 12px;
  margin-bottom: 12px;
}

.audit-hero__meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.meta-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #39d2ff;
  box-shadow: 0 0 10px rgba(57, 210, 255, 0.6);
}

.meta-text {
  color: #9cc5ef;
  font-size: 12px;
  letter-spacing: 0.04em;
}

.meta-badge {
  margin-left: 4px;
  font-size: 12px;
  line-height: 18px;
  border-radius: 8px;
  padding: 0 8px;
  border: 1px solid rgba(110, 255, 180, 0.5);
  color: #9af9c5;
  background: rgba(27, 94, 59, 0.36);
}

.audit-hero__title {
  margin: 8px 0 4px;
  font-size: 28px;
  line-height: 1.2;
  font-weight: 700;
  color: var(--text-main);
}

.audit-hero__desc {
  margin: 0;
  font-size: 13px;
  color: var(--text-sub);
  line-height: 1.5;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.summary-card {
  background: linear-gradient(180deg, rgba(8, 33, 69, 0.84), rgba(5, 18, 39, 0.9));
  border: 1px solid var(--line-soft);
  border-radius: 10px;
  padding: 12px 14px;
}

.summary-card--ok {
  border-color: rgba(34, 197, 94, 0.44);
}

.summary-card--warn {
  border-color: rgba(245, 158, 11, 0.44);
}

.summary-card--danger {
  border-color: rgba(239, 68, 68, 0.44);
}

.summary-card--neutral {
  border-color: rgba(148, 163, 184, 0.44);
}

.summary-label {
  font-size: 12px;
  color: var(--text-sub);
}

.summary-value {
  display: block;
  margin-top: 8px;
  font-size: 30px;
  line-height: 1;
  font-weight: 700;
  color: #ffffff;
}

.sec-panel {
  border: 1px solid var(--line-main);
  border-radius: 12px;
  background: linear-gradient(180deg, var(--bg-panel-top), var(--bg-panel));
  padding: 12px;
}

.sec-panel + .sec-panel {
  margin-top: 12px;
}

.sec-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.sec-panel__title {
  font-size: 15px;
  font-weight: 600;
  color: #d8ebff;
}

.sec-panel__actions {
  display: flex;
  gap: 8px;
}

.filter-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.quick-row {
  margin-top: 8px;
  display: flex;
  gap: 6px;
}

.field-sm {
  width: 154px;
}

.field-lg {
  width: 250px;
}

.field-date {
  width: 360px;
}

.domain-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.domain-strip__item {
  border: 1px solid rgba(108, 166, 240, 0.3);
  border-radius: 8px;
  color: #b8d7fa;
  background: rgba(10, 34, 67, 0.66);
  font-size: 12px;
  padding: 2px 8px;
}

.audit-table :deep(.el-table),
.audit-table :deep(.el-table__inner-wrapper),
.audit-table :deep(.el-table__header-wrapper),
.audit-table :deep(.el-table__body-wrapper) {
  background: transparent;
}

.audit-table :deep(th.el-table__cell) {
  background: rgba(11, 43, 79, 0.92);
  color: #d5e9ff;
  font-weight: 600;
}

.audit-table :deep(td.el-table__cell) {
  background: rgba(5, 19, 40, 0.82);
  color: #edf5ff;
}

.empty-state {
  margin-top: 10px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}

.pager {
  margin-top: 12px;
  justify-content: flex-end;
}

.ids-audit-page :deep(.el-input__wrapper),
.ids-audit-page :deep(.el-select__wrapper),
.ids-audit-page :deep(.el-range-editor.el-input__wrapper) {
  background: rgba(6, 19, 40, 0.9);
  box-shadow: 0 0 0 1px rgba(97, 182, 255, 0.28) inset;
}

.ids-audit-page :deep(.el-input__inner),
.ids-audit-page :deep(.el-select__placeholder),
.ids-audit-page :deep(.el-select__selected-item),
.ids-audit-page :deep(.el-range-input),
.ids-audit-page :deep(.el-range-separator) {
  color: #ecf4ff;
}

.ids-audit-page :deep(.el-input__inner::placeholder),
.ids-audit-page :deep(.el-range-input::placeholder) {
  color: #94b5da;
}

.ids-audit-page :deep(.el-button--default) {
  background: rgba(8, 28, 57, 0.9);
  border-color: rgba(112, 171, 243, 0.34);
  color: #dbeafe;
}

.ids-audit-page :deep(.el-button--primary) {
  border-color: #3b82f6;
  background: linear-gradient(180deg, #3b82f6, #2563eb);
}

@media (max-width: 1360px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1024px) {
  .ids-audit-page {
    padding: 12px;
  }

  .audit-hero__title {
    font-size: 24px;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .field-sm,
  .field-lg,
  .field-date {
    width: 100%;
  }

  .sec-panel__head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
