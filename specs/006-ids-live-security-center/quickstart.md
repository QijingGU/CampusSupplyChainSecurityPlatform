# Quickstart: IDS Live Security Center Parity

## Goal

Validate that the public upload page, security sandbox, and security situation
page now form a real IDS workflow.

## Preconditions

- Backend dependencies are installed.
- Frontend dependencies are installed.
- The database was initialized with `python init_db.py`.
- An administrator account exists: `system_admin / 123456`.

## Start The Stack

### Backend

```powershell
cd D:\ids\CampusSupplyChainSecurityPlatform\backend
pip install -r requirements.txt
python init_db.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8166
```

### Frontend

```powershell
cd D:\ids\CampusSupplyChainSecurityPlatform\frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

## Prepare Demo Files

```powershell
cd D:\ids\CampusSupplyChainSecurityPlatform
New-Item -ItemType Directory -Force tmp | Out-Null
Set-Content -Path tmp\codex-note.txt -Value 'campus supply chain notice'
Set-Content -Path tmp\codex-webshell.php -Value '<?php eval($_POST[1]); ?>'
```

## Validation Flow

### 1. Verify The Benign Upload Path

- Open `http://127.0.0.1:5173/upload`
- Upload `tmp/codex-note.txt`
- Confirm the page shows an AI-audit pass outcome.
- Confirm the response includes a public accepted-file URL.
- Confirm the file does not appear in `/security/sandbox`.

### 2. Verify The Suspicious Upload Path

- Stay on `/upload`
- Upload `tmp/codex-webshell.php`
- Confirm the page shows that the file was withheld into the sandbox.
- Confirm the result includes audit verdict, risk level, and confidence.
- Confirm the file does not receive a public accepted-file URL.

### 3. Verify Sandbox Visibility

- Log in as `system_admin / 123456`
- Open `http://127.0.0.1:5173/security/sandbox`
- Confirm the quarantined sample appears in the list.
- Confirm the row shows verdict, risk, confidence, and summary.
- Trigger the analyze action and confirm the report drawer opens.
- Refresh the page and confirm `latest_report` remains reopenable.

### 4. Verify Situation Linkage

- Open `http://127.0.0.1:5173/security/situation`
- Confirm the page loads without random attacks.
- Confirm the blocked-count and active-threat metrics are non-zero after the
  suspicious upload.
- Confirm the recent incident feed contains the malware/WebShell upload event.
- Confirm the map disclaimer states that source positions are derived
  approximations from incident IPs.

### 5. Verify APIs Directly

- `GET /api/upload/quarantine`
  - expect `items`, `analysis`, and `latest_report`
- `GET /api/upload/quarantine/{filename}/report`
  - expect the persisted report payload for the chosen sample
- `POST /api/upload/quarantine/analyze`
  - expect `logs` plus `report`
- `GET /api/ids/situation`
  - expect `generated_at`, `scope`, `disclaimer`, `target`, `metrics`, and
    `attacks`

## Validation Snapshot From 2026-04-05

- Backend compile passed for:
  `backend/app/api/upload.py`, `backend/app/api/ids.py`,
  `backend/app/services/upload_ai_audit.py`
- Frontend production build passed.
- Manual walkthrough passed for both benign and suspicious upload flows.
- gstack QA confirmed the quarantined sample appears in sandbox and situation.

## Residual Scope

- `SecurityIDS.vue` still contains intentional demo/test tools for IDS workflow
  operations and should not be mistaken for a fully de-demoed page.
- `IDSManage.vue` remains a legacy compatibility page.
- Exact geo-IP and full malware detonation remain outside this slice.
