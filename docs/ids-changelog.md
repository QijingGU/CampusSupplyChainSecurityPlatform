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
