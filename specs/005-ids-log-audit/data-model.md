# Data Model: IDS Log Audit Enhancement

## Persisted Model (Reused)

### AuditLog

- `id: int`
- `user_id: int | null`
- `user_name: str`
- `user_role: str`
- `action: str`
- `target_type: str`
- `target_id: str`
- `detail: str`
- `created_at: datetime`

## Derived View Fields

- `is_ids: bool` -> `action.startswith("ids_")`
- `is_sensitive: bool` -> `action in sensitive_action_set`

## Query Dimensions

- direct filters: `action`, `target_type`, `user_name`
- fuzzy filter: `keyword` against user/action/target/detail
- time range: `start_at`, `end_at`
- semantic filters: `ids_only`, `sensitive_only`
- pagination: `page`, `page_size`

## Summary Metrics

- `total`
- `ids_count`
- `sensitive_count`
- `today_count`
- top grouped counts by action/user/target_type
