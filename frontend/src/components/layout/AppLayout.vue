<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElNotification, ElMessageBox } from 'element-plus'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import { useUserStore } from '@/stores/user'
import { useNoticeStore } from '@/stores/notice'
import { getAndClearWarningToLogistics, clearWarningToLogistics } from '@/stores/demo'
import { listIDSEvents } from '@/api/ids'
import type { IDSEventItem } from '@/api/ids'
import { listPurchases } from '@/api/purchase'
import { listSupplierOrders } from '@/api/supplier'
import { listMyPurchases } from '@/api/purchase'
import {
  dispatchIDSFocusEvent,
  playIdsAlertSound,
  primeIdsAlertSound,
} from '@/utils/idsAdminAlert'

const route = useRoute()
const router = useRouter()
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
const isSystemAdmin = computed(() => role.value === 'system_admin')
const isOnIdsPage = computed(() => route.path.startsWith('/security/ids'))
const idsRiskAlertJumpLabel = computed(() => (isOnIdsPage.value ? '定位当前事件' : '前往 IDS 事件'))
const idsRiskAlertHintText = computed(() =>
  idsRiskAlertQueue.value.length
    ? `队列中还有 ${idsRiskAlertQueue.value.length} 条高危事件，关闭当前弹窗后会立即继续告警。`
    : '这是当前最新的一条待处理高危事件。',
)

let pollingTimer: number | null = null
const prevCounts: Record<string, number> = {}

const POLL_INTERVAL = 25000
const IDS_ALERT_POLL_INTERVAL = 10000
const IDS_ALERT_MIN_SCORE = 80
const IDS_ALERT_STATE_KEY = 'ids-admin-high-risk-alert-v1'
const idsRiskAlertVisible = ref(false)
const idsRiskAlertCurrent = ref<IDSEventItem | null>(null)
const idsRiskAlertQueue = ref<IDSEventItem[]>([])
let idsAlertPollingTimer: number | null = null
let idsRiskAlertPendingJumpEventId: number | null = null
let idsAlertAudioPrimed = false

type IDSAlertState = {
  muted_date: string | null
  watermark_event_id: number
}

function currentDateKey() {
  const now = new Date()
  const y = now.getFullYear()
  const m = `${now.getMonth() + 1}`.padStart(2, '0')
  const d = `${now.getDate()}`.padStart(2, '0')
  return `${y}-${m}-${d}`
}

function defaultIdsAlertState(): IDSAlertState {
  return {
    muted_date: null,
    watermark_event_id: 0,
  }
}

function readIdsAlertState(): IDSAlertState {
  try {
    const raw = localStorage.getItem(IDS_ALERT_STATE_KEY)
    if (!raw) return defaultIdsAlertState()
    const parsed = JSON.parse(raw) as
      | (Partial<IDSAlertState> & {
          date?: string
          muted_for_today?: boolean
          seen_event_ids?: unknown[]
        })
      | null
    const legacySeenIds = Array.isArray(parsed?.seen_event_ids)
      ? parsed.seen_event_ids
          .map((item) => Number(item))
          .filter((item) => Number.isFinite(item) && item > 0)
      : []
    const legacyWatermark = legacySeenIds.length ? Math.max(...legacySeenIds) : 0
    const watermarkEventId = Math.max(
      Number(parsed?.watermark_event_id || 0),
      legacyWatermark,
    )
    const mutedDate =
      typeof parsed?.muted_date === 'string' && parsed.muted_date === currentDateKey()
        ? parsed.muted_date
        : parsed?.muted_for_today && parsed.date === currentDateKey()
          ? currentDateKey()
          : null
    return {
      muted_date: mutedDate,
      watermark_event_id:
        Number.isFinite(watermarkEventId) && watermarkEventId > 0 ? watermarkEventId : 0,
    }
  } catch {
    return defaultIdsAlertState()
  }
}

function writeIdsAlertState(state: IDSAlertState) {
  localStorage.setItem(IDS_ALERT_STATE_KEY, JSON.stringify(state))
}

function isIdsAlertMutedToday() {
  return readIdsAlertState().muted_date === currentDateKey()
}

function eventIdOfIdsAlert(item?: IDSEventItem | null) {
  const eventId = Number(item?.id || 0)
  return Number.isFinite(eventId) && eventId > 0 ? eventId : 0
}

function advanceIdsAlertWatermark(eventIds: number[]) {
  if (!eventIds.length) return
  const latestEventId = Math.max(...eventIds)
  if (!Number.isFinite(latestEventId) || latestEventId <= 0) return
  const state = readIdsAlertState()
  if (latestEventId > state.watermark_event_id) {
    state.watermark_event_id = latestEventId
    writeIdsAlertState(state)
  }
}

function muteIdsAlertsForToday() {
  const state = readIdsAlertState()
  state.muted_date = currentDateKey()
  writeIdsAlertState(state)
}

function idsAlertAttackTitle(item?: IDSEventItem | null) {
  if (!item) return '高危安全事件'
  if (item.path === '/api/upload' || item.upload_trace) return '高危文件上传攻击'
  return item.attack_type_label || item.attack_type || '高危安全事件'
}

function idsAlertDetector(item?: IDSEventItem | null) {
  return item?.source_rule_name || item?.detector_name || item?.firewall_rule || '-'
}

function idsAlertEvidence(item?: IDSEventItem | null) {
  return (
    item?.upload_trace?.decision_basis?.hold_reason_summary ||
    item?.response_detail ||
    item?.review_note ||
    item?.ai_analysis ||
    item?.signature_matched ||
    '-'
  )
}

function primeIdsAlertAudioOnce() {
  if (idsAlertAudioPrimed) return
  idsAlertAudioPrimed = true
  void primeIdsAlertSound()
  window.removeEventListener('pointerdown', primeIdsAlertAudioOnce)
  window.removeEventListener('keydown', primeIdsAlertAudioOnce)
  window.removeEventListener('touchstart', primeIdsAlertAudioOnce)
}

function bindIdsAlertAudioPriming() {
  window.addEventListener('pointerdown', primeIdsAlertAudioOnce)
  window.addEventListener('keydown', primeIdsAlertAudioOnce)
  window.addEventListener('touchstart', primeIdsAlertAudioOnce)
}

function unbindIdsAlertAudioPriming() {
  window.removeEventListener('pointerdown', primeIdsAlertAudioOnce)
  window.removeEventListener('keydown', primeIdsAlertAudioOnce)
  window.removeEventListener('touchstart', primeIdsAlertAudioOnce)
}

function stopIdsAlertPolling() {
  if (idsAlertPollingTimer) {
    clearInterval(idsAlertPollingTimer)
    idsAlertPollingTimer = null
  }
}

function showNextIdsAlert() {
  if (!isSystemAdmin.value || isIdsAlertMutedToday() || idsRiskAlertVisible.value || idsRiskAlertCurrent.value) return
  if (!idsRiskAlertQueue.value.length) return
  const next = idsRiskAlertQueue.value.shift() || null
  if (!next) return
  idsRiskAlertCurrent.value = next
  idsRiskAlertVisible.value = true
  void playIdsAlertSound().catch(() => undefined)
}

function dismissIdsRiskAlert() {
  const jumpEventId = idsRiskAlertPendingJumpEventId
  idsRiskAlertPendingJumpEventId = null
  idsRiskAlertCurrent.value = null
  if (jumpEventId) {
    void router.push({ path: '/security/ids', query: { event: String(jumpEventId) } }).finally(() => {
      showNextIdsAlert()
    })
    return
  }
  showNextIdsAlert()
}

function handleIdsRiskAlertClose() {
  idsRiskAlertVisible.value = false
}

function handleIdsRiskAlertJump() {
  const eventId = idsRiskAlertCurrent.value?.id ?? null
  if (eventId && isOnIdsPage.value) {
    idsRiskAlertPendingJumpEventId = null
    dispatchIDSFocusEvent({ eventId, report: false })
    idsRiskAlertVisible.value = false
    return
  }
  idsRiskAlertPendingJumpEventId = eventId
  idsRiskAlertVisible.value = false
}

function handleIdsRiskAlertMuteToday() {
  muteIdsAlertsForToday()
  idsRiskAlertQueue.value = []
  idsRiskAlertVisible.value = false
}

function queueIdsRiskAlerts(items: IDSEventItem[], options?: { silent?: boolean }) {
  if (!isSystemAdmin.value || isIdsAlertMutedToday()) return
  const queuedIds = new Set<number>([
    ...(idsRiskAlertCurrent.value?.id ? [idsRiskAlertCurrent.value.id] : []),
    ...idsRiskAlertQueue.value.map((item) => item.id),
  ])
  const freshItems: IDSEventItem[] = []
  for (const item of items) {
    const eventId = eventIdOfIdsAlert(item)
    if (!eventId || queuedIds.has(eventId)) continue
    queuedIds.add(eventId)
    freshItems.push(item)
  }
  if (!freshItems.length) return
  idsRiskAlertQueue.value = [...idsRiskAlertQueue.value, ...freshItems].slice(0, 8)
  if (!options?.silent) {
    ElNotification({
      title: '高危 IDS 风险预警',
      message: `检测到 ${freshItems.length} 条新的高危安全事件，请立即复核。`,
      type: 'error',
      duration: 4000,
    })
  }
  showNextIdsAlert()
}

async function refreshAdminIdsRiskAlerts(options?: { silent?: boolean }) {
  if (!isSystemAdmin.value) {
    idsRiskAlertPendingJumpEventId = null
    idsRiskAlertQueue.value = []
    idsRiskAlertVisible.value = false
    idsRiskAlertCurrent.value = null
    return
  }
  try {
    const res: any = await listIDSEvents({
      blocked: 1,
      archived: 0,
      min_score: IDS_ALERT_MIN_SCORE,
      limit: 8,
    })
    const items: IDSEventItem[] = Array.isArray(res?.items)
      ? res.items
      : Array.isArray(res?.data?.items)
        ? res.data.items
        : []
    const scopedItems = items.filter((item) => (item.risk_score || 0) >= IDS_ALERT_MIN_SCORE)
    const eventIds = scopedItems.map((item) => eventIdOfIdsAlert(item)).filter((item) => item > 0)
    if (!eventIds.length) return

    const state = readIdsAlertState()
    if (state.watermark_event_id <= 0) {
      advanceIdsAlertWatermark(eventIds)
      return
    }

    const freshItems = scopedItems.filter((item) => eventIdOfIdsAlert(item) > state.watermark_event_id)
    advanceIdsAlertWatermark(eventIds)

    if (isIdsAlertMutedToday()) return
    queueIdsRiskAlerts(freshItems, options)
  } catch {
    /* keep silent for global polling */
  }
}

function startIdsAlertPolling() {
  stopIdsAlertPolling()
  if (!isSystemAdmin.value) return
  void refreshAdminIdsRiskAlerts({ silent: true })
  idsAlertPollingTimer = window.setInterval(() => {
    void refreshAdminIdsRiskAlerts()
  }, IDS_ALERT_POLL_INTERVAL)
}

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
  bindIdsAlertAudioPriming()
  await refreshAll({ silent: true })
  await refreshAdminIdsRiskAlerts({ silent: true })
  await markCurrentAsSeen()
  startPolling()
  startIdsAlertPolling()
  initLogisticsWarningCheck()
})

watch(
  () => route.path,
  async () => {
    await markCurrentAsSeen()
    showNextIdsAlert()
  }
)

watch(
  () => userStore.userInfo?.id,
  async () => {
    await refreshAll({ silent: true })
    await refreshAdminIdsRiskAlerts({ silent: true })
    startPolling()
    startIdsAlertPolling()
  }
)

onBeforeUnmount(() => {
  stopPolling()
  stopIdsAlertPolling()
  unbindIdsAlertAudioPriming()
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

    <el-dialog
      v-model="idsRiskAlertVisible"
      title="高危 IDS 风险预警"
      width="520px"
      class="ids-risk-alert-dialog"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      append-to-body
      @closed="dismissIdsRiskAlert"
    >
      <template v-if="idsRiskAlertCurrent">
        <div class="ids-risk-alert">
          <div class="ids-risk-alert__headline">
            <span class="ids-risk-alert__badge">HIGH</span>
            <div>
              <div class="ids-risk-alert__title">{{ idsAlertAttackTitle(idsRiskAlertCurrent) }}</div>
              <div class="ids-risk-alert__subtitle">
                事件 #{{ idsRiskAlertCurrent.id }}，风险分 {{ idsRiskAlertCurrent.risk_score ?? '-' }}，来源 {{ idsAlertDetector(idsRiskAlertCurrent) }}
              </div>
            </div>
          </div>

          <div class="ids-risk-alert__grid">
            <div class="ids-risk-alert__item">
              <span class="ids-risk-alert__label">客户端 IP</span>
              <span class="ids-risk-alert__value">{{ idsRiskAlertCurrent.client_ip || '-' }}</span>
            </div>
            <div class="ids-risk-alert__item">
              <span class="ids-risk-alert__label">事件时间</span>
              <span class="ids-risk-alert__value">{{ idsRiskAlertCurrent.created_at || '-' }}</span>
            </div>
            <div class="ids-risk-alert__item ids-risk-alert__item--full">
              <span class="ids-risk-alert__label">请求目标</span>
              <span class="ids-risk-alert__value">{{ idsRiskAlertCurrent.method }} {{ idsRiskAlertCurrent.path || '-' }}</span>
            </div>
            <div class="ids-risk-alert__item ids-risk-alert__item--full">
              <span class="ids-risk-alert__label">拦截依据</span>
              <span class="ids-risk-alert__value ids-risk-alert__value--multiline">{{ idsAlertEvidence(idsRiskAlertCurrent) }}</span>
            </div>
          </div>

          <div class="ids-risk-alert__hint">
            {{ idsRiskAlertHintText }}
          </div>
        </div>
      </template>

      <template #footer>
        <div class="ids-risk-alert__actions">
          <el-button @click="handleIdsRiskAlertClose">关闭</el-button>
          <el-button @click="handleIdsRiskAlertMuteToday">今日不再弹出</el-button>
          <el-button type="danger" @click="handleIdsRiskAlertJump">{{ idsRiskAlertJumpLabel }}</el-button>
        </div>
      </template>
    </el-dialog>
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

:deep(.ids-risk-alert-dialog) {
  .el-dialog {
    border: 1px solid rgba(255, 107, 107, 0.32);
    background:
      radial-gradient(circle at top right, rgba(255, 107, 107, 0.18), transparent 38%),
      linear-gradient(180deg, rgba(10, 20, 38, 0.98), rgba(7, 12, 25, 0.98));
    box-shadow:
      0 22px 60px rgba(0, 0, 0, 0.45),
      0 0 0 1px rgba(255, 255, 255, 0.04) inset;
    color: #ecf4ff;
  }

  .el-dialog__header {
    margin-right: 0;
    padding: 18px 22px 0;
  }

  .el-dialog__title {
    color: #f8fbff;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0.02em;
  }

  .el-dialog__headerbtn .el-dialog__close {
    color: rgba(236, 244, 255, 0.72);
  }

  .el-dialog__body {
    padding: 18px 22px 10px;
  }

  .el-dialog__footer {
    padding: 8px 22px 22px;
  }
}

.ids-risk-alert {
  display: grid;
  gap: 18px;
}

.ids-risk-alert__headline {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 16px 18px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(135, 16, 16, 0.42), rgba(61, 14, 18, 0.84));
  border: 1px solid rgba(255, 129, 129, 0.22);
}

.ids-risk-alert__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 64px;
  height: 32px;
  border-radius: 999px;
  background: linear-gradient(135deg, #ff6b6b, #ff8748);
  color: #fff9f6;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.12em;
}

.ids-risk-alert__title {
  color: #fdfefe;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.25;
}

.ids-risk-alert__subtitle {
  margin-top: 6px;
  color: rgba(236, 244, 255, 0.78);
  font-size: 13px;
  line-height: 1.6;
}

.ids-risk-alert__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.ids-risk-alert__item {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
  padding: 14px 15px;
  border-radius: 16px;
  background: rgba(12, 20, 36, 0.88);
  border: 1px solid rgba(150, 177, 216, 0.16);
}

.ids-risk-alert__item--full {
  grid-column: 1 / -1;
}

.ids-risk-alert__label {
  color: rgba(168, 188, 214, 0.82);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.ids-risk-alert__value {
  color: #f4f8ff;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.6;
  word-break: break-word;
}

.ids-risk-alert__value--multiline {
  white-space: pre-wrap;
}

.ids-risk-alert__hint {
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(68, 84, 117, 0.2);
  color: rgba(211, 223, 240, 0.92);
  font-size: 13px;
  line-height: 1.7;
}

.ids-risk-alert__actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

@media (max-width: 640px) {
  .ids-risk-alert__headline {
    flex-direction: column;
  }

  .ids-risk-alert__grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .ids-risk-alert__actions {
    flex-direction: column-reverse;
  }

  .ids-risk-alert__actions :deep(.el-button) {
    width: 100%;
    margin-left: 0;
  }
}
</style>
