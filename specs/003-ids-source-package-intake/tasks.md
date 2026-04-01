# Tasks: IDS Source Package Intake

**Input**: Design documents from `/specs/003-ids-source-package-intake/`  
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

**Purpose**: Establish the third IDS slice and document its scope

- [X] T001 Update daily progress for the new source-package-intake slice in docs/ids-changelog.md
- [X] T002 Review package-intake scope and conflict boundaries in specs/003-ids-source-package-intake/plan.md
- [X] T003 [P] Confirm the first package-intake contract and validation notes in specs/003-ids-source-package-intake/contracts/ids-source-package-intake.md and specs/003-ids-source-package-intake/quickstart.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the package-intake boundary before user-story work

- [X] T004 Add IDS source-package intake and activation storage in backend/app/models/ids_source_package.py and backend/app/schema_sync.py
- [X] T005 Create package-preview and activation helpers in backend/app/services/ids_source_packages.py
- [X] T006 Extend backend/app/api/ids.py serialization helpers so package history summaries can be returned to the frontend

**Checkpoint**: Package intake and activation records are ready for reviewer-facing work.

---

## Phase 3: User Story 1 - Preview Trusted Source Packages (Priority: P1) MVP

**Goal**: Let maintainers preview trusted source packages before activation.

**Independent Test**: Submit one valid and one invalid package manifest and
verify preview results or validation failures through the API and security
center.

### Implementation for User Story 1

- [X] T007 [US1] Implement package preview endpoint in backend/app/api/ids.py
- [X] T008 [US1] Extend frontend/src/api/ids.ts with package-intake types and requests
- [X] T009 [US1] Update frontend/src/views/security/SecurityIDS.vue to render package preview results alongside source operations
- [X] T010 [US1] Record package-preview validation results in docs/ids-changelog.md

**Checkpoint**: A maintainer can preview trusted package impact before activation.

---

## Phase 4: User Story 2 - Activate Trusted Package Versions (Priority: P2)

**Goal**: Give maintainers a controlled package activation workflow.

**Independent Test**: Activate one reviewed package version for an existing
source and verify that the source shows the new active version.

### Implementation for User Story 2

- [X] T011 [US2] Implement package activation endpoint in backend/app/api/ids.py
- [X] T012 [US2] Add package-activation form state and validation handling in frontend/src/views/security/SecurityIDS.vue
- [X] T013 [US2] Ensure `demo_test` packages remain visibly distinct and non-activatable as trusted coverage in frontend/src/views/security/SecurityIDS.vue
- [X] T014 [US2] Record package-activation behavior and remaining gaps in docs/ids-changelog.md

**Checkpoint**: A maintainer can safely activate reviewed package versions.

---

## Phase 5: User Story 3 - Review Package History And Failures (Priority: P3)

**Goal**: Make package intake history visible, reviewable, and auditable.

**Independent Test**: Trigger a successful package activation and a failed
preview or activation case, then confirm both outcomes remain visible in source
details.

### Implementation for User Story 3

- [X] T015 [US3] Implement package-history listing in backend/app/api/ids.py
- [X] T016 [US3] Surface active package version and recent package history in frontend/src/views/security/SecurityIDS.vue
- [X] T017 [US3] Add implementation-specific validation notes and operator steps to specs/003-ids-source-package-intake/quickstart.md
- [X] T018 [US3] Append the completed package-history narrative to docs/ids-changelog.md

**Checkpoint**: Package intake and activation history are traceable instead of implicit.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish the package-intake slice cleanly

- [X] T019 [P] Clean up stale package-intake wording and transitional comments across backend/app/api/ids.py, backend/app/services/ids_source_packages.py, and frontend/src/api/ids.ts
- [X] T020 Run the API-level and UI-level validation flow in specs/003-ids-source-package-intake/quickstart.md and capture results in docs/ids-changelog.md
- [X] T021 Prepare a reviewable commit and push current work to origin security-center/feature-ids

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories
- **User Story 1 (Phase 3)**: Starts after Foundational
- **User Story 2 (Phase 4)**: Starts after Foundational and builds on the same package-intake boundary
- **User Story 3 (Phase 5)**: Starts after Foundational and benefits from visible package history
- **Polish (Phase 6)**: Depends on desired story completion

### User Story Dependencies

- **US1** depends on package-intake storage and preview helpers.
- **US2** depends on reviewed package preview state and activation records.
- **US3** depends on stored package-intake and activation history.

### Parallel Opportunities

- T003 can run while T001-T002 are being finalized.
- T019 can run alongside the final validation pass.

---

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational work.
2. Deliver User Story 1 so maintainers can preview trusted packages.
3. Validate the package-preview workflow.

### Incremental Delivery

1. Create package-intake and activation records.
2. Expose previewable package impact.
3. Add trusted package activation workflow.
4. Add visible package history.
5. Validate and push for review.

## Notes

- Keep diffs narrow and limited to IDS/security-center paths.
- Do not expand local signature logic in this slice; the focus is mature-source package intake.
- Update `docs/ids-changelog.md` on every active development day.
