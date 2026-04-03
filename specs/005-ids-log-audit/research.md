# Research Notes: IDS Log Audit Enhancement

## Problem

Current audit endpoint is too shallow (few filters, no pagination/summary), and
IDS source/rulepack operations are not comprehensively written into audit logs.

## Options Considered

### Option A: Add new audit table columns/migrations

- Pros: native persisted `is_ids`/`is_sensitive`
- Cons: migration risk, more rollout complexity

### Option B: Keep schema stable and derive classification at API layer

- Pros: fast delivery, low migration risk, simpler rollback
- Cons: repeated classification logic in API

## Decision

Adopt Option B for this slice. Persist only existing fields, standardize IDS
actions with `ids_` prefix, and derive classifications in response.

## Follow-Up Ideas

- optional persistent tags if audit scale grows significantly,
- export/report endpoint for weekly security audit package.
