# Tasks: IDS Log Audit Enhancement

**Input**: Design docs from `/specs/005-ids-log-audit/`  
**Prerequisites**: spec.md, plan.md, research.md, data-model.md, contracts/  
**Tests**: Backend syntax compile + frontend build + API/UI spot validation.

## Phase 1: Setup

- [X] T001 Update scope and objectives in `specs/005-ids-log-audit/spec.md`
- [X] T002 Document implementation boundaries in `specs/005-ids-log-audit/plan.md`

## Phase 2: Backend Audit Query

- [X] T003 Extend `GET /api/audit` filtering/pagination/summary in `backend/app/api/audit.py`
- [X] T004 Add IDS/sensitive derived flags and filter options in `backend/app/api/audit.py`

## Phase 3: IDS Audit Write Coverage

- [X] T005 Add IDS source sync audit write in `backend/app/api/ids.py`
- [X] T006 Add IDS source package preview/activate audit writes (success + reject) in `backend/app/api/ids.py`
- [X] T007 Add IDS rulepack activate audit writes (success + reject + failed) in `backend/app/api/ids.py`

## Phase 4: Frontend Audit Panel

- [X] T008 Update audit API typings and params in `frontend/src/api/audit.ts`
- [X] T009 Rebuild Chinese-first audit page with filters/tabs/summary/pagination in `frontend/src/views/audit/AuditLogs.vue`

## Phase 5: Validation & Delivery

- [X] T010 Run backend compile checks for updated audit/ids files
- [X] T011 Run frontend production build
- [ ] T012 Update changelog, commit, push `security-center/feature-ids`, and prepare PR note
