# Research: IDS Source Operations

## Decision 1: Keep source operations inside the existing IDS API surface

**Decision**: Extend `backend/app/api/ids.py` with source-registry and sync
operations instead of creating a separate API module for the first slice.

**Rationale**: the repository already routes reviewer workflows through the IDS
security-center entry point. Keeping source operations adjacent to incident
operations reduces merge risk and preserves discoverability while the feature is
still narrow.

**Alternatives considered**:

- Create a new `ids_sources.py` module immediately: rejected for the first slice
  because it adds more routing churn than operational value.
- Hide source operations in raw database migrations only: rejected because the
  UI and API would still lack reviewer-facing health visibility.

## Decision 2: Model source health as derived operational state

**Decision**: Store source registry facts and sync attempts explicitly, then
derive reviewer-facing health states such as healthy, stale, failing, disabled,
and never-synced.

**Rationale**: explicit facts are auditable; derived health labels keep the UI
simple for reviewers. This also avoids overloading one column with both static
configuration and operational status.

**Alternatives considered**:

- Store only one mutable health field: rejected because it would hide why the
  source is in that state.
- Derive everything from incidents only: rejected because quiet sources could
  appear healthy even when sync has failed.

## Decision 3: Treat sync as a traceable operational action even when upstream
fetch remains partial

**Decision**: support manual or API-triggered source sync attempts that always
record result, timestamps, and detail, even if some trusted sources still rely
on partial or mocked upstream metadata.

**Rationale**: the main requirement for this slice is operational traceability,
not full upstream automation. Recording every attempt now creates the audit
trail needed before more advanced connector work arrives.

**Alternatives considered**:

- Delay sync support until a full connector is ready: rejected because source
  freshness would remain undocumented.
- Allow silent background sync without visible records: rejected because it
  violates the traceable-response principle.

## Decision 4: Keep demo/test source records explicitly separate from trusted
production-oriented classifications

**Decision**: extend source classification to include `demo_test` so demo or
test-only registry records do not get merged into `custom_project` or trusted
production-oriented source buckets.

**Rationale**: the previous IDS slice already separated demo/test incidents from
real operational metrics. The source registry needs the same clarity so a local
campus detector can remain a legitimate production source without being confused
with demos or test fixtures.

**Alternatives considered**:

- Reuse `custom_project` for demo records: rejected because it would blur the
  line between production custom detectors and non-operational fixtures.
- Store demo/test separation only in UI labels: rejected because the API and
  persisted registry would still allow misleading source state.
