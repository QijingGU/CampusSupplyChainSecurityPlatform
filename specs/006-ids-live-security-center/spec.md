# Feature Specification: IDS Live Security Center Parity

**Feature Branch**: `security-center/feature-ids-realize-ui`  
**Created**: 2026-04-05  
**Status**: Implemented  
**Input**: User description: "The IDS demo surface is larger than the real capability. Keep changes inside the security-center / IDS scope, make the upload gate, sandbox, and situation pages real, and sync the docs."

## User Scenarios & Testing

### User Story 1 - Gate Public Uploads With AI Audit (Priority: P1)

A public upload is AI-audited before release. Safe files are released to the
accepted upload area, while suspicious or review-required files are withheld
into the sandbox.

**Why this priority**: the public upload page is the first operator-facing
control point. It must stop behaving like a pure demo.

**Independent Test**: upload one benign text file and one suspicious script,
then verify the benign file is accepted and the suspicious file is withheld.

**Acceptance Scenarios**

1. **Given** a file with low-risk content and no dangerous indicators, **When**
   it is uploaded through `/upload`, **Then** the system returns an audit
   verdict of `pass`, stores the file under `uploads/accepted`, and provides a
   public file URL.
2. **Given** a file with WebShell, dynamic execution, downloader, binary
   payload, or risky extension signals, **When** it is uploaded through
   `/upload`, **Then** the system returns a `review` or `quarantine` decision,
   stores the file under `quarantine_uploads`, persists an audit report, and
   does not expose the file through the public accepted path.
3. **Given** a file is withheld by the upload gate, **When** the operator opens
   the sandbox or situation page, **Then** the same upload can be traced as a
   real sandbox sample and a real IDS-facing incident.

---

### User Story 2 - Run Real Quarantine Analysis (Priority: P1)

A security maintainer can run backend analysis against an existing quarantined
sample and reopen the persisted report after refresh.

**Why this priority**: the sandbox page had the largest gap between frontend
promise and backend behavior.

**Independent Test**: upload a suspicious file, run sandbox analysis, refresh
the page, and reopen the same report.

**Acceptance Scenarios**

1. **Given** at least one quarantined sample exists, **When** the operator
   calls `POST /api/upload/quarantine/analyze`, **Then** the backend analyzes a
   real file, persists the report, and returns phase logs plus report content.
2. **Given** a report was already generated, **When** the operator reloads
   `/security/sandbox`, **Then** the latest report metadata remains available in
   `latest_report`.
3. **Given** the quarantine directory is empty, **When** analysis is requested,
   **Then** the backend returns actionable feedback instead of fabricating a
   synthetic sample.

---

### User Story 3 - Show Real Situation Telemetry (Priority: P1)

A reviewer can open the security situation page and see event-driven telemetry
derived from real IDS incidents.

**Why this priority**: the situation page visually reads like an operational big
screen and should not be backed by random animation state.

**Independent Test**: create at least one real IDS incident through the upload
gate, open `/security/situation`, and verify counters plus recent incidents are
derived from backend data.

**Acceptance Scenarios**

1. **Given** recent real IDS incidents exist, **When** the situation page
   loads, **Then** total blocked count, active threat count, source count, and
   recent attack list are populated from `GET /api/ids/situation`.
2. **Given** no recent incidents exist, **When** the situation page loads,
   **Then** the page still renders a valid empty state instead of generating
   random attacks.
3. **Given** source geolocation is only deterministic IP-derived visualization,
   **When** the world map renders, **Then** the UI explicitly labels the
   coordinates as derived approximation, not exact threat intelligence.

---

### User Story 4 - Keep IDS Work Traceable (Priority: P2)

A collaborator can review this slice and understand what became real, how it
was validated, and what demo-only capability still remains elsewhere in IDS.

**Why this priority**: this branch is collaborative and IDS work is being
tracked slice-by-slice.

**Independent Test**: inspect `specs/006`, `docs/ids-demo-script.md`, and
`docs/ids-changelog.md`, then follow the documented validation flow.

**Acceptance Scenarios**

1. **Given** the upload, sandbox, and situation changes are implemented,
   **When** a reviewer reads the docs, **Then** they can reproduce the shipped
   flow and understand the actual API boundaries.
2. **Given** other IDS pages still retain demo or legacy affordances, **When**
   a reviewer reads the docs, **Then** those residual areas are called out
   explicitly instead of being mistaken for this slice's scope.

## Edge Cases

- AI audit infrastructure is unavailable and the upload gate must fall back to
  heuristic policy.
- A quarantined file is deleted between list and analyze actions.
- A binary file has almost no printable preview content.
- The same sample is analyzed multiple times in succession.
- The situation page has zero real incidents but some demo/test incidents exist.
- Reviewers confuse the active security-center route with the legacy
  `frontend/src/views/ids/IDSManage.vue` file.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST AI-audit every public upload before deciding
  whether it is accepted or withheld.
- **FR-002**: Accepted uploads MUST be stored in `backend/uploads/accepted/`.
- **FR-003**: Non-pass uploads (`review` or `quarantine`) MUST be withheld in
  `backend/quarantine_uploads/` and MUST not share the public accepted URL.
- **FR-004**: Each upload decision MUST persist audit metadata including verdict,
  risk level, confidence, summary, evidence, recommended actions, provider, and
  analysis mode.
- **FR-005**: Withheld uploads MUST be visible through
  `GET /api/upload/quarantine`.
- **FR-006**: The sandbox MUST support report reopening through
  `GET /api/upload/quarantine/{filename}/report`.
- **FR-007**: The sandbox MUST support real analysis execution through
  `POST /api/upload/quarantine/analyze`.
- **FR-008**: Generated sandbox reports MUST be persisted under
  `backend/upload_reports/` and survive page refresh.
- **FR-009**: Withheld uploads MUST create a real IDS-facing trace that can
  appear in the situation flow.
- **FR-010**: The situation page MUST read from `GET /api/ids/situation`.
- **FR-011**: Situation telemetry MUST default to real incidents and MUST not
  synthesize random attacks when no data exists.
- **FR-012**: Approximate map positions MUST remain clearly labeled as derived
  IP-based visualization.
- **FR-013**: This slice MUST stay within IDS, upload, security-center, and
  documentation paths.
- **FR-014**: The docs MUST record residual demo/test scope in
  `SecurityIDS.vue` and the legacy status of `IDSManage.vue`.

### Key Entities

- **Upload Audit Decision**: persisted audit-stage decision containing verdict,
  risk level, confidence, summary, evidence, recommended actions, provider,
  analysis mode, and AI availability metadata.
- **Quarantine Analysis Report**: persisted report for one quarantined file,
  including file identity, hash, indicators, audit context, report sections, and
  storage location.
- **Quarantine Item**: list-row projection for the sandbox table including saved
  name, size, modified time, risk, verdict, confidence, and summary.
- **Situation Attack Snapshot**: recent real IDS incident projected into the
  situation feed with approximate source location and protected target metadata.
- **Situation Summary**: operator payload containing generation time, real-event
  scope, disclaimer, protected target, metrics, and recent attacks.

## Success Criteria

- **SC-001**: A suspicious upload never lands in the accepted public path.
- **SC-002**: A benign upload is released through `/uploads/accepted/...`.
- **SC-003**: Sandbox analysis operates on a real quarantined file and returns a
  persisted report.
- **SC-004**: Refreshing the sandbox page preserves latest report visibility.
- **SC-005**: The situation page renders from backend incident data rather than
  random attack generation.
- **SC-006**: Backend syntax validation passes for the updated IDS and upload
  files.
- **SC-007**: Frontend production build passes after the current IDS/UI changes.
- **SC-008**: Manual and gstack QA confirm the suspicious-upload, sandbox, and
  situation flow end to end.

## Validation Snapshot

- Backend validation passed:
  `python -m py_compile backend/app/api/upload.py backend/app/api/ids.py backend/app/services/upload_ai_audit.py`
- Frontend validation passed:
  `cd frontend && npm run build`
- Manual and gstack walkthrough confirmed:
  - suspicious `codex-webshell.php` upload is withheld into the sandbox,
  - benign `codex-note.txt` upload is accepted,
  - `/security/sandbox` shows the quarantined sample and audit metadata,
  - `/security/situation` shows the resulting real malware incident.

## Assumptions And Residual Scope

- This slice builds on the earlier IDS event/source/package work from `001` to
  `003`.
- `frontend/src/views/security/SecurityIDS.vue` remains the active IDS workbench
  and still intentionally retains demo/test tooling such as demo event filters,
  demo injection, and `demo_test` package visualization.
- `frontend/src/views/ids/IDSManage.vue` remains a legacy compatibility page and
  is not the active security-center workflow.
- Exact third-party geo-IP intelligence remains out of scope. Deterministic
  approximate mapping is acceptable when labeled.
