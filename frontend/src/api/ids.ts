import request from './request'

export interface IDSUploadAuditTrace {
  verdict: string
  risk_level: string
  confidence: number
  summary: string
  provider?: string
  analysis_mode?: string
  analysis_mode_label?: string
  llm_used?: boolean
  ai_available?: boolean
  recommended_actions?: string[]
}

export interface IDSUploadIndicator {
  code: string
  detail: string
}

export interface IDSUploadTrace {
  saved_as: string
  file_name: string
  sha256?: string
  size?: number
  storage_location?: string
  indicator_count?: number
  indicators?: IDSUploadIndicator[]
  audit: IDSUploadAuditTrace
}

export type IDSLogAuditSeverity = 'informational' | 'suspicious' | 'critical' | string

export interface IDSLogAuditItem {
  id: number
  user_name: string
  user_role: string
  action: string
  target_type: string
  target_id: string
  detail: string
  severity: IDSLogAuditSeverity
  metadata?: Record<string, string | number | null>
  created_at: string | null
}

export interface IDSLogAuditSummary {
  total: number
  critical?: number
  suspicious?: number
  informational?: number
  by_action?: { action: string; count: number }[]
  by_target_type?: { target_type: string; count: number }[]
}

export interface IDSLogAuditResponse {
  items: IDSLogAuditItem[]
  total: number
  summary?: IDSLogAuditSummary
  available_actions?: string[]
  available_targets?: string[]
  available_severities?: IDSLogAuditSeverity[]
}

export interface IDSEventItem {
  id: number
  client_ip: string
  event_origin?: string
  event_origin_label?: string
  source_classification?: string
  detector_family?: string
  detector_name?: string
  source_rule_id?: string
  source_rule_name?: string
  source_version?: string
  source_freshness?: string
  event_fingerprint?: string
  correlation_key?: string
  counted_in_real_metrics?: boolean
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
  status?: string
  review_note?: string
  action_taken?: string
  response_result?: string
  response_detail?: string
  upload_trace?: IDSUploadTrace | null
  risk_score?: number
  confidence?: number
  hit_count?: number
  created_at: string | null
  ai_risk_level?: string
  ai_analysis?: string
  ai_confidence?: number
  ai_analyzed_at?: string | null
}

export interface IDSEventsResponse {
  total: number
  items: IDSEventItem[]
}

export interface IDSStatsResponse {
  total: number
  blocked_count: number
  high_risk_count?: number
  by_type: { attack_type: string; attack_type_label: string; count: number }[]
  by_status?: { status: string; count: number }[]
  by_origin?: { event_origin: string; count: number }[]
}

export interface IDSSituationAttackItem {
  id: string
  timestamp: string
  source_ip: string
  source_location: {
    country: string
    city: string
    lat: number
    lng: number
    derived?: boolean
  }
  target_ip: string
  target_location: {
    lat: number
    lng: number
  }
  attack_type: string
  severity: string
  status: string
  blocked: boolean
  detector_name: string
  uptime: string
}

export interface IDSSituationResponse {
  generated_at: string
  scope: string
  disclaimer: string
  target: {
    lat: number
    lng: number
    city: string
    country: string
    ip: string
  }
  metrics: {
    total_blocked: number
    active_threats: number
    uptime_seconds: number
    online_sources: number
  }
  attacks: IDSSituationAttackItem[]
}

export function listIDSEvents(params?: {
  attack_type?: string
  client_ip?: string
  blocked?: number
  archived?: number
  status?: string
  event_origin?: string
  source_classification?: string
  min_score?: number
  limit?: number
  offset?: number
}) {
  return request.get<IDSEventsResponse>('/ids/events', { params })
}

export function getIDSEvent(eventId: number) {
  return request.get<{ item: IDSEventItem }>(`/ids/events/${eventId}`)
}

export function getIDSStats(params?: { event_origin?: string; source_classification?: string }) {
  return request.get<IDSStatsResponse>('/ids/stats', { params })
}

export interface IDSTrendResponse {
  dates: string[]
  counts: number[]
}

// Source operations and package-history payloads for the IDS security-center
// registry panel.
export interface IDSSourceSyncAttemptItem {
  id: number
  source_id: number
  started_at: string | null
  finished_at: string | null
  result_status: string
  detail: string
  freshness_after_sync: string
  package_version: string
  package_intake_id?: number | null
  resolved_sync_endpoint?: string
  triggered_by: string
}

export interface IDSSourcePackageIntakeItem {
  id: number
  source_id: number | null
  source_key: string
  package_version: string
  release_timestamp: string | null
  trust_classification: string
  detector_family: string
  provenance_note: string
  intake_result: string
  intake_detail: string
  artifact_path?: string
  artifact_sha256?: string
  artifact_size_bytes?: number
  rule_count?: number
  triggered_by: string
  created_at: string | null
}

export interface IDSSourcePackagePreviewItem {
  source_id: number
  source_key: string
  package_version: string
  version_change_state: string
  changed_fields: string[]
  visible_warning: string
  artifact_path?: string
  artifact_sha256?: string
  artifact_size_bytes?: number
  rule_count?: number
}

export interface IDSSourceItem {
  id: number
  source_key: string
  display_name: string
  trust_classification: string
  detector_family: string
  operational_status: string
  freshness_target_hours: number
  sync_mode: string
  sync_endpoint: string
  last_synced_at: string | null
  last_sync_status: string
  last_sync_detail: string
  health_state: string
  visible_warning: string
  recent_incident_count: number
  recent_incident_last_seen_at: string | null
  provenance_note: string
  is_production_trusted: boolean
  created_at: string | null
  updated_at: string | null
  latest_sync_attempt?: IDSSourceSyncAttemptItem | null
  recent_sync_attempts: IDSSourceSyncAttemptItem[]
  active_package_version?: string
  active_package_activated_at?: string | null
  active_package_activated_by?: string
  latest_package_preview?: IDSSourcePackagePreviewItem | null
  recent_package_intakes: IDSSourcePackageIntakeItem[]
}

export interface IDSSourceListResponse {
  total: number
  items: IDSSourceItem[]
  summary: {
    total: number
    healthy_count: number
    degraded_count: number
    trusted_count: number
    demo_test_count: number
  }
}

export interface IDSSourceRegistryPayload {
  source_key: string
  display_name: string
  trust_classification: string
  detector_family: string
  operational_status: string
  freshness_target_hours: number
  sync_mode: string
  sync_endpoint?: string
  provenance_note?: string
}

export interface IDSSourceSyncResponse {
  source_id: number
  sync_attempt_id: number
  result_status: string
  health_state: string
  last_synced_at: string | null
  detail: string
  package_version?: string
  package_intake_id?: number | null
  resolved_sync_endpoint?: string
  activation_required?: boolean
  rule_count?: number
  artifact_path?: string
  artifact_sha256?: string
  change_summary?: string
  source: IDSSourceItem
}

export interface IDSSourcePackagePreviewPayload {
  source_key: string
  package_version: string
  release_timestamp?: string
  trust_classification: string
  detector_family: string
  provenance_note?: string
  triggered_by: string
}

export interface IDSSourcePackagePreviewResponse extends IDSSourcePackagePreviewItem {
  package_intake_id: number
  intake_result: string
}

export interface IDSSourcePackageActivationPayload {
  package_intake_id: number
  triggered_by: string
  activation_note?: string
}

export interface IDSSourcePackageActivationResponse {
  source_id: number
  package_activation_id: number
  package_version: string
  result_status: string
  active_package_version: string
  detail: string
}

export interface IDSSourcePackageActivationItem {
  id: number
  source_id: number
  package_intake_id: number
  package_version: string
  activated_at: string | null
  activated_by: string
  activation_detail: string
  created_at: string | null
}

export interface IDSSourcePackageHistoryItem {
  source: {
    id: number
    source_key: string
    display_name: string
    trust_classification: string
    detector_family: string
  } | null
  source_key: string
  active_package_version: string
  active_package_activated_at: string | null
  active_package_activated_by: string
  recent_intakes: IDSSourcePackageIntakeItem[]
  recent_activations: IDSSourcePackageActivationItem[]
}

export interface IDSSourcePackageHistoryResponse {
  total: number
  items: IDSSourcePackageHistoryItem[]
}

export function getIDSTrend(
  days?: number,
  params?: { event_origin?: string; source_classification?: string },
) {
  return request.get<IDSTrendResponse>('/ids/stats/trend', {
    params: { days: days ?? 7, ...params },
  })
}

export function getIDSSituation() {
  return request.get<IDSSituationResponse>('/ids/situation')
}

export function listIDSSources() {
  return request.get<IDSSourceListResponse>('/ids/sources')
}

export function createIDSSource(data: IDSSourceRegistryPayload) {
  return request.post<IDSSourceItem>('/ids/sources', data)
}

export function updateIDSSource(sourceId: number, data: IDSSourceRegistryPayload) {
  return request.put<IDSSourceItem>(`/ids/sources/${sourceId}`, data)
}

export function syncIDSSource(sourceId: number, data: { triggered_by: string; reason?: string }) {
  return request.post<IDSSourceSyncResponse>(`/ids/sources/${sourceId}/sync`, data)
}

export function previewIDSSourcePackage(data: IDSSourcePackagePreviewPayload) {
  return request.post<IDSSourcePackagePreviewResponse>('/ids/source-packages/preview', data)
}

export function activateIDSSourcePackage(data: IDSSourcePackageActivationPayload) {
  return request.post<IDSSourcePackageActivationResponse>('/ids/source-packages/activate', data)
}

export function listIDSSourcePackages(params?: { source_id?: number; source_key?: string; limit?: number }) {
  return request.get<IDSSourcePackageHistoryResponse>('/ids/source-packages', { params })
}

export function archiveIDSEvent(eventId: number) {
  return request.put<{ code: number; message: string }>(`/ids/events/${eventId}/archive`)
}

export function archiveIDSBatch(eventIds: number[]) {
  return request.post<{ code: number; message: string; archived: number }>('/ids/events/archive-batch', {
    event_ids: eventIds,
  })
}

export function analyzeIDSEventAI(eventId: number) {
  return request.post<{
    code: number
    message: string
    ai_risk_level: string
    ai_analysis: string
    ai_analyzed_at: string | null
  }>(`/ids/events/${eventId}/analyze`)
}

export function updateIDSEventStatus(eventId: number, data: { status: string; review_note?: string }) {
  return request.put<{ code: number; message: string; status: string }>(`/ids/events/${eventId}/status`, data)
}

export function blockIDSEventIp(eventId: number) {
  return request.post<{ code: number; message: string; ok: boolean; rule?: string }>(`/ids/events/${eventId}/block`)
}

export function unblockIDSEventIp(eventId: number) {
  return request.post<{ code: number; message: string; ok: boolean }>(`/ids/events/${eventId}/unblock`)
}

export function getIDSEventReport(eventId: number, forceAI?: boolean) {
  return request.get<{ report: any; markdown: string }>(`/ids/events/${eventId}/report`, {
    params: { force_ai: forceAI ? 1 : 0 },
  })
}

export interface IDSLogAuditListParams {
  action?: string
  target_type?: string
  user_name?: string
  severity?: IDSLogAuditSeverity
  limit?: number
  offset?: number
}

export function listIDSLogAudits(params?: IDSLogAuditListParams) {
  return request.get<IDSLogAuditResponse>('/ids/log-audit', { params })
}

/** 主标题彩蛋：多向量并发攻击聚合研判报告 */
// Aggregate report for the seeded phase1 demo chain.
