# Contract: IDS Source Operations

## Purpose

Define the first operational contract for trusted IDS source registry and source
synchronization workflows.

## Endpoints

- `GET /api/ids/sources`
- `POST /api/ids/sources`
- `PUT /api/ids/sources/{source_id}`
- `POST /api/ids/sources/{source_id}/sync`

## Source Registry Request Body

```json
{
  "source_key": "suricata-web-prod",
  "display_name": "Suricata Web Rules",
  "trust_classification": "external_mature",
  "detector_family": "network",
  "operational_status": "enabled",
  "freshness_target_hours": 24,
  "sync_mode": "manual",
  "provenance_note": "Campus-approved mature upstream ruleset"
}
```

## Source Registry Response Body

```json
{
  "id": 7,
  "source_key": "suricata-web-prod",
  "display_name": "Suricata Web Rules",
  "trust_classification": "external_mature",
  "detector_family": "network",
  "operational_status": "enabled",
  "freshness_target_hours": 24,
  "sync_mode": "manual",
  "last_synced_at": "2026-04-01T08:30:00Z",
  "last_sync_status": "success",
  "last_sync_detail": "Metadata refreshed successfully",
  "health_state": "healthy",
  "recent_incident_count": 14,
  "provenance_note": "Campus-approved mature upstream ruleset"
}
```

## Sync Trigger Request Body

```json
{
  "triggered_by": "system_admin",
  "reason": "Daily trusted-source refresh"
}
```

## Sync Trigger Response Body

```json
{
  "source_id": 7,
  "sync_attempt_id": 19,
  "result_status": "success",
  "health_state": "healthy",
  "last_synced_at": "2026-04-01T08:30:00Z",
  "detail": "Metadata refreshed successfully"
}
```

## Validation Rules

- `source_key`, `display_name`, `trust_classification`, and `detector_family`
  are required.
- `trust_classification` must be one of `external_mature`,
  `custom_project`, `transitional_local`, or `demo_test`.
- `operational_status` must be one of `enabled`, `disabled`, `failing`, or
  `draft`.
- `freshness_target_hours` must be a positive bounded integer.
- Demo-only or test-only source definitions must use `demo_test` and must never
  be mislabeled as `external_mature` or a production `custom_project` source.
- A sync trigger for a disabled source must record a `skipped` result instead
  of pretending success.
- A `skipped` sync attempt does not satisfy freshness on its own and must remain
  visible as the latest operational result.

## Behavioral Notes

- Source health is reviewer-facing derived state and must remain consistent with
  persisted registry facts plus the latest sync attempt.
- Recent incident counts may be approximate within a bounded review window, but
  they must remain visibly tied to each source.
- The first slice may use manual or partial upstream refresh behavior as long as
  every sync attempt remains traceable.
- Reviewer-facing trusted coverage must exclude `demo_test` sources from any
  production-oriented summary language.
