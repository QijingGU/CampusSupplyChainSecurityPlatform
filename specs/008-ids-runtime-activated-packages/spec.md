# Feature Specification: IDS Runtime Activated Packages

**Feature Branch**: `security-center/feature-ids-realize-ui`  
**Created**: 2026-04-06  
**Status**: Implemented  
**Input**: User description: "The remaining demo smell is that synced and activated IDS rule packages still do not affect runtime detection. Close that backend loop and sync the docs."

## User Scenarios & Testing

### User Story 1 - Activated Web Package Affects Runtime Detection (Priority: P1)

A security maintainer activates a reviewed `web` rule package and subsequent
requests can be matched by the active package, not only by the legacy inline
matcher.

**Independent Test**: activate `suricata-web-prod`, send
`GET /runtime-probe?sample=../`, and verify runtime detection reports
`detector_name=suricata-web-prod` with `source_version=2026.04.06`.

### User Story 2 - Runtime Events Preserve Real Source Provenance (Priority: P1)

A reviewer inspects the resulting IDS event and can see which activated source,
package version, and rule id produced the detection.

**Independent Test**: inspect the latest `/runtime-probe` IDS event and verify
`source_classification=external_mature`, `source_rule_id=9001003`, and the
runtime signature string instead of `legacy-inline`.

### User Story 3 - Source Changes Refresh Runtime State Promptly (Priority: P2)

A maintainer updates a source or activates a package and does not need to wait
for a long cache expiry before the runtime detector reflects the change.

**Independent Test**: activate the package, immediately issue the runtime probe,
and verify the event already carries the activated package metadata.

## Edge Cases

- No active package exists for a source, so the legacy inline matcher remains
  the only runtime detector.
- An active package belongs to a `demo_test` or disabled source and must not be
  loaded into the runtime matcher.
- An active package belongs to a non-`web` detector family and remains
  management-only for now.
- An activated artifact path is missing or unreadable and must not crash request
  inspection.
- A rule artifact contains lines that the current lightweight runtime parser
  cannot convert into matchable patterns.

## Requirements

### Functional Requirements

- **FR-001**: The runtime IDS matcher MUST load active rule artifacts from
  non-demo, non-disabled `web` sources.
- **FR-002**: Runtime loading MUST remain bounded to activated package records
  and MUST not execute arbitrary repo files outside the stored artifact paths.
- **FR-003**: Runtime request matches from activated packages MUST surface real
  provenance fields: source classification, detector family, source key, rule
  id, rule name, and package version.
- **FR-004**: Runtime cache refresh MUST be triggered after source updates and
  package activations so operator-visible changes take effect promptly.
- **FR-005**: Request inspection MUST continue working if no active runtime
  rules can be loaded.
- **FR-006**: This slice MUST stay inside IDS backend/runtime paths plus
  supporting specs/docs.

### Key Entities

- **Runtime Activated Rule**: derived in-memory rule entry loaded from the
  latest activated package for one `web` source.
- **Runtime-Attributed IDS Event**: persisted IDS event that preserves the
  activated source key, package version, and rule id that matched the request.

## Success Criteria

- **SC-001**: A request containing `../` after activating `suricata-web-prod`
  is attributed to the activated source instead of `inline_request_matcher`.
- **SC-002**: The persisted IDS event records `source_version=2026.04.06` and
  `source_rule_id=9001003`.
- **SC-003**: Backend syntax validation passes for the updated IDS runtime,
  middleware, and API files.
- **SC-004**: The runtime path degrades safely to the legacy inline matcher when
  no eligible activated rules are present.

## Validation Snapshot

- Backend validation passed:
  `python -m py_compile backend/app/services/ids_engine.py backend/app/middleware/ids_middleware.py backend/app/api/ids.py`
- Runtime validation passed on 2026-04-06:
  - refreshed the active `suricata-web-prod` package,
  - `scan_request_detailed("GET", "/runtime-probe", "sample=../", ...)`
    returned `detector_name=suricata-web-prod`,
    `source_version=2026.04.06`, and `source_rule_id=9001003`,
  - `GET /runtime-probe?sample=../` persisted an IDS event with the same source
    metadata and returned HTTP `404`, proving the IDS path recorded the event
    without fabricating a demo response.

## Assumptions And Residual Scope

- This slice reuses the existing source sync and package activation workflow
  from `specs/007-ids-source-real-sync`.
- The current runtime integration only extracts `content:"..."` tokens from
  activated `web` rule artifacts; it is not a full Suricata execution engine.
- Non-`web` detector families, external network pulls, and `scheduled` sync
  automation remain out of scope.
