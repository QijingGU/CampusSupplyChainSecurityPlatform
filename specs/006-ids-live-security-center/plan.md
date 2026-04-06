# Implementation Plan: IDS Live Security Center Parity

**Branch**: `security-center/feature-ids-realize-ui`  
**Date**: 2026-04-05  
**Spec**: [spec.md](/D:/ids/CampusSupplyChainSecurityPlatform/specs/006-ids-live-security-center/spec.md)

## Summary

Turn the most reviewer-visible IDS demo surfaces into backend-driven workflows.
This slice makes public upload gating real, makes sandbox analysis/report
reopening real, and makes the situation page incident-driven. The result is a
traceable chain from upload, to audit, to sandbox, to IDS incident, to live
situation telemetry.

## Technical Context

**Languages**: Python 3.11, TypeScript 5, Vue 3  
**Primary Dependencies**: FastAPI, SQLAlchemy, Pydantic, Element Plus, ECharts,
D3  
**Storage**:
- accepted files in `backend/uploads/accepted/`
- quarantined files in `backend/quarantine_uploads/`
- report sidecars in `backend/upload_reports/`
- IDS incidents in the existing application database

**Validation**:
- backend `py_compile`
- frontend production build
- local manual walkthrough
- gstack browser QA

**Constraints**:
- keep changes inside IDS/security-center/upload-related paths,
- avoid synthetic sandbox rows and random situation attacks,
- label derived map positions honestly,
- sync docs/specs/changelog on the same day as code changes.

## Constitution Check

- **Detection Integrity Over Demo Effects**: PASS. Upload gating, sandbox
  analysis, and situation telemetry now come from backend data.
- **Reuse Mature Detection Sources First**: PASS. The slice reuses real uploads,
  persisted reports, and normalized IDS incidents instead of inventing new fake
  detectors.
- **Traceable Response Loop**: PASS. A withheld upload can be traced into the
  sandbox and situation views.
- **Daily Changelog And Remote Sync Discipline**: PASS. This slice updates
  spec/docs/changelog on 2026-04-05.
- **Conflict-Minimizing Change Scope**: PASS. Changes remain in upload, IDS,
  security-center frontend views, and documentation paths.

## Planned And Shipped Changes

### Backend

- `backend/app/api/upload.py`
  - AI-audit every public upload
  - split accepted vs quarantined storage
  - persist upload audit report sidecars
  - expose quarantine list, report reopen, file fetch, analyze, and delete APIs
- `backend/app/services/upload_ai_audit.py`
  - centralize LLM-assisted plus heuristic fallback upload auditing
- `backend/app/api/ids.py`
  - expose `GET /api/ids/situation`
  - derive counters and recent attack snapshots from real incidents

### Frontend

- `frontend/src/views/upload/PublicUpload.vue`
  - render real upload gate outcomes
  - show pass vs withheld status clearly
- `frontend/src/views/security/SecuritySandbox.vue`
  - read real quarantine data
  - trigger real backend analysis
  - reopen persisted reports
- `frontend/src/views/security/SecuritySituation.vue`
  - poll real situation telemetry
  - render event-driven map arcs and counters
- `frontend/src/api/upload.ts`
  - align with the actual upload/quarantine payloads
- `frontend/src/api/ids.ts`
  - add the situation response contract

### Documentation

- `specs/006-ids-live-security-center/*`
- `docs/ids-demo-script.md`
- `docs/ids-changelog.md`
- `README.md`

## Validation Snapshot

- `python -m py_compile backend/app/api/upload.py backend/app/api/ids.py backend/app/services/upload_ai_audit.py`
  passed.
- `cd frontend && npm run build`
  passed.
- Local manual walkthrough passed for:
  - suspicious upload withheld into sandbox,
  - benign upload accepted,
  - sandbox list/report visible to `system_admin`,
  - situation page showing the resulting real malware event.
- gstack browser QA confirmed the same operator flow end to end.

## Residual Gaps

- `frontend/src/views/security/SecurityIDS.vue` still intentionally keeps
  demo/test utilities such as demo event filtering, demo injection, and
  `demo_test` rule/package visibility.
- `frontend/src/views/ids/IDSManage.vue` is still present as a legacy file and
  should not be treated as the current main route.
- Exact geo-IP intelligence, automated detonation, and external mature-source
  sync remain outside this slice.
