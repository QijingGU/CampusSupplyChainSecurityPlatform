# IDS Changelog

This file tracks day-by-day IDS work for the campus security center. Update it
whenever IDS behavior, event handling, detector sources, demo isolation, or
security-center workflows change.

Spec references:
- `specs/006-ids-live-security-center/`
- `specs/007-ids-source-real-sync/`
- `specs/008-ids-runtime-activated-packages/`
- `specs/009-ids-upload-evidence-chain/`
- `specs/010-ids-strict-ai-log-audit/`

## Working Rules

- Add a dated entry on every active development day.
- Keep each entry focused on shipped or reviewable work, not vague intentions.
- Mention affected areas, current risks, and the next step when relevant.
- Push the active IDS branch to GitHub at the end of the day after updating this
  file, unless an unresolved conflict blocks the push.

## 2026-04-08

- Closed the remaining public-upload dev-path gap after release QA:
  - `frontend/src/views/upload/PublicUpload.vue` no longer posts to a stale
    `/api/upload` proxy target when `VITE_API_BASE=/api`,
  - `frontend/src/api/request.ts` now exposes a reusable resolved API URL
    helper, and `frontend/src/api/upload.ts` reuses that helper so anonymous
    upload traffic follows the same live `8166/8167` backend probing logic as
    the authenticated frontend API client,
  - real browser validation confirmed the public upload page now releases a
    safe text file and quarantines a malicious PHP file without regressing into
    the old fake `502 / 上传审计失败` panel.
- Re-ran the IDS/security-center audit after the fix:
  - `cd frontend && npm run build` passed,
  - `python -m py_compile backend/app/api/upload.py backend/app/api/ids.py backend/app/api/audit.py backend/app/main.py backend/app/middleware/ids_middleware.py backend/app/services/ids_engine.py backend/app/services/upload_ai_audit.py` passed,
  - `/api/health` reported `llm_assisted` with `provider=deepseek` and
    `model=deepseek-chat`,
  - real static probes `GET /.env`, `GET /login?user=${jndi:ldap://demo/a}`,
    and `GET /proxy.php?url=<script>alert(1)</script>` all returned `403`,
    with IDS events attributed to `detector_name=suricata-web-prod`,
  - a safe `.txt` upload was released, a malicious `.php` upload was held in
    the sandbox and linked to IDS event `#104`, sandbox report/reanalysis both
    returned real analysis payloads, and `/api/ids/log-audit` showed the
    matching `ids_upload_release`, `ids_upload_quarantine`, and
    `ids_sandbox_analyze` records,
  - fresh browser QA exposed the remaining admin-alert gaps before the
    follow-up fix below:
    `system_admin` still saw event `#111`, the next popup for event `#110`
    appeared about `10325ms` after closing the first one, `跳转 IDS 页面`
    still landed on `/security/ids?event=110&report=1`, `logistics_admin`
    still saw no popup during a 15-second watch window, and both
    `/security/sandbox` and `/security/log-audit` loaded real operator data.
- Closed the remaining admin-alert behavior gaps on the same day:
  - `frontend/src/components/layout/AppLayout.vue` no longer rate-limits queued
    IDS popups to one every 10 seconds; each new high-risk event is shown once,
    and the next queued event appears as soon as the current popup closes,
  - the popup state now tracks a persisted event-id watermark instead of only a
    per-day seen list, so historical unarchived high-risk incidents are not
    replayed again as fresh alerts after a page reload, browser restart, or day
    change,
  - if the operator is already on `/security/ids`, the popup action now keeps
    the route in place and emits an in-page focus event instead of pushing a
    new `?event=...&report=1` route that forced another report run,
  - `frontend/src/views/security/SecurityIDS.vue` now exposes an admin-only
    warning-sound panel with enable/disable, volume, custom-audio import,
    test-playback, and reset-to-default controls, backed by persisted browser
    storage plus IndexedDB audio asset storage,
  - live browser validation on 2026-04-08 confirmed `/security/ids` stayed on
    the same URL while the in-page focus action opened the detail drawer for
    event `#117`, the next queued popup for event `#116` appeared immediately,
    and the imported custom warning sound played for both popups (`media=2` in
    the browser audio probe).


## 2026-04-07

- Historical note: popup timing and `?report=1` route behavior described in the
  validation bullets below were the branch state on 2026-04-07 and were later
  removed by the 2026-04-08 admin-alert closure above.

- Bootstrapped the bundled `suricata-web-prod` manifest/rules fixture into the
  runtime IDS source registry at startup, so fresh offline environments now
  come up with one activated external static rule package instead of waiting
  for manual source setup.
- Tightened request-side runtime blocking:
  - activated external static rules are now the primary interception path, with
    the old inline signatures only retained as a fallback when no runtime
    package is active,
  - malicious SQLi, XSS, and path-traversal probes now cross the block
    threshold and return real HTTP `403` responses,
  - blocked events now persist a structured attack packet view, matched static
    rules, decision basis, and AI/static analysis mode for the security-center
    detail/report surfaces.
- Deepened sandbox explainability:
  - quarantine reports now persist `decision_basis`, `hold_reason_summary`,
    matched indicators, provider/mode fields, and full recommended actions,
  - sandbox and IDS evidence chains can now explain why a file was held and
    whether that decision came from static rules or LLM-assisted analysis.
- Fixed the public upload result-state bug in
  `frontend/src/views/upload/PublicUpload.vue`:
  - quarantined uploads now stay in the quarantined state after the audit
    dialog closes,
  - closing the Element Plus dialog no longer sends the same request through the
    outer error path and paints a fake `上传审计执行失败 / 网络错误` panel on top of a
    real quarantine result,
  - rejected requests now explicitly clear `lastResult` before showing the
    error panel so upload outcomes do not mix across states.
- Tightened the Windows quick-start lifecycle:
  - `start-ids-dev.ps1` now uses `Start-Process -PassThru` and records the
    quick-started backend/frontend wrapper PowerShell PIDs in
    `.ids-dev-processes.json`,
  - `stop-ids-dev.ps1` now stops recorded quick-start processes first and only
    falls back to the old port / command-line scan when the recorded PIDs are
    gone,
  - `README.md` and `docs/ids-demo-script.md` now document the stop command and
    the new process-state file behavior.
- Follow-up fix on the same day for the quick-start regression:
  - fixed `start-ids-dev.ps1` so an empty previous-process list no longer
    collapses to `$null` before `Add(...)`,
  - fixed state serialization so the recorded process list is written as a real
    array instead of tripping over `Generic.List` expansion,
  - fixed both start/stop scripts to avoid the PowerShell built-in `PID`
    variable name collision while reading recorded process IDs,
  - direct regression validation confirmed one quick-start run now prints both
    `Backend window started` and `Frontend window started`, writes
    `.ids-dev-processes.json`, and the stop script consumes that state file on
    shutdown instead of dropping straight to fallback scan mode.
- Validation for this slice:
  - `cd frontend && npm run build`
  - PowerShell syntax parse passed for `start-ids-dev.ps1` and
    `stop-ids-dev.ps1`
- Closed the admin high-risk warning loop and the blocked local-dev path on the
  same day:
  - `frontend/src/components/layout/AppLayout.vue` now polls blocked,
    unarchived IDS events scoring `>= 80` and shows an admin-only global popup
    with `关闭` / `今日不再弹出` / `跳转 IDS 页面`,
  - the popup queue deduplicates already-seen events per day, enforces a
    10-second interval between queued alerts, and includes upload quarantine
    incidents because they already enter the IDS queue as blocked high-risk
    events,
  - `frontend/src/api/request.ts` now treats dev-time `/api` as a signal to
    probe `8166/8167` directly for local browser sessions, instead of pinning
    the frontend to the Vite proxy target,
  - `backend/app/config.py` now allows `5174` and `8167` in local CORS origins,
    and `backend/app/middleware/ids_middleware.py` now bypasses `OPTIONS`
    preflight requests so real browser auth/dashboard traffic is not broken by
    IDS inspection,
  - `backend/app/services/ids_engine.py` now skips incomplete runtime tokens
    such as bare `://`, derives a stricter Log4j projection
    (`${` + `jndi` + `://`) for the ET rules that depend on `pcre`, and
    whitelists the real login path `/api/user/login` so credentials are not
    dragged into IDS alert generation.
- Validation for the admin-alert + local-dev repair:
  - `python -m py_compile backend/app/config.py backend/app/middleware/ids_middleware.py backend/app/services/ids_engine.py`
  - `cd frontend && npm run build`
  - direct engine validation confirmed normal `/api/user/login` and
    `/api/dashboard` traffic no longer match IDS, while
    `GET /login?user=${jndi:ldap://demo/a}` still matches `jndi_injection`
    at score `100`,
  - Playwright browser validation on `2026-04-07` confirmed:
    `system_admin` sees the popup, `关闭` waits out the 10-second gap before the
    next queued event, `今日不再弹出` suppresses the rest of the day for that
    browser, `跳转 IDS 页面` lands on the targeted report route, and
    `logistics_admin` does not receive the popup.
- Follow-up live validation on the same branch rechecked the exact admin alert
  controls with current incidents:
  - `system_admin` received the next popup about `10.327s` after closing the
    first one
  - `浠婃棩涓嶅啀寮瑰嚭` stayed silent for the next 12 seconds of observation
  - `璺宠浆 IDS 椤甸潰` landed on `/security/ids?event=87&report=1`
  - `logistics_admin` still saw no popup during a 15-second watch window
- Documentation sync for the still-open IDS branch package:
  - refreshed `README.md` so the shipped security-center slice now explicitly
    mentions `/security/log-audit`, request-side runtime matching, upload trace
    in IDS reports, and rule-package provenance at runtime,
  - refreshed `docs/ids-demo-script.md` so the setup includes the log-audit
    page and the demo flow now has a runtime-request extension after source
    activation,
  - kept the Spec Kit trail aligned by referencing the active `006` through
    `010` IDS specs in this changelog before pushing the remaining branch work.
- Current note:
  - the stop script still keeps the fallback port scan for older demo sessions
    launched before PID tracking existed, but the main path is now precise
    process-state shutdown instead of pure heuristics.

## 2026-04-06

- Closed the upload-to-IDS evidence-chain gap inside the active security-center
  workflow:
  - quarantined upload incidents now persist richer evidence payloads including
    `sha256`, file size, and storage location in the IDS event trace,
  - `GET /api/ids/events/{event_id}/report` now returns a structured
    `upload_trace` block and includes `Upload Audit Trace` in the generated
    markdown report,
  - `frontend/src/views/security/SecurityIDS.vue` now shows upload-audit
    evidence in the event drawer and adds a direct `打开沙箱报告` jump for
    upload-gated incidents,
  - `frontend/src/views/security/SecuritySandbox.vue` now supports route-based
    deep links so `/security/sandbox?saved_as=<sample>&report=1` opens the
    targeted persisted report instead of dropping the operator into a generic
    list view.
- Validation for the evidence-chain slice:
  - `python -m py_compile backend/app/api/ids.py backend/app/api/upload.py`
  - `cd frontend && npm run build`
  - direct backend validation confirmed the latest `upload_ai_gate` incident now
    serializes `saved_as=ab45cc6b_codex-webshell.php`,
    `audit_verdict=quarantine`, `audit_risk_level=high`, and a non-empty
    `upload_trace`,
  - direct report validation confirmed `get_event_report(...)` includes
    `report.upload_trace` and the markdown `Upload Audit Trace` section.
- Residual scope after this slice:
  - the report modal now carries the upload trace in markdown/report payloads,
    but the visual report cover remains optimized for generic IDS incidents.

- Closed the biggest remaining flower-rack in `frontend/src/views/security/SecurityIDS.vue` by making IDS source sync real instead of status-only.
- Backend changes for the real sync slice:
  - added `sync_endpoint` to IDS source records,
  - added sync-attempt metadata for `package_version`, `package_intake_id`, and resolved manifest path,
  - added package-intake artifact fields for `artifact_path`, `artifact_sha256`, `artifact_size_bytes`, and `rule_count`,
  - added `backend/app/services/ids_source_sync.py` to load and validate local manifest files,
  - replaced the old `Metadata refresh completed.` sync stub with real manifest/artifact intake.
- Frontend changes for the real sync slice:
  - source create/edit now captures `sync_endpoint`,
  - the IDS source row shows the saved manifest path,
  - latest sync state now exposes imported package version plus resolved manifest path,
  - latest package preview now exposes `rules=<n>` and a shortened SHA-256,
  - the history dialog now includes a `Sync Audit` section so sync attempts and package intake can be reviewed together.
- Added deterministic review fixtures:
  - `backend/app/data/ids_source_sync/suricata-web-prod.manifest.json`
  - `backend/app/data/ids_source_sync/suricata-web-prod.rules`
- Validation for this slice:
  - `python -m py_compile backend/app/api/ids.py backend/app/models/ids_source.py backend/app/models/ids_source_package.py backend/app/schema_sync.py backend/app/services/ids_source_packages.py backend/app/services/ids_source_sync.py`
  - `cd frontend && npm run build`
  - direct API validation confirmed `suricata-web-prod` sync returns `package_version=2026.04.06`, `rule_count=4`, the artifact path, and persisted SHA-256 metadata,
  - gstack browser validation confirmed `/security/ids` now shows the sync endpoint, allows `执行同步`, and records a second sync attempt plus a second artifact-backed intake row.
- Residual scope after this slice:
  - `sync_mode=scheduled` still means scheduler-managed metadata, not an in-app cron implementation,
  - `demo`/`test` incident tooling and the legacy `IDSManage.vue` compatibility surface still remain outside this slice.

- Follow-up backend closure on the same day:
  - `backend/app/services/ids_engine.py` now loads the latest activated `web` package artifacts from trusted, non-disabled sources into a bounded runtime cache,
  - `backend/app/middleware/ids_middleware.py` now persists runtime-matched events with the activated source metadata instead of always writing `inline_request_matcher / legacy-inline`,
  - `backend/app/api/ids.py` now refreshes the runtime cache after source updates and package activations so operator changes take effect promptly.
- Validation for the runtime closure:
  - `python -m py_compile backend/app/services/ids_engine.py backend/app/middleware/ids_middleware.py backend/app/api/ids.py`
  - direct runtime validation confirmed `scan_request_detailed("GET", "/runtime-probe", "sample=../", ...)` returns `detector_name=suricata-web-prod`, `source_version=2026.04.06`, and `source_rule_id=9001003`,
  - direct HTTP validation confirmed `GET /runtime-probe?sample=../` persisted an IDS event with `source_classification=external_mature` and the same activated package metadata while still returning normal application control flow (`404` in the validation environment).
- Additional residual scope for the runtime bridge:
  - only activated `web` artifacts currently feed the lightweight runtime matcher, and the parser only extracts `content:"..."` tokens rather than executing a full Suricata engine.
- Final cleanup and operator-flow closure on the same day:
  - removed the remaining demo trigger entry points from the active `frontend/src/views/security/SecurityIDS.vue` reviewer page so the security-center IDS surface now stays on real incidents, real source sync, real package activation, and real upload evidence,
  - added direct navigation from `frontend/src/views/security/SecurityLogAudit.vue` into `/security/sandbox?saved_as=...&report=1` and `/security/ids?event=...&report=1`, closing the audit-to-evidence loop for upload and IDS actions,
  - updated `frontend/src/api/request.ts` and `docs/ids-demo-script.md` so the local startup path explicitly supports backend port `8166` or `8167` and the demo script uses the real IDS audit action names such as `ids_upload_quarantine`,
  - added root quick-start launchers `start-ids-dev.ps1` and `start-ids-dev.bat` so Windows demos can open backend/frontend in separate windows, preserve the interactive DeepSeek/Kimi startup prompt, auto-select `8166/8167`, and initialize `backend/supply_chain.db` when it is missing,
  - updated `README.md` and `docs/ids-demo-script.md` to make the quick-start launcher the preferred IDS demo boot path,
  - simplified the AI startup interaction so operators now only choose `deepseek` or `kimi` and paste the API key, while the system auto-fills the provider base URL and default model name,
  - moved the interactive AI choice into `start-ids-dev.ps1` so each quick-start launch explicitly asks again even when `backend/.env` already contains a saved key, while the backend process itself receives the selected mode as startup flags.

## 2026-04-01

- Initialized Spec Kit in the repository for IDS refactor governance and
  planning.
- Added the project constitution with explicit rules for detector reuse,
  demo/data separation, auditability, daily changelog updates, and daily remote
  sync.
- Created the first IDS refactor specification focused on replacing
  demo-dominant behavior with real event workflows and mature detection-source
  integration.
- Completed the first foundational backend slice:
  - extended the IDS event model and schema patching for event origin, source
    provenance, response result, and correlation metadata,
  - added a dedicated ingestion helper service,
  - rewrote the IDS middleware and IDS API onto a cleaner normalized incident
    shape,
  - updated frontend IDS API types to match the new fields.
- Validation:
  - Python syntax compilation passed for the updated backend files.
  - Frontend dependencies were installed locally in `frontend/` and
    `npm run build` now passes after rerunning the build outside the sandboxed
    environment.
- Completed the current security-center UI slice in
  `frontend/src/views/security/SecurityIDS.vue`:
  - defaulted stats, trend, and list scope to `real` incidents,
  - added explicit `event_origin` and `source_classification` filters so demo
    and test data are reviewed deliberately instead of polluting operational
    metrics,
  - surfaced detector provenance and response outcome details in the table and
    event drawer.
- Mature-source status for this slice:
  - currently supported in the normalized model: transitional in-process web
    matcher metadata, project demo seeds, and the documented contract for future
    upstream `external_mature` providers,
  - the backend now accepts the first normalized ingestion contract at
    `POST /api/ids/events/ingest`, including bounded correlation by
    `event_fingerprint` or `correlation_key` within a 24-hour active review
    window.
- Added quickstart execution examples for real-event ingestion, demo-event
  ingestion, and current correlation expectations in
  `specs/001-ids-refactor/quickstart.md`.
- Explicitly downgraded remaining demo-heavy wording:
  - the security-center IDS page now labels the seeded action as demo-only and
    reminds reviewers that it does not count toward real metrics,
  - the security situation screen now states that it is a visualization view and
    not the authoritative real-incident reporting surface,
  - the legacy `frontend/src/views/ids/IDSManage.vue` page now carries a
    deprecation note pointing reviewers to `/security/ids`.
- Validation:
  - Python compilation still passes for the updated IDS backend files after the
    ingestion endpoint was added.
  - Frontend `npm run build` passes after the IDS, situation, and legacy-page
    wording updates.
- Quickstart validation executed locally against the app stack:
  - initialized the backend database with `python init_db.py`,
  - logged in as `system_admin`,
  - ingested one normalized real event through `POST /api/ids/events/ingest`,
  - repeated the same real ingest and confirmed correlation reused the same
    incident with `linked_event_count=2`,
  - ingested one normalized demo event and confirmed
    `counted_in_real_metrics=false`,
  - confirmed real-only stats remained isolated from demo stats,
  - updated the real incident to `mitigated`, then archived it and confirmed the
    preserved `review_note` plus archived response state in the event payload.
- Cleanup pass:
  - clarified normalized-ingest comments in
    `backend/app/api/ids.py`,
  - clarified transitional/local matcher wording in
    `backend/app/services/ids_engine.py`,
  - replaced one stale demo-only API comment in `frontend/src/api/ids.ts`.
- Routing review:
  - `frontend/src/router/routes.ts` still routes the active reviewer experience
    to `frontend/src/views/security/SecurityIDS.vue`,
  - `/ids` remains a redirect to `/security/ids`,
  - `frontend/src/views/security/SecurityCenterLayout.vue` navigation stays
    consistent with the routed security-center entry points.
- Next step: prepare a reviewable commit/push on `security-center/feature-ids`
  and leave the branch ready for human review.
- Delivery:
  - committed the current IDS refactor slice as
    `feat: normalize ids incident workflow`,
  - pushed `security-center/feature-ids` to GitHub for review.
- Began the second IDS slice at `specs/002-ids-source-operations/`:
  - audited the new source-operations spec, plan, tasks, contract, and
    quickstart against the IDS constitution,
  - confirmed the Spec Kit scripts can stay compatible with the team branch
    workflow by setting `SPECIFY_FEATURE=002-ids-source-operations` before
    running prerequisite checks,
  - tightened the source-operations docs so `demo_test` source records stay
    distinct from production `custom_project` or `external_mature` sources,
  - clarified that skipped sync attempts do not satisfy freshness and do not
    convert never-synced sources into healthy sources,
  - expanded `specs/002-ids-source-operations/quickstart.md` with explicit
    API-level validation steps for source registration, source listing, and sync
    tracing.
- Completed the first implementation pass for
  `specs/002-ids-source-operations/`:
  - added `backend/app/models/ids_source.py` with persisted source registry and
    sync-attempt tables,
  - updated `backend/app/schema_sync.py` so existing deployments create the new
    IDS source tables safely,
  - added `backend/app/services/ids_source_ops.py` for source-key normalization,
    health derivation, recent incident linkage, and sync-attempt summaries,
  - extended `backend/app/api/ids.py` with `GET/POST/PUT /api/ids/sources` and
    `POST /api/ids/sources/{source_id}/sync`,
  - extended `frontend/src/api/ids.ts` and
    `frontend/src/views/security/SecurityIDS.vue` with a source-operations panel,
    source registry form, health table, and sync actions.
- Validation for the current slice:
  - Python `py_compile` passes for the updated IDS source model, service,
    schema, and API files,
  - frontend `npm run build` passes after the source-operations UI changes,
  - local `TestClient` validation confirmed:
    - trusted source creation returns `never_synced` before its first refresh,
    - `demo_test` sources remain distinct from trusted production-oriented
      records,
    - successful sync returns `result_status=success` and transitions the source
      to `healthy`,
    - a source updated to `operational_status=failing` returns
      `result_status=failed` and remains visibly `failing`,
    - a `demo_test` source with `sync_mode=not_applicable` returns
      `result_status=skipped`,
    - ingesting a real IDS event with `detector_name=source_key` increments the
      source's recent incident linkage count.
- Cleanup pass:
  - clarified normalized ingest/source-registry boundary wording in
    `backend/app/api/ids.py`,
  - clarified source-registry provenance comments in
    `backend/app/services/ids_ingestion.py`,
  - added explicit source-operations payload notes in `frontend/src/api/ids.ts`.
- Remaining gaps:
  - interactive browser click-through of the new source panel is still pending;
    current UI validation is based on build success plus API-level verification,
  - final cleanup/commit/push for this slice is still pending.
- Delivery:
  - committed the current source-operations slice as
    `feat: add ids source operations`,
  - pushed `security-center/feature-ids` to GitHub at commit `afce70a`.
- Next step: finish `T020` by running an interactive browser click-through of
  the new source panel, then re-audit the implemented
  `002-ids-source-operations` slice for any last UI-level gaps.
- Started the next IDS planning slice at `specs/003-ids-source-package-intake/`:
  - defined the next gap after source operations as trusted package preview,
    activation, and package-history traceability,
  - kept the new slice aligned with mature-source reuse rather than expanding
    local matcher logic,
  - documented the first `003` spec, plan, research, data model, contract,
    quickstart, and tasks set for later implementation.
- Completed the first implementation pass for
  `specs/003-ids-source-package-intake/`:
  - added `backend/app/models/ids_source_package.py` with package-intake and
    package-activation tables,
  - updated `backend/app/schema_sync.py` with package table creation plus a
    compatibility migration so `ids_source_package_intakes.source_id` can stay
    nullable for rejected previews,
  - added `backend/app/services/ids_source_packages.py` for package version
    normalization, version comparison, preview summaries, and package history
    lookup,
  - extended `backend/app/api/ids.py` with
    `POST /api/ids/source-packages/preview` and package-aware source
    serialization,
  - extended `frontend/src/api/ids.ts` and
    `frontend/src/views/security/SecurityIDS.vue` with package preview types,
    preview dialog, and source-table package summary rendering.
- Validation for the current `003` pass:
  - Python `py_compile` passes for the updated package model, service, schema,
    and IDS API files,
  - frontend `npm run build` passes after the package-preview UI changes,
  - local API validation confirmed:
    - a known source package preview returns `intake_result=previewed` with
      `version_change_state=newer`,
    - a missing `source_key` preview returns HTTP 400 but still persists a
      rejected package intake row with `source_id=NULL`,
    - source listing still returns package-aware summary fields without
      breaking the existing source-operations response shape.
- Completed the `003` activation workflow (`US2`):
  - finished `POST /api/ids/source-packages/activate` so reviewed intake
    records can create activation history and update the intake result to
    `activated`,
  - tightened `frontend/src/views/security/SecurityIDS.vue` so the activation
    dialog shows the exact candidate package, the row-level `Activating...`
    state only appears during the real request, and the latest package result
    plus trust classification stay visible in the source table,
  - kept `demo_test` packages visibly separate in the UI and blocked them from
    being activated as trusted coverage.
- Validation for the activation pass:
  - Python `py_compile` still passes for `backend/app/api/ids.py`,
    `backend/app/models/ids_source_package.py`,
    `backend/app/services/ids_source_packages.py`, and
    `backend/app/schema_sync.py`,
  - frontend `npm run build` passes after the activation UI changes,
  - local `TestClient` validation confirmed:
    - a reviewed package for `codex-activation-20260401` activates successfully
      and the source listing shows `active_package_version=2026.04.01`,
    - a `demo_test` preview remains previewable for review but activation is
      rejected with HTTP 400 and
      `demo_test packages cannot be activated as trusted coverage`.
- Audit follow-up for `003`:
  - found and fixed one traceability gap where failed activation attempts were
    rejected but not persisted for later review,
  - `POST /api/ids/source-packages/activate` now updates the intake record to
    `failed` with operator-visible detail when a rejected activation path is
    attempted.
- Validation for the audit fix:
  - local `TestClient` validation confirmed the latest intake on
    `codex-activation-audit-20260401080137` now shows
    `intake_result=failed` and keeps the rejection reason after a blocked
    `demo_test` activation attempt, while the previously activated trusted
    package remains the active version.
- Completed the `003` package-history slice (`US3`):
  - added `GET /api/ids/source-packages` so source-specific package history can
    be queried with recent intakes and recent activations,
  - extended `frontend/src/api/ids.ts` and
    `frontend/src/views/security/SecurityIDS.vue` with a source `History`
    action, a package-history dialog, and visible inline package-result tags in
    the source table,
  - updated `specs/003-ids-source-package-intake/quickstart.md` with the exact
    validation path for activation success, demo/test rejection visibility, and
    source-history review.
- Validation for the package-history pass:
  - Python `py_compile` passes for the updated package-history backend files,
  - frontend `npm run build` passes after the history dialog changes,
  - local `TestClient` validation confirmed:
    - `GET /api/ids/source-packages?source_id=<id>&limit=5` returns both
      `recent_intakes` and `recent_activations`,
    - the validated source `codex-history-20260401080652` shows
      `active_package_version=2026.04.03`,
    - the same history payload preserves a latest failed `demo_test` intake and
      still shows the earlier trusted activation in `recent_activations`.
- Cleanup pass:
  - tightened package-history wording in `backend/app/api/ids.py`,
  - clarified the bounded reviewer-facing history query note in
    `backend/app/services/ids_source_packages.py`,
  - updated the shared IDS API type comment in `frontend/src/api/ids.ts` so it
    covers both source operations and package history.
- Quickstart validation progress for `T020`:
  - completed the API-level quickstart flow for `003` with a fresh validation
    source,
  - confirmed:
    - trusted preview returns `version_change_state=newer`,
    - an invalid preview fails with actionable validation detail
      (`package_version is required`),
    - an unknown-source preview is persisted as `rejected` with `source_id=NULL`,
    - trusted activation returns `result_status=activated` and updates
      `active_package_version=2026.04.04`,
    - blocked `demo_test` activation keeps a latest failed intake while package
      history still shows the last trusted activation.
  - frontend production build still passes, but a true browser click-through of
    the security-center dialogs is still pending because this session has not
    executed interactive UI automation against the live page yet.
- UI polish pass for the IDS source/package panel:
  - converted the visible source-operation and package-intake workflow copy in
    `frontend/src/views/security/SecurityIDS.vue` from English-heavy wording to
    Chinese-first labels, buttons, dialogs, and state text,
  - tightened the source-operations card styling so the package workflow reads
    more like an operator panel than a generic table block,
  - kept the current technical values and API payloads unchanged while aligning
    the reviewer-facing language with the project's Chinese UI preference.
- Validation for the UI polish pass:
  - frontend `npm run build` still passes after the Chinese-first UI update and
    source/package styling adjustments.
- Manual UI validation completed for `003` on the live security-center page:
  - verified the source row `Manual UI Validation Source / manual-ui-20260401`
    can preview `2026.04.10`, then activate it successfully so the row shows
    `当前激活包：2026.04.10`,
  - verified the same source history dialog shows the correct source key,
    current active package, recent intake records, and recent activation
    records,
  - verified a `demo_test` package preview succeeds for review but leaves the
    `激活` action unavailable in the UI, preserving the trusted active package
    version instead of overwriting it.
- Delivery for the current `003` slice:
  - marked `T021` complete after preparing the reviewable commit
    `c405c79 feat: complete ids source package intake workflow`,
  - pushed `security-center/feature-ids` to GitHub so the branch is ready for a
    PR into `security-center/collab-setup`.

## 2026-04-05

- Started a new Spec Kit parity slice at
  `specs/006-ids-live-security-center/` focused on replacing the most visible
  demo-heavy security-center behaviors with backend-driven workflows.
- Implemented backend parity endpoints:
  - added real quarantine-analysis reporting in `backend/app/api/upload.py`
    with persisted sidecar report metadata for quarantined files,
  - added `GET /api/ids/situation` in `backend/app/api/ids.py` so the situation
    page can render real incident-driven telemetry instead of random attacks.
- Updated frontend API contracts:
  - aligned `frontend/src/api/upload.ts` with the real quarantine analysis and
    latest-report payloads,
  - extended `frontend/src/api/ids.ts` with the live situation response shape.
- Reworked the two security-center pages with the largest demo gap:
  - `frontend/src/views/security/SecuritySandbox.vue` now runs the real backend
    quarantine analysis flow and reloads persisted report metadata instead of
    relying on synthetic `local_only` samples,
  - `frontend/src/views/security/SecuritySituation.vue` was rebuilt to poll
    `GET /api/ids/situation`, render real counters and recent events, and label
    map coordinates as IP-derived approximations rather than exact geo
    intelligence.
- Validation:
  - backend `python -m py_compile backend/app/api/upload.py backend/app/api/ids.py` passes,
  - frontend `npm install` completed in `frontend/`,
  - frontend `npm run build` passes after the sandbox/situation parity changes.
- Manual QA replayed the control loop on 2026-04-05:
  - gstack browse uploaded `tmp/codex-webshell.php`, which returned the “文件已扣留到安全沙箱” banner, generated an IDS event linked to `detector_name=upload_ai_gate`, and made the sample row, AI verdict, and persisted report visible in `/security/sandbox` plus `/security/situation`.
  - `/security/sandbox` now reuses the persisted report when the drawer opens, showing verdict, risk, confidence, SHA-256, and indicator list, while `/security/situation` fetched `GET /api/ids/situation` output such as `累计阻断攻击 1`, `当前活跃威胁 1`, and the `127.0.0.1 ... WebShell ... upload_ai_gate` attack card derived from the real incident.
  - gstack browse also uploaded the benign `tmp/codex-note.txt` sample, which showed the accepted UI state, emitted a normal public URL, and never appeared in the sandbox.
- Remaining gap after this slice:
  - IDS source sync in the security-center source panel still remains a lighter
    metadata workflow rather than a full external mature-source sync process.
  - `frontend/src/views/security/SecurityIDS.vue` is still the active IDS page,
    but it intentionally retains demo/test helpers such as demo event filters,
    demo injection, and `demo_test` package visibility.
  - `frontend/src/views/ids/IDSManage.vue` remains a legacy compatibility page
    and is not the current security-center workflow.
- Follow-up sync for the same slice:
  - `frontend/src/views/upload/PublicUpload.vue` is now part of the shipped IDS
    story and shows real AI upload verdicts instead of demo-only warning copy.
  - backend validation also includes
    `backend/app/services/upload_ai_audit.py`.
  - a later local replay through gstack confirmed the current counts reached
    `累计阻断攻击 2` and `当前活跃威胁 2` after another quarantined WebShell upload,
    while `tmp/codex-note.txt` still passed and returned a public accepted-file
    URL.

## 2026-04-06 (Mode Clarification)

- Updated IDS upload behavior to explicit dual-mode audit:
  - if API key/LLM config is missing, uploads still run under clearly labeled `static_only` audit mode,
  - if API key/LLM config is present, uploads run under `llm_assisted` AI-enhanced mode.
- Added provider path for external model testing:
  - startup prompt now supports `deepseek` and `kimi`,
  - default provider preference is now `deepseek`, while `kimi` can be selected interactively at startup.
- Updated startup expectation:
  - before service starts, operator is prompted whether to input/update `LLM_API_KEY` or `LLM_BASE_URL` now,
  - choosing not to configure at boot keeps the platform in static audit mode instead of blocking upload workflows.
- Scope reminder for this update:
  - `/security/log-audit` remains part of the shipped IDS workflow and audit chain,
  - `frontend/src/views/security/SecuritySituation.vue` remains out of scope and unchanged in this round.

## 2026-04-07

- Note: This historical strict-gate entry is superseded by `2026-04-06 (Mode Clarification)` above, which defines the current behavior (`static_only` without key, `llm_assisted` with key).

- Replaced the security-center request-side static bundle with a curated ET Open Suricata package:
  - added `backend/app/data/ids_source_sync/sync_suricata_web_prod.py` to pull the official ET Open archive and regenerate the local `suricata-web-prod` artifact,
  - refreshed the runtime manifest so `/security/ids` can show the package as an externally sourced static ruleset instead of a hand-written demo list.
- Hardened runtime rule execution so the bundled rules now behave like grouped upstream signatures instead of loose token matches:
  - `backend/app/services/ids_engine.py` now decodes Suricata hex content, keeps one runtime rule per upstream rule, and requires the selected content chain to match together before the request is blocked,
  - validated examples now include `/.env`, cookie-based `UNION SELECT`, `${jndi:ldap://...}`, `/proxy.php?url=<script>...`, and `fetchLogFiles` path-traversal probes, all of which cross the real request-side `403` gate and persist rule provenance.
- Finished the last visible fake-analysis cleanup on the active IDS and sandbox pages:
  - `/security/ids` now surfaces backend-supplied `Matched Static Rules`, `Attack Packet`, `Decision Source`, and backend markdown reports, while the AI processing dialog was changed from staged fake progress to a truthful “waiting for backend” state,
  - `/security/sandbox` now reuses the persisted report when available, shows why the file was held, which static indicators fired, the AI/static mode, the linked IDS event id, and the recommended actions instead of a local-only narrative.

- Hardened the AI upload gate with strict validation:
  - `backend/app/services/upload_ai_audit.py` no longer returns fallback heuristics; missing LLM configuration or invalid responses now surface as outright rejections so every verdict truly comes from the configured AI provider,
  - the startup hook in `backend/app/main.py` now prompts the operator before spinning up to ask whether to enter or refresh `LLM_API_KEY` / `LLM_BASE_URL`, and `/api/health` now reports `llm_configured` via the same `is_llm_available()` logic that gates uploads,
  - `docs/ids-demo-script.md` calls out the pre-launch configuration step and makes clear that the upload gate is intentionally strict (the Security Situation page remains untouched by this slice).
- Added an IDS-only audit trail and UI surface:
  - backend audit logging now records upload gating, source sync/activation, analysis queues, and manual IDS actions so the new `/security/log-audit` view can explain what changed, who touched it, and when,
  - the security-center navigation links directly to that page so operators can filter by action, risk, and timestamp without leaving the IDS workflow.
- Finished the real-content cleanup on the active IDS reviewer page:
  - `frontend/src/views/security/SecurityIDS.vue` no longer carries hidden demo trigger buttons, aggregate demo reports, or the demo-only evidence timeline dialog,
  - the page now stays on real incidents, real source/package operations, real upload evidence, and jump links into the sandbox,
  - remaining non-production package classifications are still persisted as `demo_test` internally for compatibility, but the reviewer-facing text now presents them as `实验室验证` instead of demo wording.
- Documented the real upload state machine:
  - the public upload experience now communicates upload → AI audit → decision states clearly and surfaces explicit errors when the gate rejects a file because AI is not configured,
  - `specs/010-ids-strict-ai-log-audit/` captures the constitution, plan, and task breakdown for this “dual-mode upload audit + startup prompt + log audit + live upload flow” change so reviewers can trace the shipped behavior.

- Follow-up hardening and live verification for the same slice:
  - `backend/app/services/ids_engine.py` now filters low-signal Log4j/JNDI Suricata tokens during runtime-pattern derivation so normal internal requests such as `/api/user/login` or `/api/ids/events` no longer trip `jndi_injection` by accident, while real payloads such as `${jndi:ldap://...}` still match and block,
  - `frontend/src/api/request.ts` now chooses the backend probe order from the current Vite port, preferring `8167` when the frontend is running on `5174/4174`, and uses direct `fetch(.../health)` probing so local dev does not silently fall back to the wrong backend,
  - the admin-only popup queue in `frontend/src/components/layout/AppLayout.vue` was revalidated with real upload incidents instead of seed data: two quarantined PHP uploads produced IDS events `#77` and `#76`, `system_admin` received the second popup about `10.67s` after closing the first, and `logistics_admin` still received no popup during a 12-second watch after a later high-risk upload event.

