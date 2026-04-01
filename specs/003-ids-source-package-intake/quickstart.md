# Quickstart: IDS Source Package Intake

## Goal

Validate that trusted IDS source packages can be previewed, activated, and
reviewed without confusing them with `demo_test` package records.

## Preconditions

- Backend and frontend dependencies are installed.
- The application database is initialized.
- An administrator account and token are available.
- The source-registry workflow from `002-ids-source-operations` is already
  present.

## Run The Application

### Backend

```powershell
cd D:\ids\CampusSupplyChainSecurityPlatform\backend
pip install -r requirements.txt
python init_db.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8166
```

### Frontend

```powershell
cd D:\ids\CampusSupplyChainSecurityPlatform\frontend
npm install
npm run dev
```

## Validate The Source Package Intake Slice

### 1. Preview A Trusted Package

- Submit one valid trusted package preview request.
- Confirm the preview returns `version_change_state`, changed fields, and any
  warning.

### 2. Reject An Invalid Package

- Submit one incomplete or conflicting package preview request.
- Confirm the platform rejects it with actionable validation feedback.
- Submit one package preview request with an unknown `source_key`.
- Confirm the platform returns rejection and preserves a rejected intake record
  for later review.

### 3. Activate A Reviewed Package

- Activate one previewed trusted package for an existing source.
- Confirm the source now shows the active package version.
- Confirm `POST /api/ids/source-packages/activate` returns
  `result_status=activated`.
- In the security center source table, confirm the row now shows the same
  `active_package_version`.

### 4. Reject A Demo/Test Package Activation

- Preview one `demo_test` package record.
- Confirm activation as trusted coverage is rejected.
- Confirm the latest package intake for that source remains visible with
  `intake_result=failed` and an operator-visible rejection reason.

### 5. Review Package History

- Open the source details in the security center.
- Use the `History` action on the source row.
- Confirm the source view shows active package version plus recent package
  preview/activation history.
- Confirm recent intakes preserve failed `demo_test` activation attempts instead
  of losing them after the HTTP 400 response.
- Confirm recent activations still show the last trusted package that became
  active.

## Operator Notes

- Use `GET /api/ids/source-packages?source_id=<id>&limit=5` when validating
  source-specific package history without clicking through the UI.
- The source table is expected to show the latest package intake result and
  trust classification inline before you open the history dialog.
- A blocked `demo_test` activation must not change the active trusted package
  version.

### 6. Verify Changelog Discipline

- Update `docs/ids-changelog.md` with the day's package-intake work.
- Commit with `feat:`, `fix:`, or `chore:`.
- Push the active IDS branch to GitHub.
