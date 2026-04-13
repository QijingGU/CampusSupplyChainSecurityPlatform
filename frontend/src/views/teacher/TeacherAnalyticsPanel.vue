<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const pieRef = ref<HTMLElement>()
const barRef = ref<HTMLElement>()
const lineRef = ref<HTMLElement>()
let pieChart: echarts.ECharts | null = null
let barChart: echarts.ECharts | null = null
let lineChart: echarts.ECharts | null = null

function initCharts() {
  if (pieRef.value) {
    pieChart = echarts.init(pieRef.value)
    pieChart.setOption({
      title: { text: '常用物资分类占比', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'item' },
      series: [
        {
          type: 'pie',
          radius: ['42%', '68%'],
          data: [
            { value: 38, name: '办公耗材' },
            { value: 24, name: '实验教具' },
            { value: 18, name: '体育器材' },
            { value: 12, name: '保洁消杀' },
            { value: 8, name: '其他' },
          ],
        },
      ],
    })
  }
  if (barRef.value) {
    barChart = echarts.init(barRef.value)
    barChart.setOption({
      title: { text: '教研室额度使用率（演示）', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: ['Q1', 'Q2', 'Q3', 'Q4'] },
      yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
      series: [{ type: 'bar', data: [62, 71, 58, 44], itemStyle: { color: '#6366f1' } }],
    })
  }
  if (lineRef.value) {
    lineChart = echarts.init(lineRef.value)
    lineChart.setOption({
      title: { text: '月度申领趋势对比', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0, data: ['本年', '去年'] },
      xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月'] },
      yAxis: { type: 'value', name: '单数' },
      series: [
        { name: '本年', type: 'line', smooth: true, data: [3, 5, 4, 8, 6, 7] },
        { name: '去年', type: 'line', smooth: true, data: [2, 4, 3, 5, 5, 4] },
      ],
    })
  }
}

function resizeAll() {
  pieChart?.resize()
  barChart?.resize()
  lineChart?.resize()
}

onMounted(() => {
  initCharts()
  window.addEventListener('resize', resizeAll)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeAll)
  pieChart?.dispose()
  barChart?.dispose()
  lineChart?.dispose()
  pieChart = barChart = lineChart = null
})
</script>

<template>
  <div class="analytics-panel">
    <p class="lead">以下图表为前端演示数据，用于展示个人物资消耗的复盘视角。</p>
    <div class="chart-grid">
      <div ref="pieRef" class="chart-box" />
      <div ref="barRef" class="chart-box" />
      <div ref="lineRef" class="chart-box chart-box--wide" />
    </div>
  </div>
</template>

<style scoped lang="scss">
.analytics-panel {
  padding: 0;
}
.lead {
  margin: 0 0 20px 0;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}
.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.chart-box {
  height: 300px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 8px;
}
.chart-box--wide {
  grid-column: 1 / -1;
  height: 320px;
}
@media (max-width: 900px) {
  .chart-grid {
    grid-template-columns: 1fr;
  }
  .chart-box--wide {
    grid-column: 1;
  }
}
</style>
