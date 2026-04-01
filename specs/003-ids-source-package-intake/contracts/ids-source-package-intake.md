# Contract: IDS Source Package Intake

## Purpose

Define the first operational contract for trusted source package preview and
activation workflows.

## Endpoints

- `POST /api/ids/source-packages/preview`
- `POST /api/ids/source-packages/activate`
- `GET /api/ids/source-packages`

## Package Preview Request Body

```json
{
  "source_key": "suricata-web-prod",
  "package_version": "2026.04",
  "release_timestamp": "2026-04-01T08:00:00Z",
  "trust_classification": "external_mature",
  "detector_family": "network",
  "provenance_note": "Campus-reviewed Suricata upstream ruleset",
  "triggered_by": "system_admin"
}
```

## Package Preview Response Body

```json
{
  "source_id": 7,
  "source_key": "suricata-web-prod",
  "package_version": "2026.04",
  "version_change_state": "newer",
  "changed_fields": [
    "package_version",
    "release_timestamp",
    "provenance_note"
  ],
  "visible_warning": "",
  "intake_result": "previewed"
}
```

## Package Activation Request Body

```json
{
  "package_intake_id": 18,
  "triggered_by": "system_admin",
  "activation_note": "Approved after package review"
}
```

## Package Activation Response Body

```json
{
  "source_id": 7,
  "package_activation_id": 4,
  "package_version": "2026.04",
  "result_status": "activated",
  "active_package_version": "2026.04",
  "detail": "Approved after package review"
}
```

## Package History Response Body

```json
{
  "total": 1,
  "items": [
    {
      "source": {
        "id": 7,
        "source_key": "suricata-web-prod",
        "display_name": "Suricata Web Production",
        "trust_classification": "external_mature",
        "detector_family": "network"
      },
      "source_key": "suricata-web-prod",
      "active_package_version": "2026.04",
      "active_package_activated_at": "2026-04-01 09:05:00",
      "active_package_activated_by": "system_admin",
      "recent_intakes": [
        {
          "id": 18,
          "source_id": 7,
          "source_key": "suricata-web-prod",
          "package_version": "2026.04",
          "trust_classification": "external_mature",
          "intake_result": "activated",
          "intake_detail": "Approved after package review",
          "triggered_by": "system_admin",
          "created_at": "2026-04-01 09:00:00"
        },
        {
          "id": 19,
          "source_id": 7,
          "source_key": "suricata-web-prod",
          "package_version": "2026.04.demo",
          "trust_classification": "demo_test",
          "intake_result": "failed",
          "intake_detail": "demo_test packages cannot be activated as trusted coverage",
          "triggered_by": "system_admin",
          "created_at": "2026-04-01 09:06:00"
        }
      ],
      "recent_activations": [
        {
          "id": 4,
          "source_id": 7,
          "package_intake_id": 18,
          "package_version": "2026.04",
          "activated_at": "2026-04-01 09:05:00",
          "activated_by": "system_admin",
          "activation_detail": "Approved after package review",
          "created_at": "2026-04-01 09:05:00"
        }
      ]
    }
  ]
}
```

## Validation Rules

- `source_key`, `package_version`, `trust_classification`, `detector_family`,
  and `triggered_by` are required for preview.
- `trust_classification` must be one of `external_mature`,
  `custom_project`, `transitional_local`, or `demo_test`.
- `demo_test` package previews must never be activatable as trusted production
  coverage.
- Package activation requires a valid preview/intake record.
- A package preview for an older or conflicting version must remain visible and
  must not silently overwrite the active version.
- If `source_key` cannot be resolved to an existing registry source, the
  preview is rejected, the rejected intake attempt remains stored, and
  `source_id` may remain null on that rejected record.

## Behavioral Notes

- Preview is reviewer-facing proposed state and must remain visible even when it
  is rejected.
- Activation history must remain visible per source.
- The first slice may accept package metadata directly rather than parsing a
  full upstream archive as long as the package version and provenance remain
  traceable.
