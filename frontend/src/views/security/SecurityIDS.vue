<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listIDSEvents, getIDSStats, getIDSTrend, archiveIDSEvent, archiveIDSBatch } from '@/api/ids'
import type { IDSEventItem } from '@/api/ids'

const loading = ref(false)
const trendDays = ref(7)
const trendData = ref<{ dates: string[]; counts: number[] }>({ dates: [], counts: [] })
const stats = ref<{ total: number; blocked_count: number; by_type: { attack_type: string; attack_type_label: string; count: number }[] } | null>(null)
const tableData = ref<IDSEventItem[]>([])
const total = ref(0)
const attackTypeFilter = ref('')
const clientIpFilter = ref('')
const blockedFilter = ref<number | undefined>(undefined)
const archivedFilter = ref<number | undefined>(undefined)
const pageSize = ref(20)
const pageOffset = ref(0)
const selectedIds = ref<number[]>([])
const detailVisible = ref(false)
const currentRow = ref<IDSEventItem | null>(null)
const simulatingAttack = ref(false)

async function fetchStats() {
  try {
    const res: any = await getIDSStats()
    stats.value = res?.data ?? res
    renderPieChart()
  } catch {
    stats.value = null
  }
}

async function fetchTrend() {
  try {
    const res: any = await getIDSTrend(trendDays.value)
    trendData.value = res?.data ?? res ?? { dates: [], counts: [] }
    renderTrendChart()
  } catch {
    trendData.value = { dates: [], counts: [] }
  }
}

let pieChartInstance: echarts.ECharts | null = null
let trendChartInstance: echarts.ECharts | null = null

const PIE_COLORS = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899']

function renderPieChart() {
  const el = document.getElementById('ids-pie-chart')
  if (!el || !stats.value?.by_type?.length) return
  if (!pieChartInstance) pieChartInstance = echarts.init(el, 'dark')
  pieChartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    color: PIE_COLORS,
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '50%'],
      data: stats.value.by_type.map((t: { attack_type_label: string; count: number }) => ({
        name: t.attack_type_label,
        value: t.count,
      })),
      label: { color: 'rgba(255,255,255,0.7)', fontSize: 11 },
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(59,130,246,0.4)' } },
    }],
  })
}

function renderTrendChart() {
  const el = document.getElementById('ids-trend-chart')
  if (!el) return
  if (!trendChartInstance) trendChartInstance = echarts.init(el, 'dark')
  const { dates, counts } = trendData.value
  trendChartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 24, top: 24, bottom: 36 },
    xAxis: {
      type: 'category',
      data: dates?.length ? dates.map((d: string) => d.slice(5)) : [],
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } },
      axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)', type: 'dashed' } },
      axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: counts ?? [],
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(59,130,246,0.8)' },
          { offset: 1, color: 'rgba(59,130,246,0.2)' },
        ]),
      },
    }],
  })
}

function handleResize() {
  pieChartInstance?.resize()
  trendChartInstance?.resize()
}

async function fetchData() {
  loading.value = true
  try {
    const res: any = await listIDSEvents({
      attack_type: attackTypeFilter.value || undefined,
      client_ip: clientIpFilter.value || undefined,
      blocked: blockedFilter.value,
      archived: archivedFilter.value,
      limit: pageSize.value,
      offset: pageOffset.value,
    })
    const data = res?.data ?? res
    tableData.value = data?.items ?? []
    total.value = data?.total ?? 0
  } catch {
    tableData.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pageOffset.value = 0
  fetchData()
}

async function handleArchive(row: IDSEventItem) {
  try {
    await archiveIDSEvent(row.id)
    ElMessage.success('已归档')
    fetchData()
    fetchStats()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '归档失败')
  }
}

async function handleBatchArchive() {
  if (!selectedIds.value.length) {
    ElMessage.warning('请选择要归档的事件')
    return
  }
  try {
    await ElMessageBox.confirm(`确定归档选中的 ${selectedIds.value.length} 条记录？`, '批量归档')
    await archiveIDSBatch(selectedIds.value)
    ElMessage.success('批量归档成功')
    selectedIds.value = []
    fetchData()
    fetchStats()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || e?.message || '归档失败')
  }
}

function handleSelectionChange(rows: IDSEventItem[]) {
  selectedIds.value = rows.map((r) => r.id)
}

async function handleSimulateAttack() {
  simulatingAttack.value = true
  try {
    const payload = "1' or '1'='1"
    const url = `/api/goods?ids_demo=${encodeURIComponent(payload)}`
    await fetch(url, { credentials: 'include' })
  } catch {
    /* 403 为预期，请求已被 IDS 拦截 */
  }
  ElMessage.success('已发送模拟攻击请求，检测记录已生成，请查看上方列表')
  await fetchStats()
  await fetchTrend()
  await fetchData()
  simulatingAttack.value = false
}

function showDetail(row: IDSEventItem) {
  currentRow.value = row
  detailVisible.value = true
}

onMounted(() => {
  fetchStats()
  fetchTrend()
  fetchData()
  window.addEventListener('resize', handleResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  pieChartInstance?.dispose()
  trendChartInstance?.dispose()
})
watch([pageOffset, pageSize], fetchData)
watch(trendDays, () => fetchTrend())
</script>

<template>
  <div class="security-center-page">
    <header class="sec-header">
      <h1 class="sec-title">IDS 入侵检测</h1>
      <p class="sec-subtitle">抓包解析 · 特征匹配 · 攻击识别 · 留痕封禁 · 归档管理</p>
    </header>

    <main class="sec-main">
      <div v-if="stats" class="stats-row">
        <div class="stat-card sec-stat">
          <span class="stat-value">{{ stats.total }}</span>
          <span class="stat-label">检测事件总数</span>
        </div>
        <div class="stat-card sec-stat danger">
          <span class="stat-value">{{ stats.blocked_count }}</span>
          <span class="stat-label">已封禁 IP</span>
        </div>
        <div v-for="t in stats.by_type" :key="t.attack_type" class="stat-card sec-stat small">
          <span class="stat-value">{{ t.count }}</span>
          <span class="stat-label">{{ t.attack_type_label }}</span>
        </div>
      </div>

      <div class="chart-row">
        <div class="chart-card sec-card">
          <div class="chart-title">攻击类型分布</div>
          <div id="ids-pie-chart" class="chart-arena" />
        </div>
        <div class="chart-card sec-card chart-card-wide">
          <div class="chart-title">
            事件趋势
            <el-select v-model="trendDays" size="small" class="sec-select">
              <el-option label="近7天" :value="7" />
              <el-option label="近14天" :value="14" />
              <el-option label="近30天" :value="30" />
            </el-select>
          </div>
          <div id="ids-trend-chart" class="chart-arena" />
        </div>
      </div>

      <div class="filter-bar">
        <el-input v-model="clientIpFilter" placeholder="来源 IP" clearable class="sec-input" />
        <el-select v-model="attackTypeFilter" placeholder="攻击类型" clearable class="sec-select">
          <el-option label="SQL 注入" value="sql_injection" />
          <el-option label="XSS" value="xss" />
          <el-option label="路径遍历" value="path_traversal" />
          <el-option label="命令注入" value="cmd_injection" />
          <el-option label="扫描器" value="scanner" />
          <el-option label="畸形请求" value="malformed" />
        </el-select>
        <el-select v-model="blockedFilter" placeholder="封禁状态" clearable class="sec-select">
          <el-option label="已封禁" :value="1" />
          <el-option label="仅记录" :value="0" />
        </el-select>
        <el-select v-model="archivedFilter" placeholder="归档状态" clearable class="sec-select">
          <el-option label="未归档" :value="0" />
          <el-option label="已归档" :value="1" />
        </el-select>
        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button type="success" :disabled="!selectedIds.length" @click="handleBatchArchive">
          批量归档 ({{ selectedIds.length }})
        </el-button>
        <el-button type="warning" :loading="simulatingAttack" @click="handleSimulateAttack">
          模拟攻击（演示）
        </el-button>
      </div>

      <div class="table-card sec-card">
        <el-table
          :data="tableData"
          v-loading="loading"
          class="sec-table"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="45" />
          <el-table-column prop="created_at" label="时间" width="170" />
          <el-table-column prop="client_ip" label="来源 IP" width="130" />
          <el-table-column prop="attack_type_label" label="攻击类型" width="120">
            <template #default="{ row }">
              <el-tag :type="row.attack_type === 'sql_injection' ? 'danger' : 'warning'" size="small">
                {{ row.attack_type_label }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="method" label="方法" width="70" />
          <el-table-column prop="path" label="路径" min-width="180" show-overflow-tooltip />
          <el-table-column prop="blocked" label="封禁" width="70">
            <template #default="{ row }">
              <el-tag :type="row.blocked ? 'success' : 'info'" size="small">
                {{ row.blocked ? '已封禁' : '仅记录' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="firewall_rule" label="防火墙规则" width="140" show-overflow-tooltip />
          <el-table-column prop="archived" label="归档" width="70">
            <template #default="{ row }">{{ row.archived ? '已归档' : '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="showDetail(row)">查看</el-button>
              <el-button v-if="!row.archived" link type="success" size="small" @click="handleArchive(row)">归档</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          :current-page="Math.floor(pageOffset / pageSize) + 1"
          class="sec-pagination"
          @current-change="(p: number) => { pageOffset = (p - 1) * pageSize; fetchData() }"
        />
      </div>
    </main>

    <el-drawer v-model="detailVisible" title="事件详情" size="480" class="sec-drawer">
      <template v-if="currentRow">
        <p><strong>时间：</strong>{{ currentRow.created_at }}</p>
        <p><strong>来源 IP：</strong>{{ currentRow.client_ip }}</p>
        <p><strong>攻击类型：</strong>{{ currentRow.attack_type_label }}</p>
        <p><strong>匹配特征：</strong>{{ currentRow.signature_matched }}</p>
        <p><strong>方法：</strong>{{ currentRow.method }}</p>
        <p><strong>路径：</strong>{{ currentRow.path }}</p>
        <p><strong>Query 片段：</strong>{{ currentRow.query_snippet || '-' }}</p>
        <p><strong>Body 片段：</strong>{{ currentRow.body_snippet || '-' }}</p>
        <p><strong>User-Agent：</strong>{{ currentRow.user_agent || '-' }}</p>
        <p><strong>封禁：</strong>{{ currentRow.blocked ? '是' : '否' }}</p>
        <p><strong>防火墙规则：</strong>{{ currentRow.firewall_rule || '-' }}</p>
      </template>
    </el-drawer>
  </div>
</template>

<style lang="scss" scoped>
.security-center-page {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background: #050505;
  color: #fff;
  padding: 24px;
}
.sec-header {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.sec-title {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 0.2em;
  margin: 0 0 8px 0;
  background: linear-gradient(to bottom, #fff 40%, #94a3b8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.sec-subtitle {
  font-size: 12px;
  font-family: monospace;
  color: rgba(59, 130, 246, 0.6);
  letter-spacing: 0.3em;
  margin: 0;
  text-transform: uppercase;
}
.sec-main { padding: 0; }

.stats-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card.sec-stat {
  padding: 20px 24px;
  background: #0a0a0a;
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 16px;
  min-width: 140px;
  transition: border-color 0.2s;
  &:hover { border-color: rgba(255,255,255,0.1); }
  &.danger .stat-value { color: #ef4444; }
  &.small .stat-value { font-size: 22px; }
}
.stat-card .stat-value {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: #3b82f6;
  font-family: monospace;
}
.stat-card .stat-label {
  display: block;
  font-size: 11px;
  color: rgba(255,255,255,0.4);
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin-top: 6px;
}

.chart-row {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 24px;
}
.chart-card.sec-card {
  flex: 0 0 320px;
  padding: 20px;
  background: #0a0a0a;
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 16px;
  &.chart-card-wide { flex: 1; min-width: 360px; }
}
.chart-title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255,255,255,0.8);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
}
.chart-arena { height: 220px; }
.sec-select { width: 120px; margin-left: 8px; }

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
}
.sec-input { width: 140px; }
.sec-select { width: 140px; }

.table-card.sec-card {
  padding: 20px;
  background: #0a0a0a;
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 16px;
}
.sec-pagination { margin-top: 16px; }

/* 统一暗色科技风：表格、选择器、输入框、标签、分页、抽屉 */
:deep(.sec-table),
:deep(.sec-table .el-table),
:deep(.sec-table .el-table__inner-wrapper) {
  --el-table-bg-color: #0a0a0a;
  --el-table-tr-bg-color: #0a0a0a;
  --el-table-header-bg-color: rgba(255,255,255,0.04);
  --el-table-row-hover-bg-color: rgba(255,255,255,0.06);
  --el-table-border-color: rgba(255,255,255,0.06);
  --el-table-text-color: rgba(255,255,255,0.9);
  background: #0a0a0a !important;
}
:deep(.sec-table .el-table__body tr) { background: #0a0a0a !important; }
:deep(.sec-table .el-table__body tr.el-table__row--striped) { background: rgba(255,255,255,0.02) !important; }
:deep(.sec-table th.el-table__cell) { background: rgba(255,255,255,0.04) !important; color: rgba(255,255,255,0.7); }
:deep(.sec-drawer) {
  --el-drawer-bg-color: #0a0a0a;
  --el-text-color-primary: rgba(255,255,255,0.9);
  background: #0a0a0a !important;
}
:deep(.el-pagination) {
  --el-pagination-button-bg-color: transparent;
  --el-pagination-button-color: rgba(255,255,255,0.7);
  --el-pagination-hover-color: #3b82f6;
}
:deep(.sec-input .el-input__wrapper),
:deep(.sec-select .el-select__wrapper) {
  background: rgba(255,255,255,0.06) !important;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.9);
}
:deep(.sec-input .el-input__inner),
:deep(.sec-select .el-select__input) { color: rgba(255,255,255,0.9); }
:deep(.sec-input .el-input__wrapper:hover),
:deep(.sec-select .el-select__wrapper:hover) { background: rgba(255,255,255,0.08) !important; }
:deep(.el-select-dropdown) { --el-bg-color: #0f172a !important; --el-text-color-primary: rgba(255,255,255,0.9); }
:deep(.el-tag) { --el-tag-bg-color: rgba(255,255,255,0.08); --el-tag-text-color: rgba(255,255,255,0.8); }
:deep(.el-tag--danger) { --el-tag-bg-color: rgba(239,68,68,0.2); --el-tag-text-color: #f87171; }
:deep(.el-tag--warning) { --el-tag-bg-color: rgba(245,158,11,0.2); --el-tag-text-color: #fbbf24; }
:deep(.el-tag--success) { --el-tag-bg-color: rgba(16,185,129,0.2); --el-tag-text-color: #34d399; }
:deep(.el-tag--info) { --el-tag-bg-color: rgba(255,255,255,0.06); --el-tag-text-color: rgba(255,255,255,0.6); }
</style>
