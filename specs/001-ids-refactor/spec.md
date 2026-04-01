# Feature Specification: IDS Refactor Foundation

**Feature Branch**: `security-center/feature-ids`  
**Created**: 2026-04-01  
**Status**: Draft  
**Input**: User description: "Rebuild the IDS so it stops being mainly a demo, becomes materially effective, reuses mature detection sources instead of reinventing static matching, keeps a daily changelog, and stays synchronized with the existing GitHub workflow."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Review Real Security Incidents (Priority: P1)

A system administrator reviews real IDS incidents in the security center,
understands why they were raised, and completes a response workflow without
guessing whether the incident is real or demo-generated.

**Why this priority**: the current IDS loses trust when reviewers cannot tell
what is genuine, what triggered the event, and what action was already taken.

**Independent Test**: generate or ingest one real detection event, open the
security center, verify the event shows evidence, source provenance, severity,
status, and response options, then complete triage and archival without losing
audit history.

**Acceptance Scenarios**:

1. **Given** a real detection event arrives with evidence and provenance,
   **When** an administrator opens the IDS console, **Then** the event is shown
   with its source, evidence summary, severity, confidence, and current
   response status.
2. **Given** an administrator marks a real event as mitigated, false positive,
   or closed, **When** the action is saved, **Then** the disposition, review
   note, and action history remain attached to that event.
3. **Given** an automated remediation action fails, **When** the administrator
   reviews the event, **Then** the failure is visible and the incident remains
   reviewable instead of disappearing from the workflow.

---

### User Story 2 - Trust Mature Detection Sources (Priority: P2)

A security maintainer brings proven upstream detection sources into the platform
and can distinguish them from project-specific rules so the team stops relying
primarily on locally invented static matching.

**Why this priority**: the current project needs stronger detection quality, and
that depends on reusing mature sources rather than continuing to grow a
demo-first rule set.

**Independent Test**: register at least one mature detection source, ingest an
event from it, and verify the platform surfaces source identity, provenance,
and update/freshness context separately from local custom rules.

**Acceptance Scenarios**:

1. **Given** a supported upstream detector source is active, **When** it emits a
   detection consumed by the platform, **Then** the resulting incident clearly
   shows that it came from an external trusted source.
2. **Given** a platform-specific custom rule also generates incidents,
   **When** maintainers compare events, **Then** they can distinguish external
   detections from custom detections without reading raw code.
3. **Given** a detector source becomes stale, unavailable, or unknown in
   provenance, **When** maintainers inspect source status, **Then** they can see
   that trust gap and avoid assuming the detector is healthy.

---

### User Story 3 - Keep Demo Data And Delivery Traceable (Priority: P3)

A project maintainer can still run controlled demos and daily iterations, but
demo traffic does not pollute real incident metrics and reviewers can trace what
changed each day.

**Why this priority**: the team still needs demonstrations and frequent review,
but those activities must stop corrupting operational trust.

**Independent Test**: generate demo-only events and real events on the same day,
verify that real metrics exclude demo data by default, then confirm the day's
IDS repository changes are recorded in the changelog.

**Acceptance Scenarios**:

1. **Given** demo/test events exist in the system, **When** an administrator
   views default IDS metrics and trend charts, **Then** demo/test events are not
   counted as real security incidents.
2. **Given** a maintainer explicitly opens demo/test views, **When** they review
   the events, **Then** those events are visibly marked as non-production.
3. **Given** IDS-related work is completed for the day, **When** a reviewer
   opens the repository changelog, **Then** the day's changes are documented in a
   dated entry tied to the active branch workflow.

---

### Edge Cases

- What happens when one attack activity produces repeated detections from
  multiple sources in a short review window?
- How does the system handle an upstream detector source that is configured but
  currently unavailable or has unknown provenance metadata?
- What happens when historical demo events already exist in the same datastore
  as real events?
- How does the workflow behave when a blocking or unblocking action fails after
  the event has already been recorded?
- What happens when a shared backend path must change to support IDS refactor
  work without breaking non-IDS business flows?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST classify IDS events by origin, including real
  detections, demo/test events, and project-seeded examples.
- **FR-002**: The system MUST normalize detections from mature external sources
  and project-specific rules into one shared reviewable incident record.
- **FR-003**: The system MUST preserve source provenance for every event,
  including detector identity, rule or signal source, and enough context for a
  reviewer to understand why the event was raised.
- **FR-004**: The system MUST preserve evidence for every event, including
  relevant request, file, log, or payload snippets appropriate to the event
  type.
- **FR-005**: Authorized reviewers MUST be able to set incident status, add
  review notes, record response actions, and archive incidents without deleting
  the audit trail.
- **FR-006**: Real IDS metrics and trend views MUST exclude demo/test events by
  default.
- **FR-007**: The system MUST provide an explicit way to review demo/test events
  separately from real incidents.
- **FR-008**: The system MUST show whether a detection came from a mature
  external source or a project-specific custom rule.
- **FR-009**: The system MUST preserve incidents even when automated remediation
  fails, and MUST surface the failure to reviewers.
- **FR-010**: The system MUST support correlation or deduplication of repeated
  detections that represent the same attack activity within a review window.
- **FR-011**: The system MUST provide maintainers with enough metadata to assess
  whether an active detection source is current, stale, or missing provenance.
- **FR-012**: The project workflow supporting this feature MUST maintain a dated
  IDS changelog entry for each active development day so reviewers can trace
  ongoing refactor progress.

### Key Entities *(include if feature involves data)*

- **IDS Incident**: A normalized review object representing one real or demo
  detection, including origin, provenance, evidence, severity, confidence,
  status, and archival state.
- **Detection Source**: The detector or rule source that produced a signal,
  including source type, provenance, freshness, and trust classification.
- **Response Action**: A recorded automated or manual action tied to an
  incident, such as block, unblock, status update, or archival.
- **Review Note**: Reviewer-supplied context explaining triage decisions, false
  positive assessment, mitigation outcome, or follow-up work.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can open a newly ingested real incident and complete
  triage with evidence, provenance, status update, and archival actions in one
  workflow without consulting source code.
- **SC-002**: Default IDS dashboard counts and trend charts exclude demo/test
  events for all newly generated incidents in the refactored scope.
- **SC-003**: Every active detection source used in the first refactor phase has
  visible provenance and freshness context available to maintainers.
- **SC-004**: Repeated detections for the same short-window attack activity are
  reduced to a bounded review set rather than an uncontrolled alert flood.
- **SC-005**: Each development day that changes IDS behavior produces a dated
  entry in the IDS changelog that can be matched to repository activity.

## Assumptions

- The first refactor phase focuses on the existing platform security-center and
  IDS flows already present in the repository rather than introducing a new
  standalone product.
- Mature detector onboarding will be incremental; not every detector family is
  expected in the first delivery slice.
- Existing administrator roles and security-center navigation remain in place
  during the first phase of the refactor.
- The team will continue to work on `security-center/feature-ids` and submit
  pull requests into `security-center/collab-setup`.
