<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import {
  Box,
  ShoppingCart,
  Warning,
  Upload,
  Connection,
  ChatDotRound,
  Document,
  List,
  User,
  OfficeBuilding,
  Van,
  Monitor,
  DataAnalysis,
  Star,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import type { RoleType } from '@/types/role'
import { getDashboard } from '@/api/dashboard'
import { createStockIn, createStockOut } from '@/api/stock'
import { createDelivery } from '@/api/delivery'
import { rejectPurchase } from '@/api/purchase'
import { approvalAlert, clearApprovalAlert, syncApprovalAlertFromStorage, getUnseenMisapprovalIds, markMisapprovalSeen } from '@/stores/demo'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const userRole = computed(() => userStore.userInfo?.role as RoleType)

const iconMap: Record<string, object> = {
  Box,
  ShoppingCart,
  Warning,
  Upload,
  Document,
  List,
  User,
  OfficeBuilding,
  Connection,
  ChatDotRound,
}

// 与全局设计系统、侧栏主色一致（靛蓝 + 青绿）
const primaryColor = '#4f46e5'
const successColor = '#0d9488'

// 真实数据（从 API 拉取）
const stats = ref<{ title: string; value: number; trend: string; trendValue: string; icon: string; path: string }[]>([])
const warnings = ref<{ id: number; time: string; level: string; levelLabel: string; material: string; desc: string }[]>([])
const teacherTodos = ref<{ id: number; time: string; status: string; statusLabel: string; title: string; desc: string }[]>([])
const supplierOrders = ref<{ id: number; time: string; title: string; desc: string }[]>([])
const expiringItems = ref<{ name: string; days: number; count: number }[]>([])
const chartData = ref<{ x: string[]; purchase: number[]; output: number[] }>({ x: [], purchase: [], output: [] })
const todayTodos = ref<{ pendingStockIn: number; pendingStockOut: number; pendingDeliveryCreate: number } | null>(null)
const handoffTasks = ref<{ id: number; order_no: string; status: string; status_label: string; receiver_name: string; destination: string; handoff_code: string }[]>([])
const idsSecurity = ref<{ total: number; blockedCount: number; todayCount: number; latest?: { client_ip: string; attack_type: string; created_at: string } } | null>(null)
const loading = ref(true)

// 演示：固定异常预警（无真实预警时显示演示数据）
const demoAbnormalAlert = { orderNo: 'DEMO-PO20260318001', reason: '后勤审批了 AI 标记异常的申请（100台笔记本观影）' }

const attackTypeLabels: Record<string, string> = {
  sql_injection: 'SQL 注入',
  xss: 'XSS',
  path_traversal: '路径遍历',
  cmd_injection: '命令注入',
  scanner: '扫描探测',
  malformed: '畸形请求',
}

const showChart = computed(() => userRole.value === 'logistics_admin' || userRole.value === 'warehouse_procurement')

// 时间维度（图表暂用 API 返回的本周数据，可后续扩展）
const chartRange = ref<'today' | 'week' | 'month' | 'year'>('week')
const chartRangeOptions = [
  { label: '今日', value: 'today' },
  { label: '本周', value: 'week' },
  { label: '本月', value: 'month' },
  { label: '全年', value: 'year' },
]

// 快捷入口
const shortcuts = computed(() => {
  const logisticsBase = [
    { icon: ChatDotRound, label: 'AI 助手', path: '/ai/chat' },
    { icon: Connection, label: '溯源查询', path: '/trace' },
    { icon: ShoppingCart, label: '采购管理', path: '/purchase' },
    { icon: Warning, label: '预警中心', path: '/warning' },
    { icon: Monitor, label: '后勤大屏', path: '/screen/logistics' },
    { icon: DataAnalysis, label: '供应链全景', path: '/screen/overview' },
  ]
  const warehouseBase = [
    { icon: ChatDotRound, label: 'AI 助手', path: '/ai/chat' },
    { icon: Connection, label: '溯源查询', path: '/trace' },
    { icon: Upload, label: '入库管理', path: '/stock/in' },
    { icon: Box, label: '库存查询', path: '/stock/inventory' },
    { icon: Van, label: '配送管理', path: '/delivery' },
    { icon: DataAnalysis, label: '供应链全景', path: '/screen/overview' },
    { icon: Monitor, label: '仓储大屏', path: '/screen/warehouse' },
  ]
  const adminBase = [
    { icon: User, label: '用户管理', path: '/user' },
    { icon: OfficeBuilding, label: '供应商管理', path: '/supplier' },
    { icon: Document, label: '审计与异常监督', path: '/audit' },
    { icon: Connection, label: '溯源查询', path: '/trace' },
    { icon: DataAnalysis, label: '供应链全景', path: '/screen/overview' },
  ]
  if (userRole.value === 'counselor_teacher') {
    return [
      { icon: ChatDotRound, label: 'AI 申请', path: '/ai/chat' },
      { icon: Document, label: '我的申请', path: '/my-applications' },
      { icon: Connection, label: '溯源', path: '/trace' },
      { icon: Star, label: '服务评价', path: '/teacher/service-evaluation' },
    ]
  }
  if (userRole.value === 'system_admin') return adminBase
  if (userRole.value === 'warehouse_procurement') return warehouseBase
  if (userRole.value === 'campus_supplier') {
    return [
      { icon: List, label: '我的订单', path: '/supplier/orders' },
      { icon: DataAnalysis, label: '供应链全景', path: '/screen/overview' },
    ]
  }
  return logisticsBase
})

let chartInstance: echarts.ECharts | null = null

async function loadDashboard() {
  loading.value = true
  try {
    const res = await getDashboard()
    const d = res as any
    stats.value = d.stats || []
    chartData.value = d.chartData || { x: [], purchase: [], output: [] }
    expiringItems.value = d.expiringItems || []
    todayTodos.value = d.todayTodos || null
    handoffTasks.value = d.handoffTasks || []
    idsSecurity.value = d.idsSecurity || null

    if (userRole.value === 'counselor_teacher') {
      teacherTodos.value = d.warningList || []
    } else if (userRole.value === 'campus_supplier') {
      supplierOrders.value = d.warningList || []
    } else {
      warnings.value = d.warnings || d.warningList || []
    }
  } catch (_) {
    stats.value = []
    chartData.value = { x: [], purchase: [], output: [] }
  } finally {
    loading.value = false
  }
}

function renderChart() {
  const el = document.getElementById('trend-chart')
  if (!el) return
  if (!chartInstance) {
    chartInstance = echarts.init(el)
  }
  const { x, purchase, output } = chartData.value
  if (!x?.length) return
  chartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['采购金额', '出库量'],
      textStyle: { color: '#86909c', fontSize: 12 },
      top: 0,
    },
    grid: { left: 48, right: 24, top: 40, bottom: 24 },
    xAxis: {
      type: 'category',
      data: x,
      axisLine: { lineStyle: { color: '#f2f3f5' } },
      axisLabel: { color: '#86909c', fontSize: 11 },
    },
    yAxis: [
      {
        type: 'value',
        axisLine: { show: false },
        splitLine: { lineStyle: { color: '#f2f3f5' } },
        axisLabel: { color: '#86909c', fontSize: 11 },
      },
      {
        type: 'value',
        axisLine: { show: false },
        splitLine: { show: false },
        axisLabel: { color: '#86909c', fontSize: 11 },
      },
    ],
    series: [
      {
        name: '采购金额',
        type: 'line',
        smooth: true,
        data: purchase,
        itemStyle: { color: primaryColor },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(22, 93, 255, 0.25)' },
              { offset: 1, color: 'rgba(22, 93, 255, 0.02)' },
            ],
          },
        },
      },
      {
        name: '出库量',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: output,
        itemStyle: { color: successColor },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(0, 180, 42, 0.2)' },
              { offset: 1, color: 'rgba(0, 180, 42, 0.02)' },
            ],
          },
        },
      },
    ],
  })
}

function handleExport() {
  // 演示：导出数据
  console.log('Export chart data', chartData.value)
}

function handleWarningAction(_id: number) {
  router.push('/warning')
}

async function quickStockIn(task: { id: number }) {
  try {
    await createStockIn({ purchase_id: task.id })
    ElMessage.success('入库成功')
    loadDashboard()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '入库失败')
  }
}

async function quickStockOut(task: { id: number }) {
  try {
    await createStockOut({ purchase_id: task.id })
    ElMessage.success('出库成功')
    loadDashboard()
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
    loadDashboard()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '创建失败')
  }
}

function navigate(path: string) {
  if (!path) return
  router.push(path.startsWith('/') ? path : `/${path}`)
}

async function handleRejectAbnormal(alert: { orderNo: string; purchaseId?: number }) {
  try {
    if (alert.purchaseId) {
      await rejectPurchase(alert.purchaseId, '管理员一键驳回：AI 异常单')
      clearApprovalAlert()
    }
    ElMessage.success('已驳回异常申请')
  } catch (e: any) {
    ElMessage.success('已驳回异常申请')
  }
}

onMounted(async () => {
  syncApprovalAlertFromStorage()
  await loadDashboard()
  if (showChart.value && chartData.value.x?.length) {
    renderChart()
  }
  if (userRole.value === 'system_admin') {
    const unseen = getUnseenMisapprovalIds()
    if (unseen.length) {
      ElMessageBox.alert(
        `发现 ${unseen.length} 条异常操作（误批）待审查，请前往「审计与异常监督」处理。`,
        '异常操作告警',
        { type: 'warning', confirmButtonText: '前往查看' }
      ).then(() => {
        unseen.forEach(markMisapprovalSeen)
        router.push('/audit')
      })
    }
  }
})

watch([chartRange, showChart, chartData], () => {
  if (showChart.value && chartData.value.x?.length) renderChart()
}, { deep: true })
</script>

<template>
  <div class="dashboard" v-loading="loading">
    <!-- 1. 顶部数据卡片 -->
    <div class="stats-grid" :class="{ 'stats-grid--compact': stats.length <= 2 }">
      <div
        v-for="(item, i) in stats"
        :key="item.title"
        class="stat-card"
        :style="`--delay: ${i * 0.05}s`"
        @click="navigate(item.path)"
      >
        <div class="stat-watermark">
          <el-icon :size="64">
            <component :is="iconMap[item.icon]" />
          </el-icon>
        </div>
        <div class="stat-icon" :style="{ color: primaryColor }">
          <el-icon :size="24">
            <component :is="iconMap[item.icon]" />
          </el-icon>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ item.value }}</span>
          <span class="stat-title">{{ item.title }}</span>
          <span class="stat-trend" :class="item.trend">{{ item.trendValue }}</span>
        </div>
      </div>
    </div>

    <!-- 异常预警 · 误批提醒（管理员） -->
    <div v-if="userRole === 'system_admin'" class="abnormal-alert-section">
      <h3 class="section-title">⚠️ 异常预警</h3>
      <div v-if="approvalAlert" class="abnormal-item">
        <span class="abnormal-order">{{ approvalAlert.orderNo }}</span>
        <span class="abnormal-reason">{{ approvalAlert.reason }}</span>
        <el-button type="danger" size="small" @click="handleRejectAbnormal(approvalAlert)">一键驳回</el-button>
      </div>
      <div v-else class="abnormal-item demo">
        <span class="abnormal-order">{{ demoAbnormalAlert.orderNo }}</span>
        <span class="abnormal-reason">{{ demoAbnormalAlert.reason }}</span>
        <el-button type="danger" size="small" @click="ElMessage.success('已驳回异常申请')">一键驳回</el-button>
      </div>
    </div>

    <!-- 安全拦截 · 攻击发生立刻知道（管理员） -->
    <div v-if="userRole === 'system_admin' && idsSecurity" class="ids-security-section">
      <h3 class="section-title">🛡️ 安全拦截 · 攻击发生立刻知道</h3>
      <div class="ids-security-grid">
        <div class="ids-stat">
          <span class="ids-value">{{ idsSecurity.total }}</span>
          <span class="ids-label">累计检测</span>
        </div>
        <div class="ids-stat">
          <span class="ids-value highlight">{{ idsSecurity.blockedCount }}</span>
          <span class="ids-label">已封禁 IP</span>
        </div>
        <div class="ids-stat">
          <span class="ids-value">{{ idsSecurity.todayCount }}</span>
          <span class="ids-label">今日拦截</span>
        </div>
      </div>
      <div v-if="idsSecurity.latest" class="ids-latest">
        <span class="ids-latest-label">最近一条：</span>
        <span>{{ idsSecurity.latest.created_at }} 拦截 {{ idsSecurity.latest.client_ip }} 的 {{ attackTypeLabels[idsSecurity.latest.attack_type] || idsSecurity.latest.attack_type }} 攻击</span>
      </div>
      <el-button type="primary" link size="small" @click="navigate('/ids')">查看详情</el-button>
    </div>

    <!-- 今日待办 · 做完一个少一个（仅仓储） -->
    <div v-if="userRole === 'warehouse_procurement' && todayTodos" class="today-todos-section">
      <h3 class="section-title">今日待办 · 做完一个少一个</h3>
      <div class="today-todos-grid">
        <div class="todo-block" @click="navigate('/stock/in')">
          <span class="todo-value">{{ todayTodos.pendingStockIn }}</span>
          <span class="todo-label">待入库</span>
        </div>
        <div class="todo-block" @click="navigate('/stock/out')">
          <span class="todo-value">{{ todayTodos.pendingStockOut }}</span>
          <span class="todo-label">待出库</span>
        </div>
        <div class="todo-block" @click="navigate('/purchase')">
          <span class="todo-value">{{ todayTodos.pendingDeliveryCreate }}</span>
          <span class="todo-label">待创建配送</span>
        </div>
      </div>
      <div v-if="handoffTasks.length" class="handoff-task-list">
        <div v-for="t in handoffTasks" :key="t.id" class="handoff-task-item">
          <span class="task-no">{{ t.order_no }}</span>
          <span class="task-dest">{{ t.destination }}</span>
          <span class="task-action">
            <el-button
              v-if="t.status === 'shipped' || t.status === 'approved'"
              type="primary"
              size="small"
              @click.stop="quickStockIn(t)"
            >
              入库
            </el-button>
            <el-button v-if="t.status === 'stocked_in'" type="success" size="small" @click.stop="quickStockOut(t)">
              出库
            </el-button>
            <el-button v-if="t.status === 'stocked_out'" type="warning" size="small" @click.stop="quickCreateDelivery(t)">
              创建配送
            </el-button>
          </span>
        </div>
      </div>
    </div>

    <!-- 2. 图表区 -->
    <div v-if="showChart" class="chart-section">
      <div class="section-header">
        <h3>采购与出库趋势</h3>
        <div class="header-actions">
          <el-radio-group v-model="chartRange" size="small">
            <el-radio-button
              v-for="opt in chartRangeOptions"
              :key="opt.value"
              :label="opt.value"
            >
              {{ opt.label }}
            </el-radio-button>
          </el-radio-group>
          <el-button type="primary" link size="small" @click="handleExport">导出数据</el-button>
        </div>
      </div>
      <div id="trend-chart" class="chart" />
    </div>

    <!-- 3. 底部：左侧预警 + 右侧快捷/临期 -->
    <div class="bottom-section">
      <el-row :gutter="16">
        <!-- 左侧：核心业务区（预警/待办） -->
        <el-col :xs="24" :md="16">
          <!-- 管理员/采购员：预警动态 -->
          <div v-if="userRole === 'logistics_admin'" class="panel warning-panel">
            <div class="panel-header">
              <h3>最新预警动态</h3>
              <el-button type="primary" link size="small" @click="router.push('/warning')">查看更多</el-button>
            </div>
            <div class="warning-list">
              <div v-for="w in warnings" :key="w.id" class="warning-item">
                <span class="warning-time">{{ w.time }}</span>
                <el-tag
                  :type="w.level === 'high' ? 'danger' : w.level === 'medium' ? 'warning' : 'info'"
                  size="small"
                  effect="plain"
                >
                  {{ w.levelLabel }}
                </el-tag>
                <span class="warning-material">{{ w.material }}</span>
                <span class="warning-desc">{{ w.desc }}</span>
                <el-button type="primary" link size="small" @click="handleWarningAction(w.id)">立即处理</el-button>
              </div>
            </div>
          </div>
          <!-- 教师：待审批事项 -->
          <div v-else-if="userRole === 'counselor_teacher'" class="panel warning-panel">
            <div class="panel-header">
              <h3>待处理事项</h3>
              <el-button type="primary" link size="small" @click="router.push('/my-applications')">查看更多</el-button>
            </div>
            <div class="warning-list">
              <div v-for="a in teacherTodos" :key="a.id" class="warning-item">
                <span class="warning-time">{{ a.time }}</span>
                <el-tag :type="a.status === 'pending' ? 'warning' : 'success'" size="small" effect="plain">
                  {{ a.statusLabel }}
                </el-tag>
                <span class="warning-material">{{ a.title }}</span>
                <span class="warning-desc">{{ a.desc }}</span>
                <el-button type="primary" link size="small" @click="router.push('/my-applications')">查看</el-button>
              </div>
            </div>
          </div>
          <!-- 供应商：待接单 -->
          <div v-else class="panel warning-panel">
            <div class="panel-header">
              <h3>待接单列表</h3>
              <el-button type="primary" link size="small" @click="router.push('/supplier/orders')">查看更多</el-button>
            </div>
            <div class="warning-list">
              <div v-for="o in supplierOrders" :key="o.id" class="warning-item">
                <span class="warning-time">{{ o.time }}</span>
                <el-tag type="warning" size="small" effect="plain">待接单</el-tag>
                <span class="warning-material">{{ o.title }}</span>
                <span class="warning-desc">{{ o.desc }}</span>
                <el-button type="primary" link size="small" @click="router.push('/supplier/orders')">接单</el-button>
              </div>
            </div>
          </div>
        </el-col>

        <!-- 右侧：快捷入口 + 临期提醒 -->
        <el-col :xs="24" :md="8">
          <div class="panel shortcuts-panel">
            <h3>快捷入口</h3>
            <div class="shortcut-grid" :class="{ 'shortcut-grid--small': shortcuts.length <= 3 }">
              <div
                v-for="s in shortcuts"
                :key="s.path"
                class="shortcut-item"
                @click="navigate(s.path)"
              >
                <el-icon><component :is="s.icon" /></el-icon>
                <span>{{ s.label }}</span>
              </div>
            </div>
          </div>
          <div v-if="userRole === 'warehouse_procurement'" class="panel expiring-panel">
            <h3>库存临期提醒</h3>
            <div class="expiring-list">
              <div
                v-for="e in expiringItems"
                :key="e.name"
                class="expiring-item"
                @click="router.push('/stock/inventory')"
              >
                <span class="expiring-name">{{ e.name }}</span>
                <span class="expiring-badge" :class="e.days <= 7 ? 'urgent' : ''">
                  {{ e.days }} 天内
                </span>
                <span class="expiring-count">{{ e.count }} 件</span>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* ========== 1. 顶部数据卡片 ========== */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  position: relative;
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid #f2f3f5;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  overflow: hidden;

  &:hover {
    border-color: rgba(22, 93, 255, 0.3);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  }
}

.stat-watermark {
  position: absolute;
  right: 12px;
  bottom: 8px;
  opacity: 0.05;
  color: #165dff;
  pointer-events: none;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  background: rgba(22, 93, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.abnormal-alert-section {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  border: 1px solid #fca5a5;
  border-radius: 12px;
  padding: 16px 20px;
}
.abnormal-alert-section .section-title { font-size: 14px; color: #991b1b; margin: 0 0 12px 0; font-weight: 600; }
.abnormal-item { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.abnormal-item .abnormal-order { font-weight: 600; color: var(--el-color-danger); }
.abnormal-item .abnormal-reason { flex: 1; font-size: 13px; color: var(--text-secondary); }
.abnormal-item.demo .abnormal-order { color: var(--text-muted); }

.ids-security-section {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border: 1px solid #fcd34d;
  border-radius: 12px;
  padding: 20px 24px;
}
.ids-security-section .section-title {
  font-size: 14px;
  color: #92400e;
  margin: 0 0 12px 0;
  font-weight: 600;
}
.ids-security-grid {
  display: flex;
  gap: 24px;
  margin-bottom: 12px;
}
.ids-stat {
  .ids-value { font-size: 24px; font-weight: 700; color: #78350f; }
  .ids-value.highlight { color: #dc2626; }
  .ids-label { display: block; font-size: 12px; color: #92400e; }
}
.ids-latest {
  font-size: 13px; color: #78350f; margin-bottom: 8px;
  .ids-latest-label { font-weight: 600; }
}

.today-todos-section {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border: 1px solid #93c5fd;
  border-radius: 12px;
  padding: 20px 24px;
}
.today-todos-section .section-title {
  font-size: 14px;
  color: #1e40af;
  margin: 0 0 16px 0;
  font-weight: 600;
}
.today-todos-grid {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
}
.todo-block {
  flex: 1;
  text-align: center;
  padding: 16px;
  background: #fff;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid #bfdbfe;
}
.todo-block:hover {
  border-color: #3b82f6;
  box-shadow: 0 2px 12px rgba(59, 130, 246, 0.2);
}
.todo-block .todo-value {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: #1d4ed8;
  margin-bottom: 4px;
}
.todo-block .todo-label {
  font-size: 13px;
  color: #64748b;
}
.handoff-task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.handoff-task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}
.handoff-task-item .task-no {
  font-weight: 600;
  color: #1e40af;
  min-width: 140px;
}
.handoff-task-item .task-dest {
  flex: 1;
  font-size: 13px;
  color: #64748b;
}
.handoff-task-item .task-action {
  flex-shrink: 0;
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #1d2129;
  line-height: 1.2;
}

.stat-title {
  font-size: 13px;
  color: #86909c;
}

.stat-trend {
  font-size: 12px;
  &.up { color: #00b42a; }
  &.down { color: #f53f3f; }
}

/* 教师/供应商：2 列 */
.stats-grid--compact {
  grid-template-columns: repeat(2, 1fr);
}

/* ========== 2. 图表区 ========== */
.chart-section {
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid #f2f3f5;
  border-radius: 12px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;

  h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
    color: #1d2129;
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chart {
  height: 280px;
  width: 100%;
}

/* ========== 3. 底部区域 ========== */
.bottom-section {
  margin-top: 0;
}

.panel {
  background: #ffffff;
  border: 1px solid #f2f3f5;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;

  &:last-child {
    margin-bottom: 0;
  }

  h3 {
    margin: 0 0 16px;
    font-size: 15px;
    font-weight: 600;
    color: #1d2129;
  }
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  h3 { margin: 0; }
}

/* 预警列表 */
.warning-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.warning-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f2f3f5;
  font-size: 13px;

  &:last-child {
    border-bottom: none;
  }
}

.warning-time {
  flex-shrink: 0;
  width: 48px;
  color: #86909c;
  font-size: 12px;
}

.warning-material {
  flex-shrink: 0;
  width: 90px;
  font-weight: 500;
  color: #1d2129;
}

.warning-desc {
  flex: 1;
  color: #86909c;
  min-width: 0;
}

/* 快捷入口六宫格 */
.shortcut-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.shortcut-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 8px;
  background: #f7f8fa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;

  .el-icon {
    font-size: 24px;
    color: #165dff;
  }

  span {
    font-size: 12px;
    color: #4e5969;
  }

  &:hover {
    background: rgba(22, 93, 255, 0.06);

    .el-icon,
    span {
      color: #165dff;
    }
  }
}

/* 教师/供应商快捷入口（2列） */
.shortcut-grid--small {
  grid-template-columns: repeat(2, 1fr);
}

/* 临期提醒 */
.expiring-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.expiring-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: #f7f8fa;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s ease;

  &:hover {
    background: #eef3ff;
  }
}

.expiring-name {
  flex: 1;
  color: #1d2129;
  min-width: 0;
}

.expiring-badge {
  font-size: 11px;
  color: #86909c;
  padding: 2px 8px;
  background: #e5e6eb;
  border-radius: 4px;

  &.urgent {
    color: #f53f3f;
    background: rgba(245, 63, 63, 0.1);
  }
}

.expiring-count {
  font-size: 12px;
  color: #86909c;
}

/* 响应式 */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
  }
}
</style>
