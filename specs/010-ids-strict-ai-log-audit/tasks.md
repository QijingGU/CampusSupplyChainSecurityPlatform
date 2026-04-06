# Implementation Tasks: IDS Upload Audit Modes & Log Audit

## Backend Tasks

- [x] Implement dual-mode upload auditing in `upload_ai_audit`:
  - no API key/LLM config -> `static_only`,
  - API key/LLM ready -> `llm_assisted`.
- [x] Keep startup prompt behavior in `app.main`/`llm_startup`:
  - ask whether to enable AI now,
  - if enabled, ask only for `deepseek` / `kimi` selection plus `LLM_API_KEY`, then auto-fill the provider URL and default model,
  - allow service startup in static mode when operator declines at boot.
- [x] Keep `GET /api/ids/log-audit` and IDS audit-log emission for upload decisions, sandbox analysis, source sync/activation, and IDS status actions.

## Frontend Tasks

- [x] Update public upload view to show upload -> audit -> decision states and expose current mode (`static_only` or `llm_assisted`).
- [x] Keep `/security/log-audit` page/route/nav wired under `SecurityCenterLayout`.
- [x] Ensure log-audit rows link back to sandbox/event evidence and remain filterable by action/type/user/time.

## Documentation Tasks

- [x] Update `docs/ids-demo-script.md` to describe startup choice and dual-mode behavior (static vs AI-enhanced).
- [x] Update `docs/ids-changelog.md` with a dated dual-mode clarification entry and scope reminder.
- [x] Keep this spec set (`spec.md`, `plan.md`, `tasks.md`) aligned with:
  - log-audit remains in scope,
  - Security Situation remains out of scope and unchanged.
