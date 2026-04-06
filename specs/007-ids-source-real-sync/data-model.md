# Data Model

## IDSSource

- `id`: integer primary key
- `source_key`: stable source identifier
- `display_name`: reviewer-facing source name
- `trust_classification`: trusted/demo scope label
- `detector_family`: detector family label
- `operational_status`: enabled/disabled/failing/draft
- `freshness_target_hours`: reviewer freshness target
- `sync_mode`: manual/scheduled/not_applicable
- `sync_endpoint`: local manifest path used for real sync
- `last_synced_at`: last successful sync timestamp
- `last_sync_status`: latest sync state
- `last_sync_detail`: latest sync detail summary

## IDSSourceSyncAttempt

- `id`: integer primary key
- `source_id`: owning source
- `started_at`, `finished_at`: sync timing
- `result_status`: success/failed/skipped
- `detail`: operator-visible sync summary
- `freshness_after_sync`: derived source health after the attempt
- `package_version`: imported package version when available
- `package_intake_id`: linked package-intake row when a sync created one
- `resolved_sync_endpoint`: resolved manifest path used by the attempt
- `triggered_by`: operator id

## IDSSourcePackageIntake

- `id`: integer primary key
- `source_id`: owning source
- `source_key`: source identifier snapshot
- `package_version`: imported package version
- `release_timestamp`: release timestamp from manifest
- `trust_classification`, `detector_family`: manifest/source identity snapshot
- `provenance_note`: provenance note from the manifest/source
- `intake_result`: previewed/activated/rejected/failed
- `intake_detail`: reviewer-facing detail for the intake
- `artifact_path`: resolved rule artifact path
- `artifact_sha256`: computed SHA-256 of the artifact
- `artifact_size_bytes`: artifact byte size
- `rule_count`: derived rule count
- `triggered_by`: operator id
- `created_at`: intake creation time
