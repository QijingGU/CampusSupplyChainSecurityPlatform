# Feature Specification: IDS Upload Audit Modes & Log Audit

## Problem Statement

- The IDS upload flow needs an explicit, operator-visible mode model:
  - without API key/LLM config, it should run a real static audit path,
  - with API key/LLM config, it should run AI-enhanced audit.
- Operators and auditors also lack a focused log trail for IDS actions, so there is no single source of truth behind an upload-gate decision, source sync, or manual IDS action.
- The public upload experience must clearly expose which mode produced the verdict so reviewers can verify behavior directly.

## User Stories

### Story 1: Explicit dual-mode upload audit

As a security operator,
I want uploads to remain available when AI is not configured while still showing a clear static-audit label,
so that operational workflow stays usable and mode behavior is auditable.

**Acceptance Criteria**
- `backend/app/services/upload_ai_audit.py` returns a valid audit decision in both modes and labels mode as `static_only` or `llm_assisted`.
- Startup `app.main` prompts whether to enable AI now, lets the operator choose `deepseek` or `kimi`, asks only for the API key, auto-fills the provider base URL plus default model name, and still allows static mode when choosing not to configure AI immediately.
- `GET /api/health` reflects the real AI readiness state used by mode selection.
- The upload page shows one consistent terminal state per request; a quarantined result must not also surface as a rejected/network-error state for the same upload.

### Story 2: Prompt before you run

As the on-call engineer,
I want the backend to ask me explicitly whether to enable AI at boot and, if yes, only ask for provider plus API key,
so that I can decide to enable AI now or run static mode for this startup without filling low-level connection details manually.

**Acceptance Criteria**
- The startup hook prints the prompt and writes the selected provider, API key, auto-filled base URL, and auto-filled default model name to `.env` before `uvicorn` listens.
- The demo script records the “Scene 0” preflight and shows both outcomes: static mode and AI-enhanced mode.
- Documentation (changelog and demo script) mentions the new prompt so reviewers can reproduce it.

### Story 3: Audit every IDS action

As an auditor,
I want a dedicated `/security/log-audit` page that surfaces uploads, source syncs, activations, status changes, and sandbox actions,
so I can independently verify that each gate/IDS decision is logged and cross-referenced with the upload trace.

**Acceptance Criteria**
- A backend `GET /api/ids/log-audit` endpoint (or equivalent) exists, filtering `AuditLog` entries by IDS-relevant actions.
- The security-center nav adds “日志审计” and the page shows cards for counts plus a table that can filter by action type, user, and outcome.
- The log view can link back to the quarantined sample or IDS event so operators trace the chain.

## Non-Functional Requirements

- Audit log entries must store `user_id`, `action`, `target_id`, and `detail` for each supported event (`upload_ai_gate`, source sync/activation, event status changes, sandbox operations).
- The upload UI must show distinct states for `uploading`, `auditing`, `accepted`/`quarantined`, and expose the current mode (`static_only` or `llm_assisted`).
- The Windows quick-start / stop path must remain repeatable for demos, with a precise process-state shutdown path for stack instances launched by the root scripts.
- All new routes and docs must be in Chinese + minimal English so they align with the existing UX style.

## Out of Scope

- The Security Situation map remains unchanged; it is still a visualization layer and not part of this slice.
- This spec does not add new runtime detection behavior outside of the log audit and upload context.

## Success Metrics

- Upload requests without configured LLM still complete via static audit mode.
- Upload requests with configured LLM run AI-enhanced audit and are visibly labeled.
- Operators can open `/security/log-audit`, see the recent upload gate entry, and trace it back to the sandbox.
- The demo script and changelog mention the new behavior and preflight step so reviewers can replay the experience.
