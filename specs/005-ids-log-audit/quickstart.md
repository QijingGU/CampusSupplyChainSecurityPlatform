# Quickstart: IDS Log Audit Enhancement

## 1. Backend Syntax Validation

```bash
python -m py_compile backend/app/api/audit.py backend/app/api/ids.py backend/app/services/audit.py
```

## 2. Frontend Build Validation

```bash
cd frontend
npm run build
```

## 3. API Validation

1. Trigger one IDS source sync (`POST /api/ids/sources/{id}/sync`).
2. Trigger one IDS source package preview and one activate attempt.
3. Trigger one IDS rulepack activate success and one rejected/failed attempt.
4. Query:

```http
GET /api/audit?ids_only=1&page=1&page_size=20
```

5. Confirm response includes IDS actions and `summary.ids_count > 0`.

## 4. UI Validation

1. Open `/audit`.
2. Check four summary cards update.
3. Use tabs:
   - 全部日志
   - IDS 审计
   - 敏感操作
4. Use filters (动作、对象、操作人、关键词、时间范围) and verify pagination.
