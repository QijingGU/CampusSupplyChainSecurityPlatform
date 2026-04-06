# Implementation Plan: IDS Upload Audit Modes & Log Audit

## Overview

- **Goal**: Ship explicit dual-mode upload auditing (static when AI is not configured, AI-enhanced when configured), keep startup prompt-driven configuration, emit IDS audit logs, and ship a linked front-end experience.
- **Success**: Uploads remain available in static mode without key, switch to AI-enhanced mode when configured, logs capture every upload/source action, the upload UI shows mode + state flow, and the security center surfaces `/security/log-audit` with counts, filters, and evidence links.

## Architecture

```mermaid
graph LR
  User-->UploadUI[Public Upload UI]
  UploadUI-->UploadAPI[/api/upload]
  UploadAPI-->AuditService[upload_ai_audit]
  AuditService-->StaticEngine[Static Heuristic Guardrail]
  AuditService-->LLMProvider[(LLM, optional)]
  UploadAPI-->AuditLogDB[(AuditLog)]
  UploadUI-->LogAuditView[/security/log-audit]
  LogAuditView-->AuditAPI[/api/ids/log-audit]
  AuditAPI-->AuditLogDB
  Startup[Startup Prompt]
  Startup-->ConfigFile(.env / os env)
```

## Backend

1. **Dual-mode audit gating**
   - Keep static guardrail analysis as a first-class mode when AI is unavailable.
   - Ensure `audit_upload_payload` returns mode-labeled decisions in both paths:
     - `static_only` without LLM configuration,
     - `llm_assisted` when `is_llm_available()` is true.
2. **Startup prompt**
   - Startup prompts whether to enable AI now.
   - If enabled, operator chooses `deepseek` or `kimi` and enters only the API key; the system auto-fills base URL and default model name.
   - If operator declines configuration at boot, continue in static mode instead of blocking upload workflows.
   - `/api/health` reports real AI readiness used by mode selection.
3. **Audit logs**
   - Reuse `backend/app/services/audit.py` to write IDS-relevant entries for upload decisions, source sync/activation, event status updates, and sandbox actions.
   - Keep `GET /api/ids/log-audit` as the dedicated reviewer feed with summary + filters.

## Frontend

1. **Public upload**
   - Show upload stages: `Uploading` -> `Auditing` -> `Accepted` or `Quarantined`.
   - Expose mode badges/text so operators can see `static_only` vs `llm_assisted`.
2. **Security center**
   - Keep `/security/log-audit` route, view, and nav item under `SecurityCenterLayout`.
   - Log view keeps summary cards and table filters (action/user/risk/time) with links to sandbox sample or IDS event via `target_id`.
3. **Types & API**
   - Keep `frontend/src/api/ids.ts` log-audit types/helpers aligned with backend payload.
   - Ensure upload audit mode fields are surfaced for UI rendering.

## Docs & Demo

- Update `docs/ids-changelog.md` with a dated entry describing the dual-mode clarification.
- Update `docs/ids-demo-script.md` with "Scene 0: Configure AI or Continue Static Mode".
- Keep explicit note that Security Situation remains unchanged and out of scope.

## Testing & Validation

1. `python -m py_compile backend/app/api/upload.py backend/app/main.py backend/app/services/upload_ai_audit.py backend/app/api/ids.py`
2. `cd frontend && npm run build`
3. Manual replay:
   - restart backend and test both startup choices (`yes` configure AI / `no` static mode),
   - upload benign and suspicious files, verify UI states + mode labels,
   - open `/security/log-audit` and confirm traceability to sandbox sample by `saved_as`.
