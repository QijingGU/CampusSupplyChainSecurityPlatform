# Quickstart

## 1. Prepare The Existing Source Sync Fixture

Use the already-bundled local fixture, which startup now bootstraps into the
runtime source registry automatically:

- `backend/app/data/ids_source_sync/suricata-web-prod.manifest.json`
- `backend/app/data/ids_source_sync/suricata-web-prod.rules`

## 2. Activate The Package

1. Start the backend stack.
2. Confirm `suricata-web-prod` is visible as a `web` source with:
   - trust class `external_mature`
   - sync mode `manual`
   - sync endpoint `app/data/ids_source_sync/suricata-web-prod.manifest.json`
   - active package version `2026.04.07`
   - rule count `15`
3. If needed, run source sync and activate the latest package preview.

## 3. Trigger A Runtime Probe

Issue a request that matches the activated path-traversal rule:

```bash
curl "http://127.0.0.1:8166/runtime-probe?sample=../etc/passwd"
```

Expected result:

- the HTTP response is `403`,
- the IDS middleware persists an event for `/runtime-probe`,
- the event is attributed to `suricata-web-prod` rather than
  `inline_request_matcher`,
- the event detail/report surfaces show an `Attack Packet` view, the matched
  static-rule chain, and AI mode information.

## 4. Review The Event

Check the latest IDS event in the API, database, or security-center UI and
verify:

- `detector_name=suricata-web-prod`
- `source_version=2026.04.07`
- a real `source_rule_id`
- `source_classification=external_mature`
- visible block score vs threshold data
