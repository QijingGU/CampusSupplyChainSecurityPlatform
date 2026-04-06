# Quickstart

## 1. Start The Stack

```bash
cd backend
python init_db.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8166
```

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

## 2. Fixture Files

Use the bundled local sync fixture:

- Manifest: `backend/app/data/ids_source_sync/suricata-web-prod.manifest.json`
- Artifact: `backend/app/data/ids_source_sync/suricata-web-prod.rules`

## 3. Create Or Edit The Source

1. Sign in as `system_admin / 123456`.
2. Open `http://127.0.0.1:5173/security/ids`.
3. Create or edit `suricata-web-prod` with:
   - trust class: `external_mature`
   - detector family: `web`
   - sync mode: `manual`
   - sync endpoint:
     `app/data/ids_source_sync/suricata-web-prod.manifest.json`

## 4. Trigger Real Sync

1. Click `执行同步`.
2. Expect the source row to update with:
   - latest sync status `success`,
   - package version `2026.04.06`,
   - resolved manifest path,
   - `rules=4`,
   - a visible hash preview.

## 5. Review History

1. Click `历史`.
2. Expect:
   - `Sync Audit` with result, timestamp, operator, detail, and manifest path.
   - recent package intake showing the same version and intake detail.

## 6. API Spot Check

Authenticated browser/API calls should show:

- `GET /api/ids/sources`
- `GET /api/ids/source-packages?source_id=<id>&limit=5`

Both payloads should include the sync/artifact fields added in this slice.
