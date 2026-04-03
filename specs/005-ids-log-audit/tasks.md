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
- [X] T009 Rebuild Chinese-first audit pages with filters/summary/pagination in `frontend/src/views/audit/AuditLogs.vue`

## Phase 5: Validation & Delivery

- [X] T010 Run backend compile checks for updated audit/ids files
- [X] T011 Run frontend production build
- [X] T012 Update changelog, commit, push `security-center/feature-ids`, and prepare PR note
- [X] T013 Extend IDS audit dimensions (`ids_domain`, `ids_outcome`) in `backend/app/api/audit.py`
- [X] T014 Upgrade audit UI filters and IDS result visibility in `frontend/src/views/audit/AuditLogs.vue`
- [X] T015 Improve IDS terminology guidance in `frontend/src/views/security/SecurityIDS.vue` for rule source and detector family explanations
- [X] T016 Move IDS audit view into security center with dedicated page `frontend/src/views/security/SecurityIDSAudit.vue`
- [X] T017 Update security navigation and routing for `/security/audit` in `frontend/src/views/security/SecurityCenterLayout.vue` and `frontend/src/router/routes.ts`
- [X] T018 Split generic audit page from IDS audit (exclude IDS rows) via `exclude_ids` in `backend/app/api/audit.py` and `frontend/src/views/audit/AuditLogs.vue`
- [X] T019 Harden IDS page toward production workflow by default-disabling demo actions and polishing “检测场景” terminology in `frontend/src/views/security/SecurityIDS.vue`
- [X] T020 Align spec/task wording with the split audit architecture (`/audit` + `/security/audit`) in `specs/005-ids-log-audit/spec.md` and `specs/005-ids-log-audit/tasks.md`
- [X] T021 Re-run backend/frontend validation and append daily IDS changelog entry in `docs/ids-changelog.md`
- [X] T022 Fix security-center route loading regression for `/security/audit` in `frontend/src/views/security/SecurityCenterLayout.vue`
- [X] T023 Refactor `frontend/src/views/security/SecurityIDSAudit.vue` for readable Chinese copy, stronger contrast, and resilient loading/error handling
