# Requirements Checklist: IDS Log Audit Enhancement

- [X] `/api/audit` supports multi-field filters and pagination.
- [X] `/api/audit` supports IDS-specific filters (`ids_domain`, `ids_outcome`).
- [X] `/api/audit` returns summary and filter options.
- [X] IDS summary includes domain/outcome dimensions.
- [X] IDS critical operations write audit records.
- [X] Rejected/failed IDS paths are auditable.
- [X] Audit UI is Chinese-first and keeps business audit and IDS audit on separate pages.
- [X] IDS audit has a dedicated security-center page (`/security/audit`).
- [X] Generic `/audit` focuses on business daily audit (IDS records excluded by default).
- [X] Demo-only IDS operation controls are disabled by default in production workflow.
- [X] Backend compile checks pass.
- [X] Frontend build passes.
