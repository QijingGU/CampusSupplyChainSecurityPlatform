# Research: IDS Mature Rulepack Adoption

## Decision 1: Curate mature rulepacks in a dedicated service for first delivery

**Decision**: add a dedicated `ids_rulepacks.py` catalog that stores mature
rulepack metadata and signatures as reusable definitions.

**Rationale**: this gives immediate reuse value with low integration risk and
keeps patch scope narrow inside IDS paths.

**Alternatives considered**:

- Pull remote rule feeds in real time: rejected for first slice due external
  dependency and rollout complexity.
- Keep all signatures hardcoded in `ids_engine.py`: rejected because it does not
  produce rulepack-level provenance and activation control.

## Decision 2: Persist activation attempts and active runtime state

**Decision**: create IDS rulepack activation records plus a small runtime state
record for the active key.

**Rationale**: constitution requires traceable operations and failed actions to
remain visible; runtime state is needed for deterministic matcher behavior.

**Alternatives considered**:

- In-memory active key only: rejected because restart loses governance and
  history linkage.
- Overload existing source-package tables: rejected to avoid semantic coupling
  between package intake and matcher runtime state.

## Decision 3: Keep `demo_test` visible but non-trusted

**Decision**: allow `demo_test` packs in catalog and preview/history, but block
activation for trusted runtime matching.

**Rationale**: preserves demo/test clarity and avoids contaminating production
coverage claims.

**Alternatives considered**:

- Hide demo packs entirely: rejected because reviewers still need explicit
  visibility for training fixtures.
- Allow demo pack activation with warning only: rejected because it weakens
  trust boundaries.

## Decision 4: Stamp active rulepack provenance on IDS events

**Decision**: include active rulepack key in event source version metadata (and
detector metadata where needed) when middleware records matched events.

**Rationale**: reviewers need to connect detection behavior to the rulepack that
was active at event time.

**Alternatives considered**:

- Keep event schema unchanged: rejected because runtime rulepack switches would
  be invisible in incident review.
