<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { getLogisticsScreen } from '@/api/dashboard'
import type { LogisticsScreenData } from '@/api/dashboard'

const router = useRouter()
const loading = ref(true)
const data = ref<LogisticsScreenData | null>(null)
let chartInstance: echarts.ECharts | null = null
let refreshTimer: ReturnType<typeof setInterval> | null = null

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
    tooltip: { trigger: 'axis' },
    legend: { data: ['采购申请'], textStyle: { color: '#e5e7eb', fontSize: 12 }, top: 8 },
    grid: { left: 48, right: 24, top: 36, bottom: 24 },
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: '#4b5563' } },
      axisLabel: { color: '#9ca3af', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#374151' } },
      axisLabel: { color: '#9ca3af', fontSize: 11 },
    },
    series: [
      {
        name: '采购申请',
        type: 'line',
        smooth: true,
        data: purchase,
        itemStyle: { color: '#8b5cf6' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(139, 92, 246, 0.3)' },
              { offset: 1, color: 'rgba(139, 92, 246, 0.02)' },
            ],
          },
        },
      },
    ],
  })
}

const nextTick = (fn: () => void) => setTimeout(fn, 50)

function goTo(path: string) {
  router.push(path)
}

onMounted(() => {
  load()
  refreshTimer = setInterval(load, 30000)
})

onUnmounted(() => {
  refreshTimer && clearInterval(refreshTimer)
  chartInstance?.dispose()
})
</script>

<template>
  <div class="logistics-screen">
    <div class="screen-header">
      <h1>后勤管理大屏</h1>
      <span class="refresh-hint">每30秒自动刷新</span>
    </div>
    <div v-loading="loading" class="screen-body">
      <template v-if="data">
        <div class="stat-row">
          <div class="stat-card" @click="goTo('/purchase')">
            <div class="stat-value">{{ data.stats.purchasePending }}</div>
            <div class="stat-label">待审批</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ data.stats.supplierPending }}</div>
            <div class="stat-label">待供应商接单</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ data.stats.stockPending }}</div>
            <div class="stat-label">待仓储入库</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ data.stats.dispatchPending }}</div>
            <div class="stat-label">待出库/待建配送</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ data.stats.receivePending }}</div>
            <div class="stat-label">待老师签收</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ data.stats.purchaseCompleted }}</div>
            <div class="stat-label">已闭环完成</div>
          </div>
        </div>
        <div class="content-row">
          <div class="panel chart-panel">
            <h3>采购申请趋势（本周）</h3>
            <div id="lg-chart" class="chart" />
          </div>
          <div class="panel side-panel">
            <h3>待审批采购</h3>
            <div class="list">
              <div v-for="p in data.pendingPurchases" :key="p.id" class="list-item clickable" @click="goTo('/purchase')">
                <span class="order">{{ p.order_no }}</span>
                <span class="applicant">{{ p.applicant }}</span>
                <span class="summary">{{ p.summary }}</span>
              </div>
              <div v-if="!data.pendingPurchases.length" class="empty">暂无待审批</div>
            </div>
          </div>
        </div>
        <div class="content-row">
          <div class="panel">
            <h3>闭环交接总览</h3>
            <div class="list">
              <div v-for="p in data.handoffList" :key="p.id" class="list-item clickable" @click="goTo('/purchase')">
                <span class="order">{{ p.order_no }}</span>
                <span class="tag medium">{{ p.status_label }}</span>
                <span class="summary">交接码：{{ p.handoff_code }}</span>
                <span class="desc">收货人：{{ p.receiver_name }} · 目的地：{{ p.destination }}</span>
              </div>
              <div v-if="!data.handoffList.length" class="empty">暂无链路数据</div>
            </div>
          </div>
          <div class="panel">
            <h3>后勤重点事项</h3>
            <div class="list">
              <div class="list-item clickable" @click="goTo('/supplier')">
                <span class="name">合作供应商</span>
                <span class="desc">{{ data.stats.supplierCount }} 家</span>
              </div>
              <div class="list-item clickable" @click="goTo('/warning')">
                <span class="name">待处理预警</span>
                <span class="desc">{{ data.stats.warningPending }} 条</span>
              </div>
              <div class="list-item clickable" @click="goTo('/delivery')">
                <span class="name">进行中配送</span>
                <span class="desc">{{ data.stats.deliveryOngoing }} 单</span>
              </div>
            </div>
          </div>
        </div>
        <div class="content-row half">
          <div class="panel">
            <h3>待处理预警</h3>
            <div class="list">
              <div v-for="w in data.warnings" :key="w.id" class="list-item alert">
                <span class="tag" :class="w.level">{{ w.level === 'high' ? '紧急' : '关注' }}</span>
                <span class="name">{{ w.material }}</span>
                <span class="desc">{{ w.desc }}</span>
              </div>
              <div v-if="!data.warnings.length" class="empty">暂无预警</div>
            </div>
          </div>
          <div class="panel">
            <h3>进行中配送</h3>
            <div class="list">
              <div v-for="d in data.deliveries" :key="d.id" class="list-item clickable" @click="goTo('/delivery')">
                <span class="name">{{ d.delivery_no }}</span>
                <span class="summary">交接码：{{ d.handoff_code }}</span>
                <span class="desc">{{ d.destination }} · {{ d.receiver_name }} · {{ d.status }}</span>
              </div>
              <div v-if="!data.deliveries.length" class="empty">暂无</div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.logistics-screen {
  min-height: 100vh;
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%);
  color: #e5e7eb;
  padding: 24px;
}

.screen-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  h1 { font-size: 28px; font-weight: 700; color: #f8fafc; }
  .refresh-hint { font-size: 12px; color: #a5b4fc; }
}

.screen-body { min-height: 400px; }

.stat-row {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  background: rgba(49, 46, 129, 0.5);
  border: 1px solid #4c1d95;
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  &:hover { border-color: #8b5cf6; background: rgba(139, 92, 246, 0.2); }
  &.warning:hover { border-color: #f59e0b; }
}

.stat-value { font-size: 32px; font-weight: 700; color: #a78bfa; }
.stat-card.warning .stat-value { color: #fbbf24; }
.stat-label { font-size: 13px; color: #a5b4fc; margin-top: 8px; }

.content-row {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 20px;
  margin-bottom: 24px;
  &.half { grid-template-columns: 1fr 1fr; }
}

.panel {
  background: rgba(49, 46, 129, 0.5);
  border: 1px solid #4c1d95;
  border-radius: 12px;
  padding: 20px;
  h3 { font-size: 16px; margin-bottom: 16px; color: #c4b5fd; }
}

.chart-panel .chart { height: 260px; }
.side-panel .list { max-height: 240px; overflow-y: auto; }

.list-item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px solid #4c1d95;
  font-size: 13px;
  .order { font-weight: 600; color: #a78bfa; min-width: 140px; }
  .applicant { color: #94a3b8; }
  .name { flex: 1; color: #e5e7eb; }
  .summary, .desc { width: 100%; color: #94a3b8; font-size: 12px; }
  &.clickable { cursor: pointer; &:hover { background: rgba(139, 92, 246, 0.1); } }
  .tag { padding: 2px 8px; border-radius: 4px; font-size: 11px; }
  .tag.high { background: #dc2626; color: #fff; }
  .tag.medium { background: #d97706; color: #fff; }
}
.list-item.alert .desc { flex: 1; font-size: 12px; }
.empty { color: #64748b; padding: 20px; text-align: center; }
</style>
