<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// 瓦片源：国内 OSM 可能较慢或受限，备选 Geoq
const TILE_URLS = [
  'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  'https://map.geoq.cn/ArcGIS/rest/services/ChinaOnlineStreetPurplishBlue/MapServer/tile/{z}/{y}/{x}',
]
import { listDeliveries } from '@/api/delivery'
import type { DeliveryItem } from '@/api/delivery'
import { ElMessage, ElMessageBox } from 'element-plus'

const STORAGE_KEY = 'delivery_map_beacons'
const WAREHOUSE_KEY = 'delivery_map_warehouse'

export interface Beacon {
  id: string
  label: string
  lat: number
  lng: number
}

const MAP_CENTER: [number, number] = [43.8305, 125.3678]

const loading = ref(true)
const deliveries = ref<DeliveryItem[]>([])
const selectedId = ref<number | null>(null)
const vehicleMarker = ref<L.Marker | null>(null)
const animating = ref(false)

// 自定义信标（可编辑、锁定到 localStorage）
const customBeacons = ref<Beacon[]>([])
const warehouseBeaconId = ref<string | null>(null)
const addMode = ref(false)
const beaconDialogVisible = ref(false)
const beaconForm = ref({ label: '', lat: 0, lng: 0 })
const editingBeaconId = ref<string | null>(null)

// 中央仓库坐标（来自信标或默认）
const WAREHOUSE_POS = computed((): [number, number] => {
  if (warehouseBeaconId.value) {
    const b = customBeacons.value.find((x) => x.id === warehouseBeaconId.value)
    if (b) return [b.lat, b.lng]
  }
  return MAP_CENTER
})

let map: L.Map | null = null
let warehouseMarker: L.Marker | null = null
let beaconMarkers: L.Marker[] = []
let destMarkers: L.Marker[] = []
let routeLine: L.Polyline | null = null
let mapClickHandler: ((e: L.LeafletMouseEvent) => void) | null = null

function loadBeacons() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const arr = JSON.parse(raw)
      customBeacons.value = Array.isArray(arr) ? arr : []
    }
    const wid = localStorage.getItem(WAREHOUSE_KEY)
    warehouseBeaconId.value = wid || null
  } catch {
    customBeacons.value = []
  }
}

function saveBeacons() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(customBeacons.value))
  if (warehouseBeaconId.value) {
    localStorage.setItem(WAREHOUSE_KEY, warehouseBeaconId.value)
  } else {
    localStorage.removeItem(WAREHOUSE_KEY)
  }
  ElMessage.success('信标已锁定保存')
}

function getCampusPos(id: number, dest: string): [number, number] {
  const s = (dest || '').replace(/\s/g, '')
  for (const b of customBeacons.value) {
    if (s.includes(b.label.replace(/\s/g, ''))) return [b.lat, b.lng]
  }
  if (customBeacons.value.length) {
    const idx = Math.abs(id % customBeacons.value.length)
    const b = customBeacons.value[idx]
    return [b.lat, b.lng]
  }
  return MAP_CENTER
}

const deliveryPositions = computed(() =>
  deliveries.value.map((d) => ({
    ...d,
    pos: getCampusPos(d.id, d.destination),
  }))
)

const selectedDelivery = computed(() =>
  deliveryPositions.value.find((d) => d.id === selectedId.value)
)

const statusLabel: Record<string, string> = {
  pending: '待发车',
  loading: '装车中',
  on_way: '运输中',
  received: '已签收',
}

const warehouseIcon = L.divIcon({
  html: '<span class="wh-icon">仓</span>',
  className: 'custom-marker warehouse',
  iconSize: [40, 40],
  iconAnchor: [20, 20],
})

const beaconIcon = (label: string) =>
  L.divIcon({
    html: `<span class="beacon-label">${label}</span>`,
    className: 'custom-marker beacon',
    iconSize: [80, 28],
    iconAnchor: [40, 14],
  })

const destIcon = (active: boolean) =>
  L.divIcon({
    html: '<span class="dest-icon">目</span>',
    className: `custom-marker destination ${active ? 'active' : ''}`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  })

const vehicleIcon = L.divIcon({
  html: '<span class="vehicle-icon">车</span>',
  className: 'custom-marker vehicle',
  iconSize: [36, 36],
  iconAnchor: [18, 18],
})

function refreshBeaconMarkers() {
  if (!map) return
  beaconMarkers.forEach((m) => map!.removeLayer(m as unknown as L.Layer))
  beaconMarkers = []

  warehouseMarker && map.removeLayer(warehouseMarker as unknown as L.Layer)
  warehouseMarker = null

  customBeacons.value.forEach((b) => {
    const isWarehouse = b.id === warehouseBeaconId.value
    const icon = isWarehouse ? warehouseIcon : beaconIcon(b.label)
    const m = L.marker([b.lat, b.lng], { icon })
      .addTo(map!)
      .bindPopup(isWarehouse ? `【中央仓库】${b.label}` : b.label)
    m.on('click', () => {
      if (addMode.value) return
      ElMessageBox.confirm(`设为中央仓库？`, b.label, {
        confirmButtonText: '设为仓库',
        cancelButtonText: '取消',
      })
        .then(() => {
          warehouseBeaconId.value = b.id
          saveBeacons()
          refreshBeaconMarkers()
        })
        .catch(() => {})
    })
    beaconMarkers.push(m)
  })

  if (!warehouseBeaconId.value) {
    warehouseMarker = L.marker(MAP_CENTER, { icon: warehouseIcon })
      .addTo(map!)
      .bindPopup('中央仓库（默认位置，添加信标后点击可设为仓库）')
  }
}

function openAddBeacon(lat: number, lng: number) {
  beaconForm.value = { label: '', lat, lng }
  editingBeaconId.value = null
  beaconDialogVisible.value = true
}

function openEditBeacon(b: Beacon) {
  beaconForm.value = { label: b.label, lat: b.lat, lng: b.lng }
  editingBeaconId.value = b.id
  beaconDialogVisible.value = true
}

function submitBeacon() {
  const { label, lat, lng } = beaconForm.value
  if (!label.trim()) {
    ElMessage.warning('请输入信标名称')
    return
  }
  if (editingBeaconId.value) {
    const idx = customBeacons.value.findIndex((x) => x.id === editingBeaconId.value)
    if (idx >= 0) {
      customBeacons.value[idx] = { ...customBeacons.value[idx], label: label.trim(), lat, lng }
    }
  } else {
    customBeacons.value.push({
      id: `b${Date.now()}`,
      label: label.trim(),
      lat,
      lng,
    })
  }
  beaconDialogVisible.value = false
  refreshBeaconMarkers()
}

function removeBeacon(b: Beacon) {
  ElMessageBox.confirm(`删除信标「${b.label}」？`, '确认', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(() => {
      customBeacons.value = customBeacons.value.filter((x) => x.id !== b.id)
      if (warehouseBeaconId.value === b.id) warehouseBeaconId.value = null
      refreshBeaconMarkers()
      saveBeacons()
    })
    .catch(() => {})
}

function setWarehouse(b: Beacon) {
  warehouseBeaconId.value = b.id
  saveBeacons()
  refreshBeaconMarkers()
}

function toggleAddMode() {
  addMode.value = !addMode.value
  if (mapClickHandler && map) {
    map.off('click', mapClickHandler)
    mapClickHandler = null
  }
  if (addMode.value && map) {
    mapClickHandler = (e: L.LeafletMouseEvent) => {
      openAddBeacon(e.latlng.lat, e.latlng.lng)
    }
    map.on('click', mapClickHandler)
    ElMessage.info('点击地图添加信标')
  } else {
    ElMessage.info('已退出添加模式')
  }
}

let tileLayerIndex = 0
let tileSwitchDone = false

function addTileLayer() {
  if (!map) return
  const url = TILE_URLS[tileLayerIndex]
  const layer = L.tileLayer(url, {
    attribution: tileLayerIndex === 0
      ? '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      : '&copy; Geoq',
    maxZoom: 19,
    minZoom: 12,
  })
  layer.on('tileerror', () => {
    if (!tileSwitchDone && tileLayerIndex + 1 < TILE_URLS.length) {
      tileSwitchDone = true
      map?.removeLayer(layer)
      tileLayerIndex++
      addTileLayer()
    }
  })
  layer.addTo(map)
}

function initMap() {
  const el = document.getElementById('leaflet-map')
  if (!el) return
  map = L.map(el, { zoomControl: false }).setView(MAP_CENTER, 18)

  L.control.zoom({ position: 'bottomright' }).addTo(map)

  addTileLayer()

  refreshBeaconMarkers()
  nextTick(() => {
    map?.invalidateSize()
  })
}

function updateMarkers() {
  if (!map) return
  destMarkers.forEach((m) => map!.removeLayer(m as unknown as L.Layer))
  destMarkers = []
  routeLine && map.removeLayer(routeLine as unknown as L.Layer)
  routeLine = null

  deliveryPositions.value.forEach((d) => {
    const m = L.marker(d.pos as [number, number], {
      icon: destIcon(selectedId.value === d.id),
    })
      .addTo(map!)
      .on('click', () => selectDelivery(d))
    m.bindPopup(
      `${d.delivery_no}<br/>${d.purchase_order_no || '-'}<br/>${d.destination}<br/>收货人：${d.receiver_name || '-'}<br/>交接码：${d.handoff_code || '-'}`
    )
    destMarkers.push(m)
  })

  if (selectedDelivery.value && ['pending', 'loading', 'on_way'].includes(selectedDelivery.value.status)) {
    if (!vehicleMarker.value) {
      vehicleMarker.value = L.marker(WAREHOUSE_POS.value, { icon: vehicleIcon }).addTo(map!)
    }
    vehicleMarker.value.setLatLng(WAREHOUSE_POS.value)
    routeLine = L.polyline([WAREHOUSE_POS.value, selectedDelivery.value.pos as [number, number]], {
      color: '#3b82f6',
      weight: 3,
      opacity: 0.7,
      dashArray: '10, 10',
    }).addTo(map!)
  } else if (vehicleMarker.value) {
    map.removeLayer(vehicleMarker.value as unknown as L.Layer)
    vehicleMarker.value = null
  }
}

function selectDelivery(d: DeliveryItem) {
  selectedId.value = d.id
  if (['pending', 'loading', 'on_way'].includes(d.status)) {
    startSimulation(d)
  }
  updateMarkers()
}

function startSimulation(d: DeliveryItem) {
  if (animating.value || !map) return
  const dest = getCampusPos(d.id, d.destination)
  animating.value = true
  if (!vehicleMarker.value) {
    vehicleMarker.value = L.marker(WAREHOUSE_POS.value, { icon: vehicleIcon }).addTo(map!)
  }
  vehicleMarker.value.setLatLng(WAREHOUSE_POS.value)
  const start = WAREHOUSE_POS.value
  const duration = 4000
  const startTime = Date.now()

  function tick() {
    const t = Math.min(1, (Date.now() - startTime) / duration)
    const eased = t * t * (3 - 2 * t)
    const lat = start[0] + (dest[0] - start[0]) * eased
    const lng = start[1] + (dest[1] - start[1]) * eased
    vehicleMarker.value?.setLatLng([lat, lng])
    if (t >= 1) {
      animating.value = false
      updateMarkers()
      return
    }
    requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

watch(customBeacons, () => updateMarkers(), { deep: true })
watch(warehouseBeaconId, () => updateMarkers())

async function load() {
  loading.value = true
  try {
    const res: any = await listDeliveries()
    deliveries.value = Array.isArray(res) ? res : res?.data ?? []
    if (deliveries.value.length && !selectedId.value) {
      const ongoing = deliveries.value.find((d) => ['pending', 'loading', 'on_way'].includes(d.status))
      if (ongoing) selectedId.value = ongoing.id
    }
    updateMarkers()
  } catch {
    deliveries.value = []
  } finally {
    loading.value = false
  }
}

let refreshTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  loadBeacons()
  nextTick(() => {
    initMap()
    setTimeout(() => map?.invalidateSize(), 100)
  })
  load()
  refreshTimer = setInterval(load, 15000)
})

onUnmounted(() => {
  refreshTimer && clearInterval(refreshTimer)
  if (mapClickHandler && map) map.off('click', mapClickHandler)
  destMarkers.forEach((m) => map?.removeLayer(m as unknown as L.Layer))
  beaconMarkers.forEach((m) => map?.removeLayer(m as unknown as L.Layer))
  vehicleMarker.value && map?.removeLayer(vehicleMarker.value as unknown as L.Layer)
  warehouseMarker && map?.removeLayer(warehouseMarker as unknown as L.Layer)
  routeLine && map?.removeLayer(routeLine as unknown as L.Layer)
  map?.remove()
  map = null
})
</script>

<template>
  <div class="delivery-map-page">
    <div class="map-header">
      <h2>配送地图 · 长春职业技术大学（卫星校区）</h2>
      <div class="header-actions">
        <el-button :type="addMode ? 'primary' : 'default'" @click="toggleAddMode">
          {{ addMode ? '点击地图添加信标' : '添加信标' }}
        </el-button>
        <el-button type="success" @click="saveBeacons">锁定保存</el-button>
      </div>
    </div>
    <div class="map-layout">
      <div class="delivery-list">
        <div class="list-section">
          <h3>信标列表</h3>
          <div class="beacon-list">
            <div v-for="b in customBeacons" :key="b.id" class="beacon-item">
              <span class="name">{{ b.label }}</span>
              <span class="coord">{{ b.lat.toFixed(5) }}, {{ b.lng.toFixed(5) }}</span>
              <div class="beacon-actions">
                <el-button size="small" link type="primary" @click="setWarehouse(b)">
                  {{ warehouseBeaconId === b.id ? '✓仓库' : '设仓库' }}
                </el-button>
                <el-button size="small" link @click="openEditBeacon(b)">编辑</el-button>
                <el-button size="small" link type="danger" @click="removeBeacon(b)">删除</el-button>
              </div>
            </div>
            <div v-if="!customBeacons.length" class="empty-hint">暂无信标，点击「添加信标」后在地图上点击添加</div>
          </div>
        </div>
        <div class="list-section">
          <h3>配送单</h3>
          <div v-loading="loading" class="list">
            <div
              v-for="d in deliveryPositions"
              :key="d.id"
              class="list-item"
              :class="{ active: selectedId === d.id }"
              @click="selectDelivery(d)"
            >
              <span class="no">{{ d.delivery_no }}</span>
              <span class="dest">申请单：{{ d.purchase_order_no || '-' }}</span>
              <span class="dest">{{ d.destination }}</span>
              <span class="dest">收货人：{{ d.receiver_name || '-' }}</span>
              <span class="dest">交接码：{{ d.handoff_code || '-' }}</span>
              <span class="tag" :class="d.status">{{ statusLabel[d.status] || d.status }}</span>
            </div>
            <div v-if="!deliveries.length && !loading" class="empty">暂无配送单</div>
          </div>
        </div>
      </div>
      <div class="map-container">
        <div id="leaflet-map" class="map-view" :class="{ 'add-mode': addMode }" />
        <div v-if="selectedDelivery" class="map-legend">
          <p><strong>{{ selectedDelivery.delivery_no }}</strong> → {{ selectedDelivery.destination }}</p>
          <p>申请单号：{{ selectedDelivery.purchase_order_no || '-' }}</p>
          <p>收货人：{{ selectedDelivery.receiver_name || '-' }}</p>
          <p>当前状态：{{ selectedDelivery.status_label || statusLabel[selectedDelivery.status] }}</p>
          <p>交接码：{{ selectedDelivery.handoff_code || '-' }}</p>
        </div>
      </div>
    </div>

    <el-dialog v-model="beaconDialogVisible" :title="editingBeaconId ? '编辑信标' : '新增信标'" width="420">
      <el-form :model="beaconForm" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="beaconForm.label" placeholder="如：1#教学楼、图书馆" />
        </el-form-item>
        <el-form-item label="坐标">
          <el-input disabled :value="`${beaconForm.lat.toFixed(5)}, ${beaconForm.lng.toFixed(5)}`" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="beaconDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitBeacon">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.delivery-map-page {
  min-height: calc(100vh - 120px);
  background: linear-gradient(180deg, #0c4a6e 0%, #0e7490 50%, #155e75 100%);
  padding: 20px;
  color: #e5e7eb;
}

.map-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  h2 { font-size: 22px; color: #f8fafc; }
  .header-actions { display: flex; gap: 12px; }
}

.map-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 24px;
  min-height: 520px;
}

.delivery-list {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.list-section {
  h3 { font-size: 14px; margin-bottom: 10px; color: #94a3b8; }
}

.beacon-list {
  max-height: 180px;
  overflow-y: auto;
}

.beacon-item {
  padding: 10px 12px;
  margin-bottom: 8px;
  background: rgba(30, 41, 59, 0.6);
  border-radius: 8px;
  border: 1px solid #334155;
  .name { font-weight: 600; color: #38bdf8; display: block; }
  .coord { font-size: 11px; color: #64748b; display: block; margin-top: 2px; }
  .beacon-actions { margin-top: 6px; }
}

.empty-hint {
  padding: 16px;
  color: #64748b;
  font-size: 12px;
  text-align: center;
}

.list-item {
  padding: 10px 12px;
  margin-bottom: 6px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
  &:hover, &.active { background: rgba(56, 189, 248, 0.15); border-color: #38bdf8; }
  .no { font-weight: 600; color: #38bdf8; display: block; font-size: 13px; }
  .dest { font-size: 12px; color: #94a3b8; display: block; margin-top: 2px; }
  .tag { font-size: 10px; padding: 2px 6px; border-radius: 4px; margin-top: 4px; display: inline-block; }
  .tag.pending, .tag.loading { background: #f59e0b; color: #000; }
  .tag.on_way { background: #3b82f6; color: #fff; }
  .tag.received { background: #10b981; color: #fff; }
}

.list { max-height: 200px; overflow-y: auto; }
.empty { padding: 24px; text-align: center; color: #64748b; font-size: 13px; }

.map-container {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  min-height: 520px;
}

.map-view {
  flex: 1;
  min-height: 480px;
  height: 480px;
  border-radius: 8px;
  overflow: hidden;
  z-index: 1;
  &.add-mode { cursor: crosshair; }
}

.map-legend {
  margin-top: 12px;
  padding: 12px;
  background: rgba(30, 41, 59, 0.6);
  border-radius: 8px;
  font-size: 13px;
}

:deep(.custom-marker) {
  border: none !important;
  background: transparent !important;
  .wh-icon, .dest-icon, .vehicle-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    font-size: 14px;
    font-weight: 700;
  }
}
:deep(.custom-marker.beacon .beacon-label) {
  font-size: 11px;
  padding: 4px 8px;
  background: rgba(16, 185, 129, 0.9);
  color: #fff;
  border-radius: 4px;
  white-space: nowrap;
}
:deep(.custom-marker.warehouse .wh-icon) {
  background: #1e40af;
  color: #93c5fd;
  box-shadow: 0 0 12px rgba(59, 130, 246, 0.6);
}
:deep(.custom-marker.destination .dest-icon) {
  background: #065f46;
  color: #6ee7b7;
  border: 2px solid #10b981;
}
:deep(.custom-marker.destination.active .dest-icon) {
  box-shadow: 0 0 16px rgba(16, 185, 129, 0.8);
}
:deep(.custom-marker.vehicle .vehicle-icon) {
  background: #dc2626;
  color: #fecaca;
  box-shadow: 0 0 16px rgba(220, 38, 38, 0.8);
  animation: vehicle-pulse 1.5s ease-in-out infinite;
}
@keyframes vehicle-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.85; }
}
</style>
