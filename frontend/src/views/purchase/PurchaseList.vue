<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { WarningFilled, Close } from '@element-plus/icons-vue'
import { listPurchases, approvePurchase, rejectPurchase } from '@/api/purchase'
import { listSuppliers } from '@/api/supplier'
import { isAbnormalOrder, setApprovalAlert, addMisapprovalRecord } from '@/stores/demo'
import type { Purchase } from '@/api/purchase'
import type { Supplier } from '@/api/supplier'

const loading = ref(false)
const aiReportVisible = ref(false)
const aiReportRow = ref<Purchase | null>(null)
const selectedRejectReason = ref('')
const seenAbnormalReport = ref<Set<string>>(new Set())
const closedReportAt = ref(0)
const tableData = ref<Purchase[]>([])
const statusFilter = ref<string>('')
const suppliers = ref<Supplier[]>([])

const statusLabels: Record<string, string> = {
  pending: '待审批',
  approved: '待供应商接单',
  confirmed: '待供应商发货',
  shipped: '待仓储入库',
  stocked_in: '待按申请出库',
  stocked_out: '待创建配送',
  delivering: '配送中待签收',
  rejected: '已驳回',
  completed: '已签收完成',
}
const statusTypes: Record<string, string> = {
  pending: 'warning',
  approved: 'primary',
  confirmed: 'warning',
  shipped: 'primary',
  stocked_in: 'success',
  stocked_out: 'success',
  delivering: 'warning',
  rejected: 'danger',
  completed: 'success',
}

async function fetchData() {
  loading.value = true
  try {
    const res: any = await listPurchases(statusFilter.value ? { status: statusFilter.value } : undefined)
    tableData.value = Array.isArray(res) ? res : res?.data ?? []
  } catch {
    tableData.value = []
  } finally {
    loading.value = false
  }
}

async function fetchSuppliers() {
  try {
    const res: any = await listSuppliers()
    suppliers.value = Array.isArray(res) ? res : res?.data ?? []
  } catch {
    suppliers.value = []
  }
}

const rejectReasons = [
  '数量超出合理范围，不符合采购规范',
  '用途非教学核心，暂不支持',
  'AI 风控标记异常，建议核实后重申请',
  '预算不足，需重新评估',
]

const AI_REPORT_TEMPLATE = `【AI 风控分析报告】
━━━━━━━━━━━━━━━━━━━━━━━━━━
单号：{orderNo}
物资：{goodsSummary}
申请人：{applicantName}
━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 风险分析：
• 数量异常：100 台笔记本电脑显著超出常规教学设备配置
• 用途存疑：「班级观影」非教学核心场景，存在挪用风险
• 合规建议：建议驳回，要求提供合规用途说明

⚠️ 综合评估：高风险，建议驳回
━━━━━━━━━━━━━━━━━━━━━━━━━━`

function getGoodsSummary(row: Purchase): string {
  return row.goods_summary || (row.items || []).map((i: any) => `${i.goods_name}${i.quantity}${i.unit}`).join('、')
}

function getAiReportText(row: Purchase): string {
  return AI_REPORT_TEMPLATE
    .replace('{orderNo}', row.order_no)
    .replace('{goodsSummary}', getGoodsSummary(row))
    .replace('{applicantName}', row.applicant_name || '-')
}

function showAiReport(row: Purchase) {
  aiReportRow.value = row
  selectedRejectReason.value = ''
  aiReportVisible.value = true
}

function closeAiReport() {
  const row = aiReportRow.value
  if (row) seenAbnormalReport.value = new Set([...seenAbnormalReport.value, row.order_no])
  closedReportAt.value = Date.now()
  aiReportVisible.value = false
  aiReportRow.value = null
  selectedRejectReason.value = ''
}

async function doRejectFromReport() {
  const row = aiReportRow.value
  if (!row) return
  const reason = selectedRejectReason.value || rejectReasons[0]
  try {
    await rejectPurchase(row.id, reason)
    ElMessage.success('已驳回')
    aiReportVisible.value = false
    aiReportRow.value = null
    selectedRejectReason.value = ''
    fetchData()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '驳回失败')
  }
}

async function handleApprove(row: Purchase) {
  const summary = getGoodsSummary(row)
  const abnormal = isAbnormalOrder(row.order_no, summary)

  if (abnormal) {
    if (!seenAbnormalReport.value.has(row.order_no)) {
      showAiReport(row)
      return
    }
    try {
      await ElMessageBox.confirm(
        '⚠️ 您已关闭 AI 风险报告并再次点击通过。该操作将被完整记录并同步至审计与异常监督，请确认。',
        '二次确认 · 操作将留痕',
        { confirmButtonText: '确认通过', cancelButtonText: '取消', type: 'warning' }
      )
    } catch {
      return
    }
    const t2 = Date.now()
    const firstAt = closedReportAt.value || t2 - 5000
    const decisionMs = t2 - firstAt
    setApprovalAlert(row.order_no, '审批了 AI 标记异常的申请', row.id)
    addMisapprovalRecord({
      orderNo: row.order_no,
      applicantName: row.applicant_name,
      goodsSummary: summary,
      operatorName: '后勤管理员',
      operatorRole: 'logistics_admin',
      firstConfirmAt: new Date(firstAt).toISOString(),
      secondConfirmAt: new Date(t2).toISOString(),
      decisionTimeMs: decisionMs,
      estimatedLoss: '约 50,000 元（按市场价估算）',
      intentProbability: decisionMs < 3000 ? '约 85%（快速确认，犹豫时间短）' : '约 72%（基于二次确认行为分析）',
      report: `后勤在 AI 异常预警后两次确认通过。首次关闭报告：${new Date(firstAt).toLocaleString()}；二次确认通过：${new Date(t2).toLocaleString()}。决策间隔 ${(decisionMs / 1000).toFixed(1)} 秒。`,
    })
  }

  let supplierId: number | undefined = undefined
  const optionsText = suppliers.value.map((s, i) => `${i + 1}. ${s.name}`).join('\n')
  try {
    const { value } = await ElMessageBox.prompt(
      `系统会先检查库存：库存充足则直接下发仓储，库存不足则流转到供应商。\n如需指定演示供应商，可输入序号：\n${optionsText || '暂无供应商，若库存不足将无法流转'}`,
      '审批并自动分流',
      {
        confirmButtonText: '通过',
        cancelButtonText: '取消',
        inputPlaceholder: optionsText ? '可留空，或输入：1' : '无可用供应商',
        inputValue: optionsText ? '1' : '',
      }
    )
    const idx = Number(value || 0) - 1
    if (idx >= 0 && idx < suppliers.value.length) supplierId = suppliers.value[idx].id
  } catch {
    return
  }
  try {
    const res: any = await approvePurchase(row.id, supplierId)
    const result = res?.data ?? res
    ElMessage.success(result?.message || '审批通过')
    fetchData()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '审批失败')
  }
}

function handleStartPurchase() {
  ElMessage.success('已发起采购申请')
}

async function handleReject(row: Purchase) {
  try {
    const { value } = await ElMessageBox.prompt('请输入驳回理由（可选）', '驳回申请', {
      confirmButtonText: '确定驳回',
      cancelButtonText: '取消',
      inputPlaceholder: '如：预算不足、物资暂缺等',
    })
    await rejectPurchase(row.id, value || undefined)
    ElMessage.success('已驳回')
    fetchData()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.detail || e?.message || '操作失败')
    }
  }
}

onMounted(async () => {
  await fetchSuppliers()
  fetchData()
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2>采购管理</h2>
        <p class="page-desc">仅负责审批：通过（可分配供应商）或驳回。入库、出库、配送由仓储执行。</p>
      </div>
      <el-button type="primary" @click="handleStartPurchase">发起采购</el-button>
    </div>
    <div v-if="true" class="inventory-box">
      <span class="inv-title">库存联动（演示）：</span>
      <span class="inv-item ok">玻片：25套（充足）</span>
      <span class="inv-item fail">酒精：6瓶（不足）</span>
    </div>
    <div class="filter-bar">
      <el-radio-group v-model="statusFilter" @change="fetchData">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="pending">待审批</el-radio-button>
        <el-radio-button label="approved">待接单</el-radio-button>
        <el-radio-button label="confirmed">待发货</el-radio-button>
        <el-radio-button label="shipped">待入库</el-radio-button>
        <el-radio-button label="delivering">配送中</el-radio-button>
        <el-radio-button label="completed">已闭环</el-radio-button>
        <el-radio-button label="rejected">已驳回</el-radio-button>
      </el-radio-group>
    </div>
    <div class="table-card">
      <el-table :data="tableData" v-loading="loading" style="width: 100%">
        <el-table-column prop="order_no" label="单号" width="200">
          <template #default="{ row }">
            {{ row.order_no }}
            <el-tag v-if="isAbnormalOrder(row.order_no, getGoodsSummary(row))" type="danger" size="small">AI 异常</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="applicant_name" label="申请人" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="(statusTypes[row.status] || 'info') as any" size="small">{{ statusLabels[row.status] || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="明细" min-width="200">
          <template #default="{ row }">
            <span v-for="(i, k) in row.items" :key="k">{{ i.goods_name }} {{ i.quantity }}{{ i.unit }}{{ k < row.items.length - 1 ? '；' : '' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="receiver_name" label="收货人" width="110" />
        <el-table-column prop="destination" label="收货地点" min-width="160" />
        <el-table-column prop="handoff_code" label="当前交接码" width="170" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ row.created_at ? row.created_at.slice(0, 19) : '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button type="success" size="small" @click="handleApprove(row)">通过</el-button>
              <el-button type="danger" size="small" @click="handleReject(row)">驳回</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- AI 风控分析报告弹窗 -->
    <el-dialog
      v-model="aiReportVisible"
      width="560px"
      class="ai-report-dialog"
      :show-close="true"
      :close-on-click-modal="false"
      @close="closeAiReport"
    >
      <template #header>
        <div class="ai-report-header">
          <div class="header-left">
            <el-icon class="report-icon"><WarningFilled /></el-icon>
            <span>AI 风控告警 · 建议驳回</span>
          </div>
          <el-button type="danger" text circle @click="closeAiReport">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </template>
      <div v-if="aiReportRow" class="ai-report-body">
        <pre class="report-content">{{ getAiReportText(aiReportRow) }}</pre>
        <div class="reject-section">
          <div class="reject-title">建议驳回理由（可选取）：</div>
          <el-select v-model="selectedRejectReason" placeholder="选择或自定义" filterable allow-create style="width: 100%">
            <el-option v-for="r in rejectReasons" :key="r" :label="r" :value="r" />
          </el-select>
        </div>
      </div>
      <template #footer>
        <el-button @click="closeAiReport">关闭</el-button>
        <el-button type="danger" @click="doRejectFromReport">
          {{ selectedRejectReason ? '驳回' : '选择理由并驳回' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.inventory-box {
  padding: 12px 16px; background: rgba(79, 70, 229, 0.06); border: 1px solid rgba(79, 70, 229, 0.2);
  border-radius: 8px; margin-bottom: 16px; font-size: 13px;
  .inv-title { font-weight: 600; color: var(--text-secondary); margin-right: 12px; }
  .inv-item { margin-right: 16px; }
  .inv-item.ok { color: var(--el-color-success); }
  .inv-item.fail { color: var(--el-color-danger); }
}
.page-header h2 { margin: 0; font-size: 18px; }
.filter-bar { margin-bottom: 16px; }
.page-desc { margin: 4px 0 0 0; font-size: 13px; color: var(--text-muted); }
.table-card { padding: 20px; background: var(--bg-card); border-radius: 12px; }

:deep(.ai-report-dialog) {
  .el-dialog__header { padding: 0; margin: 0; }
  .el-dialog__body { padding-top: 0; }
}
.ai-report-header {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  font-size: 18px; font-weight: 700; color: #dc2626;
  padding: 16px 20px; background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.08) 100%);
  border-bottom: 2px solid #fca5a5;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.report-icon { font-size: 24px; }
.ai-report-body {
  max-height: 420px; overflow-y: auto;
}
.report-content {
  font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; line-height: 1.6;
  white-space: pre-wrap; margin: 0 0 20px 0; padding: 16px;
  background: #1e1e1e; color: #d4d4d4; border-radius: 8px;
}
.reject-section { margin-top: 16px; }
.reject-title { font-weight: 600; margin-bottom: 8px; font-size: 13px; color: var(--text-secondary); }
</style>
