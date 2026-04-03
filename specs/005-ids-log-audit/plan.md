# Implementation Plan: IDS Log Audit Enhancement

**Branch**: `security-center/feature-ids`  
**Feature**: `005-ids-log-audit`  
**Date**: 2026-04-03

## Technical Context

- Backend: FastAPI + SQLAlchemy
- Frontend: Vue 3 + Element Plus
- Existing model reused: `audit_logs`
- Existing IDS APIs reused: `backend/app/api/ids.py`

## Design Decisions

1. Reuse existing `audit_logs` table and derive `is_ids`/`is_sensitive` at
   query/serialization time, avoiding schema churn.
2. Keep `/api/audit` as single entrypoint and extend it with filtering,
   pagination, summary, and options payload.
3. Use `ids_*` action naming to provide stable IDS-specific slicing.
4. Keep UI compatibility by handling legacy array payload fallback in frontend.

## File Scope

- Backend:
  - `backend/app/api/audit.py`
  - `backend/app/api/ids.py`
- Frontend:
  - `frontend/src/api/audit.ts`
  - `frontend/src/views/audit/AuditLogs.vue`
  - `frontend/src/views/security/SecurityIDSAudit.vue`
  - `frontend/src/views/security/SecurityCenterLayout.vue`
  - `frontend/src/router/routes.ts`
- Documentation:
  - `docs/ids-changelog.md`
  - `specs/005-ids-log-audit/*`

## Validation Plan

1. `python -m py_compile` on updated backend files.
2. `npm run build` in `frontend/`.
3. Manual API spot checks for IDS audit actions and filtered queries.
