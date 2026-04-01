# Feature Specification: IDS Source Operations

**Feature Branch**: `security-center/feature-ids`  
**Created**: 2026-04-01  
**Status**: Draft  
**Input**: User description: "Continue the IDS rebuild after the normalized incident workflow by making mature detection sources operational: reviewers must see source health, maintainers must register and synchronize trusted sources safely, and the next slice must still follow the daily changelog and existing GitHub collaboration rules."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Review Source Health (Priority: P1)

A system administrator opens the security center and can immediately tell which
IDS sources are healthy, stale, disabled, or failing so they do not over-trust
incident coverage.

**Why this priority**: once incidents are normalized, the next operational risk
is false confidence about detector coverage. Reviewers need source health before
they can trust silence from the IDS.

**Independent Test**: create or update at least two detection sources with
different health states, open the security center, and verify that reviewers can
see each source's trust class, sync freshness, current status, and recent error
context without reading backend logs.

**Acceptance Scenarios**:

1. **Given** a mature external source is healthy and recently synchronized,
   **When** an administrator opens the IDS source view, **Then** the source is
   shown as healthy with its freshness window and last successful sync time.
2. **Given** a source is stale, disabled, or has recent sync failures,
   **When** the administrator reviews the same view, **Then** the degraded state
   is visible and distinguishable from healthy sources.
3. **Given** incidents were ingested from a specific source,
   **When** a reviewer inspects that source, **Then** they can see that the
   source is connected to recent incident activity rather than being an orphaned
   configuration.

---

### User Story 2 - Operate Trusted Source Registration (Priority: P2)

A security maintainer registers and updates trusted source definitions through a
controlled workflow so the platform can accept mature-source metadata without
ad hoc configuration drift.

**Why this priority**: the current slice can ingest normalized events, but it
cannot yet manage the trusted source inventory in a consistent, reviewable way.

**Independent Test**: create one trusted external source definition, edit its
freshness and sync policy, register one `demo_test` source definition, and
verify both records are persisted, validated, and visibly distinct through the
source operations API and UI.

**Acceptance Scenarios**:

1. **Given** a maintainer registers a new trusted source,
   **When** the source definition is saved,
   **Then** the platform stores its name, family, trust classification,
   freshness target, and sync policy in one reviewable record.
2. **Given** a maintainer tries to save an incomplete or invalid source
   definition,
   **When** validation runs,
   **Then** the platform rejects the change and explains what is missing.
3. **Given** an existing source must be disabled temporarily,
   **When** the maintainer changes its operational status,
   **Then** the new state is visible to reviewers and future sync actions follow
   that state.

---

### User Story 3 - Run Traceable Source Synchronization (Priority: P3)

A maintainer triggers or reviews source synchronization and can trace whether
the sync succeeded, failed, or was skipped so daily IDS work remains auditable.

**Why this priority**: source health without traceable synchronization still
leaves the team guessing whether freshness metadata is real or stale paperwork.

**Independent Test**: trigger one source sync attempt, verify the result is
recorded, confirm a failed or skipped case remains visible, and check that the
day's changelog notes the operational work.

**Acceptance Scenarios**:

1. **Given** a trusted source is eligible for synchronization,
   **When** a maintainer triggers a sync,
   **Then** the attempt records start time, result, freshness impact, and any
   returned detail.
2. **Given** a sync attempt fails or is skipped because the source is disabled,
   **When** the maintainer reviews the source record,
   **Then** the failure or skip reason remains visible instead of disappearing.
3. **Given** IDS source operations changed during the day,
   **When** the repository changelog is reviewed,
   **Then** the day's source-operation work is documented with the active branch
   workflow.

---

### Edge Cases

- What happens when a trusted source exists in the registry but has never been
  synchronized successfully?
- How does the platform behave when a source is disabled after incidents were
  already ingested from it?
- What happens when multiple incidents reference a source that has become stale
  or failed recently?
- How does the system prevent a `demo_test` source definition from being
  treated as a trusted production source or a campus-specific production
  detector?
- What happens when a source sync is requested twice within the same short
  review window?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST maintain a reviewable source registry for IDS
  detection sources used by the platform.
- **FR-002**: Each source registry record MUST preserve trust classification,
  detector family, operational status, freshness target, sync policy, and
  provenance notes.
- **FR-003**: The system MUST show source health states including healthy,
  stale, disabled, failing, and never-synced conditions.
- **FR-004**: Authorized maintainers MUST be able to create, update, disable,
  and review trusted source definitions through a validated workflow.
- **FR-005**: Invalid source definitions MUST be rejected with actionable
  validation feedback.
- **FR-006**: The system MUST record synchronization attempts for each source,
  including start time, result, status detail, and freshness impact.
- **FR-007**: Failed or skipped synchronization attempts MUST remain visible to
  reviewers and maintainers.
- **FR-008**: The security-center experience MUST expose source health and sync
  status separately from individual incident review.
- **FR-009**: The platform MUST show recent incident linkage or activity counts
  for each source so operators can connect source health with actual IDS usage.
- **FR-010**: Demo or test-only sources MUST remain distinguishable from trusted
  production-oriented sources and from non-demo `custom_project` detectors.
- **FR-011**: Source operations MUST stay within the existing IDS/security-center
  collaboration and changelog workflow.

### Key Entities *(include if feature involves data)*

- **IDS Source Registry Entry**: A persisted description of one detection
  source, including identity, trust class, freshness target, sync policy,
  operational status, and provenance notes.
- **Source Sync Attempt**: A timestamped operational record describing one
  source synchronization run, including result, detail, and freshness outcome.
- **Source Health Snapshot**: A reviewer-facing summary derived from source
  metadata, last sync result, and current freshness state.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can identify the health state of each active IDS source
  from the security center without consulting backend logs or raw database
  tables.
- **SC-002**: A maintainer can register or update a trusted source definition in
  one workflow with validation feedback for invalid input.
- **SC-003**: Every source synchronization attempt in the refactored scope
  leaves a visible operational record showing success, failure, or skip result.
- **SC-004**: Trusted-source health and sync status remain visibly separate from
  demo-only source definitions.
- **SC-005**: The day's IDS source-operation work is recorded in the changelog
  and can be matched to repository activity.

## Assumptions

- This slice extends the existing normalized IDS incident workflow rather than
  replacing it.
- The first delivery focuses on source registry and health visibility; fully
  automated upstream fetch jobs may remain partial as long as sync attempts are
  traceable.
- Existing administrator roles remain authoritative for source operations.
- The team continues working on `security-center/feature-ids` and submitting
  pull requests into `security-center/collab-setup`.
