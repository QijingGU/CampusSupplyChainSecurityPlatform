<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getWarehouseScreen } from '@/api/dashboard'
import { createStockIn, createStockOut } from '@/api/stock'
import { createDelivery } from '@/api/delivery'
import type { WarehouseScreenData } from '@/api/dashboard'

const router = useRouter()
const loading = ref(true)
const data = ref<WarehouseScreenData | null>(null)
let chartInstance: echarts.ECharts | null = null
let refreshTimer: ReturnType<typeof setInterval> | null = null

async function load() {
  try {
    const res: any = await getWarehouseScreen()
    data.value = (res?.data ?? res) as WarehouseScreenData
    nextTick(() => renderChart())
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
}

function renderChart() {
  const el = document.getElementById('wh-chart')
  if (!el || !data.value?.chart) return
  if (!chartInstance) chartInstance = echarts.init(el)
  const { labels, in: inVals, out: outVals } = data.value.chart
  chartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { data: ['入库', '出库'], textStyle: { color: '#e5e7eb', fontSize: 12 }, top: 8 },
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
      { name: '入库', type: 'bar', data: inVals, itemStyle: { color: '#3b82f6' } },
      { name: '出库', type: 'bar', data: outVals, itemStyle: { color: '#10b981' } },
    ],
  })
}

const nextTick = (fn: () => void) => setTimeout(fn, 50)

function goTo(path: string) {
  router.push(path)
}

async function quickStockIn(task: { id: number }) {
  try {
    await createStockIn({ purchase_id: task.id })
    ElMessage.success('入库成功')
    load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '入库失败')
  }
}

async function quickStockOut(task: { id: number }) {
  try {
    await createStockOut({ purchase_id: task.id })
    ElMessage.success('出库成功')
    load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '出库失败')
  }
}

async function quickCreateDelivery(task: { id: number; destination?: string; receiver_name?: string }) {
  try {
    await createDelivery({
      purchase_id: task.id,
      destination: task.destination || '',
      receiver_name: task.receiver_name || '',
    })
    ElMessage.success('配送单已创建')
    load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '创建失败')
  }
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
  <div class="warehouse-screen">
    <div class="screen-header">
      <h1>仓储管理大屏</h1>
      <span class="refresh-hint">每30秒自动刷新</span>
    </div>
    <div v-loading="loading" class="screen-body">
      <template v-if="data">
        <div class="stat-row">
          <div class="stat-card" @click="goTo('/stock/inventory')">
            <div class="stat-value">{{ data.stats.inventoryQtySum }}</div>
            <div class="stat-label">库存总量</div>
          </div>
          <div class="stat-card" @click="goTo('/stock/in')">
            <div class="stat-value">{{ data.stats.pendingStockIn }}</div>
            <div class="stat-label">待入库申请</div>
          </div>
          <div class="stat-card" @click="goTo('/stock/out')">
            <div class="stat-value">{{ data.stats.pendingStockOut }}</div>
            <div class="stat-label">待按申请出库</div>
          </div>
          <div class="stat-card" @click="goTo('/delivery')">
            <div class="stat-value">{{ data.stats.pendingDeliveryCreate }}</div>
            <div class="stat-label">待创建配送</div>
          </div>
          <div class="stat-card" @click="goTo('/stock/in')">
            <div class="stat-value">{{ data.stats.stockInToday }}</div>
            <div class="stat-label">今日入库</div>
          </div>
          <div class="stat-card" @click="goTo('/stock/out')">
            <div class="stat-value">{{ data.stats.stockOutToday }}</div>
            <div class="stat-label">今日出库</div>
          </div>
          <div class="stat-card" @click="goTo('/delivery')">
            <div class="stat-value">{{ data.stats.waitingReceive }}</div>
            <div class="stat-label">待老师签收</div>
          </div>
          <div class="stat-card warning" @click="goTo('/warning')">
            <div class="stat-value">{{ data.stats.warningPending }}</div>
            <div class="stat-label">待处理预警</div>
          </div>
          <div class="stat-card" @click="goTo('/delivery')">
            <div class="stat-value">{{ data.stats.deliveryOngoing }}</div>
            <div class="stat-label">进行中配送</div>
          </div>
        </div>
        <div class="content-row">
          <div class="panel chart-panel">
            <h3>出入库趋势（本周）</h3>
            <div id="wh-chart" class="chart" />
          </div>
          <div class="panel side-panel">
            <h3>库存 TOP10</h3>
            <div class="list">
              <div v-for="(item, i) in data.inventoryTop" :key="i" class="list-item">
                <span class="name">{{ item.name }}</span>
                <span class="val">{{ item.quantity }}</span>
              </div>
              <div v-if="!data.inventoryTop.length" class="empty">暂无数据</div>
            </div>
          </div>
        </div>
        <div class="content-row full">
          <div class="panel">
            <h3>仓储执行闭环</h3>
            <div class="list">
              <div v-for="task in data.handoffTasks" :key="task.id" class="list-item clickable">
                <span class="name">{{ task.order_no }}</span>
                <span class="tag medium">{{ task.status_label }}</span>
                <span class="desc">收货人：{{ task.receiver_name }} · 地点：{{ task.destination }}</span>
                <span class="desc">交接码：{{ task.handoff_code }}</span>
                <span class="desc">{{ task.summary }}</span>
                <span class="task-actions" @click.stop>
                  <el-button
                    v-if="task.status === 'shipped' || task.status === 'approved'"
                    type="primary"
                    size="small"
                    @click="quickStockIn(task)"
                  >
                    入库
                  </el-button>
                  <el-button v-if="task.status === 'stocked_in'" type="success" size="small" @click="quickStockOut(task)">
                    出库
                  </el-button>
                  <el-button v-if="task.status === 'stocked_out'" type="warning" size="small" @click="quickCreateDelivery(task)">
                    创建配送
                  </el-button>
                  <el-button v-if="!['approved','shipped','stocked_in','stocked_out'].includes(task.status)" type="info" link size="small" @click="goTo('/purchase')">
                    详情
                  </el-button>
                </span>
              </div>
              <div v-if="!data.handoffTasks.length" class="empty">暂无待执行闭环任务</div>
            </div>
          </div>
        </div>
        <div class="content-row">
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
            <h3>临期/低库存</h3>
            <div class="list">
              <div v-for="(e, i) in data.expiring" :key="i" class="list-item">
                <span class="name">{{ e.name }}</span>
                <span class="val">{{ e.days }}天 / {{ e.count }}件</span>
              </div>
              <div v-if="!data.expiring.length" class="empty">暂无</div>
            </div>
          </div>
          <div class="panel">
            <h3>进行中配送</h3>
            <div class="list">
              <div v-for="d in data.deliveries" :key="d.id" class="list-item">
                <span class="name">{{ d.delivery_no }}</span>
                <span class="desc">{{ d.destination }} · {{ d.receiver_name }} · {{ d.status_label }}</span>
                <span class="desc">交接码：{{ d.handoff_code }}</span>
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
.warehouse-screen {
  min-height: 100vh;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
  color: #e5e7eb;
  padding: 24px;
}

.screen-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  h1 { font-size: 28px; font-weight: 700; color: #f8fafc; }
  .refresh-hint { font-size: 12px; color: #94a3b8; }
}

.screen-body { min-height: 400px; }

.stat-row {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid #334155;
  border-radius: 16px;
  padding: 28px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  &:hover { border-color: #3b82f6; background: rgba(59, 130, 246, 0.1); }
  &.warning:hover { border-color: #f59e0b; }
}

.stat-value { font-size: 36px; font-weight: 700; color: #60a5fa; }
.stat-card.warning .stat-value { color: #fbbf24; }
.stat-label { font-size: 14px; color: #94a3b8; margin-top: 8px; }

.content-row {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 20px;
  margin-bottom: 24px;
  &.full { grid-template-columns: 1fr; }
  &:last-of-type {
    grid-template-columns: 1fr 1fr 1fr;
  }
}

.panel {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 20px;
  h3 { font-size: 16px; margin-bottom: 16px; color: #cbd5e1; }
}

.chart-panel .chart { height: 260px; }
.side-panel .list { max-height: 240px; overflow-y: auto; }

.list-item {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #334155;
  font-size: 13px;
  .name { flex: 1; color: #e5e7eb; }
  .val, .desc { color: #94a3b8; }
  .tag { padding: 2px 8px; border-radius: 4px; font-size: 11px; }
  .tag.high { background: #dc2626; color: #fff; }
  .tag.medium { background: #d97706; color: #fff; }
  &.clickable { cursor: pointer; }
  &.clickable:hover { background: rgba(59, 130, 246, 0.06); }
  .desc { width: 100%; }
}
.list-item.alert .desc { flex: 1; font-size: 12px; }
.task-actions { display: flex; gap: 8px; flex-shrink: 0; }
.empty { color: #64748b; padding: 20px; text-align: center; }
</style>
