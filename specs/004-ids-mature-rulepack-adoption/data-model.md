# Data Model: IDS Mature Rulepack Adoption

## Mature Rulepack Catalog Entry

### Fields

- `rulepack_key`: stable pack identity (e.g., `mature-web-balanced`)
- `display_name`: reviewer-facing name
- `trust_classification`: `external_mature`, `custom_project`, or `demo_test`
- `detector_family`: primary detector scope (`web`, `network`, `file`, etc.)
- `pack_version`: semantic/date-based version string
- `provenance_note`: source provenance and maintenance note
- `rule_count`: number of enabled signatures in the pack
- `signatures`: normalized signatures (`pattern`, `attack_type`, `weight`)

### Relationships

- One catalog entry may be activated multiple times across history.
- One catalog entry may be blocked from trusted activation by trust class.

## IDS Rulepack Runtime State

### Fields

- `id`: state row identifier (single-row pattern)
- `active_rulepack_key`: currently active runtime pack
- `updated_at`: last state update timestamp
- `updated_by`: operator who changed active state
- `update_note`: optional operator note

### Relationships

- One runtime state row points to one catalog entry by `active_rulepack_key`.

## IDS Rulepack Activation Record

### Fields

- `id`: activation attempt id
- `rulepack_key`: requested pack key
- `trust_classification`: copied trust class at operation time
- `detector_family`: copied detector family
- `result_status`: `activated`, `rejected`, or `failed`
- `activation_detail`: operator-visible detail
- `triggered_by`: operator id
- `created_at`: attempt timestamp

### Relationships

- Many activation records map to one catalog entry.
- Activation records are append-only audit facts.

## State Rules

- Unknown `rulepack_key` requests are rejected and recorded.
- `demo_test` rulepacks cannot become trusted active runtime packs.
- Runtime matching always resolves an active rulepack; if state is invalid, it
  falls back to `legacy-inline`.
- Repeated activation of the same active key still records a deterministic
  activation result for audit continuity.
