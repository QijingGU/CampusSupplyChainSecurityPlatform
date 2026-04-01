# Data Model: IDS Source Operations

## IDS Source Registry Entry

### Fields

- `id`: unique source identifier
- `source_key`: stable human-readable key for the source
- `display_name`: reviewer-facing source name
- `trust_classification`: `external_mature`, `custom_project`, or
  `transitional_local`, or `demo_test`
- `detector_family`: source family such as `web`, `network`, `file`, or `log`
- `operational_status`: `enabled`, `disabled`, `failing`, or `draft`
- `freshness_target_hours`: expected freshness window
- `sync_mode`: `manual`, `scheduled`, or `not_applicable`
- `last_synced_at`: latest successful sync timestamp
- `last_sync_status`: `success`, `failed`, `skipped`, or `never_synced`
- `last_sync_detail`: latest sync detail message
- `provenance_note`: justification or provenance note for reviewer trust
- `recent_incident_count`: derived count of recent incidents linked to the
  source
- `created_at`, `updated_at`: audit timestamps

### Relationships

- One registry entry may relate to many `IDS Incident` records via detector
  metadata.
- One registry entry may have many `Source Sync Attempt` records.

## Source Sync Attempt

### Fields

- `id`: unique attempt identifier
- `source_id`: parent registry entry
- `started_at`: when the sync began
- `finished_at`: when the sync completed or was abandoned
- `result_status`: `success`, `failed`, or `skipped`
- `detail`: reviewer-visible result detail
- `freshness_after_sync`: derived freshness state after the attempt
- `triggered_by`: operator or system actor responsible for the attempt

### Relationships

- Many attempts belong to one `IDS Source Registry Entry`.

## Source Health Snapshot

### Fields

- `source_id`: parent registry entry
- `health_state`: `healthy`, `stale`, `disabled`, `failing`, or `never_synced`
- `last_synced_at`: copied from registry entry for display
- `freshness_target_hours`: copied from registry entry
- `recent_incident_count`: derived reviewer-facing indicator
- `visible_warning`: concise explanation when health is not healthy

### State Rules

- `disabled` overrides freshness or sync success.
- `never_synced` applies when no successful sync has ever completed for the
  source.
- `failing` applies when the latest attempt failed.
- `stale` applies when last successful sync is older than the freshness target.
- `healthy` applies when the source is enabled and freshness remains within the
  target window.
- A latest `skipped` attempt does not count as a successful refresh. If a
  source has never synced successfully, it remains `never_synced`; otherwise it
  keeps its previous freshness-derived state while exposing the skipped detail.
- `demo_test` sources must remain visible but cannot be summarized as trusted
  production coverage in reviewer-facing health views.
