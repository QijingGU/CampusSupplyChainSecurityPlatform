# Implementation Plan: IDS Mature Rulepack Adoption

**Branch**: `security-center/feature-ids` | **Date**: 2026-04-03 | **Spec**: [spec.md](/D:/ids/CampusSupplyChainSecurityPlatform/specs/004-ids-mature-rulepack-adoption/spec.md)
**Input**: Feature specification from `/specs/004-ids-mature-rulepack-adoption/spec.md`

## Summary

Add a mature-rulepack catalog and activation workflow for inline IDS matching.
This replaces pure hardcoded matcher dependence with controlled reuse of
curated mature signatures while preserving auditability and demo isolation.

## Technical Context

**Language/Version**: Python 3.11, TypeScript 5, Vue 3  
**Primary Dependencies**: FastAPI, SQLAlchemy, Pydantic, Element Plus  
**External Rule / Signal Sources**: Curated mature rulepack definitions reused
from proven external patterns (first slice maintained in-project)  
**Storage**: Existing application database for activation history and runtime
state  
**Testing**: API-level manual quickstart validation plus local syntax checks  
**Target Platform**: Existing backend API and frontend security-center web app  
**Project Type**: Web application with backend API and frontend UI  
**Performance Goals**: Keep inline matching overhead comparable to current
local matcher for request-level detection  
**Constraints**: Keep diff narrow to IDS/security-center paths, keep
`demo_test` non-trusted, preserve branch workflow, and maintain audit records
for failed operations  
**Scale/Scope**: First delivery covers rulepack catalog, activation state,
runtime matcher switch, and activation history

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Detection Integrity Over Demo Effects**: PASS. `demo_test` rulepacks stay
  visible but blocked from trusted activation.
- **Reuse Mature Detection Sources First**: PASS. This slice explicitly shifts
  matcher logic toward curated mature packs.
- **Traceable Response Loop**: PASS. Activation attempts and runtime provenance
  are recorded and queryable.
- **Daily Changelog And Remote Sync Discipline**: PASS. Tasks include changelog
  and push/PR readiness updates.
- **Conflict-Minimizing Change Scope**: PASS. Planned files remain under IDS
  backend, IDS API, and security-center frontend API/view.

## Project Structure

### Documentation (this feature)

```text
specs/004-ids-mature-rulepack-adoption/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- ids-rulepack-adoption.md
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
|   |   `-- ids_rulepack.py
|   |-- services/
|   |   |-- ids_engine.py
|   |   `-- ids_rulepacks.py
|   `-- schema_sync.py

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

**Structure Decision**: Implement the runtime rulepack behavior as an extension
of the current IDS API/middleware path, with dedicated service/model files to
avoid bloating existing source-package modules.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Runtime state recorded in IDS-specific table | Need deterministic active pack and auditable transitions | In-memory only state would lose activation trace on restart |
| Curated pack catalog inside backend service for V1 | Fast integration with narrow diffs and review clarity | Remote feed fetch in first slice adds infra complexity and merge risk |
