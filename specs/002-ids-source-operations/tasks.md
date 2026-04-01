# Tasks: IDS Source Operations

**Input**: Design documents from `/specs/002-ids-source-operations/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/  
**Tests**: Dedicated automated tests remain deferred for this slice, but each
story still requires API-level and UI-level manual validation through
`quickstart.md`.  
**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the second IDS slice and document its scope

- [X] T001 Update daily progress for the new source-operations slice in docs/ids-changelog.md
- [X] T002 Review source-operations scope and conflict boundaries in specs/002-ids-source-operations/plan.md
- [X] T003 [P] Confirm the first source-operations contract and validation notes in specs/002-ids-source-operations/contracts/ids-source-operations.md and specs/002-ids-source-operations/quickstart.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the source registry boundary before user-story work

- [X] T004 Add IDS source registry and sync-attempt storage in backend/app/models/ids_source.py and backend/app/schema_sync.py
- [X] T005 Create source-health derivation helpers in backend/app/services/ids_ingestion.py or a new backend/app/services/ids_source_ops.py
- [X] T006 Extend backend/app/api/ids.py serialization helpers so source-health summaries can be returned to the frontend

**Checkpoint**: Source registry and health derivation are ready for reviewer-facing work.

---

## Phase 3: User Story 1 - Review Source Health (Priority: P1) MVP

**Goal**: Let reviewers see source trust and health without reading backend logs.

**Independent Test**: Register at least two sources with different health states
and verify the security center shows their trust class, health label, freshness,
and recent activity clearly.

### Implementation for User Story 1

- [X] T007 [US1] Implement source list and health summary endpoints in backend/app/api/ids.py
- [X] T008 [US1] Extend frontend/src/api/ids.ts with source-operations types and requests
- [X] T009 [US1] Update frontend/src/views/security/SecurityIDS.vue to render source-health summaries alongside the incident workflow
- [X] T010 [US1] Record reviewer-facing health validation results in docs/ids-changelog.md

**Checkpoint**: A reviewer can trust the displayed source health state.

---

## Phase 4: User Story 2 - Operate Trusted Source Registration (Priority: P2)

**Goal**: Give maintainers a controlled trusted-source registration workflow.

**Independent Test**: Create one trusted source, edit it, disable it, and verify
validation plus persisted state through the API and UI.

### Implementation for User Story 2

- [X] T011 [US2] Implement validated create/update source endpoints in backend/app/api/ids.py
- [X] T012 [US2] Add source-management form state and validation handling in frontend/src/views/security/SecurityIDS.vue
- [X] T013 [US2] Ensure demo-only or custom sources remain visibly distinct from trusted production-oriented sources in frontend/src/views/security/SecurityIDS.vue
- [X] T014 [US2] Record trusted-source registration behavior and remaining gaps in docs/ids-changelog.md

**Checkpoint**: A maintainer can safely register and update source definitions.

---

## Phase 5: User Story 3 - Run Traceable Source Synchronization (Priority: P3)

**Goal**: Make source synchronization visible, reviewable, and auditable.

**Independent Test**: Trigger success and skip/failure sync cases, confirm the
results remain visible, and verify source health updates accordingly.

### Implementation for User Story 3

- [X] T015 [US3] Implement source sync trigger and sync-attempt recording in backend/app/api/ids.py
- [X] T016 [US3] Surface sync actions and latest sync results in frontend/src/views/security/SecurityIDS.vue
- [X] T017 [US3] Append implementation-specific API-level validation notes and operator steps to specs/002-ids-source-operations/quickstart.md
- [X] T018 [US3] Append the completed source-sync narrative to docs/ids-changelog.md

**Checkpoint**: Source synchronization is traceable instead of implicit.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish the source-operations slice cleanly

- [X] T019 [P] Clean up stale source-operation wording and transitional comments across backend/app/api/ids.py, backend/app/services/ids_ingestion.py, and frontend/src/api/ids.ts
- [ ] T020 Run the API-level and UI-level validation flow in specs/002-ids-source-operations/quickstart.md and capture results in docs/ids-changelog.md
- [ ] T021 Prepare a reviewable commit and push current work to origin security-center/feature-ids

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories
- **User Story 1 (Phase 3)**: Starts after Foundational
- **User Story 2 (Phase 4)**: Starts after Foundational and builds on the same source registry
- **User Story 3 (Phase 5)**: Starts after Foundational and benefits from source health visibility
- **Polish (Phase 6)**: Depends on desired story completion

### User Story Dependencies

- **US1** depends on the source registry and health derivation layer.
- **US2** depends on the same registry boundary and can follow once health summaries exist.
- **US3** depends on stored source definitions and source-health visibility.

### Parallel Opportunities

- T003 can run while T001-T002 are being finalized.
- T019 can run alongside the final validation pass.

---

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational work.
2. Deliver User Story 1 so reviewers can see source health.
3. Validate the reviewer-facing source-health workflow.

### Incremental Delivery

1. Create source registry and health derivation.
2. Expose reviewer-facing source health.
3. Add trusted-source registration workflow.
4. Add traceable source synchronization.
5. Validate and push for review.

## Notes

- Keep diffs narrow and limited to IDS/security-center paths.
- Do not expand local signature logic in this slice; the focus is source operations.
- Update `docs/ids-changelog.md` on every active development day.
