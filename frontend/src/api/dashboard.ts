import request from './request'

export interface StatItem {
  title: string
  value: number
  trend: string
  trendValue: string
  icon: string
  path: string
}

export interface WarningItem {
  id: number
  time: string
  level: string
  levelLabel: string
  material: string
  desc: string
}

export interface TodoItem {
  id: number
  time: string
  status: string
  statusLabel: string
  title: string
  desc: string
}

export interface SupplierOrderItem {
  id: number
  time: string
  title: string
  desc: string
}

export interface ExpiringItem {
  name: string
  days: number
  count: number
}

export interface ChartData {
  x: string[]
  purchase: number[]
  output: number[]
}

export interface HandoffTask {
  id: number
  order_no: string
  status: string
  status_label: string
  receiver_name: string
  destination: string
  handoff_code: string
}

export interface TodayTodos {
  pendingStockIn: number
  pendingStockOut: number
  pendingDeliveryCreate: number
}

export interface IDSSecurity {
  total: number
  blockedCount: number
  todayCount: number
  latest?: {
    client_ip: string
    attack_type: string
    created_at: string
  }
}

export interface DashboardData {
  stats: StatItem[]
  warnings?: WarningItem[]
  warningList?: (WarningItem | TodoItem | SupplierOrderItem)[]
  expiringItems: ExpiringItem[]
  chartData: ChartData
  todayTodos?: TodayTodos
  handoffTasks?: HandoffTask[]
  idsSecurity?: IDSSecurity
}

export function getDashboard() {
  return request.get<DashboardData>('/dashboard')
}

export interface WarehouseScreenData {
  stats: {
    inventoryTotal: number
    inventoryQtySum: number
    stockInToday: number
    stockOutToday: number
    warningPending: number
    deliveryOngoing: number
    pendingStockIn: number
    pendingStockOut: number
    pendingDeliveryCreate: number
    waitingReceive: number
  }
  chart: { labels: string[]; in: number[]; out: number[] }
  inventoryTop: { name: string; quantity: number }[]
  warnings: { id: number; material: string; level: string; desc: string }[]
  expiring: { name: string; days: number; count: number }[]
  deliveries: { id: number; delivery_no: string; destination: string; status: string; status_label: string; receiver_name: string; handoff_code: string }[]
  handoffTasks: { id: number; order_no: string; status: string; status_label: string; receiver_name: string; destination: string; handoff_code: string; summary: string }[]
}

export function getWarehouseScreen() {
  return request.get<WarehouseScreenData>('/dashboard/screen/warehouse')
}

export interface LogisticsScreenData {
  stats: {
    purchasePending: number
    supplierPending: number
    stockPending: number
    dispatchPending: number
    receivePending: number
    purchaseCompleted: number
    supplierCount: number
    warningPending: number
    deliveryOngoing: number
  }
  chart: { labels: string[]; purchase: number[] }
  pendingPurchases: { id: number; order_no: string; applicant: string; summary: string }[]
  handoffList: { id: number; order_no: string; status: string; status_label: string; handoff_code: string; receiver_name: string; destination: string }[]
  warnings: { id: number; material: string; level: string; desc: string }[]
  deliveries: { id: number; delivery_no: string; destination: string; status: string; receiver_name: string; handoff_code: string }[]
}

export function getLogisticsScreen() {
  return request.get<LogisticsScreenData>('/dashboard/screen/logistics')
}
