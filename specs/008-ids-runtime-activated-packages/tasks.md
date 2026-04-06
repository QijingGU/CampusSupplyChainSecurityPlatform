# Implementation Tasks: IDS Runtime Activated Packages

- [x] Load latest activated `web` package artifacts into a bounded runtime cache
  inside `backend/app/services/ids_engine.py`.
- [x] Parse rule artifact `content`, `msg`, and `sid` data into runtime match
  metadata.
- [x] Attribute runtime-matched IDS events in
  `backend/app/middleware/ids_middleware.py` with the activated source
  provenance.
- [x] Refresh runtime cache after source updates and package activations from
  `backend/app/api/ids.py`.
- [x] Validate syntax, service-level runtime matching, and persisted event
  attribution.
- [x] Update README, changelog, demo script, and the new spec slice.
