<!--
Sync Impact Report
Version change: template -> 1.0.0
Modified principles:
- [PRINCIPLE_1_NAME] -> I. Detection Integrity Over Demo Effects
- [PRINCIPLE_2_NAME] -> II. Reuse Mature Detection Sources First
- [PRINCIPLE_3_NAME] -> III. Traceable Response Loop
- [PRINCIPLE_4_NAME] -> IV. Daily Changelog And Remote Sync Discipline
- [PRINCIPLE_5_NAME] -> V. Conflict-Minimizing Change Scope
Added sections:
- Delivery Constraints
- Quality Gates
Removed sections:
- None
Templates requiring updates:
- updated: .specify/templates/plan-template.md
- updated: .specify/templates/spec-template.md
- updated: .specify/templates/tasks-template.md
Follow-up TODOs:
- None
-->
# Campus Supply Chain Security Platform Constitution

## Core Principles

### I. Detection Integrity Over Demo Effects
All IDS-facing metrics, reports, alerts, and operator actions MUST be backed by
real backend evidence or be explicitly labeled as demo/test data. Demo flows
MUST remain isolated from the real detection path, MUST be excluded from real
security metrics by default, and MUST never be presented as proof of production
effectiveness.

Rationale: the current system has accumulated presentation-heavy behavior that
obscures real detection value. This project exists to reverse that bias.

### II. Reuse Mature Detection Sources First
The project MUST prefer proven external detection sources before expanding
project-specific rule logic. Mature sources include upstream rule packs,
signature feeds, detector engines, and established file or log matching
ecosystems. Custom rules are allowed only when they address campus-specific
business behavior, fill a documented gap, or adapt upstream outputs into the
platform's incident model.

Every new detector integration MUST record provenance, update cadence, and the
reason it was selected. Every custom detector addition MUST document why an
existing mature source was insufficient.

Rationale: time-tested detections usually outperform newly invented local rules
for common attack classes and reduce false confidence.

### III. Traceable Response Loop
Every IDS event MUST preserve enough information to support triage, response,
audit, and retrospective review. At minimum, events MUST keep origin, evidence,
severity, confidence, timestamps, disposition status, operator notes, and any
automated or manual response actions. Failed blocking or remediation attempts
MUST be recorded rather than discarded.

Rationale: an IDS without a reliable review loop becomes a dashboard, not a
security control.

### IV. Daily Changelog And Remote Sync Discipline
Any change that affects IDS behavior, security-center workflows, detector
sources, demo isolation, or event handling MUST update `docs/ids-changelog.md`
on the same day. Active work on IDS MUST be pushed to the agreed remote branch
at the end of each development day unless blocked by an unresolved conflict or
an explicit hold instruction.

Commit messages for this area MUST start with `feat:`, `fix:`, or `chore:`.

Rationale: the project is collaborative, review-driven, and time-bounded. Daily
visibility is required to prevent drift and lost work.

### V. Conflict-Minimizing Change Scope
IDS work MUST stay inside security-center, IDS, or directly related backend
integration paths unless a shared dependency truly requires expansion. When a
change touches shared modules, the author MUST document the blast radius, keep
the diff minimal, and verify that unrelated workflows are not being silently
rewired to support IDS demos.

Rationale: the repository is multi-domain and already has collaboration
pressure. Narrow changes reduce merge pain and accidental regressions.

## Delivery Constraints

- The current collaboration branch strategy remains authoritative:
  `security-center/collab-setup` is the integration branch and active IDS
  development continues on `security-center/feature-ids` or a similarly scoped
  `security-center/*` branch approved by the team.
- IDS refactor increments MUST favor real event ingestion, normalization,
  triage, and detector provenance before additional visual polish.
- Demo functionality may be retained only when it is clearly separated, easy to
  disable, and does not contaminate operational statistics or reviewer trust.
- External detector onboarding MUST be incremental. The team SHOULD phase
  integrations instead of attempting a one-shot replacement of every detector
  family.

## Quality Gates

- Before implementation planning, each IDS refactor scope MUST define:
  1. what counts as real events,
  2. what remains demo-only,
  3. which mature detector sources are in scope,
  4. how event provenance will be surfaced to reviewers.
- Before merging, every IDS-facing change MUST show:
  1. event-source separation,
  2. preserved auditability,
  3. updated changelog entry,
  4. an explicit note on conflict risk or shared-module impact.
- New detections, response actions, or status workflows MUST be independently
  testable at the API or service level even if the UI layer is still evolving.

## Governance

This constitution overrides ad hoc IDS experimentation and informal workflow
shortcuts. Any plan, task list, or pull request that conflicts with these rules
is non-compliant until the conflict is resolved or the constitution is amended.

Amendments require a documented rationale, a semantic version update, and any
necessary template or workflow synchronization. Versioning follows semantic
rules: MAJOR for incompatible governance changes, MINOR for new principles or
material obligations, PATCH for wording clarifications with no behavioral
change.

Compliance is reviewed whenever IDS-related specifications, plans, tasks, or
pull requests are updated. Reviewers MUST call out violations explicitly rather
than assuming they will be fixed later.

**Version**: 1.0.0 | **Ratified**: 2026-04-01 | **Last Amended**: 2026-04-01
