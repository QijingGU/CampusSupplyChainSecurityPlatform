# Quickstart: IDS Source Operations

## Goal

Validate that trusted IDS sources can be registered, reviewed, synchronized,
and audited without confusing them with demo-only source records.

## Preconditions

- Backend and frontend dependencies are installed.
- The application database is initialized.
- An administrator account is available.
- The normalized incident workflow from `001-ids-refactor` is already present.
- An administrator token is available for API-level validation.

## Run The Application

### Backend

```powershell
cd D:\ids\CampusSupplyChainSecurityPlatform\backend
pip install -r requirements.txt
python init_db.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8166
```

### Frontend

```powershell
cd D:\ids\CampusSupplyChainSecurityPlatform\frontend
npm install
npm run dev
```

## Validate The Source Operations Slice

### 1. Register A Trusted Source

- Create one `external_mature` source definition through
  `POST /api/ids/sources`.
- Confirm the source appears in the source operations view with
  `never_synced` or equivalent initial health.

Example request:

```powershell
curl -Method POST http://127.0.0.1:8166/api/ids/sources `
  -Headers @{ "Content-Type" = "application/json"; "Authorization" = "Bearer <admin-token>" } `
  -Body '{
    "source_key": "suricata-web-prod",
    "display_name": "Suricata Web Rules",
    "trust_classification": "external_mature",
    "detector_family": "network",
    "operational_status": "enabled",
    "freshness_target_hours": 24,
    "sync_mode": "manual",
    "provenance_note": "Campus-approved mature upstream ruleset"
  }'
```

### 2. Register A Demo-Oriented Source

- Create one `demo_test` source definition through the same API.
- Confirm it remains visibly separate from trusted production-oriented sources
  and from any real `custom_project` source.

Example request:

```powershell
curl -Method POST http://127.0.0.1:8166/api/ids/sources `
  -Headers @{ "Content-Type" = "application/json"; "Authorization" = "Bearer <admin-token>" } `
  -Body '{
    "source_key": "demo-seed-source",
    "display_name": "Demo Seed Source",
    "trust_classification": "demo_test",
    "detector_family": "web",
    "operational_status": "draft",
    "freshness_target_hours": 24,
    "sync_mode": "not_applicable",
    "provenance_note": "Demo-only source for UI and reviewer training"
  }'
```

### 3. Review Source Health At API Level

- Call `GET /api/ids/sources`.
- Confirm the trusted source shows `never_synced` before its first successful
  sync.
- Confirm the `demo_test` source is returned but not presented as trusted
  production coverage.

Example request:

```powershell
curl http://127.0.0.1:8166/api/ids/sources `
  -Headers @{ "Authorization" = "Bearer <admin-token>" }
```

### 4. Run A Successful Sync Attempt

- Trigger one sync for an enabled trusted source.
- Confirm the attempt records `success`, updates `last_synced_at`, and changes
  reviewer-facing health appropriately.

Example request:

```powershell
curl -Method POST http://127.0.0.1:8166/api/ids/sources/1/sync `
  -Headers @{ "Content-Type" = "application/json"; "Authorization" = "Bearer <admin-token>" } `
  -Body '{
    "triggered_by": "system_admin",
    "reason": "Daily trusted-source refresh"
  }'
```

### 5. Run A Skipped Or Failed Sync Attempt

- Trigger a sync for a disabled source or simulate a failure path.
- Confirm the result remains visible as `skipped` or `failed` with detail.
- Confirm a skipped attempt does not falsely mark a never-synced source as
  healthy.

### 6. Verify Incident Linkage

- Ingest at least one incident tied to the trusted source.
- Confirm the source view shows recent incident linkage or activity count.

### 7. Verify Changelog Discipline

- Update `docs/ids-changelog.md` with the day's source-operation work.
- Commit with `feat:`, `fix:`, or `chore:`.
- Push the active IDS branch to GitHub.

## Current Implementation Notes

- In the current slice, recent incident linkage is derived by matching
  `IDS Source.source_key` to ingested `IDSEvent.detector_name`.
- To validate a failed sync path without a real upstream connector, set the
  source `operational_status` to `failing` and then trigger
  `POST /api/ids/sources/{source_id}/sync`.
- To validate a skipped sync path, use a `demo_test` source with
  `sync_mode=not_applicable` or a disabled/draft source and then trigger the
  same sync endpoint.
- The frontend source-operations panel now lives inside
  `frontend/src/views/security/SecurityIDS.vue`; build validation should include
  `npm run build` after source form or table changes.
