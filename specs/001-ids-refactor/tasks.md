# Tasks: IDS Refactor Foundation

**Input**: Design documents from `/specs/001-ids-refactor/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/  
**Tests**: Dedicated test tasks are deferred for a follow-up slice; each story
still requires manual validation through `quickstart.md`.  
**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish refactor documentation and branch hygiene

- [X] T001 Update daily progress and working rules in docs/ids-changelog.md
- [X] T002 Review current IDS scope and capture active conflict boundaries in specs/001-ids-refactor/plan.md
- [X] T003 [P] Record mature-source roadmap and ingestion contract updates in specs/001-ids-refactor/research.md and specs/001-ids-refactor/contracts/ids-ingestion.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the normalized incident boundary before user-story work

- [X] T004 Extend backend incident data in backend/app/models/ids_event.py to carry event origin, source classification, provenance, freshness, and correlation fields
- [X] T005 Update schema sync and initialization paths in backend/app/schema_sync.py and backend/init_db.py for the new IDS incident fields
- [X] T006 Create a normalized incident mapping layer in backend/app/services/ids_engine.py or a new backend/app/services/ids_ingestion.py service
- [X] T007 Split demo/test seeding semantics from real detection semantics in backend/app/api/ids.py
- [X] T008 Update IDS API serialization in backend/app/api/ids.py so real/demo origin and source provenance are visible to the frontend
- [X] T009 Update frontend IDS types in frontend/src/api/ids.ts to reflect the normalized incident model

**Checkpoint**: Foundation ready for real incident review, detector provenance,
and demo isolation.

---

## Phase 3: User Story 1 - Review Real Security Incidents (Priority: P1) MVP

**Goal**: Give administrators a trustworthy real-incident review workflow.

**Independent Test**: Ingest a real event, review it in the IDS console, update
status, add notes, archive it, and verify audit history is preserved.

### Implementation for User Story 1

- [X] T010 [US1] Refactor IDS middleware behavior in backend/app/middleware/ids_middleware.py to emit normalized incident records instead of presentation-oriented fields
- [X] T011 [US1] Update review and response endpoints in backend/app/api/ids.py to preserve response history and remediation failure visibility
- [X] T012 [US1] Update IDS management UI state in frontend/src/views/security/SecurityIDS.vue to show source, origin, evidence, status, and response summaries
- [X] T013 [US1] Update any legacy IDS screen still used by reviewers in frontend/src/views/ids/IDSManage.vue or explicitly deprecate it in favor of the security-center screen
- [X] T014 [US1] Verify real-incident triage flow and record the outcome in docs/ids-changelog.md

**Checkpoint**: A reviewer can trust and operate on one real incident end to
end.

---

## Phase 4: User Story 2 - Trust Mature Detection Sources (Priority: P2)

**Goal**: Surface detector provenance and prepare mature-source ingestion.

**Independent Test**: Ingest an event with external-source metadata and confirm
the UI and backend expose provenance and source freshness separately from local
rules.

### Implementation for User Story 2

- [X] T015 [US2] Implement source provenance normalization in backend/app/services/ids_engine.py or backend/app/services/ids_ingestion.py
- [X] T016 [US2] Add an ingestion endpoint or adapter path in backend/app/api/ids.py that accepts the normalized contract from specs/001-ids-refactor/contracts/ids-ingestion.md
- [X] T017 [US2] Update IDS stats and list filtering in backend/app/api/ids.py to support source and origin-aware reporting
- [X] T018 [US2] Update frontend source and provenance rendering in frontend/src/views/security/SecurityIDS.vue
- [X] T019 [US2] Document the first supported mature-source integrations and remaining gaps in docs/ids-changelog.md

**Checkpoint**: The platform can distinguish trusted upstream signals from
custom or transitional ones.

---

## Phase 5: User Story 3 - Keep Demo Data And Delivery Traceable (Priority: P3)

**Goal**: Preserve controlled demos without contaminating real metrics or daily
review.

**Independent Test**: Generate demo and real events on the same day, confirm
default metrics show only real incidents, then confirm the changelog reflects
the delivery.

### Implementation for User Story 3

- [X] T020 [US3] Rework demo seed endpoints in backend/app/api/ids.py so they always label events as demo/test and never appear as real incidents by default
- [X] T021 [US3] Update IDS charts, filters, and metric cards in frontend/src/views/security/SecurityIDS.vue to exclude demo/test events by default and allow explicit demo review
- [X] T022 [US3] Remove or downgrade misleading demo-only wording, labels, and simulated effectiveness cues in frontend/src/views/security/SecurityIDS.vue and frontend/src/views/security/SecuritySituation.vue
- [X] T023 [US3] Add quickstart validation notes and reviewer instructions in specs/001-ids-refactor/quickstart.md
- [X] T024 [US3] Append the completed daily refactor narrative to docs/ids-changelog.md before push

**Checkpoint**: Demo support remains available but no longer undermines trust in
real IDS outputs.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish the branch with documentation, cleanup, and validation

- [X] T025 [P] Clean up stale IDS field names and transitional comments across backend/app/api/ids.py, backend/app/services/ids_engine.py, and frontend/src/api/ids.ts
- [X] T026 [P] Review security-center routing and navigation consistency in frontend/src/router/routes.ts and frontend/src/views/security/SecurityCenterLayout.vue
- [X] T027 Run the validation flow in specs/001-ids-refactor/quickstart.md and capture results in docs/ids-changelog.md
- [ ] T028 Prepare a reviewable commit and push current work to origin security-center/feature-ids

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories
- **User Story 1 (Phase 3)**: Starts after Foundational
- **User Story 2 (Phase 4)**: Starts after Foundational and builds on the same
  normalized incident model
- **User Story 3 (Phase 5)**: Starts after Foundational and benefits from User
  Story 1 metric changes
- **Polish (Phase 6)**: Depends on desired story completion

### User Story Dependencies

- **US1** depends on the normalized incident model and updated API output.
- **US2** depends on the same normalized model but can be developed after US1 or
  in parallel once foundational work is stable.
- **US3** depends on explicit origin tagging and metric filtering from earlier
  phases.

### Parallel Opportunities

- T003 can run while T001-T002 are being finalized.
- T025-T026 can run in parallel during polish.

---

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational work.
2. Deliver User Story 1 so reviewers can trust real incidents again.
3. Validate the end-to-end triage workflow.

### Incremental Delivery

1. Normalize incident model and provenance.
2. Repair the real review workflow.
3. Add mature-source ingestion support.
4. Isolate demo/test behavior.
5. Clean up and push for review.

## Notes

- Keep diffs narrow and biased toward IDS/security-center files.
- Avoid adding new broad regex matching during this feature unless it is a
  documented campus-specific gap.
- Update `docs/ids-changelog.md` on every active development day.
