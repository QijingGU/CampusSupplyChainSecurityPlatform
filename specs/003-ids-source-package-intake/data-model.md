# Data Model: IDS Source Package Intake

## IDS Source Package Intake

### Fields

- `id`: unique intake identifier
- `source_id`: parent IDS source, nullable when a preview is rejected before a
  registry source can be resolved
- `source_key`: stable source identity copied from the manifest
- `package_version`: proposed source package version
- `release_timestamp`: upstream package release timestamp
- `trust_classification`: `external_mature`, `custom_project`,
  `transitional_local`, or `demo_test`
- `detector_family`: package family such as `network`, `web`, `file`, or `log`
- `provenance_note`: reviewer-facing provenance detail
- `intake_result`: `previewed`, `activated`, `rejected`, or `failed`
- `intake_detail`: operator-visible detail or validation result
- `triggered_by`: operator responsible for preview or activation
- `created_at`: audit timestamp

### Relationships

- Many package intake records may belong to one `IDS Source Registry Entry`.
- A rejected preview may keep `source_id=NULL` while preserving `source_key`.
- One intake record may lead to zero or one `Source Package Activation`.

## Source Package Activation

### Fields

- `id`: unique activation identifier
- `source_id`: parent IDS source
- `package_intake_id`: reviewed package intake record
- `package_version`: activated package version
- `activated_at`: activation timestamp
- `activated_by`: operator responsible for activation
- `activation_detail`: reviewer-visible activation note

### Relationships

- Many activations may belong to one `IDS Source Registry Entry`.
- Many activations may reference many historical intake records over time, but
  each activation links to one specific intake record.

## Source Package Preview

### Fields

- `source_id`: parent IDS source
- `source_key`: target source identity
- `package_version`: proposed package version
- `version_change_state`: `newer`, `unchanged`, `older`, or `conflicting`
- `changed_fields`: reviewer-facing list of fields that would change on
  activation
- `visible_warning`: concise explanation when preview should not be activated

### State Rules

- `demo_test` previews remain visible but cannot activate trusted coverage.
- A preview for an older package version must remain reviewable and visibly
  downgraded.
- A failed preview keeps its detail instead of disappearing from history.
