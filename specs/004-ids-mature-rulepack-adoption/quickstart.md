# Quickstart: IDS Mature Rulepack Adoption

## Goal

Validate mature rulepack catalog visibility, trusted activation, runtime matcher
switching, and activation traceability.

## Preconditions

- Backend and frontend dependencies are installed.
- Database is initialized (`python init_db.py`).
- Admin token/session is available.
- `003-ids-source-package-intake` has been delivered.

## Run The Application

### Backend

```powershell
cd D:\ids\CampusSupplyChainSecurityPlatform\backend
pip install -r requirements.txt
python init_db.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8166
```

### Frontend (optional for this slice)

```powershell
cd D:\ids\CampusSupplyChainSecurityPlatform\frontend
npm install
npm run dev
```

## Validate Rulepack Adoption Flow

### 1. List Rulepacks

- Call `GET /api/ids/rule-packs`.
- Confirm response includes `active_rulepack_key` and catalog metadata
  (`rulepack_key`, `trust_classification`, `rule_count`, `provenance_note`).

### 2. Activate Trusted Rulepack

- Submit `POST /api/ids/rule-packs/activate` with a valid mature key.
- Confirm response returns `result_status=activated`.
- Re-query `GET /api/ids/rule-packs` and confirm active key changed.

### 3. Reject Demo Rulepack Activation

- Submit activation for a `demo_test` pack.
- Confirm request is rejected with actionable detail.
- Confirm history still records this rejected attempt.

### 4. Verify Activation History

- Call `GET /api/ids/rule-packs/activations?limit=5`.
- Confirm latest successful activation and rejected activation both remain
  visible.

### 5. Verify Event Provenance

- Trigger one request that matches current active pack signatures.
- Confirm IDS event payload/source metadata includes active rulepack identity.

### 6. Verify Daily Delivery Discipline

- Update `docs/ids-changelog.md` with today's `004` work.
- Commit with `feat:` / `fix:` / `chore:`.
- Push `security-center/feature-ids`.

## Validation Notes (2026-04-03)

- API smoke validation completed with `system_admin` account in local TestClient flow.
- Confirmed `GET /api/ids/rule-packs` returns catalog and active rulepack key.
- Confirmed activation guardrails:
  - unknown `rulepack_key` returns HTTP 400 and creates a `failed` activation record,
  - `demo-seed-pack` returns HTTP 400 and creates a `rejected` activation record,
  - `mature-web-balanced` returns HTTP 200 with `result_status=activated`.
- Confirmed `GET /api/ids/rule-packs/activations?limit=5` returns latest-first activation history.
- Runtime matcher switching verification:
  - payload `User-Agent: dirbuster` does not match under `legacy-inline`,
  - same payload matches under `mature-web-balanced` with attack type
    `scanner` and non-zero risk score.
