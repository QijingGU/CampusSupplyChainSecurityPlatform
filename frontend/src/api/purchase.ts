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
  material_type?: string
  material_spec?: string
  estimated_amount?: number
  delivery_date?: string | null
  attachment_names?: string[]
  is_draft?: number
  approval_level?: string
  approval_required_role?: string
  approval_deadline_at?: string | null
  urgent_level?: 'normal' | 'urgent'
  forwarded_to?: string
  forwarded_note?: string
  is_overdue?: boolean
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

export interface PurchaseApplyReq {
  goods_id: number
  quantity: number
  apply_reason?: string
  destination?: string
  receiver_name?: string
  material_type?: string
  material_spec?: string
  estimated_amount?: number
  delivery_date?: string
  attachment_names?: string[]
  is_draft?: number
}

export function listPurchases(params?: { status?: string }) {
  return request.get<Purchase[]>('/purchase', { params })
}

export function listMyPurchases() {
  return request.get<Purchase[]>('/purchase/my')
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

export function forwardPurchase(id: number, toRole: string, note?: string) {
  return request.put<{ code: number; message: string; order_no: string; to_role: string }>(`/purchase/${id}/forward`, {
    to_role: toRole,
    note: note || '',
  })
}

export function listPurchaseHistory(keyword?: string, limit?: number) {
  return request.get<Purchase[]>('/purchase/history', {
    params: { keyword, limit: limit || 20 },
  })
}

export function getPurchaseFavorites() {
  return request.get<Array<{
    goods_name: string
    quantity: number
    unit: string
    material_type: string
    material_spec: string
    estimated_amount: number
    count: number
  }>>('/purchase/favorites')
}

export function getPurchaseTimeline(id: number) {
  return request.get<{ summary: PurchaseTimelineSummary; timeline: PurchaseTimelineItem[] }>(`/purchase/${id}/timeline`)
}
