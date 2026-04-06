# Quickstart: IDS Upload Evidence Chain

## Prerequisites

- Backend running from `backend/`
- Frontend running from `frontend/`
- At least one quarantined upload sample already exists
- At least one `upload_ai_gate` IDS incident exists

## Validation Steps

1. In `backend/`, inspect the latest upload-gated IDS event:

   ```powershell
   @'
   from app.database import SessionLocal
   from app.models.ids_event import IDSEvent
   from app.api.ids import _serialize_ids_event

   db = SessionLocal()
   row = db.query(IDSEvent).filter(IDSEvent.detector_name == "upload_ai_gate").order_by(IDSEvent.id.desc()).first()
   print(_serialize_ids_event(row)["upload_trace"])
   db.close()
   '@ | python -
   ```

2. In `backend/`, confirm the report payload preserves the same trace:

   ```powershell
   @'
   from app.database import SessionLocal
   from app.api.ids import get_event_report

   db = SessionLocal()
   data = get_event_report(2, 0, db, None)
   print(bool(data["report"].get("upload_trace")))
   print("Upload Audit Trace" in data["markdown"])
   db.close()
   '@ | python -
   ```

3. In the browser, open `/security/ids`, inspect the latest upload-gated event,
   and verify `Upload Audit Trace` is visible.

4. Click `打开沙箱报告` and verify `/security/sandbox` opens the matching sample
   report.

5. Re-run the frontend build:

   ```powershell
   cd frontend
   npm run build
   ```
