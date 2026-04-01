# Implementation Plan: IDS Refactor Foundation

**Branch**: `security-center/feature-ids` | **Date**: 2026-04-01 | **Spec**: [spec.md](/D:/ids/CampusSupplyChainSecurityPlatform/specs/001-ids-refactor/spec.md)
**Input**: Feature specification from `/specs/001-ids-refactor/spec.md`

## Summary

Refactor the existing IDS from a demo-heavy security-center feature into a
traceable incident workflow. The first implementation slice will separate real
events from demo/test events, normalize detector provenance, preserve review and
response history, and establish an ingestion boundary for mature external
detection sources instead of further expanding local hand-written signatures.

## Technical Context

**Language/Version**: Python 3.11, TypeScript 5, Vue 3  
**Primary Dependencies**: FastAPI, SQLAlchemy, Pydantic, Element Plus, ECharts  
**External Rule / Signal Sources**: Transitional local matcher, upstream WAF or
rule-engine outputs, Suricata EVE-style network events, YARA-style file events,
future Sigma-mapped log events  
**Storage**: Existing SQLite/PostgreSQL-backed application database  
**Testing**: Existing manual verification plus new API/service-level validation
for normalized IDS workflows  
**Target Platform**: Existing backend and frontend web application deployment  
**Project Type**: Web application with backend API and frontend security center  
**Performance Goals**: Preserve current dashboard responsiveness while allowing
bounded event correlation and filtering on recent incident history  
**Constraints**: Minimize change scope to IDS/security-center areas, maintain
current collaboration branch workflow, avoid adding more demo coupling  
**Scale/Scope**: First slice covers current in-app IDS and prepares ingestion
contracts for mature external sources without attempting a one-shot full SOC
platform rewrite

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Detection Integrity Over Demo Effects**: PASS. The plan introduces explicit
  event origin classification and default real-only metrics.
- **Reuse Mature Detection Sources First**: PASS. The plan expands source
  ingestion boundaries and provenance tracking instead of growing the local
  regex rule set.
- **Traceable Response Loop**: PASS. The plan extends the incident record to
  keep provenance, evidence, response outcomes, and review notes.
- **Daily Changelog And Remote Sync Discipline**: PASS. The plan includes
  mandatory changelog updates and branch-sync tasks.
- **Conflict-Minimizing Change Scope**: PASS. Planned code changes stay within
  backend IDS paths, security-center frontend paths, specs, and docs unless a
  shared dependency is unavoidable.

## Project Structure

### Documentation (this feature)

```text
specs/001-ids-refactor/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- ids-ingestion.md
`-- tasks.md
```

### Source Code (repository root)

```text
backend/
|-- app/
|   |-- api/
|   |   `-- ids.py
|   |-- middleware/
|   |   `-- ids_middleware.py
|   |-- models/
|   |   `-- ids_event.py
|   `-- services/
|       |-- ids_ai_analysis.py
|       `-- ids_engine.py

frontend/
`-- src/
    |-- api/
    |   `-- ids.ts
    `-- views/
        |-- ids/
        |   `-- IDSManage.vue
        `-- security/
            |-- SecurityCenterLayout.vue
            `-- SecurityIDS.vue

docs/
`-- ids-changelog.md
```

**Structure Decision**: Keep the current web-app split. Refactor the backend IDS
flow into clearer incident, source, and ingestion responsibilities while
preserving the security-center frontend entry points already used by the team.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Transitional local matcher retained temporarily | The current app still depends on in-process request inspection for continuity | Removing it before source provenance and external ingestion exist would break current detection visibility without providing a replacement |
| Separate demo isolation logic instead of deleting demos immediately | The team still needs controlled demos and presentations | Hard deletion would reduce short-term demonstrability but would not solve the core trust problem of mixed data |
