# Feature Specification: IDS Source Real Sync

**Feature Branch**: `security-center/feature-ids-realize-ui`  
**Created**: 2026-04-06  
**Status**: Implemented  
**Input**: User description: "The IDS source-sync area still behaves like a flower-rack. Make the security-center source sync real, keep AI-audited upload/sandbox flows intact, update the docs, and prepare a demo script."

## User Scenarios & Testing

### User Story 1 - Register A Sync-Backed Source (Priority: P1)

A security maintainer creates or edits an IDS source with a real sync endpoint so
the source record is executable instead of being a metadata-only placeholder.

**Independent Test**: save one trusted source with
`app/data/ids_source_sync/suricata-web-prod.manifest.json` as the sync endpoint,
reload the security-center IDS page, and verify the source row shows the saved
endpoint.

### User Story 2 - Run Real Manifest Sync (Priority: P1)

A maintainer triggers source sync and the backend reads a real local manifest and
rule artifact, computes package metadata, and records a new sync attempt.

**Independent Test**: trigger sync for `suricata-web-prod` and verify the result
returns `package_version=2026.04.07`, `rule_count=15`, the artifact path, and a
SHA-256 value.

### User Story 3 - Review Sync Audit And Package Intake (Priority: P1)

A reviewer opens the IDS source history and can see both the sync audit record
and the resulting package-intake row without consulting backend logs.

**Independent Test**: open the history dialog for `suricata-web-prod` and verify
that Sync Audit shows the manifest path and operator, while package intake shows
the previewed version and intake detail.

### User Story 4 - Keep The Slice Reproducible (Priority: P2)

A collaborator can reproduce the same real sync locally from the repo fixture and
understand what remains out of scope.

**Independent Test**: follow `quickstart.md`, use the bundled fixture files, and
confirm the same IDS source row is populated from local artifacts, then verify a
fresh backend startup bootstraps the fixture into a visible source/package state
without requiring external network access.

## Edge Cases

- `sync_endpoint` is missing for a source that is otherwise marked `manual` or
  `scheduled`.
- The manifest JSON exists but is malformed.
- The manifest `source_key`, `trust_classification`, or `detector_family` does
  not match the saved source record.
- The artifact path exists in the manifest but resolves outside the repository.
- A source is `disabled`, `draft`, or `not_applicable`, so sync must be skipped
  or failed without faking success.
- Repeated manual syncs import the same package version and should still leave an
  auditable sync attempt instead of silently doing nothing.
- Fresh or reset local environments must still expose one reviewable external
  rule source after startup, even before an operator manually opens the IDS
  source panel.

## Requirements

### Functional Requirements

- **FR-001**: Each non-`not_applicable` IDS source MUST store a real
  `sync_endpoint`.
- **FR-002**: `POST /api/ids/sources/{source_id}/sync` MUST load a real local
  manifest file from the repository or backend workspace.
- **FR-003**: The manifest flow MUST validate source identity and reject
  mismatched `source_key`, `trust_classification`, or `detector_family`.
- **FR-004**: Successful source sync MUST compute and persist package version,
  release timestamp, artifact path, artifact SHA-256, artifact size, and rule
  count.
- **FR-005**: Successful source sync MUST create both a sync-attempt record and
  a package-intake record.
- **FR-006**: Sync failures and skipped runs MUST remain visible in source audit
  history.
- **FR-007**: `SecurityIDS.vue` MUST expose the saved sync endpoint, latest sync
  package metadata, and the resulting Sync Audit history.
- **FR-008**: The bundled fixture manifest and rule file MUST be usable for local
  validation and demo runs.
- **FR-009**: Fresh/offline environments MUST bootstrap the bundled external
  static rule fixture into a reviewable source/package state without external
  network access.
- **FR-010**: This slice MUST remain scoped to IDS/security-center/backend sync
  paths plus supporting docs/specs.

### Key Entities

- **Sync-Backed IDS Source**: persisted source registry row including
  `sync_endpoint`.
- **Source Sync Attempt**: timestamped audit record including result, detail,
  package version, package intake id, and resolved manifest path.
- **Artifact-Backed Package Intake**: preview/intake row including version,
  provenance, artifact path, artifact hash, artifact size, and derived rule
  count.
- **Bootstrap Runtime Fixture**: startup-created trusted source/package state
  backed by the bundled local manifest/rule artifact.

## Success Criteria

- **SC-001**: The IDS source row shows a persisted sync endpoint instead of only
  free-text provenance.
- **SC-002**: Manual sync produces a new sync attempt with real artifact-backed
  metadata rather than the old "Metadata refresh completed." placeholder.
- **SC-003**: The latest package preview on the IDS source row shows version plus
  rule-count/hash context from the imported artifact.
- **SC-004**: The history dialog exposes Sync Audit and package intake details
  for the same source.
- **SC-005**: Backend syntax validation, frontend build, API validation, and
  browser validation all pass on this slice.

## Validation Snapshot

- Backend validation passed:
  `python -m py_compile backend/app/api/ids.py backend/app/models/ids_source.py backend/app/models/ids_source_package.py backend/app/schema_sync.py backend/app/services/ids_source_packages.py backend/app/services/ids_source_sync.py`
- Frontend validation passed:
  `cd frontend && npm run build`
- API validation passed on 2026-04-06:
  - created or reused `suricata-web-prod`,
  - triggered real sync from `app/data/ids_source_sync/suricata-web-prod.manifest.json`,
  - received `package_version=2026.04.07`, `rule_count=15`,
    `artifact_path=backend/app/data/ids_source_sync/suricata-web-prod.rules`,
    and a persisted SHA-256.
- Browser validation passed with gstack on 2026-04-06:
  - `/security/ids` shows the source sync endpoint in the row,
  - row-level sync details show the manifest path and imported package version,
  - `执行同步` creates a second sync attempt and a second artifact-backed intake,
  - the history dialog shows Sync Audit plus the resulting package intake record.

## Assumptions And Residual Scope

- This slice makes local manifest sync real; external network pulls and a real
  scheduler for `sync_mode=scheduled` remain out of scope.
- `SecurityIDS.vue` still contains separate demo/test tooling such as demo
  injection and demo-only incident filters.
- The upload AI audit, sandbox, and situation pages from `specs/006` remain real
  and unchanged by this slice.
