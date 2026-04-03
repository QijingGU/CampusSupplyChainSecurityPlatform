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

As an operator, I can use Chinese labels in the audit page to search IDS logs,
view sensitive operations, and review audit summaries without switching context.

**Independent Validation**:

- audit page supports new filters and pagination,
- IDS tab and sensitive tab show expected records,
- summary cards update with query scope.

## Functional Requirements

1. `GET /api/audit` must support query filters:
   `action`, `target_type`, `user_name`, `keyword`, `start_at`, `end_at`,
   `ids_only`, `sensitive_only`, `page`, `page_size`.
2. `GET /api/audit` must return paginated shape:
   `total`, `page`, `page_size`, `items`, `summary`, `filters`.
3. Backend must classify IDS actions using `ids_` prefix and expose `is_ids`.
4. Backend must classify sensitive actions and expose `is_sensitive`.
5. IDS APIs must write audit logs for:
   source sync, source package preview (success/rejected), source package
   activation (success/rejected), rulepack activation (success/rejected/failed).
6. Frontend audit page must provide Chinese-first UI for:
   tab filtering, multi-field filters, summary cards, and pagination.

## Non-Goals

- No schema migration for audit table fields.
- No external SIEM integration in this slice.
- No role expansion beyond `system_admin` for audit page access.

## Success Criteria

- Reviewer can locate IDS activation/rejection logs within one page operation.
- Existing build (`npm run build`) and backend syntax checks remain green.
- Audit panel can be demonstrated fully in Chinese labels.
