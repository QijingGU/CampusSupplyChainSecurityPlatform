# Implementation Plan: IDS Source Operations

**Branch**: `security-center/feature-ids` | **Date**: 2026-04-01 | **Spec**: [spec.md](/D:/ids/CampusSupplyChainSecurityPlatform/specs/002-ids-source-operations/spec.md)
**Input**: Feature specification from `/specs/002-ids-source-operations/spec.md`

## Summary

Extend the normalized IDS workflow with trusted-source operations. This slice
adds a source registry, source health visibility, traceable synchronization
records, and a security-center management surface so the team can operate mature
detection sources deliberately instead of relying on undocumented source state.

## Technical Context

**Language/Version**: Python 3.11, TypeScript 5, Vue 3  
**Primary Dependencies**: FastAPI, SQLAlchemy, Pydantic, Element Plus, ECharts  
**External Rule / Signal Sources**: Trusted upstream detector metadata, manual
source sync workflows, transitional local matcher metadata, demo/test source
records  
**Storage**: Existing SQLite/PostgreSQL-backed application database  
**Testing**: Existing manual quickstart validation plus API-level local
validation for source registry and sync workflows  
**Target Platform**: Existing backend API and frontend security-center web app  
**Project Type**: Web application with backend API and frontend security center  
**Performance Goals**: Keep source-health views responsive for the expected
small operational source inventory while preserving current IDS dashboard
responsiveness  
**Constraints**: Keep diffs narrow to IDS/security-center paths, preserve the
current collaboration branch workflow, distinguish demo-only sources from
trusted production-oriented ones  
**Scale/Scope**: First delivery covers source registry CRUD, health visibility,
manual sync attempts, and incident linkage summaries for the current IDS scope

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Detection Integrity Over Demo Effects**: PASS. The plan keeps demo-only
  sources visibly separate from trusted production-oriented sources.
- **Reuse Mature Detection Sources First**: PASS. The slice focuses on
  operationalizing trusted sources instead of expanding local signature logic.
- **Traceable Response Loop**: PASS. Sync attempts and degraded source states
  remain visible rather than being hidden.
- **Daily Changelog And Remote Sync Discipline**: PASS. The plan includes
  source-operation changelog updates in the same IDS workflow.
- **Conflict-Minimizing Change Scope**: PASS. Planned changes stay within IDS
  backend, source registry storage, and security-center views.

## Project Structure

### Documentation (this feature)

```text
specs/002-ids-source-operations/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- ids-source-operations.md
`-- tasks.md
```

### Source Code (repository root)

```text
backend/
|-- app/
|   |-- api/
|   |   `-- ids.py
|   |-- models/
|   |   |-- ids_event.py
|   |   `-- ids_source.py
|   |-- schema_sync.py
|   `-- services/
|       `-- ids_ingestion.py

frontend/
`-- src/
    |-- api/
    |   `-- ids.ts
    `-- views/
        |-- ids/
        |   `-- IDSManage.vue
        `-- security/
            |-- SecurityCenterLayout.vue
            |-- SecurityIDS.vue
            `-- SecuritySituation.vue

docs/
`-- ids-changelog.md
```

**Structure Decision**: Reuse the existing IDS API and security-center entry
points. Add source operations as an extension of the IDS domain instead of
creating a separate admin module.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Source registry handled inside existing IDS API instead of a new service boundary | Keeps the diff narrow in the current collaboration branch | A separate module would increase merge risk without adding meaningful isolation for the first source-operations slice |
| Manual sync attempts supported before full automation | The team needs traceable operational state now | Waiting for fully automated upstream connectors would keep source freshness opaque and block reviewer trust |
