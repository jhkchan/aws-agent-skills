# Diagnostic Commands — Kinesis Data Firehose Troubleshooter

Pre-flight data requirements and pre-flight safety check listings moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Pre-flight: data requirements (moved from SKILL.md)

| Input | Source | Why |
|---|---|---|
| Delivery-stream-name | Console / `list-delivery-streams` | Drives `describe-delivery-stream` |
| Observed symptom | Console / CloudWatch alarm | Routes to the right diagnostic branch |
| Destination type | Console / `describe-delivery-stream` | Routes to per-destination Step |
| Region | Console | Required for all CLI calls |
| CloudWatch metric namespace | `AWS/Firehose` | For `get-metric-statistics` |
| Lambda function name (if transform) | `describe-delivery-stream` | For Lambda-layer diagnosis |
| Glue database/table (if format conversion) | `describe-delivery-stream` | For convert-layer diagnosis |
| Destination endpoint (OpenSearch / Redshift / Snowflake / Splunk) | `describe-delivery-stream` | For deliver-layer diagnosis |
| Recent CLI output (if any) | `describe-delivery-stream`, metric queries | Speeds up diagnosis |
| CloudWatch Logs excerpt (if any) | Firehose / Lambda log groups | For per-record errors |

**If the input is malformed** (no delivery-stream-name, ambiguous
symptom), emit:

```text
DIAGNOSIS: <reference>
DELIVERY_STREAM: unknown
DESTINATION: unknown
SYMPTOM: unknown
ROOT_CAUSE: Pending diagnosis - required inputs missing.
EVIDENCE:
  - No delivery-stream-name supplied.
LAYER_CHECK:
  - Source: unknown
  - Transform: unknown
  - Convert: unknown
  - Deliver: unknown
  - Observability: unknown
FIX: (pending inputs)
VERIFICATION: (pending fix)
VERDICT: NEED_MORE_INFO
NEXT_STEP: Re-supply: delivery-stream-name, the observed
  symptom (delivery-to-s3-fails / lambda-fails / delivery-lag
  / format-conversion-fails / opensearch-fails / redshift-fails
  / latest-destination-fails), the destination type, and the
  region.
ESCALATION_PATH: None
```

## Pre-flight safety checks (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE** before any state-changing operation (`update-destination`, `start-delivery-stream-encryption`, `stop-delivery-stream-encryption`, `create-delivery-stream`, `delete-delivery-stream`).
- **`update-destination` blast radius:** the change applies to all in-flight records; snapshot `describe-delivery-stream --output json` BEFORE the update.
- **KMS key policy changes:** always print the existing policy first (`get-key-policy --output json`); never overwrite without a backup.
- **OpenSearch / Redshift / Snowflake / Splunk destination changes:** these credentials live in Secrets Manager; verify the secret ARN and rotation state before `update-destination`.
- **Cross-account work:** confirm the Firehose role has the cross-account trust and the destination account has the resource policy before diagnosing the destination side.

