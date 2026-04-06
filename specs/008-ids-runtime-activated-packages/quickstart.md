# Quickstart

## 1. Prepare The Existing Source Sync Fixture

Use the already-bundled local fixture:

- `backend/app/data/ids_source_sync/suricata-web-prod.manifest.json`
- `backend/app/data/ids_source_sync/suricata-web-prod.rules`

## 2. Activate The Package

1. Start the backend stack.
2. Ensure `suricata-web-prod` exists as a `web` source with:
   - trust class `external_mature`
   - sync mode `manual`
   - sync endpoint `app/data/ids_source_sync/suricata-web-prod.manifest.json`
3. Run source sync and activate the latest package preview.

## 3. Trigger A Runtime Probe

Issue a request that matches the activated path-traversal rule:

```bash
curl "http://127.0.0.1:8166/runtime-probe?sample=../"
```

Expected result:

- the HTTP response can still be `404`,
- the IDS middleware persists an event for `/runtime-probe`,
- the event is attributed to `suricata-web-prod` rather than
  `inline_request_matcher`.

## 4. Review The Event

Check the latest IDS event in the API, database, or security-center UI and
verify:

- `detector_name=suricata-web-prod`
- `source_version=2026.04.06`
- `source_rule_id=9001003`
- `source_classification=external_mature`
