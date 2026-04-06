# Data Model: IDS Upload Evidence Chain

## Upload Trace

- `saved_as`: quarantined sample filename used as the stable cross-page key
- `file_name`: original uploaded filename
- `sha256`: artifact hash when available
- `size`: sample size in bytes
- `storage_location`: quarantine storage bucket label
- `indicator_count`: number of detected suspicious indicators
- `indicators[]`: compact `code/detail` list for operator review
- `audit.verdict`: `pass|review|quarantine`
- `audit.risk_level`: `low|medium|high`
- `audit.confidence`: bounded 0-100 confidence score
- `audit.summary`: operator-readable audit summary
- `audit.provider`: heuristic or LLM provider label
- `audit.recommended_actions[]`: bounded remediation guidance

## Sandbox Deep Link

- Route path: `/security/sandbox`
- Query keys:
  - `saved_as`: exact sandbox sample name
  - `report=1`: request report opening instead of list-only focus

## IDS Report Extension

- `report.upload_trace`: optional structured object for upload-gated incidents
- `markdown`: includes an `Upload Audit Trace` section when the structured trace
  exists
