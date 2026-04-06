# Implementation Tasks: IDS Upload Evidence Chain

- [x] Persist richer upload evidence for quarantined IDS incidents.
- [x] Parse upload evidence into a structured `upload_trace` payload in the IDS
  API layer.
- [x] Extend IDS event serialization and report generation with `upload_trace`.
- [x] Extend frontend IDS event types with upload-trace fields.
- [x] Show upload audit evidence in `SecurityIDS.vue` and add a direct sandbox
  report action.
- [x] Add route-driven sample/report focus in `SecuritySandbox.vue`.
- [x] Re-run backend syntax compile and frontend production build.
- [x] Validate the backend event/report payloads for a real upload-gated
  incident.
- [x] Update `docs/ids-changelog.md` and `docs/ids-demo-script.md`.
