# Implementation Plan: IDS Upload Evidence Chain

## Goal

Carry upload AI-audit evidence all the way into the active IDS workbench so the
operator can move from public upload, to IDS incident, to sandbox report
without losing context.

## Scope

- Backend IDS serialization and report generation
- Upload-gated incident evidence enrichment
- Security-center IDS drawer linkage
- Sandbox route-based report focus
- Demo and changelog documentation

## Technical Strategy

1. Persist richer upload evidence in the existing quarantined IDS incident
   payload.
2. Parse that evidence in `backend/app/api/ids.py` into a structured
   `upload_trace` payload with safe fallbacks for older rows.
3. Surface `upload_trace` in IDS list/report responses.
4. Render the trace in `SecurityIDS.vue` and add a route jump to the sandbox.
5. Let `SecuritySandbox.vue` consume `saved_as` and `report=1` query params to
   open the targeted report.
6. Update the changelog and demo script the same day.

## Validation Plan

- Python syntax compile for the touched backend files
- Frontend production build
- Direct backend validation for the latest `upload_ai_gate` event and report
- Browser/gstack verification of the IDS drawer to sandbox-report navigation

## Residual Risks

- `SecurityIDS.vue` remains large and still mixes production and demo tooling.
- Existing historical upload incidents may show partial traces if they were
  recorded before the richer evidence payload existed.
