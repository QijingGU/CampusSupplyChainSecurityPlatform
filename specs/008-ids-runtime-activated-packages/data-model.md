# Data Model

## Derived Runtime Activated Rule

- `attack_type`: inferred attack class for scoring and UI labels
- `pattern`: extracted match string from the active artifact
- `signature_matched`: persisted signature summary for the IDS event
- `weight`: runtime score contribution
- `source_classification`: trust classification copied from the active source
- `detector_family`: detector family copied from the active source
- `detector_name`: active source key
- `source_rule_id`: rule id derived from `sid`
- `source_rule_name`: rule name derived from `msg`
- `source_version`: active package version
- `source_freshness`: currently `current`

## Runtime-Attributed IDS Event

Existing `IDSEvent` rows now reuse the current fields with stronger provenance:

- `source_classification`
- `detector_family`
- `detector_name`
- `source_rule_id`
- `source_rule_name`
- `source_version`
- `source_freshness`

## Persistence Impact

- No new database tables or columns are introduced in this slice.
- Runtime rules are derived from:
  - `IDSSource`
  - `IDSSourcePackageIntake`
  - `IDSSourcePackageActivation`
