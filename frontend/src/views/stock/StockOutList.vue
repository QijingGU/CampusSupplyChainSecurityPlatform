<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listStockOut, createStockOut, listInventory } from '@/api/stock'
import { listPurchases } from '@/api/purchase'
import type { Purchase } from '@/api/purchase'

const loading = ref(false)
const tableData = ref<any[]>([])
const dialogVisible = ref(false)
const outMode = ref<'purchase' | 'manual'>('purchase')
const selectedPurchaseId = ref<number | null>(null)
const outItems = ref([{ goods_name: '', quantity: 1, unit: '件' }])
const inventoryList = ref<{ goods_name: string; quantity: number; unit: string }[]>([])
const availablePurchases = ref<Purchase[]>([])
const submitting = ref(false)

async function fetchData() {
  loading.value = true
  try {
    const res: any = await listStockOut()
    tableData.value = Array.isArray(res) ? res : res?.data ?? []
  } catch {
    tableData.value = []
  } finally {
    loading.value = false
  }
}

async function openDialog() {
  dialogVisible.value = true
  outMode.value = 'purchase'
  selectedPurchaseId.value = null
  outItems.value = [{ goods_name: '', quantity: 1, unit: '件' }]
  try {
    const purchaseRes: any = await listPurchases()
    const purchaseRows = Array.isArray(purchaseRes) ? purchaseRes : purchaseRes?.data ?? []
    availablePurchases.value = purchaseRows.filter((p: Purchase) => p.status === 'stocked_in')
    const res: any = await listInventory()
    const raw = Array.isArray(res) ? res : res?.data ?? []
    const map = new Map<string, { quantity: number; unit: string }>()
    for (const r of raw) {
      const cur = map.get(r.goods_name)
      if (cur) cur.quantity += r.quantity
      else map.set(r.goods_name, { quantity: r.quantity, unit: r.unit || '件' })
    }
    inventoryList.value = [...map.entries()].map(([goods_name, v]) => ({ goods_name, ...v }))
  } catch {
    inventoryList.value = []
  }
}

function addRow() {
  outItems.value.push({ goods_name: '', quantity: 1, unit: '件' })
}

function removeRow(i: number) {
  if (outItems.value.length > 1) outItems.value.splice(i, 1)
}

function selectGoods(row: (typeof outItems.value)[0]) {
  const inv = inventoryList.value.find((x) => x.goods_name === row.goods_name)
  if (inv) {
    row.unit = inv.unit || '件'
  }
}

async function submitOut() {
  submitting.value = true
  try {
    if (outMode.value === 'purchase' && selectedPurchaseId.value) {
      await createStockOut({ purchase_id: selectedPurchaseId.value })
    } else {
      const items = outItems.value.filter((r) => r.goods_name.trim())
      if (!items.length) {
        ElMessage.warning('请至少填写一条物资')
        return
      }
      await createStockOut({ items })
    }
    ElMessage.success('出库成功')
    dialogVisible.value = false
    fetchData()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '出库失败')
  } finally {
    submitting.value = false
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>出库管理</h2>
      <el-button type="primary" size="default" @click="openDialog">新建出库</el-button>
    </div>
    <div class="table-card">
      <el-table :data="tableData" v-loading="loading" style="width: 100%">
        <el-table-column prop="order_no" label="出库单号" width="160" />
        <el-table-column prop="goods_name" label="物资" />
        <el-table-column prop="quantity" label="数量" width="100" />
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column prop="batch_no" label="批次号" width="140" />
        <el-table-column prop="receiver_name" label="收货人" width="110" />
        <el-table-column prop="destination" label="目的地" min-width="140" />
        <el-table-column prop="handoff_code" label="交接码" width="170" />
        <el-table-column prop="created_at" label="出库时间" width="180">
          <template #default="{ row }">{{ row.created_at ? row.created_at.slice(0, 19) : '-' }}</template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" title="新建出库" width="520" @close="dialogVisible = false">
      <el-radio-group v-model="outMode" style="margin-bottom: 16px">
        <el-radio-button label="purchase">按申请单出库</el-radio-button>
        <el-radio-button label="manual">手工出库</el-radio-button>
      </el-radio-group>

      <template v-if="outMode === 'purchase'">
        <div v-if="!availablePurchases.length" class="hint-box">
          暂无已入库待出库的申请单。库存直采或供应商补货入库后，申请单会出现在此；或使用「手工出库」。
        </div>
        <el-select v-else v-model="selectedPurchaseId" placeholder="选择已入库待出库申请单" filterable style="width: 100%">
          <el-option
            v-for="p in availablePurchases"
            :key="p.id"
            :label="`${p.order_no} - ${p.receiver_name || '-'} - ${p.destination || '未填写地点'}`"
            :value="p.id"
          />
        </el-select>
        <div v-if="selectedPurchaseId" class="purchase-preview">
          <div>收货人：{{ availablePurchases.find((x) => x.id === selectedPurchaseId)?.receiver_name || '-' }}</div>
          <div>收货地点：{{ availablePurchases.find((x) => x.id === selectedPurchaseId)?.destination || '-' }}</div>
          <div v-for="(it, k) in availablePurchases.find((x) => x.id === selectedPurchaseId)?.items || []" :key="k">
            {{ it.goods_name }} {{ it.quantity }}{{ it.unit }}
          </div>
        </div>
      </template>

      <template v-else>
        <div v-for="(row, i) in outItems" :key="i" class="out-row">
          <el-select v-model="row.goods_name" placeholder="选择物资" filterable style="width: 180px" @change="selectGoods(row)">
            <el-option v-for="inv in inventoryList" :key="inv.goods_name" :label="`${inv.goods_name} (库存${inv.quantity}${inv.unit})`" :value="inv.goods_name" />
          </el-select>
          <el-input-number v-model="row.quantity" :min="0.1" size="default" style="width: 110px" />
          <el-input v-model="row.unit" placeholder="单位" size="default" style="width: 70px" disabled />
          <el-button type="danger" link @click="removeRow(i)">删除</el-button>
        </div>
        <el-button type="primary" link @click="addRow">+ 添加一行</el-button>
      </template>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitOut">确认出库</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; margin-bottom: 20px; }
.table-card { padding: 20px; background: var(--bg-card); border-radius: 12px; }
.out-row { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; }
.purchase-preview { margin-top: 12px; padding: 12px; background: var(--bg-hover); border-radius: 8px; font-size: 13px; }
.hint-box { padding: 12px; background: var(--el-color-info-light-9); border-radius: 8px; font-size: 13px; color: var(--el-text-color-regular); }
</style>
