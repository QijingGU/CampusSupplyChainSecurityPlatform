# Tasks: IDS Live Security Center Parity

**Input**: `/specs/006-ids-live-security-center/`  
**Prerequisites**: spec.md, plan.md, data-model.md, quickstart.md  
**Validation**: backend compile, frontend build, manual walkthrough, gstack QA

## Phase 1: Setup

- [X] T001 Record the new parity slice in `docs/ids-changelog.md`
- [X] T002 Confirm scope and review boundaries in `specs/006-ids-live-security-center/spec.md` and `plan.md`

## Phase 2: Foundation

- [X] T003 Add persisted quarantine-report helpers in `backend/app/api/upload.py`
- [X] T004 Add situation-summary aggregation in `backend/app/api/ids.py`
- [X] T005 Extend `frontend/src/api/upload.ts` and `frontend/src/api/ids.ts`

## Phase 3: User Story 1 - AI-Gated Public Upload

- [X] T006 Add upload-stage AI audit gating and accepted/quarantine storage split in `backend/app/api/upload.py`
- [X] T007 Add reusable upload audit helper in `backend/app/services/upload_ai_audit.py`
- [X] T008 Update `frontend/src/views/upload/PublicUpload.vue` to render real AI audit results

## Phase 4: User Story 2 - Real Sandbox Analysis

- [X] T009 Implement report reopen plus `POST /api/upload/quarantine/analyze` in `backend/app/api/upload.py`
- [X] T010 Update `frontend/src/views/security/SecuritySandbox.vue` to call the real analyze endpoint
- [X] T011 Render backend-provided report content and metadata in `frontend/src/views/security/SecuritySandbox.vue`

## Phase 5: User Story 3 - Real Situation Telemetry

- [X] T012 Implement `GET /api/ids/situation` in `backend/app/api/ids.py`
- [X] T013 Update `frontend/src/views/security/SecuritySituation.vue` to poll real telemetry and remove random generation
- [X] T014 Clarify derived-map wording in `frontend/src/views/security/SecuritySituation.vue`

## Phase 6: User Story 4 - Traceability

- [X] T015 Document validation steps and residual scope in `docs/ids-changelog.md`
- [X] T016 Sync the implemented slice into `specs/006-ids-live-security-center/*`
- [X] T016a Add operator quickstart guidance in `specs/006-ids-live-security-center/quickstart.md`
- [X] T016b Add the live demo script in `docs/ids-demo-script.md`

## Phase 7: Polish And Verification

- [X] T017 Run backend syntax validation for updated IDS/upload files
- [X] T018 Run frontend production build
- [X] T019 Verify suspicious-upload, sandbox, and situation flows manually against the running app
- [X] T020 Run gstack browser QA against `/upload`, `/security/sandbox`, and `/security/situation`

## Verification Note

- Manual verification covered:
  - suspicious `codex-webshell.php` upload withheld by AI audit,
  - benign `codex-note.txt` upload accepted,
  - sandbox table and report visibility for the quarantined sample,
  - situation page counters and recent incident feed reflecting the withheld
    upload.
- gstack QA confirmed:
  - `POST /api/upload` returns a withheld result for the suspicious sample and a
    release result for the benign sample,
  - `/security/sandbox` shows the quarantined sample with verdict, risk, and
    confidence,
  - `/security/situation` shows a real malware/WebShell incident with detector
    `upload_ai_gate`.
