# Data Model: IDS Refactor Foundation

## IDS Incident

Represents a normalized review object for one detection event or correlated
incident.

**Fields**

- `incident_id`: Stable internal identifier
- `event_origin`: `real`, `demo`, or `test`
- `source_classification`: `external_mature`, `custom_project`, or
  `transitional_local`
- `detector_family`: High-level source family such as web, network, file, or
  host-log
- `detector_name`: Specific source name shown to reviewers
- `rule_id`: Upstream or local rule identifier when available
- `rule_name`: Human-readable detector or rule label
- `source_version`: Version or update marker for the active source
- `source_freshness`: `current`, `stale`, `unknown`, or `unavailable`
- `event_fingerprint`: Normalized fingerprint used for deduplication
- `correlation_key`: Shared key for related events in a short attack window
- `occurred_at`: Source event time
- `ingested_at`: Platform ingestion time
- `client_ip`: Network source when applicable
- `asset_ref`: Target asset or endpoint reference when applicable
- `attack_type`: Normalized incident category
- `severity`: Normalized severity label
- `confidence`: Reviewable confidence score
- `evidence_summary`: Short display-safe summary
- `raw_evidence_ref`: Link, blob key, or stored raw detail reference
- `status`: `new`, `investigating`, `mitigated`, `false_positive`, or `closed`
- `archived`: Boolean archive state
- `review_note`: Current reviewer narrative
- `latest_response_result`: Latest remediation outcome summary
- `response_failure`: Boolean indicating remediation failure visibility
- `linked_event_count`: Number of correlated raw events behind the incident

**Relationships**

- One incident has many response actions.
- One incident references one detection source snapshot.
- One incident can summarize multiple raw detections through a shared
  correlation key.

## Detection Source Snapshot

Represents the provenance and health state of the source that produced an
incident.

**Fields**

- `source_snapshot_id`: Stable identifier
- `source_name`: Display name
- `source_classification`: `external_mature`, `custom_project`, or
  `transitional_local`
- `source_family`: Web, network, file, host-log, or other supported class
- `provenance_summary`: Reviewer-facing provenance description
- `version_label`: Current version marker
- `last_updated_at`: Most recent known upstream update time
- `health_state`: `healthy`, `stale`, `unknown`, or `offline`
- `ingestion_mode`: Direct, imported, seeded, or adapter-fed

**Relationships**

- One source snapshot can be referenced by many incidents.

## Response Action

Represents a manual or automated action taken for an incident.

**Fields**

- `action_id`: Stable identifier
- `incident_id`: Parent incident
- `action_type`: Block, unblock, status change, archive, note update, or other
- `actor_type`: `system` or `user`
- `actor_ref`: Username, service name, or automation label
- `requested_at`: When the action was attempted
- `result_state`: `success`, `failed`, or `record_only`
- `result_detail`: Reviewer-facing outcome detail

**Relationships**

- Many response actions belong to one incident.

## Incident Review Snapshot

Represents the reviewer-facing state used by the security-center UI.

**Fields**

- `incident_id`
- `display_source`
- `display_origin`
- `display_status`
- `display_severity`
- `evidence_preview`
- `response_summary`
- `is_counted_in_real_metrics`

**Relationships**

- Derived from one incident plus its latest source snapshot and response
  actions.
