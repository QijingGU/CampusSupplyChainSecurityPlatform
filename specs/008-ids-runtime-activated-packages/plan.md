# Implementation Plan: IDS Runtime Activated Packages

## Goal

Let activated IDS `web` packages influence runtime request inspection so IDS
events preserve real source provenance instead of always falling back to the
legacy inline matcher metadata.

## Architecture

### Backend Runtime Path

- Extend `backend/app/services/ids_engine.py` with a bounded runtime cache of
  activated `web` package rules.
- Load only the latest activation per source and skip `demo_test` or disabled
  sources.
- Parse the current text artifact format by extracting Suricata `content:"..."`
  tokens, plus `msg` and `sid` metadata.
- Prefer runtime hits when they carry stronger match weight than the static
  inline matcher.

### Middleware Attribution

- Extend `backend/app/middleware/ids_middleware.py` so persisted events use the
  runtime source metadata when present.
- Keep the existing `inline_request_matcher / legacy-inline` fallback for
  requests that are only matched by the static detector set.

### API Coherence

- Refresh the runtime cache from `backend/app/api/ids.py` after source updates
  and package activations so operators do not wait for a passive cache expiry.

## Data Flow

1. Maintainer syncs and activates a rule package for a `web` source.
2. The activation becomes the latest active package for that source.
3. The runtime cache loads the activated artifact and derives matchable rules.
4. A later HTTP request hits one of those patterns.
5. Middleware persists an IDS event with the activated source key, rule id, and
   package version.

## Verification Strategy

- Python syntax compile for the touched backend files.
- Service-level validation through `scan_request_detailed`.
- HTTP-level validation by issuing a probe request and reading the persisted IDS
  event row.

## Residual Risk

- Runtime parsing is intentionally lightweight and only covers the current local
  artifact style.
- Full external feed execution and non-`web` family runtime enforcement remain
  separate future slices.
