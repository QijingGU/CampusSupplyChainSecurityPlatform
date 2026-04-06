# Implementation Plan: IDS Source Real Sync

## Goal

Replace metadata-only IDS source sync with a real local manifest workflow that
creates artifact-backed sync attempts and package-intake records.

## Architecture

### Backend

- Extend `IDSSource` with `sync_endpoint`.
- Extend `IDSSourceSyncAttempt` with `package_version`, `package_intake_id`, and
  `resolved_sync_endpoint`.
- Extend `IDSSourcePackageIntake` with `artifact_path`, `artifact_sha256`,
  `artifact_size_bytes`, and `rule_count`.
- Add `backend/app/services/ids_source_sync.py` to:
  - resolve sync paths inside the repository/backend workspace,
  - parse the manifest JSON,
  - validate source identity,
  - read the artifact,
  - compute SHA-256, size, and derived rule count.
- Replace the old success stub in `POST /api/ids/sources/{source_id}/sync` with
  real manifest loading and intake creation.

### Frontend

- Extend `frontend/src/api/ids.ts` so source rows, sync attempts, and package
  intakes all carry the new sync/artifact fields.
- Extend `frontend/src/views/security/SecurityIDS.vue` so the source form captures
  `sync_endpoint`, the row shows sync endpoint + artifact context, and the history
  dialog shows Sync Audit records.

### Fixtures

- Add a repo-local manifest and rule file under
  `backend/app/data/ids_source_sync/` for deterministic QA and demos.

## Data Flow

1. Operator saves an IDS source with `sync_endpoint`.
2. `POST /api/ids/sources/{id}/sync` loads the local manifest.
3. The service validates the source metadata, resolves the artifact path, and
   computes derived metadata.
4. The backend creates:
   - one `IDSSourceSyncAttempt`,
   - one `IDSSourcePackageIntake`,
   - updated `source.last_sync_*` state.
5. The security-center source row and history dialog read those persisted records.

## Verification Strategy

- Python syntax compile for all touched backend files.
- Frontend production build.
- API-level validation against the fixture manifest.
- gstack browser validation on `/security/ids`.

## Residual Risk

- `sync_mode=scheduled` still means "scheduler-managed" metadata, not an in-app
  cron runner.
- The history dialog now shows sync audit plus package history, but the outer
  dialog title still reflects the older package-history wording.
