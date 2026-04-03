# API Contract: IDS Log Audit Enhancement

## 1) GET `/api/audit`

### Query Params

- `action?: string`
- `target_type?: string`
- `user_name?: string`
- `keyword?: string`
- `start_at?: datetime`
- `end_at?: datetime`
- `ids_only?: 0 | 1`
- `sensitive_only?: 0 | 1`
- `page?: number` (default 1)
- `page_size?: number` (default 50, max 200)

### Response

```json
{
  "total": 123,
  "page": 1,
  "page_size": 50,
  "items": [
    {
      "id": 99,
      "user_name": "system_admin",
      "user_role": "system_admin",
      "action": "ids_rulepack_activate",
      "target_type": "ids_rulepack",
      "target_id": "mature-web-balanced",
      "detail": "triggered_by=system_admin; activation_id=8; note=...",
      "is_ids": true,
      "is_sensitive": true,
      "created_at": "2026-04-03T08:12:00"
    }
  ],
  "summary": {
    "total": 123,
    "ids_count": 40,
    "sensitive_count": 17,
    "today_count": 9,
    "by_action": [{ "name": "ids_source_sync", "count": 8 }],
    "by_user": [{ "name": "system_admin", "count": 50 }],
    "by_target_type": [{ "name": "ids_source_package", "count": 12 }]
  },
  "filters": {
    "action_options": ["ids_source_sync"],
    "target_type_options": ["ids_source"]
  }
}
```

## 2) IDS Audit-Write Touchpoints

`backend/app/api/ids.py` writes audit entries for:

- source sync,
- source package preview success/reject,
- source package activate success/reject,
- rulepack activate success/reject/fail.
