import request from './request'

export interface PurchaseItem {
  goods_name: string
  quantity: number
  unit: string
}

export interface Purchase {
  id: number
  order_no: string
  status: string
  status_label?: string
  applicant_id?: number
  applicant_name?: string
  created_at: string | null
  items: PurchaseItem[]
  destination?: string
  receiver_name?: string
  handoff_code?: string
  delivery_id?: number | null
  delivery_no?: string
  delivery_status?: string
  delivery_status_label?: string
  can_confirm_receive?: boolean
  goods_summary?: string
}

export interface PurchaseTimelineItem {
  stage: string
  content: string
  time: string
}

export interface PurchaseTimelineSummary {
  purchase_id: number
  order_no: string
  status: string
  status_label: string
  receiver_name: string
  destination: string
  handoff_code: string
  delivery_count: number
  deliveries: {
    delivery_no: string
    status: string
    status_label: string
    receiver_name: string
    destination: string
    created_at: string
  }[]
}

export function listPurchases(params?: { status?: string }) {
  return request.get<Purchase[]>('/purchase', { params })
}

export function listMyPurchases() {
  return request.get<Purchase[]>('/purchase/my')
}

export interface PurchaseApplyReq {
  goods_id: number
  quantity: number
  apply_reason?: string
  destination?: string
  receiver_name?: string
}

export function createPurchase(data: PurchaseApplyReq) {
  return request.post<{ id: number; order_no: string; status: string; message: string }>('/purchase', data)
}

export function approvePurchase(id: number, supplierId?: number) {
  return request.put<{ code: number; message: string; order_no: string; handoff_code: string; status: string }>(`/purchase/${id}/approve`, {
    supplier_id: supplierId,
  })
}

export function rejectPurchase(id: number, reason?: string) {
  return request.put<{ code: number; message: string; order_no: string }>(`/purchase/${id}/reject`, {
    reason,
  })
}

export function getPurchaseTimeline(id: number) {
  return request.get<{ summary: PurchaseTimelineSummary; timeline: PurchaseTimelineItem[] }>(`/purchase/${id}/timeline`)
}
