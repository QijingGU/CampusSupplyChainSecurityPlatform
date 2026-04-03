# IDS Changelog

This file tracks day-by-day IDS work for the campus security center. Update it
whenever IDS behavior, event handling, detector sources, demo isolation, or
security-center workflows change.

## Working Rules

- Add a dated entry on every active development day.
- Keep each entry focused on shipped or reviewable work, not vague intentions.
- Mention affected areas, current risks, and the next step when relevant.
- Push the active IDS branch to GitHub at the end of the day after updating this
  file, unless an unresolved conflict blocks the push.

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

## 2026-04-03

- Synced workspace by recloning the latest repository snapshot from
  `origin` and restoring work on `security-center/feature-ids`.
- Audited completed `003-ids-source-package-intake` artifacts and confirmed all
  tasks are marked done in `specs/003-ids-source-package-intake/tasks.md`.
- Started the next IDS slice at
  `specs/004-ids-mature-rulepack-adoption/` to prioritize mature static
  rulepack reuse over expanding ad hoc local signatures.
- Added `004` specification artifacts:
  - `spec.md` with catalog/activation/history user stories,
  - `plan.md` with constitution-aligned scope and file boundaries,
  - `research.md`, `data-model.md`, `contracts/ids-rulepack-adoption.md`,
    `quickstart.md`, and `tasks.md`,
  - checklist at
    `specs/004-ids-mature-rulepack-adoption/checklists/requirements.md`.
- Task execution status:
  - completed `T001-T003` for `004`,
  - next implementation target is `T004-T007` (rulepack storage, services, and
    listing API).
- Completed backend implementation pass for `004` rulepack adoption:
  - added rulepack runtime state + activation audit models in
    `backend/app/models/ids_rulepack.py`,
  - extended `backend/app/schema_sync.py` and `backend/app/models/__init__.py`
    so runtime state and activation tables are created with IDS schema updates,
  - added curated mature rulepack service in
    `backend/app/services/ids_rulepacks.py`,
  - rewired `backend/app/services/ids_engine.py` to use active runtime
    rulepack signatures rather than fixed local-only constants,
  - updated `backend/app/middleware/ids_middleware.py` to stamp
    `source_version=rulepack:<active_key>` for inline matcher events,
  - added rulepack APIs in `backend/app/api/ids.py`:
    - `GET /api/ids/rule-packs`,
    - `POST /api/ids/rule-packs/activate`,
    - `GET /api/ids/rule-packs/activations`.
- Frontend API typing support added in `frontend/src/api/ids.ts`:
  - rulepack catalog response types,
  - activation payload/response types,
  - activation history response types.
- Security-center UI integration completed for rulepack operations in
  `frontend/src/views/security/SecurityIDS.vue`:
  - added active runtime rulepack strip and refresh action,
  - added rulepack list table with trust tags, metadata, and activate action,
  - linked page actions to new rulepack catalog/activation/history APIs.
- Validation:
  - Python `py_compile` passes for updated/new backend files,
  - frontend `npm run build` passes after installing dependencies (`npm install`),
  - local TestClient smoke flow confirms:
    - rulepack list API returns active key and catalog data,
    - unknown rulepack activation returns HTTP 400 and is recorded as `failed`,
    - `demo-seed-pack` activation returns HTTP 400 and is recorded as
      `rejected`,
    - `mature-web-balanced` activation returns HTTP 200 with
      `result_status=activated`,
    - activation history API returns latest-first records,
    - runtime signature switching is effective: payload
      `User-Agent: dirbuster` is unmatched in `legacy-inline` and matched as
      `scanner` in `mature-web-balanced`.
- Remaining gap for this slice:
  - final delivery commit/push step (`T020`) is pending.
- Reprioritized to IDS auditability and completed new slice scaffolding:
  - created `specs/005-ids-log-audit/` with `spec.md`, `plan.md`, `research.md`,
    `data-model.md`, `contracts/ids-log-audit.md`, `quickstart.md`, `tasks.md`,
    and requirements checklist,
  - set `005` execution focus to log retrieval quality and IDS operation trace
    completeness.
- Completed backend log-audit enhancement:
  - rewrote `backend/app/api/audit.py` to support pagination, keyword/user/time
    filtering, IDS-only and sensitive-only filtering, summary metrics, and
    dynamic filter options,
  - preserved the existing `audit_logs` schema and derived `is_ids` /
    `is_sensitive` in response serialization for low-risk rollout.
- Completed IDS audit write coverage in `backend/app/api/ids.py`:
  - source sync now records `ids_source_sync`,
  - source package preview records success and rejected paths,
  - source package activation records success and rejected paths,
  - rulepack activation records success, rejected, and failed paths.
- Completed audit frontend rebuild:
  - `frontend/src/api/audit.ts` now matches the enhanced `/api/audit` contract,
  - `frontend/src/views/audit/AuditLogs.vue` is now Chinese-first with summary
    cards, IDS/sensitive tabs, combined filters, and pagination.
- Validation for `005` current pass:
  - Python `py_compile` passes for
    `backend/app/api/audit.py`, `backend/app/api/ids.py`,
    `backend/app/services/audit.py`,
  - frontend `npm run build` passes after audit page and API typing updates.
- Next step:
  - run manual endpoint/UI checks for `005`, then commit and push branch updates
    for PR review.
- Delivery:
  - committed IDS log-audit slice as
    `feat: add ids log audit workflow and chinese audit panel`,
  - pushed `security-center/feature-ids` to `origin` at commit `b630b41`.
