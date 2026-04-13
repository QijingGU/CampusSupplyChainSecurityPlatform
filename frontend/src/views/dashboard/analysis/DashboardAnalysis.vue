<script setup lang="ts">
/**
 * 全景大屏：分析看板（ECharts）+ 供应链闭环监测（原全景大屏）
 */
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { Box, Van, Warning, ShoppingCart } from '@element-plus/icons-vue'
import SupplyChainOverviewScreen from '@/views/screen/SupplyChainOverviewScreen.vue'
import {
  chartEnterAnimation,
  seriesDataStaggerDelay,
  chartPieSectorEnter,
  chartBarGrowSeries,
} from '@/utils/chartAnimation'

const primary = '#4f46e5'
const teal = '#0d9488'
const amber = '#d97706'

const metrics = [
  { label: '今日采购额', value: '¥ 128.6k', change: '+8.2%', up: true, icon: ShoppingCart },
  { label: '在途配送单', value: '86', change: '+12%', up: true, icon: Van },
  { label: '入库完成批次', value: '34', change: '-3%', up: false, icon: Box },
  { label: '未闭环预警', value: '7', change: '+2', up: false, icon: Warning },
]

const route = useRoute()
const router = useRouter()
const sectionTab = ref<'analysis' | 'panorama'>('analysis')

function syncSectionFromRoute() {
  sectionTab.value = route.query.view === 'panorama' ? 'panorama' : 'analysis'
}

watch(
  () => route.query.view,
  () => syncSectionFromRoute()
)

watch(sectionTab, (v) => {
  const cur = route.query.view === 'panorama' ? 'panorama' : 'analysis'
  if (v === cur) return
  const q = { ...route.query } as Record<string, string>
  if (v === 'panorama') q.view = 'panorama'
  else delete q.view
  void router.replace({ query: q })
})

const lineRef = ref<HTMLDivElement | null>(null)
const pieRef = ref<HTMLDivElement | null>(null)
const barRef = ref<HTMLDivElement | null>(null)
const gaugeRef = ref<HTMLDivElement | null>(null)
const hbarRef = ref<HTMLDivElement | null>(null)
const mixRef = ref<HTMLDivElement | null>(null)

const charts: echarts.ECharts[] = []
let ro: ResizeObserver | null = null

function initCharts() {
  const commonGrid = { left: 48, right: 16, top: 36, bottom: 24 }

  if (lineRef.value) {
    const c = echarts.init(lineRef.value)
    charts.push(c)
    c.setOption({
      ...chartEnterAnimation,
      backgroundColor: 'transparent',
      title: { text: '采购与出库（近 7 日）', left: 0, top: 0, textStyle: { fontSize: 14, fontWeight: 600 } },
      tooltip: { trigger: 'axis' },
      legend: { data: ['采购额(万)', '出库件数'], top: 28, textStyle: { fontSize: 11 } },
      grid: { ...commonGrid, top: 56 },
      xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'], axisLine: { lineStyle: { color: '#eee' } } },
      yAxis: [
        { type: 'value', splitLine: { lineStyle: { color: '#f2f2f2' } } },
        { type: 'value', splitLine: { show: false } },
      ],
      series: [
        {
          name: '采购额(万)',
          type: 'line',
          smooth: true,
          data: [12, 19, 15, 22, 18, 24, 21],
          animationDelay: seriesDataStaggerDelay(7),
          itemStyle: { color: primary },
          areaStyle: { color: 'rgba(79,70,229,0.08)' },
        },
        {
          name: '出库件数',
          type: 'bar',
          yAxisIndex: 1,
          data: [320, 450, 380, 510, 490, 620, 540],
          ...chartBarGrowSeries,
          animationDelay: seriesDataStaggerDelay(7, 220, 55),
          itemStyle: { color: teal, borderRadius: [4, 4, 0, 0] },
        },
      ],
    })
  }

  if (pieRef.value) {
    const c = echarts.init(pieRef.value)
    charts.push(c)
    c.setOption({
      ...chartEnterAnimation,
      backgroundColor: 'transparent',
      title: { text: '订单状态分布', left: 0, top: 0, textStyle: { fontSize: 14, fontWeight: 600 } },
      tooltip: { trigger: 'item' },
      legend: { bottom: 0, textStyle: { fontSize: 11 } },
      series: [
        {
          type: 'pie',
          ...chartPieSectorEnter,
          radius: ['42%', '68%'],
          center: ['50%', '46%'],
          avoidLabelOverlap: true,
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          data: [
            { value: 128, name: '待审批' },
            { value: 86, name: '在途' },
            { value: 210, name: '已入库' },
            { value: 64, name: '待配送' },
            { value: 42, name: '已完成' },
          ],
          color: [primary, '#818cf8', teal, amber, '#94a3b8'],
        },
      ],
    })
  }

  if (barRef.value) {
    const c = echarts.init(barRef.value)
    charts.push(c)
    c.setOption({
      ...chartEnterAnimation,
      backgroundColor: 'transparent',
      title: { text: '目标达成 · 本月', left: 0, top: 0, textStyle: { fontSize: 14, fontWeight: 600 } },
      tooltip: { trigger: 'axis' },
      legend: { data: ['计划', '实际'], top: 26, textStyle: { fontSize: 11 } },
      grid: { ...commonGrid, top: 52 },
      xAxis: { type: 'category', data: ['W1', 'W2', 'W3', 'W4'], axisLine: { lineStyle: { color: '#eee' } } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: '#f2f2f2' } } },
      series: [
        {
          name: '计划',
          type: 'bar',
          data: [100, 100, 100, 100],
          ...chartBarGrowSeries,
          animationDelay: seriesDataStaggerDelay(4),
          itemStyle: { color: '#e2e8f0', borderRadius: [4, 4, 0, 0] },
        },
        {
          name: '实际',
          type: 'bar',
          data: [92, 88, 95, 78],
          ...chartBarGrowSeries,
          animationDelay: seriesDataStaggerDelay(4, 180, 70),
          itemStyle: { color: primary, borderRadius: [4, 4, 0, 0] },
        },
      ],
    })
  }

  if (gaugeRef.value) {
    const c = echarts.init(gaugeRef.value)
    charts.push(c)
    c.setOption({
      ...chartEnterAnimation,
      backgroundColor: 'transparent',
      title: { text: '供应商准时交付率', left: 0, top: 0, textStyle: { fontSize: 14, fontWeight: 600 } },
      series: [
        {
          type: 'gauge',
          animationDuration: 1200,
          animationEasing: 'cubicOut',
          center: ['50%', '58%'],
          radius: '78%',
          min: 0,
          max: 100,
          splitNumber: 10,
          axisLine: {
            lineStyle: {
              width: 14,
              color: [
                [0.7, '#f59e0b'],
                [0.85, '#6366f1'],
                [1, '#0d9488'],
              ],
            },
          },
          pointer: { itemStyle: { color: primary } },
          axisTick: { distance: -14, length: 6 },
          splitLine: { distance: -18, length: 14 },
          axisLabel: { fontSize: 10 },
          detail: { valueAnimation: true, fontSize: 22, offsetCenter: [0, '24%'], formatter: '{value}%' },
          data: [{ value: 87.5, name: '' }],
        },
      ],
    })
  }

  if (hbarRef.value) {
    const c = echarts.init(hbarRef.value)
    charts.push(c)
    c.setOption({
      ...chartEnterAnimation,
      backgroundColor: 'transparent',
      title: { text: '物资品类出库 TOP', left: 0, top: 0, textStyle: { fontSize: 14, fontWeight: 600 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 8, right: 24, top: 40, bottom: 8 },
      xAxis: { type: 'value', splitLine: { lineStyle: { color: '#f2f2f2' } } },
      yAxis: {
        type: 'category',
        data: ['消毒液', '打印纸', '实验耗材', '教材包', '办公文具'],
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: [
        {
          type: 'bar',
          data: [820, 760, 640, 520, 410],
          ...chartBarGrowSeries,
          animationDelay: seriesDataStaggerDelay(5),
          itemStyle: { color: teal, borderRadius: [0, 6, 6, 0] },
        },
      ],
    })
  }

  if (mixRef.value) {
    const c = echarts.init(mixRef.value)
    charts.push(c)
    c.setOption({
      ...chartEnterAnimation,
      backgroundColor: 'transparent',
      title: { text: '仓储吞吐与服务水平', left: 0, top: 0, textStyle: { fontSize: 14, fontWeight: 600 } },
      tooltip: { trigger: 'axis' },
      legend: { data: ['入库量', '出库量', 'SLA%'], top: 26, textStyle: { fontSize: 11 } },
      grid: { ...commonGrid, top: 54 },
      xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月'], axisLine: { lineStyle: { color: '#eee' } } },
      yAxis: [
        { type: 'value', name: '件', splitLine: { lineStyle: { color: '#f2f2f2' } } },
        { type: 'value', name: '%', max: 100, splitLine: { show: false } },
      ],
      series: [
        {
          name: '入库量',
          type: 'bar',
          data: [1200, 1320, 1100, 1450, 1380, 1520],
          ...chartBarGrowSeries,
          animationDelay: seriesDataStaggerDelay(6),
          itemStyle: { color: '#c7d2fe' },
        },
        {
          name: '出库量',
          type: 'bar',
          data: [980, 1050, 1120, 1180, 1210, 1290],
          ...chartBarGrowSeries,
          animationDelay: seriesDataStaggerDelay(6, 200, 55),
          itemStyle: { color: primary },
        },
        {
          name: 'SLA%',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          data: [94, 93, 95, 96, 95, 97],
          animationDelay: seriesDataStaggerDelay(6, 400, 45),
          itemStyle: { color: amber },
        },
      ],
    })
  }
}

onMounted(async () => {
  syncSectionFromRoute()
  await nextTick()
  initCharts()
  ro = new ResizeObserver(() => {
    charts.forEach((c) => c.resize())
  })
  ;[lineRef, pieRef, barRef, gaugeRef, hbarRef, mixRef].forEach((r) => {
    if (r.value && ro) ro.observe(r.value)
  })
})

onBeforeUnmount(() => {
  ro?.disconnect()
  charts.forEach((c) => c.dispose())
  charts.length = 0
})
</script>

<template>
  <div class="panorama-root">
    <el-tabs v-model="sectionTab" class="panorama-tabs">
      <el-tab-pane label="数据看板" name="analysis">
        <div class="analysis-page">
    <el-row :gutter="20" class="row-block">
      <el-col :xl="14" :lg="15" :xs="24">
        <div class="art-card metrics-card">
          <div class="card-hd">
            <div>
              <h4>今日供应链概览</h4>
              <p>采购 · 仓储 · 配送 · 预警（演示指标）</p>
            </div>
            <el-button size="small" type="primary" plain>导出简报</el-button>
          </div>
          <el-row :gutter="16" class="metrics-row">
            <el-col v-for="(m, i) in metrics" :key="i" :span="6" :xs="12">
              <div class="metric-tile">
                <div class="metric-ico">
                  <el-icon :size="22"><component :is="m.icon" /></el-icon>
                </div>
                <div class="metric-body">
                  <span class="metric-val">{{ m.value }}</span>
                  <span class="metric-lab">{{ m.label }}</span>
                  <small class="metric-sub">
                    较昨日
                    <em :class="m.up ? 'up' : 'down'">{{ m.change }}</em>
                  </small>
                </div>
              </div>
            </el-col>
          </el-row>
        </div>
        <div class="art-card chart-card">
          <div ref="lineRef" class="chart-box chart-tall" />
        </div>
      </el-col>
      <el-col :xl="10" :lg="9" :xs="24">
        <div class="art-card chart-card">
          <div ref="pieRef" class="chart-box chart-mid" />
        </div>
        <div class="art-card chart-card">
          <div ref="gaugeRef" class="chart-box chart-mid" />
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="row-block">
      <el-col :xl="10" :lg="10" :xs="24">
        <div class="art-card chart-card">
          <div ref="barRef" class="chart-box chart-mid" />
        </div>
      </el-col>
      <el-col :xl="7" :lg="7" :xs="24">
        <div class="art-card chart-card">
          <div ref="hbarRef" class="chart-box chart-mid" />
        </div>
      </el-col>
      <el-col :xl="7" :lg="7" :xs="24">
        <div class="art-card chart-card">
          <div ref="mixRef" class="chart-box chart-mid" />
        </div>
      </el-col>
    </el-row>
        </div>
      </el-tab-pane>
      <el-tab-pane label="供应链闭环" name="panorama">
        <SupplyChainOverviewScreen embedded />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped lang="scss">
.panorama-root {
  padding-bottom: 8px;
}
.panorama-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 16px;
  }
}
.analysis-page {
  padding-bottom: 24px;
}
.row-block {
  margin-bottom: 4px;
}
.art-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 20px 22px;
  margin-bottom: 20px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.card-hd {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 18px;
  h4 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
  }
  p {
    margin: 6px 0 0;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
}
.metric-tile {
  display: flex;
  gap: 12px;
  padding: 16px 14px;
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  background: linear-gradient(180deg, #fafbff 0%, #fff 100%);
  transition:
    border-color 0.25s ease,
    box-shadow 0.25s ease;
  &:hover {
    border-color: rgba(79, 70, 229, 0.25);
    box-shadow: 0 6px 20px rgba(79, 70, 229, 0.06);
  }
}
.metric-ico {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: rgba(79, 70, 229, 0.1);
  color: #4f46e5;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.metric-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.metric-val {
  font-size: 20px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}
.metric-lab {
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.metric-sub {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  em {
    font-style: normal;
    font-weight: 600;
    margin-left: 4px;
    &.up {
      color: var(--el-color-success);
    }
    &.down {
      color: var(--el-color-danger);
    }
  }
}
.metrics-row {
  margin-top: 4px;
}
.chart-card {
  padding-top: 12px;
}
.chart-box {
  width: 100%;
}
.chart-tall {
  height: 320px;
}
.chart-mid {
  height: 280px;
}
@media (max-width: 768px) {
  .chart-tall {
    height: 260px;
  }
  .chart-mid {
    height: 240px;
  }
}
</style>
