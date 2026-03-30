<script setup lang="ts">
import { computed, ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DeleteFilled } from '@element-plus/icons-vue'
import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'
import {
  listIDSEvents,
  getIDSStats,
  getIDSTrend,
  archiveIDSEvent,
  archiveIDSBatch,
  analyzeIDSEventAI,
  updateIDSEventStatus,
  blockIDSEventIp,
  unblockIDSEventIp,
  getIDSEventReport,
  seedIDSDemoPhase1,
  seedIDSDemoPhase2,
  resetIDSDemoEvents,
  getIDSPhase1AggregateReport,
} from '@/api/ids'
import type { IDSEventItem } from '@/api/ids'

const loading = ref(false)
const trendDays = ref(7)
const trendData = ref<{ dates: string[]; counts: number[] }>({ dates: [], counts: [] })
const stats = ref<{
  total: number
  blocked_count: number
  high_risk_count?: number
  by_type: { attack_type: string; attack_type_label: string; count: number }[]
  by_status?: { status: string; count: number }[]
} | null>(null)
const tableData = ref<IDSEventItem[]>([])
const total = ref(0)
const attackTypeFilter = ref('')
const clientIpFilter = ref('')
const blockedFilter = ref<number | undefined>(undefined)
const archivedFilter = ref<number | undefined>(undefined)
const statusFilter = ref<string>('')
const minScoreFilter = ref<number | undefined>(undefined)
const pageSize = ref(20)
const pageOffset = ref(0)
const selectedIds = ref<number[]>([])
const detailVisible = ref(false)
const currentRow = ref<IDSEventItem | null>(null)
const simulatingAttack = ref(false)
const aiAnalyzingId = ref<number | null>(null)
const reportVisible = ref(false)
const reportLoading = ref(false)
const reportMarkdown = ref('')
const reportData = ref<any | null>(null)
const reportOrderNo = ref('')
const reportMeta = ref<{ reportNo: string; generatedAt: string; title: string; headerSuffix: string }>({
  reportNo: '',
  generatedAt: '',
  title: '校园物资供应链安全监测平台',
  headerSuffix: '安全事件分析报告',
})
const reportContainerRef = ref<HTMLElement | null>(null)
const aiProcessVisible = ref(false)
const aiProcessText = ref('AI 正在初始化安全研判引擎...')
const aiProcessStage = ref(1)
const aiProcessTotalStages = ref(4)
const aiProcessProgress = ref(12)
const aiProcessMode = ref<'analysis' | 'phase1' | 'phase2'>('analysis')
const aiProcessFeed = ref<string[]>([])
let aiProcessTimer: ReturnType<typeof setInterval> | null = null
const phase1UnlockCounter = ref(0)
const phase2UnlockCounter = ref(0)
const phase1Unlocked = ref(false)
const phase2Unlocked = ref(false)
let phase1UnlockTimer: ReturnType<typeof setTimeout> | null = null
let phase2UnlockTimer: ReturnType<typeof setTimeout> | null = null
const clearArmed = ref(false)
let clearArmTimer: ReturnType<typeof setTimeout> | null = null
const timelineVisible = ref(false)
const timelineLoading = ref(false)
const timelineRows = ref<IDSEventItem[]>([])
const timelineAutoStage = ref(1)
let timelineStageTimer: ReturnType<typeof setInterval> | null = null

const idsHudClock = ref('')
let idsHudClockTimer: ReturnType<typeof setInterval> | null = null
function tickIdsHudClock() {
  idsHudClock.value = new Date().toLocaleString('zh-CN', { hour12: false })
}

async function fetchStats() {
  try {
    const res: any = await getIDSStats()
    stats.value = res?.data ?? res
    renderPieChart()
  } catch {
    stats.value = null
  }
}

async function fetchTrend() {
  try {
    const res: any = await getIDSTrend(trendDays.value)
    trendData.value = res?.data ?? res ?? { dates: [], counts: [] }
    renderTrendChart()
  } catch {
    trendData.value = { dates: [], counts: [] }
  }
}

let pieChartInstance: echarts.ECharts | null = null
let trendChartInstance: echarts.ECharts | null = null

const PIE_COLORS = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899']

function renderPieChart() {
  const el = document.getElementById('ids-pie-chart')
  if (!el || !stats.value?.by_type?.length) return
  if (!pieChartInstance) pieChartInstance = echarts.init(el, 'dark')
  pieChartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
      backgroundColor: 'rgba(15, 23, 42, 0.96)',
      borderColor: 'rgba(56, 189, 248, 0.35)',
      borderWidth: 1,
      padding: [10, 14],
      textStyle: { color: '#e2e8f0', fontSize: 14 },
    },
    color: PIE_COLORS,
    legend: {
      type: 'scroll',
      orient: 'vertical',
      right: 14,
      top: 'middle',
      width: 200,
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 10,
      textStyle: { color: 'rgba(255,255,255,0.82)', fontSize: 13 },
      pageTextStyle: { color: 'rgba(255,255,255,0.55)' },
      pageIconColor: 'rgba(255,255,255,0.45)',
      pageIconInactiveColor: 'rgba(255,255,255,0.2)',
    },
    series: [{
      type: 'pie',
      radius: ['40%', '62%'],
      center: ['30%', '50%'],
      data: stats.value.by_type.map((t: { attack_type_label: string; count: number }) => ({
        name: t.attack_type_label,
        value: t.count,
      })),
      label: { show: false },
      labelLine: { show: false },
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(59,130,246,0.4)' } },
    }],
  })
}

function renderTrendChart() {
  const el = document.getElementById('ids-trend-chart')
  if (!el) return
  if (!trendChartInstance) trendChartInstance = echarts.init(el, 'dark')
  const { dates, counts } = trendData.value
  trendChartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.96)',
      borderColor: 'rgba(56, 189, 248, 0.35)',
      borderWidth: 1,
      padding: [10, 14],
      textStyle: { color: '#e2e8f0', fontSize: 14 },
    },
    grid: { left: 48, right: 24, top: 24, bottom: 36 },
    xAxis: {
      type: 'category',
      data: dates?.length ? dates.map((d: string) => d.slice(5)) : [],
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } },
      axisLabel: { color: 'rgba(255,255,255,0.55)', fontSize: 13 },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)', type: 'dashed' } },
      axisLabel: { color: 'rgba(255,255,255,0.55)', fontSize: 13 },
    },
    series: [{
      type: 'bar',
      data: counts ?? [],
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(59,130,246,0.8)' },
          { offset: 1, color: 'rgba(59,130,246,0.2)' },
        ]),
      },
    }],
  })
}

const idsTableMaxHeight = ref(440)

function refreshIdsTableMaxHeight() {
  idsTableMaxHeight.value = Math.max(300, Math.min(560, Math.round(window.innerHeight - 400)))
}

function handleResize() {
  pieChartInstance?.resize()
  trendChartInstance?.resize()
  refreshIdsTableMaxHeight()
}

async function fetchData() {
  loading.value = true
  try {
    const res: any = await listIDSEvents({
      attack_type: attackTypeFilter.value || undefined,
      client_ip: clientIpFilter.value || undefined,
      blocked: blockedFilter.value,
      archived: archivedFilter.value,
      status: statusFilter.value || undefined,
      min_score: minScoreFilter.value,
      limit: pageSize.value,
      offset: pageOffset.value,
    })
    const data = res?.data ?? res
    tableData.value = data?.items ?? []
    total.value = data?.total ?? 0
  } catch {
    tableData.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function parseDateTime(v: string | null | undefined): Date | null {
  if (!v) return null
  const dt = new Date(v.replace(' ', 'T'))
  if (Number.isNaN(dt.getTime())) return null
  return dt
}

function fmtNodeTime(v: string | null | undefined): string {
  return v || '-'
}

/** 表格中单行展示时间，避免换行导致行高不齐 */
function fmtTableDateTime(v: string | null | undefined): string {
  if (!v) return '-'
  return String(v).trim().replace(/\s+/g, ' ')
}

function fmtConfidencePct(v: number | null | undefined): string {
  const n = v == null || Number.isNaN(Number(v)) ? 0 : Number(v)
  return `${Math.round(n)}%`
}

/** 列表「策略」列：规则名改为固定两字中文，避免 IDS-Block… 被截断 */
function fmtFirewallRuleTable(rule: string | null | undefined): string {
  if (!rule?.trim()) return '-'
  const s = rule.trim()
  if (/IDS[-_]?Block/i.test(s)) return '拦截'
  if (/IDS[-_]?Allow/i.test(s)) return '放行'
  if (/drop|deny|block/i.test(s)) return '拦截'
  if (/pass|accept|allow/i.test(s)) return '放行'
  return '已配'
}

const timelineSummaryNodes = computed(() => {
  const rows = [...timelineRows.value].sort((a, b) => (parseDateTime(a.created_at)?.getTime() || 0) - (parseDateTime(b.created_at)?.getTime() || 0))
  const phase1 = rows.filter((r) => (r.action_taken || '').startsWith('demo_seed_phase1::'))
  const phase2 = rows.filter((r) => (r.action_taken || '').startsWith('demo_seed_phase2::'))
  const all = [...phase1, ...phase2]
  const first = all[0]
  const highRisk = all.filter((r) => Number(r.risk_score || 0) >= 70).length
  const blocked = all.filter((r) => !!r.blocked).length
  const archived = all.filter((r) => !!r.archived || r.status === 'closed').length
  const aiDone = all.filter((r) => !!(r.ai_analysis || r.ai_risk_level)).length
  const byAttack = new Map<string, number>()
  all.forEach((r) => {
    const key = r.attack_type_label || r.attack_type || '未知类型'
    byAttack.set(key, (byAttack.get(key) || 0) + 1)
  })
  const attacks = [...byAttack.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([name, cnt]) => `${name} x${cnt}`)
    .join('，')
  return [
    {
      key: 's-1',
      title: '请求进入',
      detail: `${fmtNodeTime(first?.created_at)} 开始接收攻防流量，累计事件 ${all.length} 条`,
      state: 'info' as const,
    },
    {
      key: 's-2',
      title: '命中特征',
      detail: `涉及攻击：${attacks || '无'}；高风险 ${highRisk} 条`,
      state: highRisk > 0 ? ('danger' as const) : ('warning' as const),
    },
    {
      key: 's-3',
      title: '响应动作',
      detail: `已执行阻断/封禁 ${blocked} 次，形成联动处置与审计留痕`,
      state: blocked > 0 ? ('success' as const) : ('warning' as const),
    },
    {
      key: 's-4',
      title: 'AI 结论',
      detail: `AI 已完成 ${aiDone} 条研判，输出风险等级与处置建议`,
      state: aiDone > 0 ? ('success' as const) : ('info' as const),
    },
    {
      key: 's-5',
      title: '归档闭环',
      detail: `已归档 ${archived} 条，形成“检测 -> 响应 -> 研判 -> 留档”总体链路`,
      state: archived > 0 ? ('success' as const) : ('info' as const),
    },
  ]
})

const timelineAttackList = computed(() => {
  const rows = timelineRows.value.filter((r) =>
    (r.action_taken || '').startsWith('demo_seed_phase1::') || (r.action_taken || '').startsWith('demo_seed_phase2::'),
  )
  const byAttack = new Map<string, number>()
  rows.forEach((r) => {
    const key = r.attack_type_label || r.attack_type || '未知类型'
    byAttack.set(key, (byAttack.get(key) || 0) + 1)
  })
  return [...byAttack.entries()].sort((a, b) => b[1] - a[1]).map(([name, cnt]) => ({ name, cnt }))
})

async function openEvidenceTimeline() {
  timelineVisible.value = true
  timelineLoading.value = true
  timelineAutoStage.value = 1
  if (timelineStageTimer) clearInterval(timelineStageTimer)
  timelineStageTimer = setInterval(() => {
    timelineAutoStage.value = Math.min(5, timelineAutoStage.value + 1)
  }, 520)
  try {
    const res: any = await listIDSEvents({ limit: 200, offset: 0 })
    const data = res?.data ?? res
    timelineRows.value = data?.items ?? []
    await new Promise((resolve) => setTimeout(resolve, 1800))
  } catch (e: any) {
    timelineRows.value = []
    ElMessage.error(e?.response?.data?.detail || e?.message || '加载证据链失败')
  } finally {
    if (timelineStageTimer) clearInterval(timelineStageTimer)
    timelineStageTimer = null
    timelineAutoStage.value = 5
    timelineLoading.value = false
  }
}

function handleSearch() {
  pageOffset.value = 0
  fetchData()
}

async function handleArchive(row: IDSEventItem) {
  try {
    await archiveIDSEvent(row.id)
    ElMessage.success('已归档')
    fetchData()
    fetchStats()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '归档失败')
  }
}

async function handleBatchArchive() {
  if (!selectedIds.value.length) {
    ElMessage.warning('请选择要归档的事件')
    return
  }
  try {
    await ElMessageBox.confirm(`确定归档选中的 ${selectedIds.value.length} 条记录？`, '批量归档')
    await archiveIDSBatch(selectedIds.value)
    ElMessage.success('批量归档成功')
    selectedIds.value = []
    fetchData()
    fetchStats()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || e?.message || '归档失败')
  }
}

function handleSelectionChange(rows: IDSEventItem[]) {
  selectedIds.value = rows.map((r) => r.id)
}

async function handleSimulateAttack() {
  simulatingAttack.value = true
  try {
    const payload = "1' OR '1'='1"
    // /api/goods 在 IDS 白名单内，改用未白名单的公开大屏接口以便规则命中
    const url = `/api/overview/screen?ids_demo=${encodeURIComponent(payload)}`
    await fetch(url, { credentials: 'include' })
  } catch {
    /* 403 为预期，请求已被 IDS 拦截 */
  }
  ElMessage.success('已发送模拟攻击请求，检测记录已生成，请查看上方列表')
  await fetchStats()
  await fetchTrend()
  await fetchData()
  simulatingAttack.value = false
}

function showDetail(row: IDSEventItem) {
  currentRow.value = row
  detailVisible.value = true
}

async function handleAiAnalyze(row: IDSEventItem) {
  aiAnalyzingId.value = row.id
  startAiProcess('AI 正在深度研判当前事件...')
  try {
    const res: any = await analyzeIDSEventAI(row.id)
    const data = res?.data ?? res
    ElMessage.success(data?.message || 'AI 研判完成')
    if (currentRow.value?.id === row.id) {
      currentRow.value = {
        ...currentRow.value,
        ai_risk_level: data?.ai_risk_level,
        ai_analysis: data?.ai_analysis,
        ai_confidence: data?.ai_confidence,
        ai_analyzed_at: data?.ai_analyzed_at,
      }
    }
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || 'AI 研判失败')
  } finally {
    aiAnalyzingId.value = null
    stopAiProcess()
  }
}

async function handleUpdateStatus(row: IDSEventItem, status: string) {
  try {
    await updateIDSEventStatus(row.id, { status })
    ElMessage.success('状态已更新')
    await fetchData()
    await fetchStats()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '状态更新失败')
  }
}

/** 操作列「更多」：状态 / 封禁 / 解封 / 归档 */
function handleIdsMoreMenu(row: IDSEventItem, cmd: string | number) {
  const c = String(cmd)
  if (c === 'investigating' || c === 'mitigated' || c === 'false_positive' || c === 'closed') {
    handleUpdateStatus(row, c)
    return
  }
  if (c === 'block') {
    handleManualBlock(row)
    return
  }
  if (c === 'unblock') {
    handleManualUnblock(row)
    return
  }
  if (c === 'archive' && !row.archived) {
    handleArchive(row)
  }
}

async function handleManualBlock(row: IDSEventItem) {
  try {
    const res: any = await blockIDSEventIp(row.id)
    const data = res?.data ?? res
    ElMessage.success(data?.message || '封禁已执行')
    await fetchData()
    await fetchStats()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '封禁失败')
  }
}

async function handleManualUnblock(row: IDSEventItem) {
  try {
    const res: any = await unblockIDSEventIp(row.id)
    const data = res?.data ?? res
    ElMessage.success(data?.message || '解封已执行')
    await fetchData()
    await fetchStats()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '解封失败')
  }
}

function stopAiProcess() {
  if (aiProcessTimer) clearInterval(aiProcessTimer)
  aiProcessTimer = null
  aiProcessVisible.value = false
  aiProcessStage.value = 1
  aiProcessTotalStages.value = 4
  aiProcessProgress.value = 12
  aiProcessFeed.value = []
  aiProcessMode.value = 'analysis'
}

function startAiProcess(
  a?: string,
  b?: 'analysis' | 'phase1' | 'phase2',
) {
  const stagesByMode: Record<'analysis' | 'phase1' | 'phase2', string[]> = {
    analysis: [
      'AI 正在深度研判事件并生成报告...',
      '正在回放命中规则并提取关键证据...',
      '正在计算风险等级与置信度...',
      '正在输出结构化安全报告...',
    ],
    phase1: [
      '战情引擎启动：批量注入多向量攻击链样本...',
      '规则与特征库匹配：SQL/XSS/路径/JNDI 等并发命中...',
      '联动响应执行：评分、拦截与审计留痕...',
      '正在生成多向量并发攻击聚合研判报告...',
      '报告中心同步：向量明细与处置建议已固化...',
    ],
    phase2: [
      '高危木马样本进入检测通道...',
      '入口层识别恶意上传并即时阻断...',
      '封禁策略联动执行，告警证据固化...',
      'AI 正在进行高危事件深度研判...',
      '报告中心生成审计级文档（PDF可导出）...',
    ],
  }
  let mode: 'analysis' | 'phase1' | 'phase2' = 'analysis'
  let customTitle: string | undefined
  if (b) {
    mode = b
    customTitle = a
  } else if (a === 'phase1' || a === 'phase2' || a === 'analysis') {
    mode = a
  } else {
    customTitle = a
  }
  const stages = stagesByMode[mode]
  const initialTitle = customTitle?.trim() ? customTitle : stages[0]
  if (aiProcessTimer) clearInterval(aiProcessTimer)
  aiProcessMode.value = mode
  aiProcessText.value = initialTitle
  aiProcessVisible.value = true
  aiProcessStage.value = 1
  aiProcessProgress.value = 12
  aiProcessTotalStages.value = stages.length
  aiProcessFeed.value = [initialTitle]
  let idx = 0
  aiProcessTimer = setInterval(() => {
    if (idx >= stages.length - 1) {
      aiProcessProgress.value = 100
      if (aiProcessTimer) clearInterval(aiProcessTimer)
      aiProcessTimer = null
      return
    }
    idx += 1
    aiProcessStage.value = idx + 1
    aiProcessText.value = stages[idx]
    aiProcessProgress.value = Math.min(100, 12 + Math.round(((idx + 1) / stages.length) * 88))
    aiProcessFeed.value = [...aiProcessFeed.value.slice(-4), stages[idx]]
  }, mode === 'analysis' ? 900 : 720)
}

async function exportReport(format: 'md' | 'html' | 'pdf') {
  const content = reportMarkdown.value?.trim()
  if (!content) {
    ElMessage.warning('暂无可导出的报告内容')
    return
  }
  const stamp = new Date().toISOString().replace(/[:.]/g, '-')
  const base = `ids-report-${reportOrderNo.value || 'event'}-${stamp}`
  let blob: Blob
  let filename: string
  if (format === 'pdf') {
    const el = reportContainerRef.value
    if (!el) {
      ElMessage.error('报告容器不可用，无法导出 PDF')
      return
    }
    try {
      const canvas = await html2canvas(el, {
        scale: 2,
        backgroundColor: '#0a0a0a',
        useCORS: true,
      })
      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF('p', 'pt', 'a4')
      const pageW = pdf.internal.pageSize.getWidth()
      const pageH = pdf.internal.pageSize.getHeight()
      const imgW = pageW - 40
      const imgH = (canvas.height * imgW) / canvas.width
      let heightLeft = imgH
      let position = 20
      pdf.addImage(imgData, 'PNG', 20, position, imgW, imgH)
      heightLeft -= (pageH - 40)
      while (heightLeft > 0) {
        position = heightLeft - imgH + 20
        pdf.addPage()
        pdf.addImage(imgData, 'PNG', 20, position, imgW, imgH)
        heightLeft -= (pageH - 40)
      }
      pdf.save(`${base}.pdf`)
      ElMessage.success('PDF 导出成功')
    } catch (e: any) {
      ElMessage.error(e?.message || 'PDF 导出失败')
    }
    return
  } else if (format === 'html') {
    const html = `<!doctype html><html><head><meta charset="utf-8"><title>${base}</title><style>body{font-family:Consolas,monospace;padding:24px;background:#0a0a0a;color:#e5e7eb;white-space:pre-wrap;line-height:1.6}</style></head><body>${content.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</body></html>`
    blob = new Blob([html], { type: 'text/html;charset=utf-8' })
    filename = `${base}.html`
  } else {
    blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
    filename = `${base}.md`
  }
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
  ElMessage.success('报告导出成功')
}

function buildProfessionalMarkdown(data: any, eventId: number): string {
  const r = data?.report || {}
  if (r.kind === 'aggregate_phase1') {
    const o = r?.overview || {}
    const reportNo = `SCSP-IDS-AGM-${String(eventId).padStart(6, '0')}`
    const generatedAt = r?.generated_at || new Date().toISOString().slice(0, 19).replace('T', ' ')
    const vectors = r?.vectors || []
    const labels = (r?.attack_type_labels || []).join('、')
    reportMeta.value = {
      reportNo,
      generatedAt,
      title: '校园物资供应链安全监测平台',
      headerSuffix: '多向量并发攻击研判报告',
    }
    const lines = [
      `# ${reportMeta.value.title}`,
      '',
      '## 多向量并发攻击 · 安全研判报告',
      '',
      `- 报告编号：${reportNo}`,
      `- 生成时间：${generatedAt}`,
      `- 聚合事件数：${r.event_count ?? vectors.length}`,
      `- 攻击类型覆盖：${labels || '-'}`,
      '',
      '## 一、总体概览',
      `- 监测窗口：${o.time || '-'}`,
      `- 来源 IP 分布：${o.client_ip || '-'}`,
      `- 事件性质：${o.attack_type_label || '多向量并发攻击'}`,
      `- 请求特征：${o.method || '-'}；暴露接口：${o.path || '-'}`,
      '',
      '## 二、综合风险评估',
      `- 峰值规则风险分：${r.score?.risk_score ?? '-'} / 100`,
      `- 规则置信度上限：${r.score?.rule_confidence ?? '-'} / 100`,
      `- 命中次数合计：${r.score?.hit_count ?? '-'}`,
      `- AI 风险等级：${r.score?.ai_risk_level || 'high'}`,
      '',
      '## 三、攻击向量明细',
      ...vectors.map(
        (v: any, i: number) =>
          `${i + 1}. [${v.attack_type_label || v.attack_type}] ${v.method} ${v.path} ← ${v.client_ip}（风险 ${v.risk_score}，${v.blocked ? '已阻断' : '仅记录'}）`,
      ),
      '',
      '## 四、关键证据摘要',
      `- 聚合签名：${r.evidence?.signature || '-'}`,
      `- 特征摘要：${r.evidence?.query_snippet || '-'}`,
      `- User-Agent：${r.evidence?.user_agent || '-'}`,
      '',
      '## 五、处置与建议',
      `- 封禁策略：${r.response?.blocked ? '已对部分来源执行阻断' : '以记录与复核为主'}`,
      `- 规则引用：${r.response?.firewall_rule || '-'}`,
      '',
      '## 六、AI 研判结论',
      r.ai_analysis || '暂无',
      '',
      ...(r.analysis_json
        ? [
            '## 七、结构化研判 JSON（IDS + AI）',
            '```json',
            JSON.stringify(r.analysis_json, null, 2),
            '```',
          ]
        : []),
      '',
      '---',
      '本报告由 校园物资供应链安全监测平台 自动生成，仅供安全运营与审计留档使用。',
    ]
    return lines.join('\n')
  }
  const o = r?.overview || {}
  const s = r?.score || {}
  const e = r?.evidence || {}
  const resp = r?.response || {}
  const reportNo = `SCSP-IDS-${String(eventId).padStart(6, '0')}`
  const generatedAt = r?.generated_at || new Date().toISOString().slice(0, 19).replace('T', ' ')
  const malware =
    (o.attack_type || '') === 'malware' ||
    String(o.attack_type_label || '').includes('木马') ||
    String(o.attack_type_label || '').includes('WebShell')
  reportMeta.value = {
    reportNo,
    generatedAt,
    title: '校园物资供应链安全监测平台',
    headerSuffix: malware ? '木马/WebShell 安全事件分析报告' : '安全事件分析报告',
  }
  return [
    `# ${reportMeta.value.title}`,
    '',
    '## 安全事件分析报告',
    '',
    `- 报告编号：${reportNo}`,
    `- 生成时间：${generatedAt}`,
    `- 事件ID：${eventId}`,
    '',
    '## 一、事件概览',
    `- 事件时间：${o.time || '-'}`,
    `- 来源IP：${o.client_ip || '-'}`,
    `- 攻击类型：${o.attack_type_label || '-'} (${o.attack_type || '-'})`,
    `- 请求路径：${o.method || '-'} ${o.path || '-'}`,
    `- 当前处置状态：${o.status || '-'}`,
    '',
    '## 二、风险评估',
    `- 规则风险分：${s.risk_score ?? '-'} / 100`,
    `- 规则置信度：${s.rule_confidence ?? '-'} / 100`,
    `- 命中次数：${s.hit_count ?? '-'}`,
    `- AI风险等级：${s.ai_risk_level || 'unknown'}`,
    `- AI置信度：${s.ai_confidence ?? 0}`,
    '',
    '## 三、关键证据',
    `- 规则签名：${e.signature || '-'}`,
    `- Query片段：${e.query_snippet || '-'}`,
    `- Body片段：${e.body_snippet || '-'}`,
    `- User-Agent：${e.user_agent || '-'}`,
    '',
    '## 四、处置动作',
    `- 是否封禁：${resp.blocked ? '是' : '否'}`,
    `- 防火墙规则：${resp.firewall_rule || '-'}`,
    `- 执行动作：${resp.action_taken || '-'}`,
    `- 复核备注：${resp.review_note || '-'}`,
    '',
    '## 五、AI研判结论',
    data?.report?.ai_analysis || '暂无 AI 研判结果',
    '',
    '---',
    '本报告由 校园物资供应链安全监测平台 自动生成，仅供安全运营与审计留档使用。',
  ].join('\n')
}

async function openReport(
  row: IDSEventItem,
  forceAI = true,
  opts?: { skipProcessOverlay?: boolean },
) {
  reportOrderNo.value = `${row.id}`
  if (forceAI && !opts?.skipProcessOverlay) startAiProcess()
  reportLoading.value = true
  try {
    const res: any = await getIDSEventReport(row.id, forceAI)
    const data = res?.data ?? res
    reportData.value = data?.report || null
    reportMarkdown.value = buildProfessionalMarkdown(data, row.id)
    reportVisible.value = true
  } catch (e: any) {
    reportData.value = null
    reportMarkdown.value = ''
    ElMessage.error(e?.response?.data?.detail || e?.message || '生成报告失败')
  } finally {
    reportLoading.value = false
    stopAiProcess()
  }
}

/** 主标题彩蛋：多向量并发聚合报告（数据就绪后再打开弹窗，避免白屏闪烁） */
async function openPhase1AggregateReport(opts?: { skipProcessOverlay?: boolean }) {
  if (!opts?.skipProcessOverlay) startAiProcess('phase1')
  reportLoading.value = true
  try {
    const res: any = await getIDSPhase1AggregateReport()
    const data = res?.data ?? res
    const rep = data?.report
    reportData.value = rep || null
    const firstId = rep?.event_id ?? 0
    reportOrderNo.value = `AGM-${firstId}`
    reportMarkdown.value = buildProfessionalMarkdown(data, firstId)
    reportVisible.value = true
  } catch (e: any) {
    reportData.value = null
    reportMarkdown.value = ''
    ElMessage.error(e?.response?.data?.detail || e?.message || '聚合报告生成失败')
  } finally {
    reportLoading.value = false
    stopAiProcess()
  }
}

function aiRiskTagType(level: string | undefined) {
  const l = (level || '').toLowerCase()
  if (l === 'high' || l === 'critical') return 'danger'
  if (l === 'medium') return 'warning'
  if (l === 'low') return 'success'
  return 'info'
}

/** 列表 AI 列：单字等级，避免 high/medium/low 英文撑破单元格 */
function aiRiskLevelTableLabel(level: string | undefined) {
  const l = (level || '').toLowerCase()
  if (l === 'high' || l === 'critical') return '高'
  if (l === 'medium') return '中'
  if (l === 'low') return '低'
  return '-'
}

function riskLevelLabel(level: string | undefined) {
  const l = (level || '').toLowerCase()
  if (l === 'high') return '高危'
  if (l === 'medium') return '中危'
  if (l === 'low') return '低危'
  return '未评估'
}

function reportConclusionText() {
  if (reportData.value?.kind === 'aggregate_phase1') {
    return '已识别多向量并发攻击并完成聚合研判，建议按来源 IP 与暴露接口维度持续封禁、限速与复核。'
  }
  const blocked = !!reportData.value?.response?.blocked
  const level = (reportData.value?.score?.ai_risk_level || '').toLowerCase()
  if (blocked && level === 'high') return '已拦截并完成高危处置，建议继续监控同源流量。'
  if (blocked) return '已拦截并完成处置闭环，建议保持封禁策略。'
  if (level === 'high') return '高危事件未封禁，建议立即人工复核并执行阻断。'
  return '事件已记录，建议持续观察并结合上下文复核。'
}

function reportCoverSubtitle() {
  if (reportData.value?.kind === 'aggregate_phase1') return '多向量并发攻击 · 研判摘要'
  if ((reportData.value?.overview?.attack_type || '') === 'malware') return '木马 / WebShell 安全事件分析报告'
  return '网络安全事件分析报告'
}

function reportFingerprint() {
  const src = `${reportMeta.value.reportNo}|${reportMeta.value.generatedAt}|${reportData.value?.event_id || 0}|${reportData.value?.event_count || 0}`
  let h = 2166136261
  for (let i = 0; i < src.length; i += 1) {
    h ^= src.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return `EVT-${(h >>> 0).toString(16).toUpperCase().padStart(8, '0')}`
}

function handlePhase1SecretTap() {
  phase1UnlockCounter.value += 1
  if (phase1UnlockTimer) clearTimeout(phase1UnlockTimer)
  phase1UnlockTimer = setTimeout(() => {
    phase1UnlockCounter.value = 0
  }, 2500)
  if (phase1UnlockCounter.value >= 5) {
    phase1Unlocked.value = true
    phase1UnlockCounter.value = 0
    triggerDemoPhase1()
  }
}

function handlePhase2SecretTap() {
  phase2UnlockCounter.value += 1
  if (phase2UnlockTimer) clearTimeout(phase2UnlockTimer)
  phase2UnlockTimer = setTimeout(() => {
    phase2UnlockCounter.value = 0
  }, 2500)
  if (phase2UnlockCounter.value >= 5) {
    phase2Unlocked.value = true
    phase2UnlockCounter.value = 0
    triggerDemoPhase2()
  }
}

async function triggerDemoPhase1() {
  try {
    startAiProcess('phase1')
    const res: any = await seedIDSDemoPhase1(true)
    const data = res?.data ?? res
    const ids: number[] = data?.event_ids || []
    await fetchData()
    await fetchStats()
    await fetchTrend()
    if (ids.length > 0) {
      await openPhase1AggregateReport({ skipProcessOverlay: true })
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '多向量演示数据注入失败')
  } finally {
    stopAiProcess()
  }
}

async function triggerDemoPhase2() {
  try {
    startAiProcess('phase2')
    const res: any = await seedIDSDemoPhase2(true)
    const data = res?.data ?? res
    const eventId = data?.event_id
    await fetchData()
    await fetchStats()
    await fetchTrend()
    const row = tableData.value.find((x) => x.id === eventId) || tableData.value[0]
    if (row) {
      currentRow.value = row
      detailVisible.value = true
      await openReport(row, true, { skipProcessOverlay: true })
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '木马演示数据注入失败')
  } finally {
    stopAiProcess()
  }
}

async function clearDemoData() {
  if (!clearArmed.value) {
    clearArmed.value = true
    if (clearArmTimer) clearTimeout(clearArmTimer)
    clearArmTimer = setTimeout(() => {
      clearArmed.value = false
    }, 3000)
    ElMessage.warning('再次点击“清理演示数据”以确认')
    return
  }
  try {
    const res: any = await resetIDSDemoEvents()
    const data = res?.data ?? res
    ElMessage.success(data?.message || '演示数据已清理')
    await fetchData()
    await fetchStats()
    await fetchTrend()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '清理失败')
  } finally {
    clearArmed.value = false
    if (clearArmTimer) clearTimeout(clearArmTimer)
    clearArmTimer = null
  }
}

onMounted(() => {
  tickIdsHudClock()
  idsHudClockTimer = setInterval(tickIdsHudClock, 1000)
  refreshIdsTableMaxHeight()
  fetchStats()
  fetchTrend()
  fetchData()
  window.addEventListener('resize', handleResize)
})
onBeforeUnmount(() => {
  if (idsHudClockTimer) clearInterval(idsHudClockTimer)
  idsHudClockTimer = null
  stopAiProcess()
  if (phase1UnlockTimer) clearTimeout(phase1UnlockTimer)
  if (phase2UnlockTimer) clearTimeout(phase2UnlockTimer)
  if (clearArmTimer) clearTimeout(clearArmTimer)
  if (timelineStageTimer) clearInterval(timelineStageTimer)
  window.removeEventListener('resize', handleResize)
  pieChartInstance?.dispose()
  trendChartInstance?.dispose()
})
watch([pageOffset, pageSize], fetchData)
watch(trendDays, () => fetchTrend())
</script>

<template>
  <div class="security-center-page">
    <header class="sec-header">
      <div class="sec-hud-rail" aria-hidden="true">
        <span class="sec-hud-rail__dot" />
        <span class="sec-hud-rail__brand">旁路流量镜像 · 规则引擎 · 运行态</span>
        <span class="sec-hud-rail__split" />
        <span class="sec-hud-rail__clock">
          <span class="sec-hud-rail__tlab">系统时间</span>
          <span class="sec-hud-rail__tval">{{ idsHudClock }}</span>
        </span>
        <span class="sec-hud-rail__cursor">_</span>
      </div>
      <h1 class="sec-title" @click="handlePhase1SecretTap">IDS 入侵检测</h1>
      <div class="sec-hud-pipeline" role="button" tabindex="0" @click="handlePhase2SecretTap" @keydown.enter.prevent="handlePhase2SecretTap">
        <span class="sec-hud-pipeline__step">抓包解析</span>
        <span class="sec-hud-pipeline__sep">·</span>
        <span class="sec-hud-pipeline__step">特征匹配（含 Body 抽样）</span>
        <span class="sec-hud-pipeline__sep">·</span>
        <span class="sec-hud-pipeline__step">攻击识别</span>
        <span class="sec-hud-pipeline__sep">·</span>
        <span class="sec-hud-pipeline__step">留痕封禁</span>
        <span class="sec-hud-pipeline__sep">·</span>
        <span class="sec-hud-pipeline__step">LLM 研判</span>
        <span class="sec-hud-pipeline__sep">·</span>
        <span class="sec-hud-pipeline__step">归档管理</span>
      </div>
      <div v-if="phase1Unlocked || phase2Unlocked" class="demo-secret-actions" />
    </header>

    <main class="sec-main">
      <div v-if="stats" class="stats-row">
        <div class="stat-card sec-stat">
          <span class="stat-value">{{ stats.total }}</span>
          <span class="stat-label">检测事件总数</span>
        </div>
        <div class="stat-card sec-stat danger">
          <span class="stat-value">{{ stats.blocked_count }}</span>
          <span class="stat-label">已封禁 IP</span>
        </div>
        <div class="stat-card sec-stat warning">
          <span class="stat-value">{{ stats.high_risk_count || 0 }}</span>
          <span class="stat-label">高风险事件</span>
        </div>
        <div v-for="t in stats.by_type" :key="t.attack_type" class="stat-card sec-stat small">
          <span class="stat-value">{{ t.count }}</span>
          <span class="stat-label">{{ t.attack_type_label }}</span>
        </div>
      </div>

      <div class="chart-row">
        <div class="chart-card sec-card">
          <div class="chart-title">攻击类型分布</div>
          <div id="ids-pie-chart" class="chart-arena" />
        </div>
        <div class="chart-card sec-card chart-card-wide">
          <div class="chart-title">
            事件趋势
            <el-select v-model="trendDays" size="small" class="sec-select">
              <el-option label="近7天" :value="7" />
              <el-option label="近14天" :value="14" />
              <el-option label="近30天" :value="30" />
            </el-select>
          </div>
          <div id="ids-trend-chart" class="chart-arena" />
        </div>
      </div>

      <div class="filter-bar">
        <el-input v-model="clientIpFilter" placeholder="来源 IP" clearable class="sec-input" />
        <el-select v-model="attackTypeFilter" placeholder="攻击类型" clearable class="sec-select">
          <el-option label="SQL 注入" value="sql_injection" />
          <el-option label="XSS" value="xss" />
          <el-option label="路径遍历" value="path_traversal" />
          <el-option label="命令注入" value="cmd_injection" />
          <el-option label="扫描器" value="scanner" />
          <el-option label="畸形请求" value="malformed" />
          <el-option label="JNDI 类" value="jndi_injection" />
          <el-option label="原型链污染" value="prototype_pollution" />
        </el-select>
        <el-select v-model="blockedFilter" placeholder="封禁状态" clearable class="sec-select">
          <el-option label="已封禁" :value="1" />
          <el-option label="仅记录" :value="0" />
        </el-select>
        <el-select v-model="archivedFilter" placeholder="归档状态" clearable class="sec-select">
          <el-option label="未归档" :value="0" />
          <el-option label="已归档" :value="1" />
        </el-select>
        <el-select v-model="statusFilter" placeholder="处置状态" clearable class="sec-select">
          <el-option label="新事件" value="new" />
          <el-option label="调查中" value="investigating" />
          <el-option label="已缓解" value="mitigated" />
          <el-option label="误报" value="false_positive" />
          <el-option label="已关闭" value="closed" />
        </el-select>
        <el-select v-model="minScoreFilter" placeholder="最低风险分" clearable class="sec-select">
          <el-option label="≥40" :value="40" />
          <el-option label="≥60" :value="60" />
          <el-option label="≥70" :value="70" />
          <el-option label="≥85" :value="85" />
        </el-select>
        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button type="success" :disabled="!selectedIds.length" @click="handleBatchArchive">
          批量归档 ({{ selectedIds.length }})
        </el-button>
        <el-button type="warning" :loading="simulatingAttack" @click="handleSimulateAttack">
          模拟攻击（演示）
        </el-button>
        <el-button type="info" @click="openEvidenceTimeline">证据链时间轴</el-button>
      </div>

      <div class="table-card sec-card ids-table-shell">
        <el-table
          :data="tableData"
          v-loading="loading"
          class="sec-table"
          style="width: 100%"
          :max-height="idsTableMaxHeight"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="40" align="center" />
          <el-table-column label="时间" width="154" min-width="148">
            <template #default="{ row }">
              <span class="cell-ellipsis cell-time">{{ fmtTableDateTime(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="client_ip" label="源 IP" width="148" min-width="132">
            <template #default="{ row }">
              <span class="cell-ellipsis cell-mono">{{ row.client_ip }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="attack_type_label" label="类型" width="124" min-width="118" align="center">
            <template #default="{ row }">
              <el-tag :type="row.attack_type === 'sql_injection' ? 'danger' : 'warning'" size="small" class="ids-table-tag ids-table-tag--clip">
                {{ row.attack_type_label }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="method" label="方法" width="78" min-width="72" align="center">
            <template #default="{ row }">
              <span class="cell-ellipsis cell-mono">{{ row.method }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="path" label="路径" min-width="72">
            <template #default="{ row }">
              <span class="cell-path-ellipsis cell-mono">{{ row.path }}</span>
            </template>
          </el-table-column>
          <el-table-column label="风险" width="56" min-width="52" align="center" header-align="center">
            <template #default="{ row }">
              <span class="cell-ellipsis cell-mono">{{ row.risk_score ?? 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="置信" width="64" min-width="58" align="center" header-align="center">
            <template #default="{ row }">
              <span class="cell-ellipsis cell-mono">{{ fmtConfidencePct(row.confidence) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="blocked" label="封禁" width="80" min-width="76" align="center">
            <template #default="{ row }">
              <el-tag :type="row.blocked ? 'success' : 'info'" size="small" class="ids-table-tag">
                {{ row.blocked ? '已封禁' : '仅记录' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="策略" width="64" min-width="56" align="center" header-align="center">
            <template #default="{ row }">
              <span class="ids-fw-cn">{{ fmtFirewallRuleTable(row.firewall_rule) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="84" min-width="80" align="center">
            <template #default="{ row }">
              <el-tag
                size="small"
                class="ids-table-tag"
                :type="row.status === 'closed' ? 'info' : row.status === 'false_positive' ? 'warning' : row.status === 'mitigated' ? 'success' : 'primary'"
              >
                {{
                  row.status === 'new'
                    ? '新事件'
                    : row.status === 'investigating'
                      ? '调查中'
                      : row.status === 'mitigated'
                        ? '已缓解'
                        : row.status === 'false_positive'
                          ? '误报'
                          : row.status === 'closed'
                            ? '已关闭'
                            : row.status || '-'
                }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="AI" width="52" min-width="48" align="center">
            <template #default="{ row }">
              <el-tag
                v-if="row.ai_risk_level"
                :type="aiRiskTagType(row.ai_risk_level) as any"
                size="small"
                class="ids-table-tag ids-table-tag--ai ids-table-tag--ai-cn"
              >
                {{ aiRiskLevelTableLabel(row.ai_risk_level) }}
              </el-tag>
              <span v-else class="muted-ai">-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="248" min-width="232" align="center" header-align="center" fixed="right">
            <template #default="{ row }">
              <div class="ids-ops ids-ops--row">
                <button type="button" class="ids-act ids-act--primary" @click="showDetail(row)">查看</button>
                <span class="ids-ops__sep" aria-hidden="true">|</span>
                <button
                  type="button"
                  class="ids-act ids-act--warn"
                  :disabled="aiAnalyzingId === row.id"
                  @click="handleAiAnalyze(row)"
                >
                  <span class="ai-btn-label">
                    研判
                    <span v-if="aiAnalyzingId === row.id" class="mini-orbit" />
                  </span>
                </button>
                <span class="ids-ops__sep" aria-hidden="true">|</span>
                <button type="button" class="ids-act ids-act--primary" @click="openReport(row)">报告</button>
                <span class="ids-ops__sep" aria-hidden="true">|</span>
                <el-dropdown trigger="click" @command="(cmd: string | number) => handleIdsMoreMenu(row, cmd)">
                  <button type="button" class="ids-act ids-act--muted">更多</button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="investigating">状态 → 调查中</el-dropdown-item>
                      <el-dropdown-item command="mitigated">状态 → 已缓解</el-dropdown-item>
                      <el-dropdown-item command="false_positive">状态 → 误报</el-dropdown-item>
                      <el-dropdown-item command="closed">状态 → 已关闭</el-dropdown-item>
                      <el-dropdown-item divided command="block">封禁 IP</el-dropdown-item>
                      <el-dropdown-item command="unblock">解封 IP</el-dropdown-item>
                      <el-dropdown-item v-if="!row.archived" divided command="archive">归档本条</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          :current-page="Math.floor(pageOffset / pageSize) + 1"
          class="sec-pagination"
          @current-change="(p: number) => { pageOffset = (p - 1) * pageSize; fetchData() }"
        />
        <div class="demo-clear-area">
          <el-button
            class="demo-clear-logo"
            :class="{ armed: clearArmed }"
            type="danger"
            circle
            :icon="DeleteFilled"
            :title="clearArmed ? '再次点击确认清理' : '清理演示数据'"
            @click="clearDemoData"
          />
        </div>
      </div>
    </main>

    <el-drawer v-model="detailVisible" title="事件详情" size="480" class="sec-drawer">
      <template v-if="currentRow">
        <p><strong>时间：</strong>{{ currentRow.created_at }}</p>
        <p><strong>来源 IP：</strong>{{ currentRow.client_ip }}</p>
        <p><strong>攻击类型：</strong>{{ currentRow.attack_type_label }}</p>
        <p><strong>匹配特征：</strong>{{ currentRow.signature_matched }}</p>
        <p><strong>方法：</strong>{{ currentRow.method }}</p>
        <p><strong>路径：</strong>{{ currentRow.path }}</p>
        <p><strong>Query 片段：</strong>{{ currentRow.query_snippet || '-' }}</p>
        <p><strong>Body 片段：</strong>{{ currentRow.body_snippet || '-' }}</p>
        <p><strong>User-Agent：</strong>{{ currentRow.user_agent || '-' }}</p>
        <p><strong>封禁：</strong>{{ currentRow.blocked ? '是' : '否' }}</p>
        <p><strong>防火墙规则：</strong>{{ currentRow.firewall_rule || '-' }}</p>
        <p><strong>风险评分：</strong>{{ currentRow.risk_score || 0 }} / 100（置信度 {{ fmtConfidencePct(currentRow.confidence) }}）</p>
        <p><strong>命中数量：</strong>{{ currentRow.hit_count || 0 }}</p>
        <p><strong>处置状态：</strong>{{ currentRow.status || 'new' }}</p>
        <p><strong>处置备注：</strong>{{ currentRow.review_note || '-' }}</p>
        <div class="ai-block">
          <p class="ai-head">
            <strong>AI 研判</strong>
            <el-tag v-if="currentRow.ai_risk_level" :type="aiRiskTagType(currentRow.ai_risk_level) as any" size="small">
              {{ currentRow.ai_risk_level }}
            </el-tag>
            <span class="ai-time">置信度 {{ fmtConfidencePct(currentRow.ai_confidence) }}</span>
            <span v-if="currentRow.ai_analyzed_at" class="ai-time">{{ currentRow.ai_analyzed_at }}</span>
          </p>
          <pre v-if="currentRow.ai_analysis" class="ai-text">{{ currentRow.ai_analysis }}</pre>
          <p v-else class="ai-empty">暂无研判（命中后将后台异步分析；也可点击列表「AI 研判」手动触发，需配置 LLM）</p>
          <el-button type="primary" size="small" :loading="aiAnalyzingId === currentRow.id" @click="handleAiAnalyze(currentRow)">
            重新研判
          </el-button>
          <el-button size="small" @click="openReport(currentRow, true)">生成报告（强制AI）</el-button>
        </div>
      </template>
    </el-drawer>

    <el-dialog
      v-model="timelineVisible"
      title="证据链时间轴"
      width="980px"
      class="timeline-modal"
      modal-class="timeline-modal-overlay"
    >
      <div v-loading="timelineLoading" class="timeline-container">
        <div v-if="timelineLoading" class="timeline-loading-note">
          正在汇总总体攻防链路... 阶段 {{ timelineAutoStage }} / 5
        </div>
        <div v-if="!timelineLoading && !timelineSummaryNodes.length" class="timeline-empty">暂无可展示的总体链路</div>
        <div v-if="!timelineLoading && timelineSummaryNodes.length" class="chain-card">
          <div class="chain-head">
            <span class="chain-title">总体攻防闭环链路（全部攻击）</span>
            <span class="chain-meta">自动汇总</span>
          </div>
          <div class="chain-attack-list">
            <el-tag v-for="a in timelineAttackList" :key="a.name" size="small" type="danger" effect="plain">
              {{ a.name }} x{{ a.cnt }}
            </el-tag>
          </div>
          <div class="chain-nodes">
            <div v-for="node in timelineSummaryNodes" :key="node.key" class="chain-node">
              <span class="chain-dot" :class="`state-${node.state}`" />
              <div class="chain-body">
                <div class="chain-node-title">{{ node.title }}</div>
                <div class="chain-node-detail">{{ node.detail }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <el-dialog
      v-model="reportVisible"
      title="安全事件分析报告"
      width="860px"
      class="report-modal"
      modal-class="report-modal-overlay"
    >
      <template #header>
        <div class="report-header">
          <span>{{ reportMeta.title }} · {{ reportMeta.headerSuffix }}</span>
          <div class="report-actions">
            <el-button size="small" @click="exportReport('md')">导出 MD</el-button>
            <el-button size="small" @click="exportReport('html')">导出 HTML</el-button>
            <el-button type="primary" size="small" @click="exportReport('pdf')">导出 PDF</el-button>
          </div>
        </div>
      </template>
      <div ref="reportContainerRef" class="report-panel">
        <div v-if="reportData" class="report-cover">
          <div class="report-cover-title">校园物资供应链安全监测平台</div>
          <div class="report-cover-subtitle">{{ reportCoverSubtitle() }}</div>
          <div class="report-cover-badges">
            <el-tag :type="aiRiskTagType(reportData?.score?.ai_risk_level) as any" effect="dark" size="small">
              {{ riskLevelLabel(reportData?.score?.ai_risk_level) }}
            </el-tag>
            <el-tag type="info" effect="plain" size="small">事件指纹 {{ reportFingerprint() }}</el-tag>
          </div>
          <div class="report-kv">
            <span>报告编号：{{ reportMeta.reportNo || '-' }}</span>
            <span>生成时间：{{ reportMeta.generatedAt || '-' }}</span>
            <span v-if="reportData?.kind === 'aggregate_phase1'">聚合事件数：{{ reportData?.event_count ?? '-' }}</span>
            <span v-else>事件ID：{{ reportData?.event_id || '-' }}</span>
            <span>风险分：{{ reportData?.score?.risk_score ?? '-' }} / 100</span>
          </div>
          <div class="report-conclusion">
            <strong>处置结论：</strong>{{ reportConclusionText() }}
          </div>
        </div>
        <div v-if="reportData?.kind === 'aggregate_phase1' && reportData?.analysis_json" class="report-json-block">
          <div class="report-vector-head">AI 研判结构化 JSON</div>
          <pre class="report-json-pre">{{ JSON.stringify(reportData.analysis_json, null, 2) }}</pre>
        </div>
        <div v-if="reportData?.kind === 'aggregate_phase1' && reportData?.vectors?.length" class="report-vector-table">
          <div class="report-vector-head">攻击向量明细（并发）</div>
          <table class="report-vec-tbl">
            <thead>
              <tr>
                <th>#</th>
                <th>类型</th>
                <th>来源 IP</th>
                <th>请求</th>
                <th>风险</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(v, idx) in reportData.vectors" :key="idx">
                <td>{{ Number(idx) + 1 }}</td>
                <td>{{ v.attack_type_label }}</td>
                <td>{{ v.client_ip }}</td>
                <td class="report-vec-path">{{ v.method }} {{ v.path }}</td>
                <td>{{ v.risk_score }}</td>
                <td>{{ v.blocked ? '已阻断' : '仅记录' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="reportData" class="report-grid">
          <div class="report-card">
            <h4>事件概览</h4>
            <p>时间：{{ reportData?.overview?.time || '-' }}</p>
            <p>来源IP：{{ reportData?.overview?.client_ip || '-' }}</p>
            <p>类型：{{ reportData?.overview?.attack_type_label || '-' }}</p>
            <p>路径：{{ reportData?.overview?.method || '-' }} {{ reportData?.overview?.path || '-' }}</p>
          </div>
          <div class="report-card">
            <h4>风险评估</h4>
            <p>规则风险分：{{ reportData?.score?.risk_score ?? '-' }}</p>
            <p>规则置信度：{{ reportData?.score?.rule_confidence ?? '-' }}</p>
            <p>AI风险等级：{{ reportData?.score?.ai_risk_level || '-' }}</p>
            <p>AI置信度：{{ reportData?.score?.ai_confidence ?? '-' }}</p>
          </div>
          <div class="report-card report-card-full">
            <h4>关键证据与处置</h4>
            <p>特征：{{ reportData?.evidence?.signature || '-' }}</p>
            <p>处置动作：{{ reportData?.response?.action_taken || '-' }}</p>
            <p>封禁状态：{{ reportData?.response?.blocked ? '已封禁' : '仅记录' }}</p>
          </div>
        </div>
        <pre class="ai-text report-text">{{ reportMarkdown || '暂无报告内容' }}</pre>
        <div class="report-footer-sign">
          <span>平台签章：校园物资供应链安全监测平台</span>
          <span>审计用途：答辩留档 / 安全复盘</span>
        </div>
      </div>
    </el-dialog>
    <el-dialog
      v-model="aiProcessVisible"
      width="760px"
      :show-close="false"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      class="ai-process-modal"
      modal-class="ai-process-overlay"
    >
      <div class="ai-process-wrap" :class="`mode-${aiProcessMode}`">
        <div class="ai-process-bg-grid" />
        <div class="ai-process-bg-beam" />
        <div class="ai-process-core">
          <div class="pulse pulse-1" />
          <div class="pulse pulse-2" />
          <div class="pulse pulse-3" />
          <div class="core-dot" />
        </div>
        <div class="ai-process-title">
          {{ aiProcessMode === 'phase2' ? '木马/WebShell 拦截与处置引擎运行中' : (aiProcessMode === 'phase1' ? '多向量并发攻击链研判引擎运行中' : 'AI 研判引擎运行中') }}
        </div>
        <div class="ai-process-stage">阶段 {{ aiProcessStage }} / {{ aiProcessTotalStages }}</div>
        <div class="ai-process-progress">
          <div class="ai-process-progress-bar" :style="{ width: `${aiProcessProgress}%` }" />
        </div>
        <div class="ai-process-desc">{{ aiProcessText }}</div>
        <div class="ai-feed">
          <div v-for="(line, idx) in aiProcessFeed" :key="`${idx}-${line}`" class="ai-feed-line">
            <span class="dot" />
            <span>{{ line }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.security-center-page {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background: var(--sec-hud-page-bg);
  color: #fff;
  padding: 24px 28px;
  color-scheme: dark;
}
.sec-header {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(34, 211, 238, 0.14);
}
.sec-hud-rail {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 15px;
  color: rgba(34, 211, 238, 0.78);
  letter-spacing: 0.06em;
}
.sec-hud-rail__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--sec-hud-cyan);
  box-shadow: 0 0 12px var(--sec-hud-cyan);
  animation: sec-hud-pulse 2s ease-in-out infinite;
}
@keyframes sec-hud-pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.55;
    transform: scale(0.88);
  }
}
.sec-hud-rail__brand {
  font-family:
    'Segoe UI',
    'PingFang SC',
    'Microsoft YaHei',
    system-ui,
    sans-serif;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.14em;
  color: rgba(207, 250, 254, 0.95);
  text-shadow:
    0 0 18px rgba(34, 211, 238, 0.22),
    0 0 1px rgba(255, 255, 255, 0.08);
}
.sec-hud-rail__split {
  width: 1px;
  height: 14px;
  background: rgba(34, 211, 238, 0.28);
  margin: 0 2px;
}
.sec-hud-rail__clock {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  color: rgba(226, 232, 240, 0.92);
  font-weight: 600;
}
.sec-hud-rail__tlab {
  font-family:
    'Segoe UI',
    'PingFang SC',
    system-ui,
    sans-serif;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: rgba(148, 163, 184, 0.88);
}
.sec-hud-rail__tval {
  font-family: ui-monospace, 'Cascadia Mono', Consolas, monospace;
  font-size: 14px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: rgba(226, 232, 240, 0.95);
}
.sec-hud-rail__cursor {
  animation: sec-hud-blink 1.1s step-end infinite;
  color: var(--sec-hud-cyan);
  font-family: ui-monospace, monospace;
}
@keyframes sec-hud-blink {
  50% {
    opacity: 0;
  }
}
.sec-title {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 0.2em;
  margin: 0 0 10px 0;
  background: linear-gradient(to bottom, #fff 40%, #94a3b8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 0 28px rgba(34, 211, 238, 0.18);
  cursor: pointer;
  user-select: none;
}
.sec-hud-pipeline {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.2em 0.35em;
  margin: 0;
  cursor: pointer;
  user-select: none;
  line-height: 1.65;
}
.sec-hud-pipeline:focus-visible {
  outline: 2px solid rgba(34, 211, 238, 0.5);
  outline-offset: 4px;
  border-radius: 4px;
}
.sec-hud-pipeline__step {
  font-size: 16px;
  font-weight: 650;
  font-family: ui-monospace, 'Cascadia Mono', Consolas, monospace;
  letter-spacing: 0.06em;
  color: #a5f3fc;
  text-shadow:
    0 0 18px rgba(34, 211, 238, 0.45),
    0 0 2px rgba(255, 255, 255, 0.15);
  transition: color 0.15s, text-shadow 0.15s;
}
.sec-hud-pipeline:hover .sec-hud-pipeline__step {
  color: #ecfeff;
  text-shadow:
    0 0 22px rgba(34, 211, 238, 0.65),
    0 0 3px rgba(255, 255, 255, 0.2);
}
.sec-hud-pipeline__sep {
  color: rgba(34, 211, 238, 0.35);
  font-weight: 300;
  font-size: 18px;
  user-select: none;
  padding: 0 0.08em;
}
.demo-secret-actions {
  margin-top: 12px;
  display: inline-flex;
  align-items: center;
}
.demo-secret-hint {
  font-size: 12px;
  color: rgba(148, 163, 184, 0.9);
  border: 1px dashed rgba(148, 163, 184, 0.45);
  border-radius: 10px;
  padding: 4px 10px;
}
.sec-main { padding: 0; }

.stats-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: stretch;
  margin-bottom: 24px;
}
.stat-card.sec-stat {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 18px 20px;
  background: rgba(10, 14, 22, 0.92);
  border: 1px solid rgba(34, 211, 238, 0.12);
  border-radius: 16px;
  min-width: 140px;
  min-height: 104px;
  box-sizing: border-box;
  transition: border-color 0.2s;
  &:hover { border-color: rgba(255,255,255,0.1); }
  &.danger .stat-value { color: #ef4444; }
  &.warning .stat-value { color: #f59e0b; }
  &.small .stat-value { font-size: 26px; }
}
.stat-card .stat-value {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: #3b82f6;
  font-family: monospace;
  line-height: 1.1;
  min-height: 1.1em;
}
.stat-card .stat-label {
  display: block;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.55);
  letter-spacing: 0.04em;
  margin-top: 10px;
  line-height: 1.35;
  max-width: 168px;
}

.chart-row {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 24px;
}
.chart-card.sec-card {
  flex: 0 0 320px;
  padding: 20px;
  background: rgba(10, 14, 22, 0.92);
  border: 1px solid rgba(34, 211, 238, 0.12);
  border-radius: 16px;
  &.chart-card-wide { flex: 1; min-width: 360px; }
}
.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: rgba(165, 243, 252, 0.92);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  letter-spacing: 0.04em;
  text-shadow: 0 0 14px rgba(34, 211, 238, 0.2);
}
.chart-arena { height: 220px; }
.sec-select { width: 120px; margin-left: 8px; }

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
  align-items: center;
}

:deep(.filter-bar .el-button) {
  font-size: 15px;
  padding: 10px 18px;
}
.sec-input { width: 140px; }
.sec-select { width: 140px; }

.table-card.sec-card {
  padding: 20px;
  background: rgba(10, 14, 22, 0.92);
  border: 1px solid rgba(34, 211, 238, 0.12);
  border-radius: 16px;
}
/* 不再强制 min-width / table-layout:fixed，避免表头与表体列宽错位、防火墙列「盖住」封禁 */
.ids-table-shell {
  min-width: 0;
  width: 100%;
}
:deep(.ids-table-shell .sec-table .el-table__body-wrapper),
:deep(.ids-table-shell .sec-table .el-table__header-wrapper) {
  width: 100% !important;
}
.sec-pagination {
  margin-top: 16px;
}

:deep(.sec-pagination) {
  font-size: 15px;
  --el-pagination-font-size: 15px;
}
.demo-clear-area {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}
.demo-clear-logo {
  box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.28) inset;
}
.demo-clear-logo.armed {
  animation: clear-armed-pulse 0.9s ease-in-out infinite;
}
@keyframes clear-armed-pulse {
  0% { box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.28) inset, 0 0 0 rgba(239, 68, 68, 0.15); }
  50% { box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.45) inset, 0 0 14px rgba(239, 68, 68, 0.35); }
  100% { box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.28) inset, 0 0 0 rgba(239, 68, 68, 0.15); }
}

/* 统一暗色科技风：表格、选择器、输入框、标签、分页、抽屉 */
:deep(.sec-table),
:deep(.sec-table .el-table),
:deep(.sec-table .el-table__inner-wrapper) {
  --el-table-bg-color: rgba(10, 14, 22, 0.98);
  --el-table-tr-bg-color: rgba(10, 14, 22, 0.98);
  --el-table-header-bg-color: rgba(34, 211, 238, 0.06);
  --el-table-row-hover-bg-color: rgba(34, 211, 238, 0.07);
  --el-table-border-color: rgba(34, 211, 238, 0.1);
  --el-table-text-color: rgba(255, 255, 255, 0.9);
  background: rgba(10, 14, 22, 0.98) !important;
}
:deep(.sec-table .el-table__body tr) { background: rgba(10, 14, 22, 0.98) !important; }
:deep(.sec-table .el-table__body tr.el-table__row--striped) { background: rgba(255,255,255,0.02) !important; }
/* 主表体与右侧固定区行悬停背景一致，避免出现半截透明蒙层 */
:deep(.sec-table .el-table__body tr.hover-row > td.el-table__cell) {
  background-color: var(--el-table-row-hover-bg-color) !important;
}
:deep(.sec-table .el-table__fixed-right .el-table__body tr.hover-row > td.el-table__cell) {
  background-color: var(--el-table-row-hover-bg-color) !important;
}
/* 右侧固定区：与左侧滚动区清晰分界，避免仅靠阴影造成「盖住」错觉 */
:deep(.sec-table .el-table__fixed-right::before),
:deep(.sec-table .el-table__fixed-right::after) {
  box-shadow: none !important;
}
:deep(.sec-table .el-table__fixed-right-patch) {
  background-color: rgba(10, 14, 22, 0.98) !important;
}
:deep(.sec-table .el-table__fixed-right) {
  background: rgba(10, 14, 22, 0.98);
  border-left: 1px solid rgba(34, 211, 238, 0.15);
}
:deep(.sec-table .el-table__fixed-right .el-table__cell) {
  background: rgba(10, 14, 22, 0.98) !important;
}
:deep(.sec-table .el-table__fixed-right .el-table__header-wrapper th.el-table__cell) {
  background: rgba(255, 255, 255, 0.04) !important;
}
:deep(.sec-table th.el-table__cell) {
  background: rgba(34, 211, 238, 0.07) !important;
  color: rgba(226, 254, 255, 0.9);
  font-size: 13px;
  font-weight: 600;
  vertical-align: middle;
  padding: 8px 6px !important;
}
:deep(.sec-table th.el-table__cell .cell) {
  white-space: nowrap !important;
  line-height: 1.35 !important;
  word-break: keep-all;
}
:deep(.sec-table td.el-table__cell) {
  vertical-align: middle;
  font-size: 14px;
  padding: 8px 6px !important;
}
:deep(.sec-table .cell) {
  line-height: 1.45;
}
:deep(.sec-drawer) {
  --el-drawer-bg-color: #0a0a0a;
  --el-text-color-primary: rgba(255,255,255,0.9);
  background: #0a0a0a !important;
}
:deep(.el-pagination) {
  --el-pagination-button-bg-color: transparent;
  --el-pagination-button-color: rgba(255,255,255,0.7);
  --el-pagination-hover-color: #3b82f6;
}
:deep(.sec-input .el-input__wrapper),
:deep(.sec-select .el-select__wrapper) {
  background: rgba(255,255,255,0.06) !important;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.9);
}
:deep(.sec-input .el-input__inner),
:deep(.sec-select .el-select__input) {
  color: rgba(255, 255, 255, 0.9);
  font-size: 15px;
}
:deep(.sec-select .el-select__selected-item) {
  font-size: 15px;
}
:deep(.sec-input .el-input__wrapper:hover),
:deep(.sec-select .el-select__wrapper:hover) { background: rgba(255,255,255,0.08) !important; }
:deep(.el-select-dropdown) { --el-bg-color: #0f172a !important; --el-text-color-primary: rgba(255,255,255,0.9); }
:deep(.el-tag) { --el-tag-bg-color: rgba(255,255,255,0.08); --el-tag-text-color: rgba(255,255,255,0.8); }
:deep(.el-tag--danger) { --el-tag-bg-color: rgba(239,68,68,0.2); --el-tag-text-color: #f87171; }
:deep(.el-tag--warning) { --el-tag-bg-color: rgba(245,158,11,0.2); --el-tag-text-color: #fbbf24; }
:deep(.el-tag--success) { --el-tag-bg-color: rgba(16,185,129,0.2); --el-tag-text-color: #34d399; }
:deep(.el-tag--info) { --el-tag-bg-color: rgba(255,255,255,0.06); --el-tag-text-color: rgba(255,255,255,0.6); }

:deep(.sec-table .el-tag) {
  font-size: 12px;
  height: auto;
  line-height: 1.35;
  padding: 3px 8px;
  max-width: 100%;
}
:deep(.sec-table .ids-table-tag--clip) {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: middle;
}

:deep(.sec-table .ids-table-tag--ai.el-tag) {
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  overflow: hidden;
  vertical-align: middle;
}
:deep(.sec-table .ids-table-tag--ai .el-tag__content) {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

:deep(.sec-table .ids-table-tag--ai-cn.el-tag) {
  padding: 2px 7px !important;
  max-width: 2.25em;
}
:deep(.sec-table .ids-table-tag--ai-cn .el-tag__content) {
  text-align: center;
  font-weight: 700;
  font-size: 13px;
}

.ids-fw-cn {
  font-size: 13px;
  font-weight: 600;
  color: rgba(226, 254, 255, 0.9);
  letter-spacing: 0.04em;
}

.cell-nowrap {
  white-space: nowrap;
}

.cell-ellipsis,
.cell-path-ellipsis {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-time,
.cell-mono {
  font-family: ui-monospace, 'Cascadia Mono', Consolas, monospace;
  font-variant-numeric: tabular-nums;
}

/* 仅表体：避免与表头 .cell 规则不一致导致列对不齐；表头走 Element Plus 默认 */
:deep(
    .sec-table .el-table__body-wrapper .el-table__body tr > td:nth-child(2) .cell,
    .sec-table .el-table__body-wrapper .el-table__body tr > td:nth-child(3) .cell,
    .sec-table .el-table__body-wrapper .el-table__body tr > td:nth-child(5) .cell,
    .sec-table .el-table__body-wrapper .el-table__body tr > td:nth-child(7) .cell,
    .sec-table .el-table__body-wrapper .el-table__body tr > td:nth-child(8) .cell
  ) {
  white-space: nowrap !important;
}
/* 下拉触发器外层默认带可聚焦盒子，悬停时像透明浮层盖住文字 */
:deep(.sec-table .ids-ops .el-dropdown),
:deep(.sec-table .ids-ops .el-dropdown .el-tooltip__trigger) {
  display: inline-flex;
  align-items: center;
  vertical-align: middle;
}
:deep(.sec-table .ids-ops .el-dropdown .el-tooltip__trigger) {
  outline: none !important;
  box-shadow: none !important;
  background: transparent !important;
}
:deep(.sec-table .ids-ops .el-dropdown:focus-visible .el-tooltip__trigger) {
  outline: 2px solid rgba(59, 130, 246, 0.45) !important;
  outline-offset: 2px;
  border-radius: 2px;
}

.ids-ops {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  width: 100%;
  max-width: 100%;
}
.ids-ops--row {
  flex-direction: row;
  flex-wrap: nowrap;
}
.ids-ops__sep {
  color: rgba(255, 255, 255, 0.14);
  font-size: 11px;
  user-select: none;
  padding: 0 1px;
  flex-shrink: 0;
}

.ids-act {
  margin: 0;
  padding: 2px 5px;
  border: none;
  border-radius: 2px;
  background: transparent !important;
  box-shadow: none !important;
  font-size: 13px;
  font-family: ui-monospace, Consolas, monospace;
  letter-spacing: 0.02em;
  line-height: 1.4;
  cursor: pointer;
  color: rgba(103, 232, 249, 0.88);
  white-space: nowrap;
  transition: color 0.15s, text-shadow 0.15s, background 0.15s;
}

.ids-act:hover:not(:disabled) {
  color: #ecfeff;
  text-shadow: 0 0 12px rgba(34, 211, 238, 0.45);
  background: rgba(34, 211, 238, 0.07) !important;
  text-decoration: none;
}

.ids-act:focus-visible {
  outline: 2px solid rgba(59, 130, 246, 0.65);
  outline-offset: 2px;
  border-radius: 2px;
}

.ids-act:disabled {
  opacity: 0.55;
  cursor: wait;
}

.ids-act--warn {
  color: #fbbf24;
}

.ids-act--warn:hover:not(:disabled) {
  color: #fde68a;
}

.ids-act--danger {
  color: #f87171;
}

.ids-act--danger:hover:not(:disabled) {
  color: #fecaca;
}

.ids-act--ok {
  color: #4ade80;
}

.ids-act--ok:hover:not(:disabled) {
  color: #bbf7d0;
}

.ids-act--muted {
  color: #94a3b8;
}

.ids-act--muted:hover:not(:disabled) {
  color: #cbd5e1;
}

.muted-ai {
  color: rgba(255, 255, 255, 0.35);
  font-size: 15px;
}
.ai-block {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(255,255,255,0.08);
}
.ai-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.ai-time {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.55);
}
.ai-text {
  margin: 0 0 12px 0;
  padding: 12px;
  background: rgba(0, 0, 0, 0.35);
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
  color: rgba(255, 255, 255, 0.85);
  max-height: 280px;
  overflow-y: auto;
}
.ai-empty {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.45);
  margin: 0 0 12px 0;
}
.report-text { max-height: 460px; }

.ai-btn-label { display: inline-flex; align-items: center; gap: 6px; }
.mini-orbit {
  width: 10px;
  height: 10px;
  border: 2px solid rgba(59, 130, 246, 0.75);
  border-top-color: transparent;
  border-radius: 50%;
  display: inline-block;
  animation: spin-mini 0.8s linear infinite;
}

.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.report-actions { display: flex; gap: 8px; }
.timeline-toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}
.timeline-loading-note {
  margin-bottom: 10px;
  color: #93c5fd;
  font-size: 12px;
  letter-spacing: 0.08em;
}
.timeline-container {
  max-height: 600px;
  overflow-y: auto;
  padding-right: 4px;
}
.timeline-empty {
  padding: 18px;
  text-align: center;
  color: rgba(148, 163, 184, 0.9);
}
.chain-card {
  border: 1px solid rgba(56, 189, 248, 0.2);
  background: rgba(15, 23, 42, 0.55);
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 10px;
}
.chain-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.chain-title {
  color: #e2e8f0;
  font-size: 13px;
  font-weight: 700;
}
.chain-meta {
  color: #94a3b8;
  font-size: 12px;
}
.chain-attack-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}
.chain-node {
  display: flex;
  gap: 10px;
  padding: 8px 0;
  border-left: 1px dashed rgba(148, 163, 184, 0.3);
  margin-left: 7px;
  padding-left: 14px;
}
.chain-node:last-child {
  border-left-color: transparent;
}
.chain-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-left: -20px;
  margin-top: 5px;
  flex: 0 0 auto;
}
.chain-dot.state-info { background: #38bdf8; box-shadow: 0 0 8px rgba(56, 189, 248, 0.55); }
.chain-dot.state-warning { background: #f59e0b; box-shadow: 0 0 8px rgba(245, 158, 11, 0.55); }
.chain-dot.state-danger { background: #ef4444; box-shadow: 0 0 8px rgba(239, 68, 68, 0.55); }
.chain-dot.state-success { background: #22c55e; box-shadow: 0 0 8px rgba(34, 197, 94, 0.55); }
.chain-node-title {
  color: #e2e8f0;
  font-size: 12px;
  font-weight: 600;
}
.chain-node-detail {
  margin-top: 2px;
  color: #94a3b8;
  font-size: 12px;
}
.report-panel {
  position: relative;
  background: linear-gradient(180deg, rgba(2, 6, 23, 0.95), rgba(3, 7, 18, 0.98));
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: 12px;
  padding: 14px;
}
.report-panel::after {
  content: "Campus Supply Chain Security Platform";
  position: absolute;
  right: 18px;
  bottom: 12px;
  font-size: 12px;
  color: rgba(148, 163, 184, 0.14);
  letter-spacing: 0.08em;
  pointer-events: none;
}
.report-cover {
  border: 1px solid rgba(56, 189, 248, 0.25);
  border-radius: 10px;
  padding: 12px 14px;
  background: rgba(15, 23, 42, 0.65);
  margin-bottom: 12px;
}
.report-cover-title {
  font-size: 16px;
  font-weight: 700;
  color: #e2e8f0;
}
.report-cover-subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: #93c5fd;
  letter-spacing: 0.08em;
}
.report-cover-badges {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.report-kv {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
  color: #cbd5e1;
  font-size: 12px;
}
.report-conclusion {
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid rgba(56, 189, 248, 0.25);
  background: rgba(2, 132, 199, 0.08);
  color: #e2e8f0;
  font-size: 12px;
}
.report-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 12px;
}
.report-card {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: rgba(15, 23, 42, 0.55);
  color: #dbeafe;
  h4 {
    margin: 0 0 8px 0;
    font-size: 13px;
    color: #67e8f9;
  }
  p {
    margin: 4px 0;
    font-size: 12px;
    color: #cbd5e1;
  }
}
.report-card-full { grid-column: 1 / -1; }
.report-vector-table {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(56, 189, 248, 0.22);
  background: rgba(15, 23, 42, 0.45);
  overflow-x: auto;
}
.report-json-block {
  margin-bottom: 12px;
}
.report-json-pre {
  margin: 0;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid rgba(56, 189, 248, 0.25);
  background: rgba(2, 6, 23, 0.92);
  color: #a5f3fc;
  font-size: 11px;
  line-height: 1.45;
  overflow-x: auto;
  max-height: 320px;
  font-family: ui-monospace, Consolas, monospace;
}
.report-vector-head {
  font-size: 13px;
  font-weight: 600;
  color: #67e8f9;
  margin-bottom: 8px;
}
.report-vec-tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
  color: #cbd5e1;
}
.report-vec-tbl th,
.report-vec-tbl td {
  border: 1px solid rgba(148, 163, 184, 0.2);
  padding: 6px 8px;
  text-align: left;
}
.report-vec-tbl th {
  color: #94a3b8;
  font-weight: 600;
}
.report-vec-path {
  max-width: 220px;
  word-break: break-all;
}
.report-footer-sign {
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: rgba(148, 163, 184, 0.9);
  border-top: 1px dashed rgba(148, 163, 184, 0.3);
  padding-top: 8px;
}

.ai-loading-fx {
  position: relative;
  height: 92px;
  margin-bottom: 10px;
  border: 1px dashed rgba(59,130,246,0.25);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: rgba(191, 219, 254, 0.92);
  font-size: 12px;
  letter-spacing: 0.08em;
  background: radial-gradient(circle at center, rgba(37,99,235,0.08), rgba(0,0,0,0));
}
.ring {
  width: 26px;
  height: 26px;
  border: 2px solid rgba(59,130,246,0.65);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1.4s linear infinite;
}
.ring-2 { width: 18px; height: 18px; border-color: rgba(147,197,253,0.72); border-top-color: transparent; animation-duration: 1s; }
.ring-3 { width: 10px; height: 10px; border-color: rgba(96,165,250,0.9); border-top-color: transparent; animation-duration: 0.7s; }

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
@keyframes spin-mini {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

:global(.ai-process-modal .el-dialog),
:global(.el-dialog.ai-process-modal) {
  --el-dialog-bg-color: #020617 !important;
  background: radial-gradient(circle at 50% 35%, rgba(30, 64, 175, 0.26), rgba(2, 6, 23, 0.98)) !important;
  border: 1px solid rgba(56, 189, 248, 0.42);
  border-radius: 16px;
  box-shadow: 0 20px 56px rgba(2, 6, 23, 0.75), 0 0 24px rgba(14, 165, 233, 0.2);
}
:global(.ai-process-modal .el-dialog__body),
:global(.el-dialog.ai-process-modal .el-dialog__body) {
  padding: 0;
  background: transparent !important;
}
:global(.ai-process-modal .el-dialog__header),
:global(.el-dialog.ai-process-modal .el-dialog__header) { display: none; }
:global(.ai-process-overlay) {
  background: rgba(1, 3, 10, 0.72) !important;
  backdrop-filter: blur(2px);
}
.ai-process-wrap {
  position: relative;
  overflow: hidden;
  padding: 28px 22px 24px;
  text-align: center;
}
.ai-process-wrap.mode-phase2 {
  box-shadow: inset 0 0 0 1px rgba(248, 113, 113, 0.22);
}
.ai-process-wrap.mode-phase2 .ai-process-bg-beam {
  background: linear-gradient(120deg, transparent 42%, rgba(248, 113, 113, 0.22) 50%, transparent 58%);
}
.ai-process-wrap.mode-phase2 .ai-process-progress-bar {
  background: linear-gradient(90deg, #ef4444, #f97316 52%, #f43f5e);
  box-shadow: 0 0 16px rgba(248, 113, 113, 0.45);
}
.ai-process-wrap.mode-phase2 .ai-process-title {
  text-shadow: 0 0 14px rgba(248, 113, 113, 0.42);
}
.ai-process-bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(56, 189, 248, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(56, 189, 248, 0.06) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: radial-gradient(circle at 50% 42%, #000 40%, transparent 90%);
  pointer-events: none;
}
.ai-process-bg-beam {
  position: absolute;
  top: -35%;
  left: -20%;
  width: 140%;
  height: 200%;
  background: linear-gradient(120deg, transparent 42%, rgba(56, 189, 248, 0.14) 50%, transparent 58%);
  transform: rotate(8deg);
  animation: beam-scan 2.8s linear infinite;
  pointer-events: none;
}
.ai-process-core {
  position: relative;
  width: 140px;
  height: 140px;
  margin: 0 auto 14px;
}
.pulse {
  position: absolute;
  inset: 0;
  border: 2px solid rgba(59,130,246,0.45);
  border-radius: 50%;
  animation: pulse 1.8s ease-out infinite;
}
.pulse-2 { animation-delay: 0.35s; border-color: rgba(96,165,250,0.45); }
.pulse-3 { animation-delay: 0.7s; border-color: rgba(147,197,253,0.45); }
.core-dot {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 22px;
  height: 22px;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: #60a5fa;
  box-shadow: 0 0 22px rgba(96,165,250,0.9);
}
.ai-process-title {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #f8fafc;
  text-shadow: 0 0 14px rgba(56, 189, 248, 0.36);
}
.ai-process-stage {
  margin-top: 6px;
  color: #dbeafe;
  font-size: 13px;
  letter-spacing: 0.18em;
}
.ai-process-progress {
  width: 88%;
  height: 8px;
  margin: 14px auto 0;
  border-radius: 99px;
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(125, 211, 252, 0.22);
  overflow: hidden;
}
.ai-process-progress-bar {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #0ea5e9, #38bdf8 52%, #22d3ee);
  box-shadow: 0 0 16px rgba(56, 189, 248, 0.5);
  transition: width 0.45s ease;
}
.ai-process-desc {
  margin-top: 14px;
  color: #f1f5f9;
  font-size: 15px;
  font-weight: 600;
}
.ai-feed {
  margin: 16px auto 0;
  width: 88%;
  text-align: left;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid rgba(56, 189, 248, 0.35);
  background: rgba(15, 23, 42, 0.78);
}
.ai-feed-line {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #e2e8f0;
  line-height: 1.7;
}
.ai-feed-line .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22d3ee;
  box-shadow: 0 0 8px rgba(34, 211, 238, 0.75);
}
@keyframes pulse {
  0% { transform: scale(0.45); opacity: 0.9; }
  70% { transform: scale(1); opacity: 0.15; }
  100% { transform: scale(1.08); opacity: 0; }
}
@keyframes beam-scan {
  0% { transform: translateX(-12%) rotate(8deg); opacity: 0.2; }
  50% { transform: translateX(8%) rotate(8deg); opacity: 0.5; }
  100% { transform: translateX(24%) rotate(8deg); opacity: 0.2; }
}
</style>

<style lang="scss">
/* Teleport 到 body 的 Dialog 兜底样式（非 scoped） */
.el-dialog.ai-process-modal,
.ai-process-modal .el-dialog {
  background: radial-gradient(circle at 50% 35%, rgba(30, 64, 175, 0.26), rgba(2, 6, 23, 0.98)) !important;
  border: 1px solid rgba(56, 189, 248, 0.42) !important;
  box-shadow: 0 20px 56px rgba(2, 6, 23, 0.75), 0 0 24px rgba(14, 165, 233, 0.2) !important;
}

.el-dialog.ai-process-modal .el-dialog__body,
.ai-process-modal .el-dialog__body {
  background: transparent !important;
}

.ai-process-overlay {
  background: rgba(1, 3, 10, 0.72) !important;
  backdrop-filter: blur(2px);
}

.el-dialog.report-modal,
.report-modal .el-dialog {
  background: linear-gradient(180deg, rgba(2, 6, 23, 0.98), rgba(3, 7, 18, 0.98)) !important;
  border: 1px solid rgba(56, 189, 248, 0.28) !important;
  box-shadow: 0 24px 64px rgba(2, 6, 23, 0.75) !important;
}

.el-dialog.report-modal .el-dialog__header,
.report-modal .el-dialog__header {
  border-bottom: 1px solid rgba(56, 189, 248, 0.2);
  margin-right: 0 !important;
}

.el-dialog.report-modal .el-dialog__title,
.report-modal .el-dialog__title {
  color: #e2e8f0 !important;
  font-weight: 700;
}

.el-dialog.report-modal .el-dialog__body,
.report-modal .el-dialog__body {
  background: transparent !important;
}

.report-modal-overlay {
  background: rgba(1, 3, 10, 0.7) !important;
  backdrop-filter: blur(2px);
}

.el-dialog.timeline-modal,
.timeline-modal .el-dialog {
  background: linear-gradient(180deg, rgba(2, 6, 23, 0.98), rgba(3, 7, 18, 0.98)) !important;
  border: 1px solid rgba(56, 189, 248, 0.25) !important;
  box-shadow: 0 24px 64px rgba(2, 6, 23, 0.75) !important;
}

.el-dialog.timeline-modal .el-dialog__title,
.timeline-modal .el-dialog__title {
  color: #e2e8f0 !important;
  font-weight: 700;
}

.el-dialog.timeline-modal .el-dialog__body,
.timeline-modal .el-dialog__body {
  background: transparent !important;
}

.timeline-modal-overlay {
  background: rgba(1, 3, 10, 0.72) !important;
  backdrop-filter: blur(2px);
}
</style>
