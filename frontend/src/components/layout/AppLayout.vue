<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElNotification, ElMessageBox } from 'element-plus'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import { useUserStore } from '@/stores/user'
import { useNoticeStore } from '@/stores/notice'
import { getAndClearWarningToLogistics, clearWarningToLogistics } from '@/stores/demo'
import { listPurchases } from '@/api/purchase'
import { listSupplierOrders } from '@/api/supplier'
import { listMyPurchases } from '@/api/purchase'

const route = useRoute()
const userStore = useUserStore()
const noticeStore = useNoticeStore()
const sidebarCollapsed = ref(false)

/** 数据大屏与侧栏、顶栏统一深色指挥台，避免浅色导航压在霓虹内容上 */
const immersiveScreen = computed(() => {
  const p = route.path || ''
  return p.startsWith('/screen/')
})

const pageTitle = computed(() => (route.meta?.title as string) || '')
const role = computed(() => userStore.userInfo?.role as string)

let pollingTimer: number | null = null
const prevCounts: Record<string, number> = {}

const POLL_INTERVAL = 25000

function notifyIfIncreased(key: string, count: number, title: string, message: string, type: 'warning' | 'info' | 'success' = 'warning') {
  const prev = prevCounts[key] ?? 0
  prevCounts[key] = count
  if (count > 0 && count > prev) {
    ElNotification({ title, message, type, duration: 5000 })
  }
}

function markSeen(key: string) {
  prevCounts[key] = 0
}

async function refreshPurchaseReminder(options?: { silent?: boolean }) {
  if (role.value !== 'logistics_admin') {
    noticeStore.clearNewPurchaseCount()
    return
  }
  try {
    const res: any = await listPurchases({ status: 'pending' })
    const data = Array.isArray(res) ? res : res?.data ?? []
    const list = data.filter((x: any) => x?.status === 'pending')
    const count = list.length
    noticeStore.setNewPurchaseCount(count)
    if (!options?.silent) notifyIfIncreased('purchase', count, '新申请提醒', `收到 ${count} 条新的待审批申请，请及时处理。`)
  } catch {
    noticeStore.clearNewPurchaseCount()
  }
}

async function refreshSupplierOrderReminder(options?: { silent?: boolean }) {
  if (role.value !== 'campus_supplier') {
    noticeStore.clearSupplierOrderCount()
    return
  }
  try {
    const res: any = await listSupplierOrders()
    const data = Array.isArray(res) ? res : res?.data ?? []
    const list = data.filter((x: any) => x?.status === 'approved' || x?.status === 'confirmed')
    const count = list.length
    noticeStore.setSupplierOrderCount(count)
    if (!options?.silent) notifyIfIncreased('supplier', count, '待办提醒', `有 ${count} 条待办订单（待接单/待发货），请及时处理。`)
  } catch {
    noticeStore.clearSupplierOrderCount()
  }
}

async function refreshWarehouseReminder(options?: { silent?: boolean }) {
  if (role.value !== 'warehouse_procurement') {
    noticeStore.clearWarehouseCounts()
    return
  }
  try {
    const [inRes, outRes]: any[] = await Promise.all([
      listPurchases(),
      listPurchases({ status: 'stocked_in' }),
    ])
    const inList = Array.isArray(inRes) ? inRes : inRes?.data ?? []
    const outList = Array.isArray(outRes) ? outRes : outRes?.data ?? []
    const inCount = inList.filter(
      (x: any) => (x?.status === 'approved' && !x?.supplier_id) || x?.status === 'shipped'
    ).length
    const outCount = outList.filter((x: any) => x?.status === 'stocked_in').length
    noticeStore.setWarehouseStockInCount(inCount)
    noticeStore.setWarehouseStockOutCount(outCount)
    const total = inCount + outCount
    if (!options?.silent && total > 0) {
      const prev = (prevCounts['warehouse_in'] ?? 0) + (prevCounts['warehouse_out'] ?? 0)
      prevCounts['warehouse_in'] = inCount
      prevCounts['warehouse_out'] = outCount
      if (total > prev) {
        const parts: string[] = []
        if (inCount) parts.push(`${inCount} 条待入库`)
        if (outCount) parts.push(`${outCount} 条待出库`)
        ElNotification({ title: '仓储待办提醒', message: parts.join('，') + '，请及时处理。', type: 'warning', duration: 5000 })
      }
    }
  } catch {
    noticeStore.clearWarehouseCounts()
  }
}

async function refreshDeliveryToCreateReminder(options?: { silent?: boolean }) {
  if (role.value !== 'logistics_admin' && role.value !== 'warehouse_procurement') {
    noticeStore.clearDeliveryToCreateCount()
    return
  }
  try {
    const res: any = await listPurchases({ status: 'stocked_out' })
    const data = Array.isArray(res) ? res : res?.data ?? []
    const list = data.filter((x: any) => x?.status === 'stocked_out')
    const count = list.length
    noticeStore.setDeliveryToCreateCount(count)
    if (!options?.silent) notifyIfIncreased('delivery', count, '待创建配送提醒', `有 ${count} 条出库单待创建配送，请及时处理。`)
  } catch {
    noticeStore.clearDeliveryToCreateCount()
  }
}

async function refreshTeacherReceiveReminder(options?: { silent?: boolean }) {
  if (role.value !== 'counselor_teacher') {
    noticeStore.clearTeacherReceiveCount()
    return
  }
  try {
    const res: any = await listMyPurchases()
    const data = Array.isArray(res) ? res : res?.data ?? []
    const list = data.filter((x: any) => x?.can_confirm_receive === true)
    const count = list.length
    noticeStore.setTeacherReceiveCount(count)
    if (!options?.silent) notifyIfIncreased('teacher', count, '待签收提醒', `有 ${count} 个配送已到达，请及时确认收货。`, 'info')
  } catch {
    noticeStore.clearTeacherReceiveCount()
  }
}

async function refreshAll(options?: { silent?: boolean }) {
  await Promise.all([
    refreshPurchaseReminder(options),
    refreshSupplierOrderReminder(options),
    refreshWarehouseReminder(options),
    refreshDeliveryToCreateReminder(options),
    refreshTeacherReceiveReminder(options),
  ])
}

async function markCurrentAsSeen() {
  const path = route.path
  if (path.startsWith('/purchase') && role.value === 'logistics_admin') {
    markSeen('purchase')
    noticeStore.clearNewPurchaseCount()
  }
  if (path.startsWith('/supplier/orders') && role.value === 'campus_supplier') {
    markSeen('supplier')
    noticeStore.clearSupplierOrderCount()
  }
  if ((path.startsWith('/stock/in') || path.startsWith('/stock/out')) && role.value === 'warehouse_procurement') {
    markSeen('warehouse_in')
    markSeen('warehouse_out')
    noticeStore.clearWarehouseCounts()
  }
  if (path.startsWith('/delivery') && (role.value === 'logistics_admin' || role.value === 'warehouse_procurement')) {
    markSeen('delivery')
    noticeStore.clearDeliveryToCreateCount()
  }
  if (path.startsWith('/my-applications') && role.value === 'counselor_teacher') {
    markSeen('teacher')
    noticeStore.clearTeacherReceiveCount()
  }
}

function startPolling() {
  if (pollingTimer) clearInterval(pollingTimer)
  pollingTimer = window.setInterval(() => refreshAll(), POLL_INTERVAL)
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

function showLogisticsWarning(warn: { subject: string; body: string }) {
  ElMessageBox.alert(
    `【审计警告】\n\n${warn.subject}\n\n${warn.body}`,
    '管理员已向您发起警告',
    { type: 'warning', confirmButtonText: '已知晓' }
  )
}

function initLogisticsWarningCheck() {
  if (role.value !== 'logistics_admin') return
  const warn = getAndClearWarningToLogistics()
  if (warn) showLogisticsWarning(warn)
  const handler = (e: CustomEvent) => {
    showLogisticsWarning(e.detail)
    clearWarningToLogistics()
  }
  window.addEventListener('demo-logistics-warning', handler as EventListener)
  onBeforeUnmount(() => {
    window.removeEventListener('demo-logistics-warning', handler as EventListener)
  })
}

function syncImmersiveBodyClass(on: boolean) {
  if (typeof document === 'undefined') return
  document.body.classList.toggle('layout-immersive', on)
}

watch(
  immersiveScreen,
  (v) => {
    syncImmersiveBodyClass(v)
  },
  { immediate: true }
)

onMounted(async () => {
  await refreshAll({ silent: true })
  await markCurrentAsSeen()
  startPolling()
  initLogisticsWarningCheck()
})

watch(
  () => route.path,
  async () => {
    await markCurrentAsSeen()
  }
)

watch(
  () => userStore.userInfo?.id,
  async () => {
    await refreshAll({ silent: true })
    startPolling()
  }
)

onBeforeUnmount(() => {
  stopPolling()
  syncImmersiveBodyClass(false)
})
</script>

<template>
  <div class="app-layout" :class="{ 'app-layout--immersive': immersiveScreen }">
    <AppSidebar v-model:collapsed="sidebarCollapsed" :immersive="immersiveScreen" />
    <div class="main-wrapper" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'main-wrapper--immersive': immersiveScreen }">
      <AppHeader
        :title="pageTitle"
        :collapsed="sidebarCollapsed"
        :immersive="immersiveScreen"
        @toggle="sidebarCollapsed = !sidebarCollapsed"
      />
      <main class="main-content" :class="{ 'main-content--immersive': immersiveScreen }">
        <Transition name="page" mode="out-in">
          <router-view v-slot="{ Component }">
            <component :is="Component" />
          </router-view>
        </Transition>
      </main>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  background: var(--bg-base);
}

.main-wrapper {
  flex: 1;
  margin-left: 220px;
  transition: margin-left var(--transition-base);
  display: flex;
  flex-direction: column;
  min-width: 0;

  &.sidebar-collapsed {
    margin-left: 68px;
  }
}

.main-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.app-layout--immersive {
  background: var(--screen-bg-mid);
}

.main-wrapper--immersive {
  background: transparent;
}

.main-content--immersive {
  padding: 0;
  overflow-x: hidden;
  overflow-y: auto;
  background: transparent;
}

.page-enter-active,
.page-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
