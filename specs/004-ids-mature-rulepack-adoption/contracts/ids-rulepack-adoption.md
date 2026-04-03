# Contract: IDS Mature Rulepack Adoption

## Purpose

Define API contracts for mature rulepack catalog, activation, and activation
history.

## Endpoints

- `GET /api/ids/rule-packs`
- `POST /api/ids/rule-packs/activate`
- `GET /api/ids/rule-packs/activations`

## List Rulepacks Response Body

```json
{
  "active_rulepack_key": "mature-web-balanced",
  "items": [
    {
      "rulepack_key": "mature-web-balanced",
      "display_name": "Mature Web Balanced Pack",
      "pack_version": "2026.04",
      "trust_classification": "external_mature",
      "detector_family": "web",
      "provenance_note": "Curated from mature OWASP/Suricata style signatures",
      "rule_count": 24
    }
  ]
}
```

## Activate Rulepack Request Body

```json
{
  "rulepack_key": "mature-web-balanced",
  "triggered_by": "system_admin",
  "activation_note": "Switch to mature pack after review"
}
```

## Activate Rulepack Response Body

```json
{
  "result_status": "activated",
  "active_rulepack_key": "mature-web-balanced",
  "rulepack_key": "mature-web-balanced",
  "activation_id": 12,
  "detail": "Rulepack activated for inline IDS matcher."
}
```

## Activation History Response Body

```json
{
  "total": 2,
  "items": [
    {
      "id": 12,
      "rulepack_key": "mature-web-balanced",
      "trust_classification": "external_mature",
      "detector_family": "web",
      "result_status": "activated",
      "activation_detail": "Rulepack activated for inline IDS matcher.",
      "triggered_by": "system_admin",
      "created_at": "2026-04-03 12:20:00"
    },
    {
      "id": 13,
      "rulepack_key": "demo-seed-pack",
      "trust_classification": "demo_test",
      "detector_family": "web",
      "result_status": "rejected",
      "activation_detail": "demo_test rulepacks cannot be activated as trusted runtime coverage",
      "triggered_by": "system_admin",
      "created_at": "2026-04-03 12:23:00"
    }
  ]
}
```

## Validation Rules

- `rulepack_key` and `triggered_by` are required for activation.
- Unknown `rulepack_key` is rejected and recorded as a failed activation attempt.
- `demo_test` packs must remain visible but rejected for trusted activation.
- Activation history returns latest-first ordering and retains rejected/failed
  operations.
- Runtime matcher uses `active_rulepack_key` and falls back to
  `legacy-inline` when state is missing.

## Behavioral Notes

- Catalog can include mixed trust classes; activation policy enforces trusted
  runtime boundaries.
- Event provenance should reflect the active runtime rulepack key.
