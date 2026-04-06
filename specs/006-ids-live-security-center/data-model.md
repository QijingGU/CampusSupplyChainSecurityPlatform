# Data Model: IDS Live Security Center Parity

## Upload Audit Decision

### Fields

- `verdict`: `pass`, `review`, or `quarantine`
- `risk_level`: `low`, `medium`, or `high`
- `confidence`: operator-facing confidence score
- `summary`: short reviewer-facing decision summary
- `evidence`: list of matched reasons
- `recommended_actions`: next-step actions
- `provider`: audit provider label, for example heuristic fallback or LLM model
- `analysis_mode`: heuristic fallback vs LLM-assisted mode
- `ai_available`: whether AI capability was available during the audit
- `generated_at`: decision timestamp

### State Rules

- Every public upload receives one audit decision before storage is chosen.
- `pass` routes the file to the accepted directory.
- `review` and `quarantine` both route the file to the sandbox directory.

## Quarantine Item

### Fields

- `saved_as`: stored filename used as the sandbox identity
- `original_name` or `file_name`: reviewer-facing name when available
- `size`: file size in bytes
- `modified_at`: latest storage or update time
- `url`: downloadable sandbox file URL
- `risk_level`: derived risk shown in the table
- `extension`: file extension
- `has_report`: whether a persisted report exists
- `report_generated_at`: latest report timestamp
- `audit_verdict`: last audit verdict for the file
- `audit_confidence`: latest confidence score
- `audit_summary`: latest summary shown in the table

### State Rules

- Quarantine items come from real files under the sandbox storage path.
- The list is refresh-safe and must not rely on browser-only synthetic rows.

## Quarantine Analysis Report

### Fields

- `saved_as`: sandbox identity
- `file_name`: reviewer-facing file name
- `size`: file size in bytes
- `extension`: detected extension
- `sha256`: file hash
- `risk_level`: derived final risk level
- `indicator_count`: number of matched static indicators
- `indicators`: list of code/detail pairs
- `generated_at`: initial report generation time
- `last_updated_at`: latest persisted update time
- `analysis_generated_at`: time of the latest sandbox analysis execution
- `storage_location`: `accepted`, `quarantine`, or transitional source value
- `audit`: nested upload audit decision
- `sections`: ordered report sections displayed in the drawer

### State Rules

- Reports are stored under `backend/upload_reports/`.
- Report reopening must work after page refresh.
- If the quarantined file is deleted, the related report sidecar should also be
  removable.

## Situation Attack Snapshot

### Fields

- `id`: IDS event identifier
- `timestamp`: reviewer-facing event time
- `source_ip`: source IP from the real IDS incident
- `source_location`: deterministic approximate map point derived from the IP
- `target_ip`: protected target IP
- `target_location`: protected-node coordinates
- `attack_type`: reviewer-facing attack label
- `severity`: severity label shown in the situation sidebar
- `status`: current operator-facing state such as blocked or investigating
- `blocked`: whether the event is currently blocked
- `detector_name`: detector provenance label

### State Rules

- Situation snapshots default to real IDS incidents only.
- Source location is approximate derived visualization, not authoritative
  geo-intel.

## Situation Summary

### Fields

- `generated_at`: payload generation time
- `scope`: expected to be `real`
- `disclaimer`: derived-location note shown on the page
- `target`: protected target metadata
- `metrics.total_blocked`: blocked real incidents
- `metrics.active_threats`: active real incidents
- `metrics.uptime_seconds`: backend situation-service uptime
- `metrics.online_sources`: current IDS source count
- `attacks`: recent situation attack snapshots

### State Rules

- Empty real-event state is valid and must not synthesize fake attacks.
- The situation page consumes this payload directly.
