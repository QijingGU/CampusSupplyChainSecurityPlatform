# Research: IDS Source Package Intake

## Decision 1: Intake trusted package manifests through the existing IDS API

**Decision**: extend `backend/app/api/ids.py` with package preview and package
activation operations instead of creating a new package-specific API module for
the first slice.

**Rationale**: package intake is a continuation of source operations, not a new
security domain. Keeping it adjacent to source registry logic reduces merge risk
and keeps reviewer workflows concentrated in the current IDS screen.

**Alternatives considered**:

- Create a new `ids_packages.py` module immediately: rejected for the first
  slice because it increases routing churn without meaningful isolation.
- Hide package intake in raw database updates only: rejected because reviewers
  and maintainers would still lack previewable package impact.

## Decision 2: Model package preview and package activation as separate facts

**Decision**: store preview or intake attempts separately from package
activations so maintainers can see what was proposed, what failed, and what
actually became active.

**Rationale**: preview is not activation. Keeping them distinct preserves audit
clarity and avoids losing failed or rejected package attempts.

**Alternatives considered**:

- Store only one mutable active-package record: rejected because failed or
  abandoned previews would disappear.
- Store package version only on the source row: rejected because reviewers could
  not trace how the version changed.

## Decision 3: Use source-key and package version as the first intake boundary

**Decision**: require package manifests to specify `source_key`, package
version, trust classification, detector family, and provenance detail before
they can be previewed or applied.

**Rationale**: the existing source registry already uses `source_key` as the
operational identity. Keeping package intake keyed the same way minimizes drift
and keeps version transitions reviewable.

**Alternatives considered**:

- Key package intake only by display name: rejected because display names are
  weaker identifiers and easier to drift.
- Accept partially specified package manifests: rejected because they would
  reduce trust in package activation.

## Decision 4: Keep `demo_test` package records visible but non-trusted

**Decision**: allow `demo_test` package manifests for training or fixture
purposes, but keep them visibly separate and non-activatable for trusted
production-oriented source coverage.

**Rationale**: the constitution requires demo separation. Package intake must
preserve the same trust boundary already introduced for incidents and sources.

**Alternatives considered**:

- Collapse `demo_test` packages into `custom_project`: rejected because it would
  blur real custom detectors with training fixtures.
- Ignore package trust class during activation: rejected because it would permit
  false production confidence.
