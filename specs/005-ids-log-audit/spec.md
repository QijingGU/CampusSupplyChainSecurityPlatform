# Feature Specification: IDS Log Audit Enhancement

**Feature Branch**: `005-ids-log-audit`  
**Created**: 2026-04-03  
**Status**: Draft  
**Scope**: Security center IDS and audit panel

## Summary

Build a practical log-audit capability that supports IDS operations review:

- backend supports pagination and multi-dimensional filtering,
- IDS source/rulepack key operations leave auditable traces,
- frontend audit screen is Chinese-first and supports fast investigation.

## User Stories

### US1 - Audit Reviewer Filters and Traces (P1)

As a system admin, I can filter logs by action/target/operator/keyword/time range
with pagination and summary metrics, so I can quickly locate meaningful traces.

**Independent Validation**:

- `GET /api/audit` supports pagination and combined filters.
- response includes `items`, `total`, `summary`, and filter options.

### US2 - IDS Action Audit Coverage (P1)

As a security maintainer, I can see explicit audit records for IDS source sync,
source package preview/activation, and rulepack activation results, including
rejected/failed paths.

**Independent Validation**:

- trigger IDS source/package/rulepack operations and confirm related `ids_*`
  actions are written into audit logs.

### US3 - Chinese-First Audit UI (P2)

As an operator, I can use Chinese labels in both business audit and IDS audit
views, so I can separate daily supervision from security traceability without
confusing contexts.

**Independent Validation**:

- `/audit` focuses on business/sensitive logs and excludes IDS rows by default,
- `/security/audit` supports IDS module/result filtering and pagination,
- both pages keep Chinese-first labels and clear summary cards.

## Functional Requirements

1. `GET /api/audit` must support query filters:
   `action`, `target_type`, `user_name`, `keyword`, `start_at`, `end_at`,
   `ids_only`, `ids_domain`, `ids_outcome`, `sensitive_only`, `page`,
   `page_size`.
2. `GET /api/audit` must return paginated shape:
   `total`, `page`, `page_size`, `items`, `summary`, `filters`.
3. Backend must classify IDS actions using `ids_` prefix and expose `is_ids`.
4. Backend must classify sensitive actions and expose `is_sensitive`.
5. IDS APIs must write audit logs for:
   source sync, source package preview (success/rejected), source package
   activation (success/rejected), rulepack activation (success/rejected/failed).
6. Frontend audit views must provide Chinese-first UI:
   `/audit` for business/sensitive supervision and `/security/audit` for IDS
   traceability, each with multi-field filters and pagination.
7. IDS audit must be presented inside Security Center as a dedicated operational
   view, separated from business daily-audit pages.
8. Generic `/audit` page must support non-IDS review focus by excluding IDS
   records in its default workflow.
9. Demo-only IDS operation controls must be disabled by default and only be
   enabled when an explicit environment flag is turned on.

## Non-Goals

- No schema migration for audit table fields.
- No external SIEM integration in this slice.
- No role expansion beyond `system_admin` for audit page access.

## Success Criteria

- Reviewer can locate IDS activation/rejection logs within one page operation.
- Existing build (`npm run build`) and backend syntax checks remain green.
- Audit panel can be demonstrated fully in Chinese labels.
