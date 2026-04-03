import request from './request'

export interface AuditItem {
  id: number
  user_name: string
  user_role: string
  action: string
  target_type: string
  target_id: string
  detail: string
  is_ids: boolean
  is_sensitive: boolean
  ids_domain: 'source_sync' | 'source_package' | 'rulepack' | null
  ids_outcome: 'success' | 'rejected' | 'failed' | 'skipped' | null
  created_at: string | null
}

export interface AuditSummaryBucket {
  name: string
  count: number
}

export interface AuditSummary {
  total: number
  ids_count: number
  sensitive_count: number
  today_count: number
  by_action: AuditSummaryBucket[]
  by_user: AuditSummaryBucket[]
  by_target_type: AuditSummaryBucket[]
  ids_by_domain: AuditSummaryBucket[]
  ids_by_outcome: AuditSummaryBucket[]
}

export interface AuditFilterOptions {
  action_options: string[]
  target_type_options: string[]
  ids_domain_options: Array<'source_sync' | 'source_package' | 'rulepack'>
  ids_outcome_options: Array<'success' | 'rejected' | 'failed' | 'skipped'>
}

export interface AuditListResponse {
  total: number
  page: number
  page_size: number
  items: AuditItem[]
  summary: AuditSummary
  filters: AuditFilterOptions
}

export interface AuditListParams {
  action?: string
  target_type?: string
  user_name?: string
  keyword?: string
  start_at?: string
  end_at?: string
  ids_only?: 0 | 1
  exclude_ids?: 0 | 1
  ids_domain?: 'source_sync' | 'source_package' | 'rulepack'
  ids_outcome?: 'success' | 'rejected' | 'failed' | 'skipped'
  sensitive_only?: 0 | 1
  page?: number
  page_size?: number
}

export function listAuditLogs(params?: AuditListParams) {
  return request.get<AuditListResponse>('/audit', { params })
}
