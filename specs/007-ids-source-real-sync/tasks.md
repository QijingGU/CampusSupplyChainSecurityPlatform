# Implementation Tasks: IDS Source Real Sync

- [x] Add persisted sync-endpoint and artifact metadata fields to IDS source,
  sync-attempt, and package-intake models.
- [x] Update schema synchronization so existing databases gain the new columns.
- [x] Add a dedicated source-sync service that resolves local manifest/artifact
  paths, validates identity, and computes artifact metadata.
- [x] Replace the old source-sync stub in `POST /api/ids/sources/{source_id}/sync`
  with real manifest-backed sync plus package-intake creation.
- [x] Extend frontend IDS API types with sync endpoint, sync audit, and artifact
  fields.
- [x] Update `SecurityIDS.vue` to capture `sync_endpoint`, expose sync metadata
  on the row, and show Sync Audit in history.
- [x] Add deterministic manifest/rule fixtures for local validation.
- [x] Re-run backend syntax compile and frontend production build.
- [x] Validate the flow through direct API calls and gstack browser checks.
- [x] Update changelog, README, and the demo script for this slice.
