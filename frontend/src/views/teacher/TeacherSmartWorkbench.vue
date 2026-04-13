<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick, type Component } from 'vue'
import { useRouter } from 'vue-router'
import {
  Promotion,
  Microphone,
  RefreshRight,
  CircleCheck,
  WarningFilled,
  Cpu,
  Paperclip,
  Calendar,
  Refresh,
  Warning,
  ShoppingBag,
  Van,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { chat, executeAction } from '@/api/ai'
import { listMyPurchases } from '@/api/purchase'
import { workbenchChatPrefill } from '@/utils/teacherWorkbenchBus'
import { addAbnormalOrder } from '@/stores/demo'
import type { ChatAction, ReactStep } from '@/api/ai'

const THINK_MIN_MS = 1800
const STEP_MS = 420

const BUNDLES_KEY = 'teacher-workbench-bundles-v1'
const TRACK_KEY = 'teacher-workbench-track-v1'

const router = useRouter()
const userStore = useUserStore()

const displayName = computed(
  () => userStore.userInfo?.real_name || userStore.userInfo?.username || '老师'
)

const greetingFull = computed(() => {
  const h = new Date().getHours()
  const prefix = h < 12 ? '上午好' : h < 18 ? '下午好' : '晚上好'
  return `${prefix}，${displayName.value}。今天需要准备什么物资，或是安排什么活动？`
})

const greetingChars = computed(() => Array.from(greetingFull.value))
const greetingRevealCount = ref(0)
let greetingRevealTimer: ReturnType<typeof setInterval> | null = null

function startGreetingReveal() {
  if (greetingRevealTimer) {
    clearInterval(greetingRevealTimer)
    greetingRevealTimer = null
  }
  greetingRevealCount.value = 0
  const fullLen = greetingFull.value.length
  if (fullLen === 0) return
  greetingRevealTimer = window.setInterval(() => {
    if (greetingRevealCount.value < fullLen) {
      greetingRevealCount.value += 1
    } else if (greetingRevealTimer) {
      clearInterval(greetingRevealTimer)
      greetingRevealTimer = null
    }
  }, 42)
}

const showCapabilityPanel = ref(false)

/** 教职工体检卡片：一键演示完整「提问 → AI 回复 → 申请单 → 同意提交 → 成功」 */
const HEALTH_DEMO_USER =
  '本周五教研室安排体检留守值班，约 6 人，请生成基础饮水与茶歇包申领清单（矿泉水、纸杯、茶包、饼干）'

const scenarioFlowActive = ref(false)
const scenarioAiReplyText = ref('')
const scenarioReplyTyping = ref(false)
const scenarioSheetReady = ref(false)
const scenarioSubmitSuccess = ref(false)

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}

function buildHealthScenarioReply(teacherName: string) {
  return `好的，${teacherName}。已根据校历「教职工体检」和教研室周五留守安排，按约 6 人值守为您匹配「基础饮水与茶歇包」档位，并完成了可用库存核对。

下面已为您生成可编辑的申领申请单，请确认数量与收货信息；确认无误后提交即可进入后勤审批与配送队列。`
}

async function typeQueryChars(full: string, msPerChar = 14) {
  queryInput.value = ''
  for (let i = 1; i <= full.length; i++) {
    queryInput.value = full.slice(0, i)
    await sleep(msPerChar)
  }
}

async function typeScenarioReply(full: string, msPerChar = 10) {
  scenarioAiReplyText.value = ''
  scenarioReplyTyping.value = true
  for (let i = 1; i <= full.length; i++) {
    scenarioAiReplyText.value = full.slice(0, i)
    await sleep(msPerChar)
  }
  scenarioReplyTyping.value = false
}

async function runHealthCheckListDemo() {
  if (sending.value) return
  scenarioFlowActive.value = true
  scenarioSheetReady.value = false
  scenarioAiReplyText.value = ''
  scenarioSubmitSuccess.value = false
  sheetItems.value = []

  await typeQueryChars(HEALTH_DEMO_USER, 14)
  await sleep(360)
  queryInput.value = ''
  uiPhase.value = 'result'
  assistantNote.value = ''
  abnormalMode.value = false
  forceAction.value = null
  await nextTick()

  sending.value = true
  await runThinkAnimation(
    [
      { step: 1, text: '读取校历：教职工体检（周五）' },
      { step: 2, text: '匹配留守编制与茶歇档位（6 人）' },
      { step: 3, text: '仓储库存 / 额度联动校验' },
      { step: 4, text: '生成智能申领微件' },
    ],
    buildThinkPhrases(HEALTH_DEMO_USER)
  )
  sending.value = false

  await typeScenarioReply(buildHealthScenarioReply(displayName.value), 9)
  await sleep(420)
  scenarioSheetReady.value = true
  sheetItems.value = fallbackHealthCheckSheet()
  assistantNote.value =
    '请核对物资明细与收货信息，点击「同意并提交」即表示确认并提交至后勤仓储（演示流程）。'
  sheetTitle.value = '申领申请单（智能生成）'
  if (!receiverDest.value.trim()) {
    receiverDest.value = '综合楼 A 区教研室值班室（演示）'
  }
}

const capabilityScript = [
  {
    q: '你可以做什么？',
    a: '我是采购与物资 Copilot：可以用自然语言生成申领清单、按场景匹配库存、提醒归还与周期复购，并一键提交后勤仓储。',
  },
  {
    q: '怎么最快领到耗材？',
    a: '建议在工作日上午早些时候提交；周三上午配送资源通常更充裕（演示数据）。合并同楼宇申领可缩短等待。',
  },
]
const capabilityStep = ref(0)
const capabilityTyping = ref('')
const capabilityRole = ref<'user' | 'assistant'>('user')

async function playCapabilityDemo() {
  capabilityStep.value = 0
  capabilityTyping.value = ''
  for (let s = 0; s < capabilityScript.length; s++) {
    if (!showCapabilityPanel.value) return
    capabilityStep.value = s
    const { q, a } = capabilityScript[s]!
    capabilityRole.value = 'user'
    capabilityTyping.value = ''
    for (let i = 1; i <= q.length; i++) {
      if (!showCapabilityPanel.value) return
      capabilityTyping.value = q.slice(0, i)
      await sleep(28)
    }
    await sleep(450)
    capabilityRole.value = 'assistant'
    capabilityTyping.value = ''
    for (let i = 1; i <= a.length; i++) {
      if (!showCapabilityPanel.value) return
      capabilityTyping.value = a.slice(0, i)
      await sleep(10)
    }
    await sleep(800)
  }
  capabilityTyping.value = ''
}

async function toggleCapabilityDemo() {
  if (showCapabilityPanel.value) {
    showCapabilityPanel.value = false
    return
  }
  showCapabilityPanel.value = true
  await playCapabilityDemo()
}

const uiPhase = ref<'home' | 'result'>('home')
const queryInput = ref('')
const sending = ref(false)
const sessionId = ref<string | null>(null)

const omniboxFocused = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

const placeholderIndex = ref(0)
const placeholderOptions = [
  '输入活动名称配置物资…',
  '上传破损桌椅照片申请更换…',
  '语音说说下周的实验安排…',
  '例如：明天下午 30 人跨院系交流会茶歇与资料…',
  '问问「粉笔还有库存吗」或「上月打印纸规格」…',
]
let placeholderTimer: ReturnType<typeof setInterval> | null = null

const activePlaceholder = computed(() => {
  if (queryInput.value.trim()) return placeholderOptions[0]
  return placeholderOptions[placeholderIndex.value % placeholderOptions.length]
})

type InsightKind = 'calendar' | 'cycle' | 'reverse'

type InsightCard = {
  id: string
  kind: InsightKind
  icon: Component
  title: string
  analysis: string
  gradient: string
  cta: string
  secondaryCta?: string
  prompt?: string
  onSecondary?: () => void
}

const insightCards = computed<InsightCard[]>(() => {
  const cards: InsightCard[] = [
    {
      id: 'rev-1',
      kind: 'reverse',
      icon: Warning,
      title: '公共物资归还提醒',
      analysis:
        '您名下有 2 台便携投影仪将于明日到期，逾期未还将影响教研室信用分。可一键发起回收呼叫或申请续借。',
      gradient: 'linear-gradient(125deg, #fff7ed 0%, #ffedd5 45%, #fed7aa 100%)',
      cta: '一键呼叫回收',
      secondaryCta: '申请续借',
      prompt: '申请续借便携投影仪 2 台，原借用单即将到期，请走续借审批',
      onSecondary: () => {
        void submitQuery('申请续借便携投影仪 2 台，原借用单即将到期，请走续借审批')
      },
    },
    {
      id: 'cal-1',
      kind: 'calendar',
      icon: Calendar,
      title: '教职工体检（周五）',
      analysis:
        '校历显示本周五有统一体检安排，教研室需留守值班。AI 建议为留守同事申领「基础饮水与茶歇包」，避免现场临时凑物资。',
      gradient: 'linear-gradient(125deg, #eef2ff 0%, #e0e7ff 50%, #c7d2fe 100%)',
      cta: '一键生成清单',
      prompt:
        '本周五教研室安排体检留守值班，约 6 人，请生成基础饮水与茶歇包申领清单（矿泉水、纸杯、茶包、饼干）',
    },
    {
      id: 'cyc-1',
      kind: 'cycle',
      icon: Refresh,
      title: '周期性消耗预判',
      analysis:
        '根据历史行为，您在每月 15 号前后常申领 A4 打印纸。本月周期已到，可按上月规格一键复购，减少重复填表。',
      gradient: 'linear-gradient(125deg, #ecfdf5 0%, #d1fae5 45%, #a7f3d0 100%)',
      cta: '按上月规格一键复购',
      prompt: '按我上月申领的 A4 打印纸规格与数量一键复购，并附带常用订书钉',
    },
  ]
  const order: Record<InsightKind, number> = { reverse: 0, calendar: 1, cycle: 2 }
  return [...cards].sort((a, b) => order[a.kind] - order[b.kind])
})

function onInsightPrimary(card: InsightCard) {
  if (card.id === 'cal-1') {
    void runHealthCheckListDemo()
    return
  }
  if (card.prompt) void submitQuery(card.prompt)
  else if (card.id === 'rev-1') {
    ElMessage.success('已通知后勤班组：回收任务已排队（演示）')
  }
}

function onInsightSecondary(card: InsightCard) {
  card.onSecondary?.()
}

const thinkSteps = ref<{ text: string; done: boolean }[]>([])
const thinking = ref(false)
const thinkStreamLine = ref('')

type StockLevel = 'ok' | 'low' | 'substituted'

type SheetItem = {
  key: string
  name: string
  quantity: number
  unit: string
  emoji: string
  stockLevel: StockLevel
  lowStockCount?: number
  substitutionNote?: string
  unitPrice: number
}

const sheetItems = ref<SheetItem[]>([])
const sheetTitle = ref('智能申领清单')
const assistantNote = ref('')
const abnormalMode = ref(false)
const abnormalText = ref('')
const forceAction = ref<ChatAction | null>(null)

const receiverName = ref('')
const receiverDest = ref('')
const submitting = ref(false)

const estimatedTotal = computed(() =>
  sheetItems.value.reduce((sum, r) => sum + r.unitPrice * r.quantity, 0)
)

type Bundle = { id: string; label: string; prompt: string }
const bundles = ref<Bundle[]>([
  { id: 'b1', label: '标准组会包', prompt: '标准组会包：A4纸2包、白板笔1盒、矿泉水一箱、纸杯一包，生成申领清单' },
  { id: 'b2', label: '期末大考包', prompt: '期末大考包：答题卡、草稿纸、备用笔、密封条，按40人考场估算数量' },
])

type TrackState = {
  order_no: string
  message: string
  step: number
  total: number
}
const tracking = ref<TrackState | null>(null)

function applyPrefill(v: string) {
  if (!v) return
  queryInput.value = v
  workbenchChatPrefill.value = ''
}

watch(workbenchChatPrefill, (v) => applyPrefill(v || ''), { flush: 'post' })

function loadBundles() {
  try {
    const raw = localStorage.getItem(BUNDLES_KEY)
    if (raw) {
      const arr = JSON.parse(raw) as Bundle[]
      if (Array.isArray(arr) && arr.length) bundles.value = arr
    }
  } catch {
    /* ignore */
  }
}

function loadTracking() {
  try {
    const raw = sessionStorage.getItem(TRACK_KEY)
    if (raw) tracking.value = JSON.parse(raw) as TrackState
  } catch {
    tracking.value = null
  }
}

function saveTracking(t: TrackState | null) {
  if (!t) {
    sessionStorage.removeItem(TRACK_KEY)
    tracking.value = null
    return
  }
  sessionStorage.setItem(TRACK_KEY, JSON.stringify(t))
  tracking.value = t
}

async function refreshTrackingFromApi() {
  try {
    const res: any = await listMyPurchases()
    const list = (Array.isArray(res) ? res : res?.data ?? []) as {
      order_no: string
      status: string
      goods_summary?: string
    }[]
    const proc = list.find((p) => !['completed', 'rejected'].includes(p.status))
    if (!proc) {
      if (!sessionStorage.getItem(TRACK_KEY)) tracking.value = null
      return
    }
    const stepMap: Record<string, number> = {
      pending: 1,
      approved: 2,
      confirmed: 2,
      shipped: 2,
      stocked_in: 3,
      stocked_out: 3,
      delivering: 3,
      completed: 4,
    }
    const step = stepMap[proc.status] ?? 2
    const msg =
      step <= 2
        ? '审批/接单流转中'
        : step === 3
          ? '仓储端拣货打包或配送中'
          : '已完成'
    saveTracking({
      order_no: proc.order_no,
      message: `${proc.goods_summary ? proc.goods_summary.slice(0, 24) + '… · ' : ''}${msg}`,
      step,
      total: 4,
    })
  } catch {
    /* ignore */
  }
}

onMounted(() => {
  if (workbenchChatPrefill.value) applyPrefill(workbenchChatPrefill.value)
  receiverName.value = userStore.userInfo?.real_name || userStore.userInfo?.username || ''
  receiverDest.value = ''
  loadBundles()
  loadTracking()
  void refreshTrackingFromApi()
  startGreetingReveal()
  placeholderTimer = window.setInterval(() => {
    if (!omniboxFocused.value && !queryInput.value.trim()) {
      placeholderIndex.value = (placeholderIndex.value + 1) % placeholderOptions.length
    }
  }, 3200)
})

onUnmounted(() => {
  if (placeholderTimer) clearInterval(placeholderTimer)
  if (thinkStreamTimer) clearInterval(thinkStreamTimer)
  if (greetingRevealTimer) clearInterval(greetingRevealTimer)
})

let thinkStreamTimer: ReturnType<typeof setInterval> | null = null

function stopThinkStream() {
  if (thinkStreamTimer) {
    clearInterval(thinkStreamTimer)
    thinkStreamTimer = null
  }
  thinkStreamLine.value = ''
}

function startThinkStream(phrases: string[]) {
  stopThinkStream()
  let i = 0
  thinkStreamLine.value = phrases[0] || ''
  thinkStreamTimer = window.setInterval(() => {
    i = (i + 1) % phrases.length
    thinkStreamLine.value = phrases[i]
  }, 580)
}

function buildThinkPhrases(q: string): string[] {
  if (/30人|三十人|交流会|跨院系|茶歇/.test(q)) {
    return [
      '正在解析场景（跨院系交流）…',
      '正在匹配 30 人标准茶歇与资料配置…',
      '正在核对仓储端实时库存…',
      '正在校验院系额度与审批规则…',
      '正在生成可编辑申领微件…',
    ]
  }
  if (/体检|留守|周五/.test(q)) {
    return [
      '正在读取校历与值班排期…',
      '正在匹配留守人数与茶歇档位…',
      '正在联动后勤饮水与茶包库存…',
    ]
  }
  return [
    '正在理解您的自然语言意图…',
    '正在检索物资主数据与规格…',
    '正在模拟多主体（教务·仓储·额度）联调…',
    '正在生成智能申领清单…',
  ]
}

function onOmniboxBlur(e: FocusEvent) {
  const cur = e.currentTarget as HTMLElement | null
  nextTick(() => {
    if (cur && !cur.contains(document.activeElement)) omniboxFocused.value = false
  })
}

function triggerFilePick() {
  fileInputRef.value?.click()
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  ElMessage.info('正在识别图片中的耗材特征并匹配物资库…')
  window.setTimeout(() => {
    ElMessage.success('识别完成：推测为课桌椅紧固件 / 脚垫类耗材，已填入申领意图，您可补充数量后发送。')
    queryInput.value =
      '根据上传现场照片，申请更换同规格课桌椅紧固件套装若干（请后勤按图匹配库存）'
    input.value = ''
  }, 1600)
}

function isAbnormalRequest(q: string): boolean {
  const lower = q.toLowerCase()
  return (lower.includes('100') && lower.includes('笔记本')) || (lower.includes('笔记本') && lower.includes('观影'))
}

function uid() {
  return `i-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

function fallbackHealthCheckSheet(): SheetItem[] {
  return [
    { key: uid(), name: '瓶装饮用水 550ml', quantity: 24, unit: '瓶', emoji: '🥤', stockLevel: 'ok', unitPrice: 2 },
    { key: uid(), name: '一次性纸杯', quantity: 2, unit: '包', emoji: '🥤', stockLevel: 'ok', unitPrice: 8 },
    { key: uid(), name: '袋泡茶（组合装）', quantity: 2, unit: '盒', emoji: '🍵', stockLevel: 'ok', unitPrice: 22 },
    {
      key: uid(),
      name: '独立包装饼干',
      quantity: 3,
      unit: '包',
      emoji: '🍪',
      stockLevel: 'low',
      lowStockCount: 8,
      unitPrice: 12,
    },
  ]
}

function mapPayloadToSheetItems(payload: Record<string, unknown> | undefined): SheetItem[] {
  const raw = (payload as { items?: { name?: string; quantity?: number; unit?: string }[] })?.items
  if (!Array.isArray(raw) || !raw.length) return []
  return raw.map((it, idx) => ({
    key: uid() + idx,
    name: String(it.name || '物资'),
    quantity: Math.max(1, Number(it.quantity) || 1),
    unit: String(it.unit || '件'),
    emoji: pickEmoji(String(it.name)),
    stockLevel: 'ok' as StockLevel,
    unitPrice: 3,
  }))
}

function pickEmoji(name: string): string {
  if (/纸|打印|资料/.test(name)) return '📄'
  if (/笔|粉笔/.test(name)) return '✏️'
  if (/水|饮|茶|杯/.test(name)) return '🥤'
  if (/消毒|清洁/.test(name)) return '🧴'
  if (/实验|试剂/.test(name)) return '🧪'
  if (/袋|包/.test(name)) return '🛍️'
  return '📦'
}

function fallbackSheetFromQuery(q: string): SheetItem[] {
  if (/体检|留守|茶歇包|教职工体检/.test(q)) {
    return fallbackHealthCheckSheet()
  }
  if (/30人|三十人|交流会|跨院系|茶歇/.test(q)) {
    return [
      {
        key: uid(),
        name: '瓶装饮用水 550ml',
        quantity: 30,
        unit: '瓶',
        emoji: '🥤',
        stockLevel: 'ok',
        unitPrice: 2,
      },
      {
        key: uid(),
        name: '会议资料袋（含笔）',
        quantity: 30,
        unit: '份',
        emoji: '🛍️',
        stockLevel: 'ok',
        unitPrice: 3.5,
      },
      {
        key: uid(),
        name: '绿茶茶包（替选）',
        quantity: 3,
        unit: '盒',
        emoji: '🍵',
        stockLevel: 'substituted',
        substitutionNote:
          '原定「特级红茶包」库存不足，已自动为您替换为同等价位的「绿茶茶包」，单价与预算不变。',
        unitPrice: 18,
      },
      {
        key: uid(),
        name: '独立包装点心',
        quantity: 30,
        unit: '份',
        emoji: '🍪',
        stockLevel: 'low',
        lowStockCount: 5,
        unitPrice: 4,
      },
    ]
  }
  if (/粉笔|发货|物流|配送/.test(q)) {
    return [
      { key: uid(), name: '无尘粉笔（白）', quantity: 10, unit: '盒', emoji: '✏️', stockLevel: 'ok', unitPrice: 8 },
      { key: uid(), name: '板擦', quantity: 4, unit: '个', emoji: '🧽', stockLevel: 'ok', unitPrice: 6 },
    ]
  }
  if (/期中|考试|答题/.test(q)) {
    return [
      { key: uid(), name: '答题卡（A4）', quantity: 200, unit: '张', emoji: '📋', stockLevel: 'ok', unitPrice: 0.15 },
      { key: uid(), name: '草稿纸', quantity: 200, unit: '张', emoji: '📄', stockLevel: 'ok', unitPrice: 0.08 },
      { key: uid(), name: '备用中性笔', quantity: 30, unit: '支', emoji: '✒️', stockLevel: 'low', lowStockCount: 12, unitPrice: 1.2 },
    ]
  }
  if (/班会|茶歇|活动/.test(q)) {
    return [
      { key: uid(), name: '一次性纸杯', quantity: 50, unit: '个', emoji: '🥤', stockLevel: 'ok', unitPrice: 0.2 },
      { key: uid(), name: '袋泡茶', quantity: 3, unit: '盒', emoji: '🍵', stockLevel: 'ok', unitPrice: 22 },
      { key: uid(), name: '湿纸巾', quantity: 5, unit: '包', emoji: '🧻', stockLevel: 'ok', unitPrice: 6 },
    ]
  }
  return [
    { key: uid(), name: 'A4 打印纸', quantity: 5, unit: '包', emoji: '📄', stockLevel: 'ok', unitPrice: 28 },
    { key: uid(), name: '订书钉（通用）', quantity: 2, unit: '盒', emoji: '📎', stockLevel: 'ok', unitPrice: 5 },
    { key: uid(), name: '便利贴', quantity: 6, unit: '本', emoji: '📝', stockLevel: 'ok', unitPrice: 4 },
  ]
}

function pickCreateAction(actions: ChatAction[] | undefined): ChatAction | null {
  if (!actions?.length) return null
  return actions.find((a) => a.type === 'create_purchase' || a.type === 'force_submit') || null
}

async function runThinkAnimation(steps: ReactStep[], streamPhrases: string[]) {
  startThinkStream(streamPhrases)
  thinkSteps.value = (steps.length ? steps : [{ step: 1, text: '理解您的意图…' }]).map((s) => ({
    text: s.text,
    done: false,
  }))
  thinking.value = true
  for (let i = 0; i < thinkSteps.value.length; i++) {
    await new Promise((r) => setTimeout(r, STEP_MS))
    thinkSteps.value[i].done = true
  }
  await new Promise((r) => setTimeout(r, 260))
  thinking.value = false
  stopThinkStream()
}

async function submitQuery(raw?: string) {
  const q = (raw ?? queryInput.value).trim()
  if (!q || sending.value) return
  queryInput.value = ''
  uiPhase.value = 'result'
  sheetItems.value = []
  assistantNote.value = ''
  abnormalMode.value = false
  forceAction.value = null
  await nextTick()

  const phrases = buildThinkPhrases(q)

  if (isAbnormalRequest(q)) {
    sending.value = true
    await runThinkAnimation(
      [
        { step: 1, text: '校验采购政策与教学用途…' },
        { step: 2, text: '多主体风控：规模/用途异常标记' },
      ],
      ['正在比对设备采购政策…', '正在触发风控复核通道…']
    )
    abnormalMode.value = true
    abnormalText.value =
      '该需求不符合教学设备常规申领规范（例如大规模设备或非教学核心用途）。如需留痕申报，可在下方走「强制提交」流程。'
    forceAction.value = {
      type: 'force_submit',
      label: '强制提交',
      payload: { items: [{ name: '笔记本电脑', quantity: 100, unit: '台' }] },
    }
    sheetItems.value = []
    assistantNote.value = ''
    sending.value = false
    return
  }

  abnormalMode.value = false
  forceAction.value = null
  sending.value = true
  await runThinkAnimation(
    [
      { step: 1, text: '自然语言 → 结构化场景' },
      { step: 2, text: '物资主数据 / 规格匹配' },
      { step: 3, text: '仓储可用量 / 替代策略' },
      { step: 4, text: '额度校验 & 生成微件' },
    ],
    phrases
  )

  try {
    const apiPromise = chat(q, sessionId.value)
    const minDelay = new Promise((r) => setTimeout(r, THINK_MIN_MS))
    const res: any = await Promise.all([apiPromise, minDelay]).then(([r]) => r)
    const data = res?.data || res
    if (!data) throw new Error('无效响应')
    if (data.session_id) sessionId.value = data.session_id

    assistantNote.value = String(data.reply || '').trim()
    const act = pickCreateAction(data.actions)
    let items = mapPayloadToSheetItems(act?.payload as Record<string, unknown>)
    if (!items.length) items = fallbackSheetFromQuery(q)
    sheetItems.value = items
    sheetTitle.value = act?.type === 'force_submit' ? '待复核申领单（异常通道）' : '智能申领清单'
  } catch (e: any) {
    assistantNote.value = `智能体暂不可用：${e?.message || '请检查网络或后端'}\n已为您生成本地演示清单，可直接微调后提交后勤仓储。`
    sheetItems.value = fallbackSheetFromQuery(q)
    sheetTitle.value = '智能申领清单（演示）'
  } finally {
    sending.value = false
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    void submitQuery()
  }
}

function bumpQty(row: SheetItem, delta: number) {
  const n = row.quantity + delta
  row.quantity = Math.max(1, Math.min(9999, n))
}

async function confirmPurchase() {
  const name = receiverName.value.trim()
  const dest = receiverDest.value.trim()
  if (!name || !dest) {
    ElMessage.warning('请填写收货人与收货地点')
    return
  }
  if (!sheetItems.value.length) {
    ElMessage.warning('没有可提交的物资行')
    return
  }
  submitting.value = true
  const isScenario = scenarioFlowActive.value
  try {
    const items = sheetItems.value.map((r) => ({
      name: r.name,
      quantity: r.quantity,
      unit: r.unit,
    }))
    const res: any = await executeAction('create_purchase', {
      items,
      receiver_name: name,
      destination: dest,
    })
    const data = res?.data || res
    const orderNo = data?.orderNo || `WB-${Date.now().toString(36).toUpperCase()}`
    if (!data?.success) throw new Error('提交失败')
    if (isScenario) {
      scenarioSubmitSuccess.value = true
      await sleep(2600)
      scenarioSubmitSuccess.value = false
      scenarioFlowActive.value = false
      scenarioSheetReady.value = false
      scenarioAiReplyText.value = ''
    }
    ElMessage.success(`申领已提交：${orderNo}`)
    saveTracking({
      order_no: orderNo,
      message: '单号 ' + orderNo + ' · 正在被仓储端打包中…',
      step: 2,
      total: 4,
    })
    void router.push('/teacher/personal?tab=orders')
  } catch {
    const orderNo = `WB-${Date.now().toString(36).toUpperCase()}`
    if (isScenario) {
      scenarioSubmitSuccess.value = true
      await sleep(2600)
      scenarioSubmitSuccess.value = false
      scenarioFlowActive.value = false
      scenarioSheetReady.value = false
      scenarioAiReplyText.value = ''
    }
    ElMessage.success(`演示：已提交后勤仓储 ${orderNo}`)
    saveTracking({
      order_no: orderNo,
      message: '单号 ' + orderNo + ' · 正在被仓储端打包中…',
      step: 2,
      total: 4,
    })
    void router.push('/teacher/personal?tab=orders')
  } finally {
    submitting.value = false
    void refreshTrackingFromApi()
  }
}

async function confirmForceSubmit() {
  const name = receiverName.value.trim()
  const dest = receiverDest.value.trim()
  if (!name || !dest) {
    ElMessage.warning('请填写收货人与收货地点')
    return
  }
  const act = forceAction.value
  if (!act) return
  submitting.value = true
  try {
    const res: any = await executeAction('create_purchase', {
      ...(act.payload || {}),
      items: (act.payload as { items?: unknown[] })?.items || [],
      receiver_name: name,
      destination: dest,
    })
    const data = res?.data || res
    const orderNo = data?.orderNo || `DEMO-${Date.now()}`
    ElMessage.success(`已创建留痕单号：${orderNo}`)
    addAbnormalOrder(orderNo)
    resetHome()
  } catch {
    const orderNo = `DEMO-${Date.now()}`
    ElMessage.success(`演示：已创建留痕单号 ${orderNo}`)
    addAbnormalOrder(orderNo)
    resetHome()
  } finally {
    submitting.value = false
  }
}

function resetHome() {
  uiPhase.value = 'home'
  sheetItems.value = []
  assistantNote.value = ''
  abnormalMode.value = false
  forceAction.value = null
  thinking.value = false
  thinkSteps.value = []
  stopThinkStream()
  sessionId.value = null
  showCapabilityPanel.value = false
  scenarioFlowActive.value = false
  scenarioAiReplyText.value = ''
  scenarioSheetReady.value = false
  scenarioSubmitSuccess.value = false
  scenarioReplyTyping.value = false
  nextTick(() => startGreetingReveal())
}

function onVoice() {
  ElMessage.info('语音输入演示：请直接使用文字或上传图片，后续可对接语音识别服务。')
}

function applyBundle(b: Bundle) {
  void submitQuery(b.prompt)
}

const focusDim = computed(() => uiPhase.value === 'home' && omniboxFocused.value)

const formatMoney = (n: number) =>
  n.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
</script>

<template>
  <div
    class="native"
    :class="{
      'native--result': uiPhase === 'result',
      'native--dim': focusDim,
    }"
  >
    <div class="native-bg" aria-hidden="true" />

    <header
      class="composer-zone"
      :class="{ 'composer-zone--top': uiPhase === 'result' }"
      @focusin="omniboxFocused = true"
      @focusout="onOmniboxBlur"
    >
      <transition name="greet-fade" mode="out-in">
        <p v-if="uiPhase === 'home'" class="greeting" aria-live="polite">
          <span
            v-for="(ch, idx) in greetingChars"
            :key="idx"
            class="greeting-char"
            :class="{ 'greeting-char--on': idx < greetingRevealCount }"
          >
            {{ ch === ' ' ? '\u00a0' : ch }}
          </span>
        </p>
      </transition>

      <div class="floating-shell" :class="{ 'floating-shell--pulse': uiPhase === 'home' }">
        <div class="omnibox-halo" aria-hidden="true" />
        <p v-if="uiPhase === 'home'" class="omnibox-ready">
          <span class="ready-dot" />
          AI 已就绪 · 多模态中枢
        </p>
        <div class="floating-bar">
          <textarea
            v-model="queryInput"
            class="floating-input"
            rows="1"
            :placeholder="activePlaceholder"
            @keydown="onKeydown"
          />
          <div class="floating-actions">
            <input
              ref="fileInputRef"
              type="file"
              accept="image/*"
              class="file-input"
              @change="onFileChange"
            />
            <el-button text circle class="ico-btn" title="上传照片 / 附件（演示识别）" @click="triggerFilePick">
              <el-icon :size="20"><Paperclip /></el-icon>
            </el-button>
            <el-button text circle class="ico-btn" title="语音输入（演示）" @click="onVoice">
              <el-icon :size="20"><Microphone /></el-icon>
            </el-button>
            <el-button
              type="primary"
              round
              class="send-btn"
              :loading="sending"
              :disabled="!queryInput.trim()"
              @click="submitQuery()"
            >
              <el-icon><Promotion /></el-icon>
              发送
            </el-button>
          </div>
        </div>
        <p v-if="uiPhase === 'home'" class="floating-hint">Enter 发送 · Shift+Enter 换行 · 支持图片触发识别</p>

        <div v-if="uiPhase === 'home'" class="capability-row">
          <el-button text type="primary" size="small" class="capability-toggle" @click="toggleCapabilityDemo">
            {{ showCapabilityPanel ? '收起「你可以做什么」' : '你可以做什么？' }}
          </el-button>
        </div>
        <transition name="cap-panel">
          <div v-if="uiPhase === 'home' && showCapabilityPanel" class="capability-panel">
            <div class="capability-panel-inner">
              <span class="cap-role" :class="capabilityRole === 'user' ? 'cap-role--u' : 'cap-role--a'">
                {{ capabilityRole === 'user' ? '示例提问' : 'AI' }}
              </span>
              <p class="cap-typing">
                {{ capabilityTyping }}<span v-if="capabilityTyping" class="demo-caret demo-caret--dim" />
              </p>
            </div>
          </div>
        </transition>
      </div>

      <section
        v-if="uiPhase === 'home'"
        class="insight-section"
        :class="{ 'insight-section--dim': focusDim }"
        aria-label="启发式建议"
      >
        <div class="insight-head">
          <span class="insight-title">动态赋能流</span>
          <span class="insight-sub">结合校历、周期行为与闭环状态，AI 主动置顶更紧急的卡片</span>
        </div>
        <div class="insight-track">
          <article
            v-for="(card, idx) in insightCards"
            :key="card.id"
            class="insight-card insight-card--float"
            :style="{ background: card.gradient, animationDelay: `${idx * 0.12}s` }"
          >
            <div class="insight-card-inner">
              <div class="insight-left">
                <div class="insight-ico">
                  <el-icon :size="22"><component :is="card.icon" /></el-icon>
                </div>
                <div>
                  <div class="insight-kind">
                    {{
                      card.kind === 'calendar'
                        ? '伴随式日程'
                        : card.kind === 'cycle'
                          ? '周期预判'
                          : '逆向闭环'
                    }}
                  </div>
                  <h3 class="insight-card-title">{{ card.title }}</h3>
                </div>
              </div>
              <p class="insight-analysis">{{ card.analysis }}</p>
              <div class="insight-actions">
                <el-button type="primary" round size="small" :disabled="sending" @click="onInsightPrimary(card)">
                  {{ card.cta }}
                </el-button>
                <el-button
                  v-if="card.secondaryCta"
                  round
                  size="small"
                  :disabled="sending"
                  @click="onInsightSecondary(card)"
                >
                  {{ card.secondaryCta }}
                </el-button>
              </div>
            </div>
          </article>
        </div>
      </section>

      <div v-if="uiPhase === 'result'" class="result-toolbar">
        <el-button text type="primary" :icon="RefreshRight" @click="resetHome">新对话</el-button>
      </div>
    </header>

    <section v-if="uiPhase === 'result'" class="workspace" aria-live="polite">
      <transition name="panel-rise">
        <div v-if="thinking" key="think" class="think-panel">
          <div v-if="thinkStreamLine" class="think-stream">{{ thinkStreamLine }}</div>
          <div class="think-title">
            <el-icon class="spin"><Cpu /></el-icon>
            多主体联动中
          </div>
          <ul class="think-list">
            <li v-for="(s, i) in thinkSteps" :key="i" :class="{ done: s.done }">
              <el-icon v-if="s.done" class="chk"><CircleCheck /></el-icon>
              <span v-else class="dot" />
              {{ s.text }}
            </li>
          </ul>
        </div>
      </transition>

      <transition name="panel-rise">
        <div v-if="!thinking && abnormalMode" key="abn" class="sheet-panel abnormal">
          <div class="abn-head">
            <el-icon><WarningFilled /></el-icon>
            风控提示
          </div>
          <p class="abn-text">{{ abnormalText }}</p>
          <el-form label-width="88px" class="recv-form">
            <el-form-item label="收货人" required>
              <el-input v-model="receiverName" placeholder="姓名" />
            </el-form-item>
            <el-form-item label="收货地点" required>
              <el-input v-model="receiverDest" placeholder="如：教学楼 A302" />
            </el-form-item>
          </el-form>
          <el-button type="danger" :loading="submitting" class="full-btn" @click="confirmForceSubmit">
            强制提交（留痕）
          </el-button>
        </div>
      </transition>

      <transition name="panel-rise">
        <div
          v-if="!thinking && scenarioFlowActive && (scenarioAiReplyText || scenarioReplyTyping)"
          key="scenario-reply"
          class="scenario-reply-panel"
        >
          <div class="scenario-reply-head">
            <span class="scenario-reply-avatar">AI</span>
            <div>
              <div class="scenario-reply-name">采购与物资助手</div>
              <div class="scenario-reply-tag">模拟回复 · 预设演示</div>
            </div>
          </div>
          <p class="scenario-reply-body">
            {{ scenarioAiReplyText }}<span v-if="scenarioReplyTyping" class="demo-caret" />
          </p>
        </div>
      </transition>

      <transition name="panel-rise">
        <div
          v-if="
            !thinking &&
            !abnormalMode &&
            sheetItems.length &&
            (!scenarioFlowActive || scenarioSheetReady)
          "
          key="sheet"
          class="sheet-panel"
        >
          <div class="linkage-bar">
            <span>教务场景</span>
            <span class="dot-sep">·</span>
            <span>仓储 WMS</span>
            <span class="dot-sep">·</span>
            <span>院系额度</span>
            <span class="linkage-ok">已联动预检</span>
          </div>

          <div class="sheet-header">
            <div>
              <h2 class="sheet-title">{{ sheetTitle }}</h2>
              <p v-if="assistantNote" class="sheet-note">{{ assistantNote }}</p>
            </div>
            <div class="sheet-badge">
              <span class="live-dot" />
              健康度监测 · 库存预检
            </div>
          </div>

          <div class="sheet-grid">
            <div v-for="row in sheetItems" :key="row.key" class="sku-card">
              <div class="sku-emoji" aria-hidden="true">{{ row.emoji }}</div>
              <div class="sku-main">
                <div class="sku-name">{{ row.name }}</div>
                <div class="sku-meta">
                  <span v-if="row.stockLevel === 'ok'" class="stock-pill ok">🟢 库存充足</span>
                  <span v-else-if="row.stockLevel === 'low'" class="stock-pill low">
                    🟡 仅剩 {{ row.lowStockCount ?? '—' }} 份
                  </span>
                  <span v-else-if="row.stockLevel === 'substituted'" class="stock-pill sub">🔄 智能替换</span>
                </div>
                <p v-if="row.substitutionNote" class="subst-note">{{ row.substitutionNote }}</p>
                <div class="qty-row">
                  <span class="qty-label">建议数量</span>
                  <el-button size="small" circle @click="bumpQty(row, -1)">−</el-button>
                  <span class="qty-val">{{ row.quantity }}</span>
                  <el-button size="small" circle @click="bumpQty(row, 1)">+</el-button>
                  <span class="unit">{{ row.unit }}</span>
                  <span v-if="row.unitPrice > 0" class="unit-price">约 ¥{{ row.unitPrice }}/单位</span>
                </div>
              </div>
            </div>
          </div>

          <div class="sheet-footer">
            <div class="footer-left">
              <div class="estimate-row">
                <span class="estimate-label">预估消耗额度（演示）</span>
                <span class="estimate-val">¥{{ formatMoney(estimatedTotal) }}</span>
              </div>
              <el-form label-width="88px" class="recv-form recv-form--row">
                <el-form-item label="收货人" required>
                  <el-input v-model="receiverName" placeholder="默认可改" class="recv-input" />
                </el-form-item>
                <el-form-item label="收货地点" required>
                  <el-input v-model="receiverDest" placeholder="送达位置" class="recv-input-wide" />
                </el-form-item>
              </el-form>
            </div>
            <el-button
              type="primary"
              size="large"
              class="confirm-btn"
              :loading="submitting"
              @click="confirmPurchase"
            >
              {{ scenarioFlowActive ? '同意并提交' : '确认无误，提交后勤仓储' }}
            </el-button>
          </div>
        </div>
      </transition>

      <div
        v-if="
          !thinking &&
          !abnormalMode &&
          !sheetItems.length &&
          uiPhase === 'result' &&
          !sending &&
          !scenarioFlowActive
        "
        class="empty-hint"
      >
        未生成业务微件，请在上方的万能中枢重新描述需求。
      </div>
    </section>

    <footer class="dock" :class="{ 'dock--compact': uiPhase === 'result' }">
      <div class="dock-bundles">
        <span class="dock-label"><el-icon><ShoppingBag /></el-icon> 常用物资组合包</span>
        <div class="dock-chips">
          <button
            v-for="b in bundles"
            :key="b.id"
            type="button"
            class="dock-bundle-btn"
            :disabled="sending"
            @click="applyBundle(b)"
          >
            {{ b.label }}
          </button>
        </div>
      </div>
      <div v-if="tracking" class="dock-track">
        <div class="dock-track-head">
          <el-icon><Van /></el-icon>
          <span>在途</span>
          <span class="mono">{{ tracking.order_no }}</span>
        </div>
        <p class="dock-track-msg">{{ tracking.message }}</p>
        <div class="dock-progress">
          <div
            class="dock-progress-fill"
            :style="{ width: `${Math.round((tracking.step / tracking.total) * 100)}%` }"
          />
        </div>
        <div class="dock-steps">
          <span :class="{ on: tracking.step >= 1 }">已提交</span>
          <span :class="{ on: tracking.step >= 2 }">仓储处理</span>
          <span :class="{ on: tracking.step >= 3 }">配送</span>
          <span :class="{ on: tracking.step >= 4 }">签收</span>
        </div>
      </div>
      <el-button text type="primary" size="small" class="dock-refresh" @click="refreshTrackingFromApi">
        同步订单状态
      </el-button>
    </footer>

    <teleport to="body">
      <transition name="success-pop">
        <div v-if="scenarioSubmitSuccess" class="submit-success-overlay">
          <div class="submit-success-card">
            <div class="submit-success-ring" aria-hidden="true" />
            <el-icon class="submit-success-icon" :size="56"><CircleCheck /></el-icon>
            <h3 class="submit-success-title">申请提交成功</h3>
            <p class="submit-success-desc">后勤仓储已接单，正在为您备货与安排配送</p>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<style scoped lang="scss">
.native {
  position: relative;
  min-height: calc(100vh - 100px);
  padding: 8px 8px 120px;
  max-width: 1120px;
  margin: 0 auto;
  transition: background-color 0.35s ease;
}

.native--dim .native-bg {
  opacity: 0.38;
  filter: saturate(0.75);
}

.native-bg {
  pointer-events: none;
  position: fixed;
  inset: 0;
  background: radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99, 102, 241, 0.14), transparent 55%),
    radial-gradient(ellipse 60% 40% at 100% 0%, rgba(14, 165, 233, 0.08), transparent 45%);
  z-index: 0;
  transition: opacity 0.35s ease;
}

.native > .native-bg {
  z-index: 0;
}

.native > .composer-zone,
.native > .workspace {
  position: relative;
  z-index: 2;
}
.native > .dock {
  z-index: 30;
}

.composer-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 28px 12px 8px;
  transition:
    padding 0.45s cubic-bezier(0.22, 1, 0.36, 1),
    align-items 0.35s ease;
}

.composer-zone--top {
  align-items: stretch;
  padding: 8px 0 12px;
  position: sticky;
  top: 0;
  z-index: 20;
  background: linear-gradient(180deg, var(--el-bg-color-page, #f8fafc) 75%, transparent);
  backdrop-filter: blur(12px);
}

.greeting {
  margin: 0 0 24px 0;
  font-size: clamp(21px, 3.4vw, 28px);
  font-weight: 650;
  letter-spacing: -0.02em;
  text-align: center;
  line-height: 1.38;
  max-width: 820px;
  color: var(--text-primary);
}

.greeting-char {
  display: inline-block;
  opacity: 0.08;
  transform: translateY(6px);
  transition:
    opacity 0.32s ease,
    transform 0.42s cubic-bezier(0.22, 1, 0.36, 1);
}

.greeting-char--on {
  opacity: 1;
  transform: translateY(0);
}

.greet-fade-enter-active,
.greet-fade-leave-active {
  transition: opacity 0.35s ease, transform 0.35s ease;
}
.greet-fade-enter-from,
.greet-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.floating-shell {
  width: 100%;
  max-width: 760px;
  position: relative;
}

.composer-zone--top .floating-shell {
  max-width: none;
}

.floating-shell--pulse .omnibox-halo {
  position: absolute;
  inset: -3px;
  border-radius: 22px;
  background: linear-gradient(
    120deg,
    rgba(99, 102, 241, 0.45),
    rgba(14, 165, 233, 0.35),
    rgba(99, 102, 241, 0.45)
  );
  background-size: 200% 200%;
  animation: halo-breathe 4s ease-in-out infinite;
  opacity: 0.55;
  filter: blur(8px);
  z-index: 0;
  pointer-events: none;
}
@keyframes halo-breathe {
  0%,
  100% {
    background-position: 0% 50%;
    opacity: 0.45;
  }
  50% {
    background-position: 100% 50%;
    opacity: 0.7;
  }
}

.omnibox-ready {
  position: relative;
  z-index: 1;
  margin: 0 0 10px 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  display: flex;
  align-items: center;
  gap: 8px;
}
.ready-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.35);
  animation: pulse 2s ease-in-out infinite;
}

.floating-bar {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 14px 14px 14px 20px;
  border-radius: 20px;
  background: var(--bg-card);
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow:
    0 4px 6px -1px rgba(15, 23, 42, 0.06),
    0 18px 48px -12px rgba(79, 70, 229, 0.2);
}

.composer-zone--top .floating-bar {
  border-radius: 14px;
  padding: 10px 12px 10px 16px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.08);
}

.composer-zone--top .omnibox-halo,
.composer-zone--top .omnibox-ready {
  display: none;
}

.floating-input {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  min-height: 52px;
  max-height: 160px;
  font-size: 16px;
  line-height: 1.5;
  background: transparent;
  color: var(--text-primary);
  font-family: inherit;
}

.composer-zone--top .floating-input {
  min-height: 40px;
  font-size: 15px;
}

.floating-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.file-input {
  display: none;
}

.ico-btn {
  color: var(--text-muted);
}

.send-btn {
  padding: 10px 20px;
  font-weight: 600;
}

.floating-hint {
  position: relative;
  z-index: 1;
  margin: 10px 0 0 0;
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
}

.scenario-reply-panel {
  margin-bottom: 16px;
  padding: 18px 20px;
  border-radius: 18px;
  background: var(--bg-card);
  border: 1px solid rgba(99, 102, 241, 0.16);
  box-shadow: 0 14px 40px rgba(79, 70, 229, 0.1);
}

.scenario-reply-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.scenario-reply-avatar {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(135deg, #6366f1, #0ea5e9);
}

.scenario-reply-name {
  font-size: 14px;
  font-weight: 750;
  color: var(--text-primary);
}

.scenario-reply-tag {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.scenario-reply-body {
  margin: 0;
  font-size: 14px;
  line-height: 1.65;
  color: var(--text-primary);
  white-space: pre-wrap;
}

.submit-success-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(8px);
}

.submit-success-card {
  position: relative;
  text-align: center;
  padding: 40px 48px 36px;
  border-radius: 24px;
  background: var(--bg-card);
  box-shadow:
    0 24px 80px rgba(15, 23, 42, 0.2),
    0 0 0 1px rgba(255, 255, 255, 0.08) inset;
  animation: success-card-in 0.55s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.submit-success-ring {
  position: absolute;
  left: 50%;
  top: 44px;
  width: 88px;
  height: 88px;
  margin-left: -44px;
  margin-top: -44px;
  border-radius: 50%;
  border: 3px solid rgba(16, 185, 129, 0.35);
  animation: success-ring-pulse 1.4s ease-out 0.2s both;
  pointer-events: none;
}

.submit-success-icon {
  color: #10b981;
  margin-bottom: 12px;
  animation: success-icon-pop 0.6s cubic-bezier(0.22, 1, 0.36, 1) 0.15s both;
}

.submit-success-title {
  margin: 0 0 8px 0;
  font-size: 22px;
  font-weight: 800;
  color: var(--text-primary);
}

.submit-success-desc {
  margin: 0;
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.5;
}

.success-pop-enter-active,
.success-pop-leave-active {
  transition: opacity 0.35s ease;
}
.success-pop-enter-active .submit-success-card,
.success-pop-leave-active .submit-success-card {
  transition:
    transform 0.35s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.35s ease;
}
.success-pop-enter-from,
.success-pop-leave-to {
  opacity: 0;
}
.success-pop-enter-from .submit-success-card,
.success-pop-leave-to .submit-success-card {
  opacity: 0;
  transform: scale(0.92) translateY(12px);
}

@keyframes success-card-in {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes success-icon-pop {
  from {
    opacity: 0;
    transform: scale(0.2);
  }
  70% {
    transform: scale(1.08);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes success-ring-pulse {
  from {
    opacity: 0.9;
    transform: scale(0.75);
  }
  to {
    opacity: 0;
    transform: scale(1.45);
  }
}

.demo-caret {
  display: inline-block;
  width: 7px;
  height: 1em;
  margin-left: 1px;
  vertical-align: -2px;
  border-radius: 1px;
  background: var(--primary);
  animation: caret-blink 0.9s step-end infinite;
}

.demo-caret--dim {
  background: var(--text-muted);
  opacity: 0.65;
}

@keyframes caret-blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}

.capability-row {
  margin-top: 10px;
  text-align: center;
}

.capability-toggle {
  font-weight: 650;
}

.cap-panel-enter-active,
.cap-panel-leave-active {
  transition:
    opacity 0.3s ease,
    transform 0.4s cubic-bezier(0.22, 1, 0.36, 1);
}
.cap-panel-enter-from,
.cap-panel-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.capability-panel {
  margin-top: 8px;
  width: 100%;
  max-width: 760px;
  border-radius: 14px;
  border: 1px dashed rgba(99, 102, 241, 0.28);
  background: rgba(255, 255, 255, 0.55);
  padding: 12px 14px;
}

.capability-panel-inner {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cap-role {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  align-self: flex-start;
  padding: 2px 8px;
  border-radius: 6px;
}

.cap-role--u {
  color: #4f46e5;
  background: rgba(79, 70, 229, 0.12);
}

.cap-role--a {
  color: #0d9488;
  background: rgba(13, 148, 136, 0.14);
}

.cap-typing {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--text-primary);
  min-height: 2.8em;
}

.insight-section {
  width: 100%;
  max-width: 100%;
  margin-top: 28px;
  padding: 0 4px 8px;
  transition: opacity 0.35s ease, filter 0.35s ease;
}
.insight-section--dim {
  opacity: 0.4;
  filter: saturate(0.8);
  pointer-events: none;
}
.insight-head {
  margin-bottom: 14px;
  max-width: 760px;
  margin-left: auto;
  margin-right: auto;
}
.insight-title {
  font-weight: 800;
  font-size: 16px;
  display: block;
  margin-bottom: 4px;
}
.insight-sub {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.45;
}

.insight-track {
  display: flex;
  gap: 14px;
  overflow-x: auto;
  padding: 6px 2px 14px;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
}
.insight-card {
  flex: 0 0 min(360px, 88vw);
  scroll-snap-align: start;
  border-radius: 18px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.08);
}

.insight-card--float {
  opacity: 0;
  animation: card-float-in 0.72s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

@keyframes card-float-in {
  from {
    opacity: 0;
    transform: translateY(26px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.insight-card-inner {
  padding: 16px 16px 14px;
}
.insight-left {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 10px;
}
.insight-ico {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
}
.insight-kind {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-bottom: 2px;
}
.insight-card-title {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
}
.insight-analysis {
  margin: 0 0 12px 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--text-secondary);
}
.insight-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.result-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.workspace {
  padding: 8px 0 32px;
  max-width: 960px;
  margin: 0 auto;
}

.think-panel {
  padding: 20px 22px;
  border-radius: 18px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  margin-bottom: 16px;
}
.think-stream {
  font-size: 13px;
  font-weight: 600;
  color: var(--primary);
  margin-bottom: 12px;
  min-height: 1.4em;
  line-height: 1.45;
}
.think-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 15px;
  margin-bottom: 12px;
}
.spin {
  animation: spin 1.1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.think-list {
  list-style: none;
  margin: 0;
  padding: 0;
  li {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 0;
    font-size: 13px;
    color: var(--text-secondary);
    &.done {
      color: var(--text-primary);
    }
  }
  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--border-subtle);
    flex-shrink: 0;
  }
  .chk {
    color: var(--el-color-success);
    flex-shrink: 0;
  }
}

.linkage-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 14px;
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(99, 102, 241, 0.06);
  border: 1px solid rgba(99, 102, 241, 0.12);
}
.dot-sep {
  opacity: 0.45;
}
.linkage-ok {
  margin-left: auto;
  color: #059669;
}

.sheet-panel {
  border-radius: 20px;
  border: 1px solid rgba(99, 102, 241, 0.2);
  background: linear-gradient(165deg, rgba(99, 102, 241, 0.06) 0%, var(--bg-card) 38%);
  padding: 20px 22px 18px;
  box-shadow: 0 20px 60px rgba(79, 70, 229, 0.1);
}
.sheet-panel.abnormal {
  border-color: rgba(239, 68, 68, 0.35);
  background: linear-gradient(165deg, rgba(239, 68, 68, 0.08) 0%, var(--bg-card) 40%);
}
.abn-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: #dc2626;
  margin-bottom: 10px;
}
.abn-text {
  margin: 0 0 16px 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.sheet-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  align-items: flex-start;
}
.sheet-title {
  margin: 0 0 8px 0;
  font-size: 21px;
  font-weight: 800;
  letter-spacing: -0.02em;
}
.sheet-note {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.55;
  white-space: pre-wrap;
  max-width: 640px;
}
.sheet-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #059669;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.12);
}
.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.25);
  animation: pulse 1.6s ease-in-out infinite;
}
@keyframes pulse {
  50% {
    opacity: 0.65;
    transform: scale(0.92);
  }
}

.sheet-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(268px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.sku-card {
  display: flex;
  gap: 12px;
  padding: 14px;
  border-radius: 14px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
}
.sku-emoji {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  flex-shrink: 0;
}
.sku-name {
  font-weight: 600;
  font-size: 15px;
  margin-bottom: 6px;
}
.stock-pill {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 6px;
  font-weight: 600;
  &.ok {
    background: #d1fae5;
    color: #047857;
  }
  &.low {
    background: #fef9c3;
    color: #a16207;
  }
  &.sub {
    background: #e0e7ff;
    color: #4338ca;
  }
}
.subst-note {
  margin: 8px 0 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: #92400e;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(251, 191, 36, 0.15);
  border: 1px dashed rgba(245, 158, 11, 0.45);
}
.qty-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}
.qty-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-right: 4px;
}
.qty-val {
  min-width: 28px;
  text-align: center;
  font-weight: 700;
  font-size: 15px;
}
.unit {
  font-size: 12px;
  color: var(--text-muted);
}
.unit-price {
  font-size: 11px;
  color: var(--text-muted);
  margin-left: auto;
}

.sheet-footer {
  border-top: 1px solid var(--border-subtle);
  padding-top: 16px;
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 16px;
  justify-content: space-between;
}
.footer-left {
  flex: 1;
  min-width: 240px;
}
.estimate-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 12px;
}
.estimate-label {
  font-size: 13px;
  color: var(--text-muted);
}
.estimate-val {
  font-size: 22px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}
.recv-form {
  flex: 1;
  min-width: 240px;
}
.recv-form--row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 28px;
  align-items: flex-end;
}
.recv-input {
  width: 200px;
  max-width: 100%;
}
.recv-input-wide {
  width: 260px;
  max-width: 100%;
}
.confirm-btn {
  min-width: 220px;
  font-weight: 800;
  font-size: 15px;
  border-radius: 14px;
  padding: 22px 28px;
  box-shadow: 0 8px 28px rgba(79, 70, 229, 0.35);
}
.full-btn {
  width: 100%;
  margin-top: 8px;
}

.empty-hint {
  text-align: center;
  color: var(--text-muted);
  font-size: 14px;
  padding: 32px 12px;
}

.panel-rise-enter-active {
  transition: all 0.45s cubic-bezier(0.22, 1, 0.36, 1);
}
.panel-rise-enter-from {
  opacity: 0;
  transform: translateY(24px);
}

.dock {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 16px;
  width: calc(100% - 32px);
  max-width: 1120px;
  z-index: 30;
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px 20px;
  padding: 12px 16px;
  border-radius: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  box-shadow: 0 12px 48px rgba(15, 23, 42, 0.12);
}
.dock--compact {
  padding: 10px 14px;
}
.dock-bundles {
  flex: 1;
  min-width: 200px;
}
.dock-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
}
.dock-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.dock-bundle-btn {
  border: 1px solid var(--border-subtle);
  background: var(--bg-elevated);
  font-size: 12px;
  font-weight: 600;
  padding: 8px 14px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.15s ease;
  &:hover:not(:disabled) {
    border-color: rgba(99, 102, 241, 0.45);
    color: var(--primary);
  }
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}
.dock-track {
  flex: 1;
  min-width: 260px;
  max-width: 400px;
  padding: 8px 12px;
  border-radius: 12px;
  background: rgba(99, 102, 241, 0.06);
  border: 1px solid rgba(99, 102, 241, 0.12);
}
.dock-track-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.mono {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  color: var(--primary);
}
.dock-track-msg {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
}
.dock-progress {
  height: 4px;
  border-radius: 4px;
  background: rgba(15, 23, 42, 0.08);
  overflow: hidden;
  margin-bottom: 6px;
}
.dock-progress-fill {
  height: 100%;
  border-radius: 4px;
  background: linear-gradient(90deg, #6366f1, #22d3ee);
  transition: width 0.4s ease;
}
.dock-steps {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--text-muted);
  span.on {
    color: var(--primary);
    font-weight: 700;
  }
}
.dock-refresh {
  align-self: center;
}

:global(html.dark) .floating-bar {
  border-color: rgba(148, 163, 184, 0.15);
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.35);
}
:global(html.dark) .composer-zone--top {
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.94) 70%, transparent);
}
:global(html.dark) .dock {
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.45);
}
</style>
