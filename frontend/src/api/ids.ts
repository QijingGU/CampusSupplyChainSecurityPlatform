import request from './request'

export interface IDSEventItem {
  id: number
  client_ip: string
  attack_type: string
  attack_type_label: string
  signature_matched: string
  method: string
  path: string
  query_snippet: string
  body_snippet: string
  user_agent: string
  blocked: number
  firewall_rule: string
  archived: number
  created_at: string | null
}

export interface IDSEventsResponse {
  total: number
  items: IDSEventItem[]
}

export interface IDSStatsResponse {
  total: number
  blocked_count: number
  by_type: { attack_type: string; attack_type_label: string; count: number }[]
}

export function listIDSEvents(params?: {
  attack_type?: string
  client_ip?: string
  blocked?: number
  archived?: number
  limit?: number
  offset?: number
}) {
  return request.get<IDSEventsResponse>('/ids/events', { params })
}

export function getIDSStats() {
  return request.get<IDSStatsResponse>('/ids/stats')
}

export interface IDSTrendResponse {
  dates: string[]
  counts: number[]
}

export function getIDSTrend(days?: number) {
  return request.get<IDSTrendResponse>('/ids/stats/trend', { params: { days: days ?? 7 } })
}

export function archiveIDSEvent(eventId: number) {
  return request.put<{ code: number; message: string }>(`/ids/events/${eventId}/archive`)
}

export function archiveIDSBatch(eventIds: number[]) {
  return request.post<{ code: number; message: string; archived: number }>('/ids/events/archive-batch', {
    event_ids: eventIds,
  })
}
