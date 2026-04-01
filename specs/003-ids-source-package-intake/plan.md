# Implementation Plan: IDS Source Package Intake

**Branch**: `security-center/feature-ids` | **Date**: 2026-04-01 | **Spec**: [spec.md](/D:/ids/CampusSupplyChainSecurityPlatform/specs/003-ids-source-package-intake/spec.md)
**Input**: Feature specification from `/specs/003-ids-source-package-intake/spec.md`

## Summary

Extend IDS source operations with a trusted package intake workflow. This slice
adds previewable package manifests, traceable package activation, and visible
package history so mature-source updates become operationally reviewable instead
of staying informal.

## Technical Context

**Language/Version**: Python 3.11, TypeScript 5, Vue 3  
**Primary Dependencies**: FastAPI, SQLAlchemy, Pydantic, Element Plus, ECharts  
**External Rule / Signal Sources**: Trusted upstream package manifests, reviewed
source version metadata, existing source registry records  
**Storage**: Existing SQLite/PostgreSQL-backed application database  
**Testing**: Existing manual quickstart validation plus API-level local
validation for package preview and activation workflows  
**Target Platform**: Existing backend API and frontend security-center web app  
**Project Type**: Web application with backend API and frontend security center  
**Performance Goals**: Keep package-preview and source-detail views responsive
for a small operational source inventory  
**Constraints**: Keep diffs narrow to IDS/security-center paths, preserve the
current collaboration branch workflow, and prevent `demo_test` packages from
being treated as trusted production coverage  
**Scale/Scope**: First delivery covers package preview, activation records, and
package history visibility for current IDS source operations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Detection Integrity Over Demo Effects**: PASS. The plan keeps `demo_test`
  packages visibly separate from trusted production-oriented package history.
- **Reuse Mature Detection Sources First**: PASS. The slice focuses on intake of
  mature upstream package metadata rather than expanding local matcher logic.
- **Traceable Response Loop**: PASS. Preview, activation, and failed package
  attempts remain auditable.
- **Daily Changelog And Remote Sync Discipline**: PASS. The plan includes
  changelog and branch-workflow tracking for package-intake work.
- **Conflict-Minimizing Change Scope**: PASS. Planned changes stay within IDS
  backend, source-operation storage, and security-center views.

## Project Structure

### Documentation (this feature)

```text
specs/003-ids-source-package-intake/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- ids-source-package-intake.md
`-- tasks.md
```

### Source Code (repository root)

```text
backend/
|-- app/
|   |-- api/
|   |   `-- ids.py
|   |-- models/
|   |   |-- ids_source.py
|   |   `-- ids_source_package.py
|   |-- schema_sync.py
|   `-- services/
|       `-- ids_source_packages.py

frontend/
`-- src/
    |-- api/
    |   `-- ids.ts
    `-- views/
        `-- security/
            `-- SecurityIDS.vue

docs/
`-- ids-changelog.md
```

**Structure Decision**: Reuse the current IDS source-operations API and
security-center screen. Add package intake as an extension of the existing
source registry instead of creating a separate admin surface.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Package intake handled inside the existing IDS API instead of a new module | Keeps the diff narrow in the current collaboration branch | A separate module would add routing churn without meaningful isolation for the first package-intake slice |
| Manifest preview is supported before live upstream fetch | The team needs controlled source updates now | Waiting for full live feed automation would leave mature-source updates manual and undocumented |
