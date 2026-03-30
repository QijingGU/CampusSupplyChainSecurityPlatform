<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listMyPurchases } from '@/api/purchase'
import { confirmDeliveryReceive } from '@/api/delivery'
import { isAbnormalOrder } from '@/stores/demo'
import type { Purchase } from '@/api/purchase'

const router = useRouter()
const loading = ref(false)
const tableData = ref<Purchase[]>([])
const detailVisible = ref(false)
const currentRow = ref<Purchase | null>(null)

// 流程条：申请→审批→接单→发货→入库→出库→配送→签收
const FLOW_STEPS = [
  { key: 'pending', label: '申请' },
  { key: 'approved', label: '审批' },
  { key: 'confirmed', label: '接单' },
  { key: 'shipped', label: '发货' },
  { key: 'stocked_in', label: '入库' },
  { key: 'stocked_out', label: '出库' },
  { key: 'delivering', label: '配送' },
  { key: 'completed', label: '签收' },
] as const

// 当前状态对应的流程步骤下标（审批通过后当前=接单）
const STATUS_ORDER: Record<string, number> = {
  pending: 0, approved: 2, confirmed: 3, shipped: 4,
  stocked_in: 5, stocked_out: 6, delivering: 6, completed: 8, rejected: -1,
}

const processingItems = computed(() =>
  tableData.value.filter((p) => !['completed', 'rejected'].includes(p.status))
)

function getFlowState(row: Purchase) {
  const idx = STATUS_ORDER[row.status] ?? 0
  return FLOW_STEPS.map((s, i) => ({
    ...s,
    done: i < idx,
    current: i === idx,
  }))
}

async function fetchData() {
  loading.value = true
  try {
    const res: any = await listMyPurchases()
    tableData.value = (Array.isArray(res) ? res : res?.data ?? []).map((p: any) => ({
      ...p,
      goods_summary: p.goods_summary || (p.items || []).map((i: any) => `${i.goods_name}${i.quantity}${i.unit}`).join('、'),
    }))
  } catch {
    tableData.value = []
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)

function getStatusType(status: string) {
  const map: Record<string, string> = {
    pending: 'warning',
    approved: 'primary',
    confirmed: 'warning',
    shipped: 'primary',
    stocked_in: 'success',
    stocked_out: 'success',
    delivering: 'warning',
    completed: 'success',
    rejected: 'danger',
  }
  return map[status] || 'info'
}

function getStatusLabel(status: string) {
  const map: Record<string, string> = {
    pending: '待审批',
    approved: '待供应商接单',
    confirmed: '待供应商发货',
    shipped: '待仓储入库',
    stocked_in: '待按申请出库',
    stocked_out: '待创建配送',
    delivering: '配送中待签收',
    completed: '已签收完成',
    rejected: '已驳回',
  }
  return map[status] || status
}

async function handleConfirmReceive(row: Purchase) {
  if (!row.delivery_id) return
  try {
    await confirmDeliveryReceive(row.delivery_id)
    ElMessage.success('确认收货成功，当前申请已闭环完成')
    fetchData()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '确认失败')
  }
}

function openDetail(row: Purchase) {
  currentRow.value = row
  detailVisible.value = true
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>我的申请</h2>
      <el-button type="primary" @click="router.push('/ai/chat')">通过 AI 发起申请</el-button>
    </div>

    <!-- 进行中的申请 · 一眼看清进度 -->
    <div v-if="processingItems.length" class="flow-section">
      <h3 class="flow-section-title">进行中的申请 · 一眼看清到哪了</h3>
      <div v-for="row in processingItems" :key="row.id" class="flow-card">
        <div class="flow-card-header">
          <span class="order-no">{{ row.order_no }}</span>
          <el-tag v-if="isAbnormalOrder(row.order_no, row.goods_summary)" type="danger" size="small">AI 标记异常</el-tag>
          <span class="goods-brief">{{ row.goods_summary || '-' }}</span>
        </div>
        <div class="flow-bar">
          <template v-for="(step, i) in getFlowState(row)" :key="step.key">
            <div
              class="flow-step"
              :class="{ done: step.done, current: step.current }"
            >
              <span class="step-dot" />
              <span class="step-label">{{ step.label }}</span>
            </div>
            <div v-if="i < FLOW_STEPS.length - 1" class="flow-line" :class="{ done: step.done }" />
          </template>
        </div>
        <div class="flow-card-footer">
          <span v-if="row.destination" class="dest">送至 {{ row.destination }}</span>
          <el-button v-if="row.can_confirm_receive" type="success" size="small" @click="handleConfirmReceive(row)">
            确认收货
          </el-button>
          <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
        </div>
      </div>
    </div>

    <div class="table-card">
      <el-table :data="tableData" v-loading="loading" style="width: 100%">
        <el-table-column prop="order_no" label="申请单号" width="180">
          <template #default="{ row }">
            {{ row.order_no }}
            <el-tag v-if="isAbnormalOrder(row.order_no, row.goods_summary)" type="danger" size="small">AI 异常</el-tag>
            <el-tag v-if="row.urgent_level === 'urgent'" type="warning" size="small">⚡紧急</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="物资/类型" min-width="160">
          <template #default="{ row }">
            <div>{{ row.goods_summary || '-' }}</div>
            <div v-if="row.material_type" class="row-sub">{{ row.material_type }}{{ row.material_spec ? ' · ' + row.material_spec : '' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="审批" width="130">
          <template #default="{ row }">
            <div v-if="row.approval_level" class="approval-badge" :class="row.approval_level">
              {{ row.approval_level === 'minor' ? '小额' : row.approval_level === 'special' ? '特殊' : '大额' }}审批
            </div>
            <div v-if="row.approval_deadline_at && row.status === 'pending'" class="deadline-hint" :class="{ overdue: row.is_overdue }">
              截止：{{ row.approval_deadline_at.slice(0, 16).replace('T', ' ') }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="receiver_name" label="收货人" width="100" />
        <el-table-column prop="destination" label="收货地点" min-width="140" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="配送状态" width="140">
          <template #default="{ row }">{{ row.delivery_status_label || '-' }}</template>
        </el-table-column>
        <el-table-column prop="handoff_code" label="当前交接码" width="170" />
        <el-table-column prop="created_at" label="申请时间" width="120">
          <template #default="{ row }">{{ row.created_at ? row.created_at.slice(0, 10) : '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.can_confirm_receive" link type="success" @click="handleConfirmReceive(row)">确认收货</el-button>
            <el-button link type="primary" @click="openDetail(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="detailVisible" title="申请详情" width="520px">
      <template v-if="currentRow">
        <p><strong>申请单号：</strong>{{ currentRow.order_no || '-' }}</p>
        <p><strong>状态：</strong>{{ getStatusLabel(currentRow.status) }}</p>
        <p><strong>申请时间：</strong>{{ currentRow.created_at ? currentRow.created_at.slice(0, 19) : '-' }}</p>
        <p><strong>物资摘要：</strong>{{ currentRow.goods_summary || '-' }}</p>
        <p><strong>收货人：</strong>{{ currentRow.receiver_name || '-' }}</p>
        <p><strong>收货地点：</strong>{{ currentRow.destination || '-' }}</p>
        <p><strong>配送单号：</strong>{{ currentRow.delivery_no || '-' }}</p>
        <p><strong>配送状态：</strong>{{ currentRow.delivery_status_label || '-' }}</p>
        <p><strong>当前交接码：</strong>{{ currentRow.handoff_code || '-' }}</p>
      </template>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 18px; font-weight: 600; }

.flow-section {
  margin-bottom: 24px;
}
.flow-section-title {
  font-size: 14px; color: var(--text-muted); margin: 0 0 12px 0; font-weight: 500;
}
.flow-card {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 1px solid #bae6fd;
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 12px;
}
.flow-card-header {
  margin-bottom: 14px;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  .order-no { font-weight: 700; color: var(--primary); font-size: 15px; }
  .goods-brief { font-size: 13px; color: var(--text-secondary); }
}
.flow-bar {
  display: flex; align-items: center; flex-wrap: wrap; gap: 0 4px;
}
.flow-step {
  display: flex; align-items: center; flex-direction: column; gap: 4px;
  .step-dot {
    width: 10px; height: 10px; border-radius: 50%; background: #cbd5e1; transition: all 0.2s;
  }
  .step-label { font-size: 11px; color: #94a3b8; }
  &.done .step-dot { background: var(--el-color-success); }
  &.done .step-label { color: var(--el-color-success); }
  &.current .step-dot { background: var(--primary); transform: scale(1.3); box-shadow: 0 0 0 3px rgba(22, 93, 255, 0.3); }
  &.current .step-label { color: var(--primary); font-weight: 600; }
}
.flow-line {
  width: 24px; height: 2px; background: #cbd5e1; margin: 0 2px; flex-shrink: 0;
  &.done { background: var(--el-color-success); }
}
.flow-card-footer {
  margin-top: 12px; padding-top: 12px; border-top: 1px solid #e2e8f0;
  display: flex; align-items: center; gap: 12px;
  .dest { font-size: 12px; color: var(--text-muted); }
}

.table-card { padding: 24px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 16px; box-shadow: var(--shadow-card); }
.row-sub { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.approval-badge {
  font-size: 10px; padding: 1px 6px; border-radius: 4px; display: inline-block; margin-bottom: 2px;
  &.minor { background: #dcfce7; color: #16a34a; }
  &.major { background: #fef3c7; color: #d97706; }
  &.special { background: #fee2e2; color: #dc2626; }
}
.deadline-hint {
  font-size: 10px; color: #64748b;
  &.overdue { color: #dc2626; font-weight: 600; }
}
</style>
