# Feature Specification: IDS Upload Evidence Chain

**Feature Branch**: `security-center/feature-ids-realize-ui`  
**Created**: 2026-04-06  
**Status**: Implemented  
**Input**: User description: "Keep pushing IDS so the flower-rack parts become real. Make upload AI audit, sandbox retention, and the IDS workbench connect as one traceable flow."

## User Scenarios & Testing

### User Story 1 - Review Upload Audit Inside IDS (Priority: P1)

A security operator opens an upload-gated IDS incident and can review the
quarantined sample metadata without guessing from raw strings.

**Independent Test**: open a recent `upload_ai_gate` incident in
`/security/ids`, then verify the drawer shows `Upload Audit Trace` with sample
identity, SHA-256, verdict, and audit summary.

### User Story 2 - Jump From IDS To The Exact Sandbox Report (Priority: P1)

An operator can move from an IDS incident back to the exact sandbox report for
the same quarantined sample.

**Independent Test**: click `打开沙箱报告` from the IDS event drawer and verify
`/security/sandbox` opens the report for the same `saved_as` sample.

### User Story 3 - Keep Reports Exportable And Traceable (Priority: P1)

The generated IDS event report keeps the same upload-audit trace so reviewers do
not need the live UI to understand why the sample was withheld.

**Independent Test**: request `GET /api/ids/events/{event_id}/report` for an
upload-gated incident and verify both `report.upload_trace` and the markdown
`Upload Audit Trace` section are present.

### User Story 4 - Keep The Slice Documented (Priority: P2)

A collaborator can understand the new IDS-to-sandbox linkage and demo it
without rediscovering the flow manually.

**Independent Test**: follow `docs/ids-demo-script.md` and the current quickstart
to narrate the upload, IDS, and sandbox evidence chain.

## Edge Cases

- Older upload incidents may lack the richer `sha256`, `size`, or
  `storage_location` fields and must still render from fallback parsing.
- An IDS incident may not originate from the upload gate and therefore must not
  show a fake upload trace block.
- The sandbox report deep link may point at a valid sample that already has a
  persisted report and should open that report directly instead of rerunning
  analysis.
- The route query may reference a sample that no longer exists in the sandbox.

## Requirements

### Functional Requirements

- **FR-001**: Upload-gated IDS incidents MUST serialize a structured
  `upload_trace` payload derived from persisted event evidence.
- **FR-002**: The upload-trace payload MUST preserve `saved_as`, original file
  name, SHA-256 when available, indicator summaries, audit verdict, audit risk,
  confidence, and audit summary.
- **FR-003**: `GET /api/ids/events/{event_id}/report` MUST include
  `report.upload_trace` for upload-gated incidents.
- **FR-004**: The generated IDS markdown report MUST include an
  `Upload Audit Trace` section when upload evidence exists.
- **FR-005**: `SecurityIDS.vue` MUST expose upload evidence in the event drawer
  and provide a direct jump to the matching sandbox report.
- **FR-006**: `SecuritySandbox.vue` MUST accept route-driven sample focus so a
  deep link can open the targeted report.
- **FR-007**: This slice MUST remain within IDS, upload, sandbox, and
  documentation paths.

### Key Entities

- **Upload Trace**: structured IDS incident sub-payload containing sample
  identity, hash, indicators, and AI audit output.
- **Sandbox Deep Link**: route-based navigation contract using
  `saved_as=<sample>&report=1`.
- **Report Trace Section**: exported markdown/report content that preserves the
  upload evidence chain for offline review.

## Success Criteria

- **SC-001**: An upload-gated IDS event drawer shows real upload evidence rather
  than only generic response text.
- **SC-002**: Clicking the IDS drawer action opens the exact sandbox report for
  the quarantined sample.
- **SC-003**: API report payloads and markdown exports preserve the upload audit
  trace.
- **SC-004**: Backend syntax compilation and frontend production build pass
  after the changes.
- **SC-005**: The changelog and demo script explicitly describe the new
  evidence-chain step.

## Validation Snapshot

- Backend validation passed:
  `python -m py_compile backend/app/api/ids.py backend/app/api/upload.py`
- Frontend validation passed:
  `cd frontend && npm run build`
- Direct backend validation passed on 2026-04-06:
  - latest `upload_ai_gate` event serialized a non-empty `upload_trace`,
  - latest report payload included `report.upload_trace`,
  - report markdown contained `Upload Audit Trace`.

## Assumptions And Residual Scope

- Existing upload, sandbox, and situation flows from `specs/006` remain the
  foundation for this slice.
- `SecurityIDS.vue` still retains demo/test seed tooling outside this scope.
- The sandbox deep link opens persisted reports and sample focus; it does not
  create a new investigation workflow beyond the existing sandbox page.
