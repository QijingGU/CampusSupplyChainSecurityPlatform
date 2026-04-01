# Contract: IDS Incident Ingestion

## Purpose

Define the normalized ingestion contract used by the backend to accept real,
demo, and future external-source IDS events without mixing provenance or event
origin.

## Endpoint

- `POST /api/ids/events/ingest`

## Request Body

```json
{
  "event_origin": "real",
  "source_classification": "external_mature",
  "detector_family": "web",
  "detector_name": "trusted-web-detector",
  "rule_id": "RULE-1234",
  "rule_name": "Suspicious Injection Attempt",
  "source_version": "2026.04",
  "source_freshness": "current",
  "occurred_at": "2026-04-01T10:20:30Z",
  "client_ip": "203.0.113.10",
  "asset_ref": "/api/upload/public",
  "attack_type": "sql_injection",
  "severity": "high",
  "confidence": 92,
  "event_fingerprint": "web:203.0.113.10:/api/upload/public:RULE-1234",
  "correlation_key": "2026-04-01T10:20:web:203.0.113.10",
  "evidence_summary": "Matched upstream injection rule against upload endpoint",
  "raw_evidence": {
    "method": "POST",
    "path": "/api/upload/public",
    "query_snippet": "id=1' OR '1'='1",
    "body_snippet": "multipart payload omitted"
  }
}
```

## Validation Rules

- `event_origin` is required and must be one of `real`, `demo`, `test`.
- `source_classification` is required and must be one of `external_mature`,
  `custom_project`, `transitional_local`.
- `detector_name`, `detector_family`, `attack_type`, and `occurred_at` are
  required.
- `confidence` must be within a bounded review range.
- `event_fingerprint` is required for real and demo events that should be
  deduplicated or correlated.
- `raw_evidence` may be omitted only when the source cannot safely provide it;
  in that case `evidence_summary` remains required.

## Response Body

```json
{
  "incident_id": 123,
  "correlation_key": "2026-04-01T10:20:web:203.0.113.10",
  "linked_event_count": 1,
  "counted_in_real_metrics": true,
  "status": "new"
}
```

## Behavioral Notes

- Real and demo/test events follow the same normalization contract but differ in
  default metric inclusion and UI treatment.
- The ingestion layer may correlate an incoming event into an existing incident
  when the fingerprint or correlation key matches an active review window.
- Existing in-process middleware detections can be adapted into this contract so
  the current matcher becomes a provider rather than the core incident model.

## Future Contract Extensions

- Batch ingestion for network-alert feeds
- Source health and freshness synchronization
- File-scan evidence attachments
- Host-log enrichment payloads
