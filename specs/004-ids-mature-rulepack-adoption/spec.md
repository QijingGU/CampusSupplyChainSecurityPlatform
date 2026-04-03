# Feature Specification: IDS Mature Rulepack Adoption

**Feature Branch**: `security-center/feature-ids`  
**Created**: 2026-04-03  
**Status**: Draft  
**Input**: User description: "继续改 IDS，优先复用别人已经做好的成熟静态匹配规则，再做项目内魔改，并按 Spec Kit 流程推进。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preview Mature Rulepack Coverage (Priority: P1)

A security maintainer can preview an existing mature rulepack before activation
and understand what attack families and rule counts it contributes.

**Why this priority**: the current inline matcher is mostly local hardcoded
rules. The first value is visibility and controllable reuse of mature
rulepacks.

**Independent Test**: call the rulepack listing API and preview metadata for at
least one mature pack; verify response includes pack key, source provenance,
coverage summary, and validation warnings.

**Acceptance Scenarios**:

1. **Given** at least one mature rulepack is available, **When** the maintainer
   requests rulepack catalog data, **Then** each pack includes key, source,
   version, detector family coverage, and rule count.
2. **Given** a maintainer chooses one rulepack, **When** preview is requested,
   **Then** the response indicates whether the pack is valid for trusted use or
   blocked by trust constraints.
3. **Given** a malformed or unknown rulepack key, **When** preview is requested,
   **Then** the system rejects it with actionable detail.

---

### User Story 2 - Activate Mature Rulepack For Inline Matching (Priority: P2)

A maintainer can activate a reviewed mature rulepack so runtime inline matching
uses it instead of only legacy local signatures.

**Why this priority**: preview without activation does not improve runtime
detection behavior.

**Independent Test**: activate one mature rulepack, submit a known matching
payload, and verify the IDS event records the activated rulepack key and
matched attack type.

**Acceptance Scenarios**:

1. **Given** a valid mature rulepack key, **When** activation succeeds,
   **Then** subsequent inline matching uses that rulepack as active runtime
   signatures.
2. **Given** a rulepack marked `demo_test`, **When** trusted activation is
   attempted, **Then** activation is rejected and rejection is auditable.
3. **Given** activation is repeated for the same active rulepack, **When** the
   maintainer confirms, **Then** the operation remains deterministic and leaves
   a traceable record.

---

### User Story 3 - Review Rulepack Activation History (Priority: P3)

A reviewer can inspect which rulepack is currently active and see recent
activation history with operator, time, and notes.

**Why this priority**: runtime changes to matcher behavior must be auditable.

**Independent Test**: perform one successful activation and one rejected
activation, then query activation history and verify both outcomes are visible.

**Acceptance Scenarios**:

1. **Given** at least one activation happened, **When** a reviewer opens
   history, **Then** current active pack and recent activations are visible.
2. **Given** an activation attempt was rejected, **When** history is queried,
   **Then** failure detail remains visible instead of being dropped.
3. **Given** IDS events are created after activation, **When** events are
   listed, **Then** event provenance includes active rulepack identity.

---

### Edge Cases

- What happens when a rulepack key exists in catalog but has zero enabled rules?
- What happens when two activation requests arrive in quick succession?
- How does runtime behave if the active rulepack key becomes unavailable?
- What happens when activation note is empty but operator identity is present?
- How does the system keep `demo_test` packs visible but non-trusted?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a catalog of mature rulepacks with
  provenance, version, detector family, and rule-count metadata.
- **FR-002**: The system MUST allow preview of one selected rulepack before
  activation.
- **FR-003**: The system MUST reject unknown rulepack keys with actionable
  validation detail.
- **FR-004**: Authorized maintainers MUST be able to activate a reviewed
  non-demo rulepack for inline IDS matching.
- **FR-005**: Activation attempts MUST record operator, timestamp, activation
  result, and detail.
- **FR-006**: Rejected activation attempts MUST remain visible in activation
  history.
- **FR-007**: Runtime inline matcher MUST use the currently active rulepack for
  signature matching.
- **FR-008**: IDS event provenance MUST expose the active rulepack key used at
  detection time.
- **FR-009**: `demo_test` rulepacks MUST remain distinguishable and MUST not be
  activatable as trusted runtime coverage.
- **FR-010**: This slice MUST remain in IDS/security-center scope and update the
  daily changelog and branch workflow records.

### Key Entities *(include if feature involves data)*

- **Mature Rulepack Catalog Entry**: one curated reusable rulepack with stable
  key, provenance, version, detector families, trust class, and signature set.
- **Rulepack Activation Record**: one auditable operation that attempts to
  switch runtime matcher to a rulepack.
- **Runtime Rulepack State**: current active rulepack key used by inline matcher
  at detection time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A maintainer can list and preview mature rulepacks in one API
  workflow without querying raw files.
- **SC-002**: A maintainer can activate one reviewed mature rulepack in under
  one minute including validation feedback.
- **SC-003**: 100% of activation attempts in scope produce traceable history
  records with operator and result detail.
- **SC-004**: IDS events generated after activation include rulepack provenance
  in event metadata.
- **SC-005**: Daily changelog and tasks reflect this slice's delivery progress
  on the same development day.

## Assumptions

- This slice builds on `003-ids-source-package-intake` and keeps the same
  branch workflow (`security-center/feature-ids` -> `security-center/collab-setup`).
- First delivery uses curated in-project mature rulepack definitions and does
  not yet fetch remote rule archives automatically.
- Runtime matcher keeps a deterministic fallback pack if activation state is
  missing or invalid.
- Security-center UI extension may be incremental; API and event provenance are
  the primary MVP outcomes.
