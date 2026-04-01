# Feature Specification: IDS Source Package Intake

**Feature Branch**: `security-center/feature-ids`  
**Created**: 2026-04-01  
**Status**: Draft  
**Input**: User description: "Continue the IDS rebuild after source operations by letting maintainers import trusted mature-source packages deliberately: package metadata must be previewed before activation, active package versions must stay visible to reviewers, and the workflow must still favor mature external sources over new local detector logic."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preview Trusted Source Packages (Priority: P1)

A security maintainer submits a trusted source package manifest and can preview
what source/version metadata would change before anything is activated.

**Why this priority**: after source registry and sync visibility exist, the next
operational gap is that mature-source updates still have no controlled intake
path. Previewing package impact prevents blind source drift.

**Independent Test**: submit one valid package manifest and one invalid package
manifest, confirm the preview returns structured impact details for the valid
case, and confirm the invalid case is rejected with actionable feedback.

**Acceptance Scenarios**:

1. **Given** a maintainer provides a valid mature-source package manifest,
   **When** preview runs,
   **Then** the platform shows the targeted source, package version, provenance,
   and the fields that would change if activated.
2. **Given** the package manifest is incomplete or mislabeled,
   **When** preview runs,
   **Then** the platform rejects the package and explains what is wrong.
3. **Given** a package targets a source that is already registered,
   **When** the preview is opened,
   **Then** the maintainer can see whether the package is newer, unchanged, or
   conflicting with the active source state.

---

### User Story 2 - Activate Trusted Package Versions (Priority: P2)

A maintainer applies a reviewed trusted package to a registered source so the
platform can track which upstream package version currently backs the source.

**Why this priority**: preview alone is not operationally useful unless the
reviewed package can become the active source version in a traceable way.

**Independent Test**: preview one valid trusted package, apply it to an
existing source, and verify that the source record now shows the active package
version and refreshed provenance detail.

**Acceptance Scenarios**:

1. **Given** a valid previewed package for a trusted source,
   **When** the maintainer applies it,
   **Then** the source record updates to the package version and keeps a
   traceable activation record.
2. **Given** a package is marked `demo_test` or otherwise unsuitable for
   production trust,
   **When** activation is attempted for a production-oriented source,
   **Then** the activation is rejected instead of silently downgrading trust.
3. **Given** a package is already active,
   **When** the maintainer tries to apply it again,
   **Then** the system responds deterministically and preserves the audit trail.

---

### User Story 3 - Review Package History And Failures (Priority: P3)

A reviewer inspects a source and can see recent package imports, activation
history, and failed intake attempts so mature-source operations stay auditable.

**Why this priority**: once package activation exists, reviewers must be able to
trace which version is active and whether recent import failures could explain
coverage gaps.

**Independent Test**: create one successful package activation and one failed
package intake attempt, then verify that the source view exposes both outcomes
without consulting backend logs.

**Acceptance Scenarios**:

1. **Given** a package activation succeeded,
   **When** the reviewer opens the source details,
   **Then** the active version and recent intake history remain visible.
2. **Given** a package intake failed validation or activation,
   **When** the reviewer inspects the same source,
   **Then** the failed result and reason remain visible instead of being lost.
3. **Given** the team reviews the day's IDS work,
   **When** `docs/ids-changelog.md` is checked,
   **Then** the package-intake work is recorded with the active branch workflow.

---

### Edge Cases

- What happens when a package manifest references a `source_key` that does not
  yet exist in the source registry?
- How does the platform behave when a package version is older than the active
  source version?
- What happens when two package intake attempts target the same source in quick
  succession?
- How does the system prevent a `demo_test` package manifest from being applied
  to a trusted production-oriented source?
- What happens when a package manifest is structurally valid but its provenance
  note is missing or weak?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a reviewable intake workflow for trusted
  IDS source packages or manifests.
- **FR-002**: Each source package preview MUST preserve `source_key`, package
  version, release timestamp, trust classification, detector family, package
  provenance, and summary change impact.
- **FR-003**: Authorized maintainers MUST be able to preview a package before it
  becomes active on a source.
- **FR-004**: Invalid or conflicting package manifests MUST be rejected with
  actionable validation feedback.
- **FR-005**: Authorized maintainers MUST be able to activate a reviewed trusted
  package for an existing IDS source.
- **FR-006**: The system MUST record package intake attempts and activation
  outcomes, including operator, timestamp, result, and detail.
- **FR-007**: Failed preview or activation attempts MUST remain visible to
  reviewers and maintainers.
- **FR-008**: The security-center experience MUST expose active package version
  and recent package intake history for each source.
- **FR-009**: `demo_test` packages MUST remain distinguishable from trusted
  production-oriented packages and MUST not be activatable as trusted coverage.
- **FR-010**: Package intake operations MUST stay within the existing
  IDS/security-center collaboration and changelog workflow.

### Key Entities *(include if feature involves data)*

- **IDS Source Package Intake**: A submitted package manifest or trusted-source
  intake record that captures source identity, package version, provenance,
  review result, and activation intent.
- **Source Package Activation**: A traceable record showing that one reviewed
  package version became active for one source.
- **Source Package Preview**: A reviewer-facing diff summary showing how a
  proposed package would change the active source state before activation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A maintainer can preview a trusted source package and understand
  its impact before activation without querying raw tables.
- **SC-002**: A maintainer can activate a reviewed package version for a source
  in one workflow with validation feedback for invalid input.
- **SC-003**: Every package preview or activation attempt in scope leaves a
  visible operational record showing success, failure, or no-op result.
- **SC-004**: Active package version and package history remain visibly separate
  from `demo_test` package records.
- **SC-005**: The day's IDS package-intake work is recorded in the changelog and
  can be matched to repository activity.

## Assumptions

- This slice extends the completed source-registry workflow from
  `002-ids-source-operations`.
- The first delivery focuses on package manifest intake and activation records,
  not full live upstream feed fetching.
- Existing administrator roles remain authoritative for package intake.
- The team continues working on `security-center/feature-ids` and submitting
  pull requests into `security-center/collab-setup`.
