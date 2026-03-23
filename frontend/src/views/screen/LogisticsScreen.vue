<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { getLogisticsScreen } from '@/api/dashboard'
import type { LogisticsScreenData } from '@/api/dashboard'

const router = useRouter()
const loading = ref(true)
const data = ref<LogisticsScreenData | null>(null)
const now = ref(new Date())
let chartInstance: echarts.ECharts | null = null
let refreshTimer: ReturnType<typeof setInterval> | null = null
let clockTimer: ReturnType<typeof setInterval> | null = null

const formattedTime = computed(() => {
  const d = now.value
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).replace(/\//g, '-')
})

function padNum(n: number) {
  return String(n).padStart(2, '0')
}

async function load() {
  try {
    const res: any = await getLogisticsScreen()
    data.value = (res?.data ?? res) as LogisticsScreenData
    nextTick(() => renderChart())
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
}

function renderChart() {
  const el = document.getElementById('lg-chart')
  if (!el || !data.value?.chart) return
  if (!chartInstance) chartInstance = echarts.init(el)
  const { labels, purchase } = data.value.chart
  chartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(10, 25, 41, 0.95)',
      borderColor: 'rgba(0, 212, 255, 0.4)',
      textStyle: { color: '#94a3b8', fontSize: 12 },
    },
    grid: { left: 52, right: 24, top: 40, bottom: 32 },
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.15)' } },
      axisLabel: { color: 'rgba(148, 163, 184, 0.8)', fontSize: 11 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.08)' } },
      axisLabel: { color: 'rgba(148, 163, 184, 0.7)', fontSize: 11 },
    },
    series: [
      {
        name: '采购申请',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        data: purchase,
        lineStyle: { width: 2, color: '#00d4ff' },
        itemStyle: { color: '#00d4ff' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(0, 212, 255, 0.35)' },
              { offset: 0.6, color: 'rgba(0, 212, 255, 0.08)' },
              { offset: 1, color: 'rgba(0, 212, 255, 0.01)' },
            ],
          },
        },
      },
    ],
  }, true)
}

const nextTick = (fn: () => void) => setTimeout(fn, 80)

function goTo(path: string) {
  router.push(path)
}

const statCards = computed(() => {
  if (!data.value?.stats) return []
  const s = data.value.stats
  return [
    { value: s.purchasePending, label: '待审批', path: '/purchase', urgent: s.purchasePending > 0 },
    { value: s.supplierPending, label: '待接单', path: '/purchase' },
    { value: s.stockPending, label: '待入库', path: '/purchase' },
    { value: s.dispatchPending, label: '待出库/配送', path: '/purchase' },
    { value: s.receivePending, label: '待签收', path: '/delivery' },
    { value: s.purchaseCompleted, label: '已完成', path: '/purchase' },
  ]
})

const handoffInProgress = computed(() => {
  return (data.value?.handoffList || []).filter((h) => h.status !== 'pending')
})

const hasTodoItems = computed(() => {
  return (data.value?.pendingPurchases?.length || 0) > 0 || handoffInProgress.value.length > 0
})

onMounted(() => {
  load()
  refreshTimer = setInterval(load, 30000)
  clockTimer = setInterval(() => { now.value = new Date() }, 1000)
})

onUnmounted(() => {
  refreshTimer && clearInterval(refreshTimer)
  clockTimer && clearInterval(clockTimer)
  chartInstance?.dispose()
})
</script>

<template>
  <div class="screen">
    <div class="bg-layer">
      <div class="bg-gradient" />
      <div class="bg-grid" />
      <div class="bg-scan" />
    </div>

    <header class="header">
      <div class="header-left">
        <div class="logo-bar" />
        <h1>校园物资供应链 · 后勤运营指挥中心</h1>
      </div>
      <div class="header-right">
        <span class="clock">{{ formattedTime }}</span>
        <span class="refresh-hint">每 30 秒刷新</span>
      </div>
    </header>

    <main v-loading="loading" class="main">
      <template v-if="data">
        <section class="stat-section">
          <div
            v-for="(card, i) in statCards"
            :key="i"
            class="stat-card"
            :class="{ urgent: card.urgent }"
            @click="goTo(card.path)"
          >
            <div class="stat-value">{{ padNum(card.value) }}</div>
            <div class="stat-label">{{ card.label }}</div>
          </div>
        </section>

        <section class="content-section">
          <div class="panel chart-panel">
            <div class="panel-head">
              <span class="panel-title">采购申请态势</span>
              <span class="panel-sub">本周趋势</span>
            </div>
            <div id="lg-chart" class="chart" />
          </div>
          <div class="panel todo-panel">
            <div class="panel-head">
              <span class="panel-title">待办事项 · 闭环衔接</span>
            </div>
            <div class="list-wrap">
              <div
                v-for="p in data.pendingPurchases"
                :key="'p-' + p.id"
                class="list-row"
                @click="goTo('/purchase')"
              >
                <span class="col-order">{{ p.order_no }}</span>
                <span class="col-applicant">{{ p.applicant }}</span>
                <span class="col-summary">{{ p.summary }}</span>
              </div>
              <div
                v-for="p in handoffInProgress"
                :key="'h-' + p.id"
                class="list-row"
                @click="goTo('/purchase')"
              >
                <span class="col-order">{{ p.order_no }}</span>
                <span class="col-tag">{{ p.status_label }}</span>
                <span class="col-summary">{{ p.receiver_name }} · {{ p.destination }}</span>
              </div>
              <div v-if="!hasTodoItems" class="empty">
                暂无待办
              </div>
            </div>
          </div>
        </section>

        <section class="bottom-section">
          <div class="panel warning-panel">
            <div class="panel-head">
              <span class="panel-title">预警与风控</span>
              <span class="panel-badge">{{ data.warnings?.length || 0 }}</span>
            </div>
            <div class="list-wrap">
              <div v-for="w in data.warnings" :key="w.id" class="list-row alert-row">
                <span class="tag" :class="w.level">{{ w.level === 'high' ? '紧急' : '关注' }}</span>
                <span class="col-name">{{ w.material }}</span>
                <span class="col-desc">{{ w.desc }}</span>
              </div>
              <div v-if="!data.warnings?.length" class="empty">暂无预警</div>
            </div>
          </div>
          <div class="panel delivery-panel">
            <div class="panel-head">
              <span class="panel-title">在途配送</span>
              <span class="panel-badge">{{ data.deliveries?.length || 0 }}</span>
            </div>
            <div class="list-wrap">
              <div
                v-for="d in data.deliveries"
                :key="d.id"
                class="list-row"
                @click="goTo('/delivery')"
              >
                <span class="col-name">{{ d.delivery_no }}</span>
                <span class="col-dot" :class="d.status" />
                <span class="col-summary">{{ d.destination }} · {{ d.receiver_name }}</span>
              </div>
              <div v-if="!data.deliveries?.length" class="empty">暂无在途</div>
            </div>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<style lang="scss" scoped>
.screen {
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  color: #e2e8f0;
}

.bg-layer {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.bg-gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(160deg, #0a1929 0%, #0d2137 40%, #0a1628 100%);
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
  background-size: 48px 48px;
}

.bg-scan {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    transparent 0%,
    rgba(0, 212, 255, 0.02) 50%,
    transparent 100%
  );
  background-size: 100% 200px;
  animation: scan 8s linear infinite;
}

@keyframes scan {
  0% { background-position: 0 0; }
  100% { background-position: 0 200px; }
}

.header {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 32px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.15);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.logo-bar {
  width: 4px;
  height: 32px;
  background: linear-gradient(180deg, #00d4ff 0%, transparent 100%);
  border-radius: 2px;
}

.header h1 {
  font-size: 22px;
  font-weight: 600;
  color: #f1f5f9;
  letter-spacing: 0.5px;
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.clock {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 18px;
  font-weight: 500;
  color: #00d4ff;
  letter-spacing: 1px;
}

.refresh-hint {
  font-size: 12px;
  color: rgba(148, 163, 184, 0.7);
}

.main {
  position: relative;
  z-index: 1;
  padding: 24px 32px 32px;
  min-height: calc(100vh - 80px);
}

.stat-section {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: rgba(13, 33, 55, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
  padding: 20px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.25s ease;

  &:hover {
    border-color: rgba(0, 212, 255, 0.5);
    box-shadow: 0 0 24px rgba(0, 212, 255, 0.12);
  }

  &.urgent {
    border-color: rgba(245, 158, 11, 0.5);
    .stat-value { color: #fbbf24; }
  }

  &.urgent:hover {
    box-shadow: 0 0 24px rgba(245, 158, 11, 0.15);
  }
}

.stat-value {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 42px;
  font-weight: 700;
  color: #00d4ff;
  letter-spacing: 2px;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: rgba(148, 163, 184, 0.9);
  margin-top: 8px;
  letter-spacing: 0.3px;
}

.content-section {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 20px;
  margin-bottom: 24px;
}

.bottom-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.panel {
  background: rgba(13, 33, 55, 0.5);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 12px;
  padding: 20px 24px;
}

.panel-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #cbd5e1;
  letter-spacing: 0.5px;
}

.panel-sub {
  font-size: 12px;
  color: rgba(148, 163, 184, 0.6);
}

.panel-badge {
  font-size: 11px;
  padding: 2px 8px;
  background: rgba(0, 212, 255, 0.2);
  color: #00d4ff;
  border-radius: 4px;
  margin-left: auto;
}

.chart-panel .chart {
  height: 240px;
}

.list-wrap {
  max-height: 220px;
  overflow-y: auto;

  &::-webkit-scrollbar {
    width: 6px;
  }
  &::-webkit-scrollbar-track {
    background: rgba(0, 212, 255, 0.05);
    border-radius: 3px;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(0, 212, 255, 0.2);
    border-radius: 3px;
  }
}

.list-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  font-size: 13px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.06);
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: rgba(0, 212, 255, 0.06);
  }

  &:last-child {
    border-bottom: none;
  }
}

.col-order {
  min-width: 140px;
  font-family: 'Consolas', monospace;
  font-weight: 600;
  color: #00d4ff;
}

.col-applicant { color: #94a3b8; flex-shrink: 0; }
.col-name { flex: 1; color: #e2e8f0; min-width: 0; }
.col-summary { color: #94a3b8; font-size: 12px; flex: 1; min-width: 0; }
.col-desc { color: #94a3b8; font-size: 12px; flex: 1; min-width: 0; }

.col-tag {
  padding: 2px 8px;
  font-size: 11px;
  border-radius: 4px;
  background: rgba(0, 212, 255, 0.15);
  color: #67e8f9;
  flex-shrink: 0;
}

.tag {
  padding: 2px 8px;
  font-size: 11px;
  border-radius: 4px;
  flex-shrink: 0;
  &.high { background: rgba(239, 68, 68, 0.3); color: #fca5a5; }
  &:not(.high) { background: rgba(245, 158, 11, 0.25); color: #fcd34d; }
}

.col-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  background: #00d4ff;

  &.on_way { background: #22c55e; box-shadow: 0 0 8px rgba(34, 197, 94, 0.5); }
  &.pending, &.loading { background: #fbbf24; }
}

.alert-row { cursor: default; }
.alert-row:hover { background: transparent; }

.empty {
  padding: 32px;
  text-align: center;
  color: rgba(148, 163, 184, 0.5);
  font-size: 13px;
}

@media (max-width: 1400px) {
  .stat-section {
    grid-template-columns: repeat(3, 1fr);
  }
  .content-section {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .stat-section {
    grid-template-columns: repeat(2, 1fr);
  }
  .bottom-section {
    grid-template-columns: 1fr;
  }
}
</style>
