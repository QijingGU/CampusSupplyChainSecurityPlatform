# Quickstart: IDS Refactor Foundation

## Goal

Validate that the refactored IDS can separate real events from demo/test data,
retain source provenance, and preserve the response workflow.

## Preconditions

- Backend and frontend dependencies are installed.
- The application database is initialized.
- An administrator account is available.

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

## Validate The First Refactor Slice

### 1. Ingest A Real Incident

Send one normalized real event through the new ingestion path and confirm that:

- the incident appears in the IDS console,
- the origin is shown as real,
- provenance fields are visible,
- the incident counts toward default metrics.

Example request:

```powershell
curl -Method POST http://127.0.0.1:8166/api/ids/events/ingest `
  -Headers @{ "Content-Type" = "application/json"; "Authorization" = "Bearer <admin-token>" } `
  -Body '{
    "event_origin": "real",
    "source_classification": "external_mature",
    "detector_family": "web",
    "detector_name": "trusted-web-detector",
    "rule_id": "RULE-1234",
    "rule_name": "Suspicious Injection Attempt",
    "source_version": "2026.04",
    "source_freshness": "current",
    "occurred_at": "2026-04-01T10:20:30Z",
    "client_ip": "203.0.113.10",
    "asset_ref": "/api/upload/public",
    "attack_type": "sql_injection",
    "severity": "high",
    "confidence": 92,
    "event_fingerprint": "web:203.0.113.10:/api/upload/public:RULE-1234",
    "correlation_key": "2026-04-01T10:20:web:203.0.113.10",
    "evidence_summary": "Matched upstream injection rule against upload endpoint",
    "raw_evidence": {
      "method": "POST",
      "path": "/api/upload/public",
      "query_snippet": "id=1'' OR ''1''=''1",
      "body_snippet": "multipart payload omitted"
    }
  }'
```

### 2. Ingest A Demo Incident

Send one normalized demo event and confirm that:

- the incident is clearly marked as demo/test,
- it does not count toward default real metrics,
- it remains viewable when demo/test filters are explicitly enabled.

Example request:

```powershell
curl -Method POST http://127.0.0.1:8166/api/ids/events/ingest `
  -Headers @{ "Content-Type" = "application/json"; "Authorization" = "Bearer <admin-token>" } `
  -Body '{
    "event_origin": "demo",
    "source_classification": "custom_project",
    "detector_family": "web",
    "detector_name": "demo-seed-adapter",
    "rule_id": "DEMO-001",
    "rule_name": "Demo SQL Injection",
    "source_version": "demo-2026.04",
    "source_freshness": "current",
    "occurred_at": "2026-04-01T10:22:00Z",
    "client_ip": "198.51.100.24",
    "asset_ref": "/api/demo/ids",
    "attack_type": "sql_injection",
    "severity": "medium",
    "confidence": 74,
    "event_fingerprint": "demo:198.51.100.24:/api/demo/ids:DEMO-001",
    "correlation_key": "2026-04-01T10:22:demo:198.51.100.24",
    "evidence_summary": "Seeded demo event for UI verification"
  }'
```

### 3. Exercise Response Workflow

From the IDS console:

- move the real incident through investigation and mitigation states,
- add a review note,
- archive the incident,
- verify response history remains visible.

### 4. Verify Correlation Behavior

Submit repeated events with the same short-window correlation key and confirm
they are grouped or bounded into a reviewable set instead of generating an
unlimited row flood.

Current expected behavior in this slice:

- the endpoint reuses an active, non-archived incident when either
  `event_fingerprint` or `correlation_key` matches within a 24-hour review
  window,
- the matched incident keeps one row and increments `hit_count`,
- the latest evidence summary replaces the response detail for quick operator
  review.

### 5. Verify Changelog Discipline

- update `docs/ids-changelog.md` with the day's work,
- commit with `feat:`, `fix:`, or `chore:`,
- push the active IDS branch to GitHub.

## Current Validation Snapshot

- Python compilation passes for the updated IDS backend files.
- Frontend `npm run build` passes after installing local dependencies and
  rerunning outside the sandbox restriction that blocked Vite process spawning.
- Full manual triage validation is still pending and should be recorded in
  `docs/ids-changelog.md` after an operator runs the above steps end to end.
