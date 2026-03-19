import request from './request'

export function listStockIn() {
  return request.get('/stock/in')
}

export function listStockOut() {
  return request.get('/stock/out')
}

export function listInventory(params?: { keyword?: string }) {
  return request.get('/stock/inventory', { params })
}

export interface StockInItem {
  goods_name: string
  quantity: number
  unit: string
  batch_no?: string
}

export function createStockIn(data: { purchase_id?: number; items?: StockInItem[] }) {
  return request.post<{ code: number; message: string; order_no: string }>('/stock/in', data)
}

export interface StockOutItem {
  goods_name: string
  quantity: number
  unit: string
  batch_no?: string
}

export function createStockOut(data: { purchase_id?: number; items?: StockOutItem[] }) {
  return request.post<{ code: number; message: string; order_no: string }>('/stock/out', data)
}
