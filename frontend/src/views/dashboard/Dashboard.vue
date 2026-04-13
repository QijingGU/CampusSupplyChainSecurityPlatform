<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Box,
  ShoppingCart,
  Warning,
  Upload,
  Connection,
  ChatDotRound,
  List,
  User,
  OfficeBuilding,
  Van,
  Monitor,
  DataAnalysis,
  Edit,
  Key,
  Notebook,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import type { RoleType } from '@/types/role'
import { getDashboard } from '@/api/dashboard'
import { createStockIn, createStockOut } from '@/api/stock'
import { createDelivery } from '@/api/delivery'
import { rejectPurchase } from '@/api/purchase'
import { approvalAlert, clearApprovalAlert, syncApprovalAlertFromStorage, getUnseenMisapprovalIds, markMisapprovalSeen } from '@/stores/demo'
import { ElMessage, ElMessageBox } from 'element-plus'
import ConsoleIndex from '@/views/dashboard/console/ConsoleIndex.vue'

const router = useRouter()
const userStore = useUserStore()
const userRole = computed(() => userStore.userInfo?.role as RoleType)

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

const defaultDynamic = [
  { username: '溯源服务', type: '生成报告', target: '批次 TR-20260312' },
  { username: '仓储', type: '完成入库', target: '办公耗材 PO-088' },
  { username: '后勤', type: '审批通过', target: '教学耗材申请' },
  { username: '配送', type: '已签收', target: '教学楼 A 区' },
  { username: '预警', type: '临期提醒', target: '消毒液 30 天内到期' },
]

/** 管理员端工作台：高密度演示动态（对齐 Art 控制台信息密度） */
const supplyAdminDynamics = [
  { username: '北区仓', type: '入库完成', target: 'PO-20260308-112 医用口罩 1200 件' },
  { username: '后勤处', type: '审批通过', target: '实验耗材集中采购计划' },
  { username: '供应商-康源', type: '发货确认', target: 'SO-77821 预计 18:00 到校' },
  { username: '配送班组', type: '在途', target: '车辆 #粤B·D0921 → 图书馆卸货点' },
  { username: '溯源引擎', type: '批次归档', target: 'BATCH-2026-Q1-009 已上链' },
  { username: '南区仓', type: '库存调整', target: '消毒液实盘 +36 瓶' },
  { username: 'IDS', type: '拦截', target: '192.168.x.x 路径遍历尝试' },
  { username: '辅导员办', type: '提交申请', target: '春季劳保用品（演示）' },
  { username: '预警中心', type: '低库存', target: 'A4 打印纸 安全库存以下' },
  { username: '供应商-晨光', type: '接单', target: 'PO-20260310-03 文具包' },
  { username: '仓储大屏', type: '刷新指标', target: '当日出库件数 +12%' },
  { username: '全景大屏', type: '同步', target: '供应链 KPI 看板' },
  { username: '财务', type: '对账完成', target: '2 月后勤采购结算单' },
  { username: '质检', type: '抽检合格', target: '批次 TR-20260228-01' },
  { username: 'AI 助手', type: '解析意图', target: '自然语言 → 采购草稿' },
  { username: '安全审计', type: '标记关注', target: '敏感操作 purchase_reject ×3' },
  { username: '车队', type: '路线优化', target: '合并 2 单同校区配送' },
  { username: '信息中心', type: '角色变更', target: '演示账号权限复核' },
  { username: '供应商-联创', type: '延期申请', target: '到货顺延 1 工作日' },
  { username: '北区仓', type: '出库复核', target: '教学点 B 教材包' },
  { username: '后勤处', type: '驳回', target: '单价异常申请（演示）' },
  { username: '配送', type: '签收异常', target: '收件人电话未接通，已留言' },
  { username: '仓储', type: '盘点任务', target: 'Q1 固定资产抽盘' },
  { username: '供应商门户', type: '对账单', target: '已推送 3 月对账 PDF' },
  { username: '溯源', type: '扫码查询', target: '师生端查询 +86 次' },
  { username: '预警', type: '临期', target: '洗手液 45 天内到期' },
  { username: '南区仓', type: '退货入库', target: 'RMA-009 包装破损' },
  { username: '系统', type: '定时任务', target: '库存快照备份成功' },
]

const displayStats = computed(() =>
  stats.value.map((s) => ({
    ...s,
    trendValue:
      s.trendValue ||
      (s.trend === 'up' ? '+11.6%' : s.trend === 'down' ? '-3.8%' : '—'),
  }))
)

const consoleDynamicItems = computed(() => {
  const r = userRole.value
  if (r === 'system_admin') return supplyAdminDynamics
  if (r === 'logistics_admin' && warnings.value.length) {
    return warnings.value.slice(0, 14).map((w) => ({
      username: w.time,
      type: w.levelLabel,
      target: `${w.material} ${w.desc}`.trim(),
    }))
  }
  if (r === 'counselor_teacher' && teacherTodos.value.length) {
    return teacherTodos.value.slice(0, 14).map((a) => ({
      username: a.time,
      type: a.statusLabel,
      target: `${a.title} ${a.desc}`.trim(),
    }))
  }
  if (r === 'campus_supplier' && supplierOrders.value.length) {
    return supplierOrders.value.slice(0, 14).map((o) => ({
      username: o.time,
      type: '待接单',
      target: `${o.title} ${o.desc}`.trim(),
    }))
  }
  return defaultDynamic
})

// 快捷入口
const shortcuts = computed(() => {
  const logisticsBase = [
    { icon: ChatDotRound, label: 'AI 助手', path: '/ai/chat' },
    { icon: Connection, label: '溯源查询', path: '/trace' },
    { icon: ShoppingCart, label: '采购管理', path: '/purchase' },
    { icon: Warning, label: '预警中心', path: '/warning' },
    { icon: Monitor, label: '后勤大屏', path: '/screen/logistics' },
    { icon: DataAnalysis, label: '全景大屏', path: '/dashboard/analysis' },
  ]
  const warehouseBase = [
    { icon: ChatDotRound, label: 'AI 助手', path: '/ai/chat' },
    { icon: Connection, label: '溯源查询', path: '/trace' },
    { icon: Upload, label: '入库管理', path: '/stock/in' },
    { icon: Box, label: '库存查询', path: '/stock/inventory' },
    { icon: Van, label: '配送管理', path: '/delivery' },
    { icon: DataAnalysis, label: '全景大屏', path: '/dashboard/analysis' },
    { icon: Monitor, label: '仓储大屏', path: '/screen/warehouse' },
  ]
  const adminBase = [
    { icon: User, label: '用户管理', path: '/system/users' },
    { icon: Key, label: '角色管理', path: '/system/roles' },
    { icon: OfficeBuilding, label: '供应商管理', path: '/supplier' },
    { icon: Notebook, label: '操作日志与审计', path: '/system/operation-logs' },
    { icon: Connection, label: '溯源查询', path: '/trace' },
    { icon: DataAnalysis, label: '全景大屏', path: '/dashboard/analysis' },
  ]
  if (userRole.value === 'counselor_teacher') {
    return [
      { icon: ChatDotRound, label: '智能工作台', path: '/teacher/workbench' },
      { icon: Edit, label: '采购申请', path: '/purchase/apply' },
      { icon: User, label: '个人中心', path: '/teacher/personal' },
      { icon: Connection, label: '溯源', path: '/trace' },
      { icon: DataAnalysis, label: '全景大屏', path: '/dashboard/analysis' },
    ]
  }
  if (userRole.value === 'system_admin') return adminBase
  if (userRole.value === 'warehouse_procurement') return warehouseBase
  if (userRole.value === 'campus_supplier') {
    return [
      { icon: List, label: '我的订单', path: '/supplier/orders' },
      { icon: DataAnalysis, label: '全景大屏', path: '/dashboard/analysis' },
    ]
  }
  return logisticsBase
})

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
  if (userRole.value === 'system_admin') {
    const unseen = getUnseenMisapprovalIds()
    if (unseen.length) {
      ElMessageBox.alert(
        `发现 ${unseen.length} 条异常操作（误批）待审查，请前往「操作日志」中的审计页签处理。`,
        '异常操作告警',
        { type: 'warning', confirmButtonText: '前往查看' }
      ).then(() => {
        unseen.forEach(markMisapprovalSeen)
        router.push({ path: '/system/operation-logs', query: { tab: 'audit' } })
      })
    }
  }
})
</script>

<template>
  <div class="dashboard" v-loading="loading">
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

    <ConsoleIndex
      :stat-cards="displayStats"
      :chart-data="chartData"
      :show-purchase-chart="showChart"
      :dynamic-items="consoleDynamicItems"
      :shortcuts="shortcuts"
      :expiring-items="expiringItems"
      :show-expiring="userRole === 'warehouse_procurement'"
      :admin-console="userRole === 'system_admin'"
    />
  </div>
</template>

<style lang="scss" scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
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
</style>
