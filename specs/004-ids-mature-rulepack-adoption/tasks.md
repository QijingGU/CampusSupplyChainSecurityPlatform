# Tasks: IDS Mature Rulepack Adoption

**Input**: Design documents from `/specs/004-ids-mature-rulepack-adoption/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/  
**Tests**: Dedicated test files remain deferred for this slice; each story still
requires API-level quickstart validation.  
**Organization**: Tasks are grouped by user story to enable independent
implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the fourth IDS slice and scope boundaries

- [X] T001 Update daily progress for the new rulepack-adoption slice in docs/ids-changelog.md
- [X] T002 Review rulepack-adoption scope and conflict boundaries in specs/004-ids-mature-rulepack-adoption/plan.md
- [X] T003 [P] Confirm the initial API contract and operator validation path in specs/004-ids-mature-rulepack-adoption/contracts/ids-rulepack-adoption.md and specs/004-ids-mature-rulepack-adoption/quickstart.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create rulepack catalog and runtime state boundaries before story work

- [X] T004 Add rulepack runtime state and activation storage in backend/app/models/ids_rulepack.py and backend/app/schema_sync.py
- [X] T005 Add mature rulepack catalog and activation helpers in backend/app/services/ids_rulepacks.py
- [X] T006 Extend backend/app/models/__init__.py and backend/app/api/ids.py serialization helpers for rulepack state and history responses

**Checkpoint**: Rulepack catalog, runtime state, and activation audit storage are ready.

---

## Phase 3: User Story 1 - Preview Mature Rulepack Coverage (Priority: P1) MVP

**Goal**: Let maintainers inspect mature rulepacks before activation.

**Independent Test**: Call rulepack catalog API and validate metadata plus
unknown-key rejection behavior.

### Implementation for User Story 1

- [X] T007 [US1] Implement `GET /api/ids/rule-packs` in backend/app/api/ids.py
- [X] T008 [US1] Extend frontend/src/api/ids.ts with rulepack catalog and activation-history types
- [X] T009 [US1] Record rulepack-catalog validation notes in docs/ids-changelog.md

**Checkpoint**: Maintainers can view reusable mature rulepacks and current active pack.

---

## Phase 4: User Story 2 - Activate Mature Rulepack (Priority: P2)

**Goal**: Allow reviewed mature rulepack activation for inline matcher runtime.

**Independent Test**: Activate one trusted pack and confirm runtime matcher uses
the new active key in IDS event provenance.

### Implementation for User Story 2

- [X] T010 [US2] Implement `POST /api/ids/rule-packs/activate` with rejection/audit paths in backend/app/api/ids.py
- [X] T011 [US2] Update backend/app/services/ids_engine.py and backend/app/middleware/ids_middleware.py to resolve and stamp active rulepack provenance
- [X] T012 [US2] Ensure `demo_test` rulepacks remain visible but non-activatable as trusted runtime coverage in backend/app/api/ids.py
- [X] T013 [US2] Record activation behavior and remaining gaps in docs/ids-changelog.md

**Checkpoint**: Runtime matcher is controllable by reviewed mature rulepack activation.

---

## Phase 5: User Story 3 - Review Rulepack Activation History (Priority: P3)

**Goal**: Keep rulepack activation and rejection history visible and auditable.

**Independent Test**: Perform one successful and one rejected activation, then
confirm both appear in history query.

### Implementation for User Story 3

- [X] T014 [US3] Implement `GET /api/ids/rule-packs/activations` in backend/app/api/ids.py
- [X] T015 [US3] Surface active rulepack and recent activation history in frontend/src/views/security/SecurityIDS.vue
- [X] T016 [US3] Add operator validation steps to specs/004-ids-mature-rulepack-adoption/quickstart.md
- [X] T017 [US3] Append completed history narrative to docs/ids-changelog.md

**Checkpoint**: Rulepack switching operations are reviewable instead of implicit.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish the rulepack-adoption slice cleanly

- [X] T018 [P] Clean up stale matcher-only wording and transitional comments across backend/app/services/ids_engine.py, backend/app/services/ids_rulepacks.py, backend/app/api/ids.py, and frontend/src/api/ids.ts
- [X] T019 Run API-level validation flow in specs/004-ids-mature-rulepack-adoption/quickstart.md and capture results in docs/ids-changelog.md
- [ ] T020 Prepare a reviewable commit and push current work to origin security-center/feature-ids

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories
- **User Story 1 (Phase 3)**: Starts after Foundational
- **User Story 2 (Phase 4)**: Starts after Foundational and builds on runtime state and catalog
- **User Story 3 (Phase 5)**: Starts after Foundational and benefits from activation records
- **Polish (Phase 6)**: Depends on desired story completion

### User Story Dependencies

- **US1** depends on rulepack catalog and serialization helpers.
- **US2** depends on activation helpers and runtime state storage.
- **US3** depends on activation records and history serialization.

### Parallel Opportunities

- T003 can run while T001-T002 are being finalized.
- T018 can run alongside the final validation pass.

---

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational tasks.
2. Deliver User Story 1 for catalog visibility.
3. Validate catalog and preview behavior.

### Incremental Delivery

1. Add runtime state and activation storage.
2. Expose mature rulepack catalog.
3. Add activation and matcher runtime switching.
4. Add activation history visibility.
5. Validate and push for review.

## Notes

- Keep diffs narrow and limited to IDS/security-center paths.
- Prioritize mature rulepack reuse over expanding local ad hoc signatures.
- Update `docs/ids-changelog.md` on every active development day.
