---
description: Diagnose Amazon Kinesis Data Firehose delivery stream failures via an 8-symptom decision tree and 5-layer health check.
nl_triggers:
  - "Firehose delivery fails"
  - "Firehose delivery lag"
  - "Firehose to S3 fails"
  - "Firehose to OpenSearch fails"
  - "Firehose to Redshift fails"
  - "Firehose to Snowflake fails"
  - "Firehose HTTP endpoint fails"
  - "Firehose Splunk delivery fails"
  - "Firehose Lambda transformation fails"
  - "DeliveryToS3.Success drops"
  - "DeliveryToS3.DataFreshnessSec high"
  - "data format conversion fails"
  - "Parquet conversion 0 bytes"
  - "ORC SerDe mismatch"
  - "Firehose circuit breaker"
  - "OpenSearch 429"
  - "Redshift COPY fails"
  - "Splunk HEC token invalid"
  - "Firehose KMS denied"
  - "bucket region mismatch"
routes_to: kinesis-firehose-troubleshooter
---

# /aws:troubleshoot-kinesis-firehose

Activate the `kinesis-firehose-troubleshooter` skill and diagnose
a Kinesis Data Firehose delivery stream failure via a systematic
8-symptom decision tree and 5-layer health check (source, transform,
convert, deliver, observability).

## What it does

Reads a delivery-stream-name and observed symptom, then applies
a 9-step diagnostic process:

1. Run the 5-layer Firehose health check (source, transform,
   convert, deliver, observability).
2. Diagnose delivery to S3 fails (bucket deleted, KMS key policy,
   bucket region mismatch, bucket policy, IAM gap).
3. Diagnose data transformation Lambda fails (timeout, exception,
   6 MB cap, resource policy, concurrency).
4. Diagnose delivery lag (buffering hints, Lambda slow, throttling,
   destination backpressure).
5. Diagnose data format conversion fails (non-JSON input, Glue
   schema mismatch, SerDe mismatch, 0-byte output).
6. Diagnose delivery to OpenSearch fails (cluster unreachable, auth,
   fine-grained access control, 429 circuit breaker).
7. Diagnose delivery to Redshift fails (cluster unavailable, COPY
   column mismatch, staging bucket IAM, encoding).
8. Diagnose latest destinations (Snowflake PrivateLink, HTTP
   endpoint, Splunk HEC).
9. Emit the DIAGNOSIS block with ROOT_CAUSE_FOUND, NEED_MORE_INFO,
   or ESCALATE.

Emits a deterministic VERDICT per diagnosis:

```text
DIAGNOSIS: <reference>
DELIVERY_STREAM: <stream-name>
DESTINATION: <s3 | opensearch | redshift | snowflake | http-endpoint | splunk | lambda>
SYMPTOM: DeliveryToS3Fails | LambdaFails | DeliveryLag | FormatConversionFails | OpenSearchFails | RedshiftFails | LatestDestinationFails
ROOT_CAUSE: <specific cause cited>
EVIDENCE: <diagnostic signals>
LAYER_CHECK: Source / Transform / Convert / Deliver / Observability
FIX: <action with CLI snippet>
VERIFICATION: <command to confirm fix>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
NEXT_STEP: <if NEED_MORE_INFO, the next diagnostic>
ESCALATION_PATH: <if ESCALATE, the recommended path>
```

## When to invoke

Paste a delivery-stream-name and symptom, or live diagnostic
output, and ask any of:

- "why is my Firehose stream failing to deliver"
- "DeliveryToS3.Success is at zero"
- "my Parquet conversion is producing 0-byte files"
- "the OpenSearch circuit breaker is engaged"
- "Firehose to Redshift COPY keeps failing"
- "Firehose to Snowflake can't reach the PrivateLink"
- "Splunk HEC token is getting 403"
- "DeliveryToS3.DataFreshnessSec is spiking"

A bare "delivery-stream-name + symptom" also routes here via the
orchestrator.

## Inputs

- Delivery-stream-name.
- Observed symptom (delivery-to-s3-fails / lambda-fails /
  delivery-lag / format-conversion-fails / opensearch-fails /
  redshift-fails / latest-destination-fails).
- Destination type (s3 / opensearch / redshift / snowflake /
  http-endpoint / splunk / lambda).
- Region.
- Lambda function name (optional, if transform configured).
- Glue database / table (optional, if format conversion configured).
- Destination endpoint (optional, OpenSearch / Redshift / Snowflake /
  Splunk).
- Recent CLI output from `describe-delivery-stream`, CloudWatch
  metrics, Lambda logs, etc. (optional, speeds diagnosis).
- CloudWatch Logs excerpt (optional, for per-record errors).

## Outputs

- One DIAGNOSIS block per delivery stream with SYMPTOM,
  ROOT_CAUSE, EVIDENCE, LAYER_CHECK, FIX, VERIFICATION, VERDICT,
  NEXT_STEP, and ESCALATION_PATH fields.
- For ROOT_CAUSE_FOUND: a specific cause + actionable fix CLI.
- For NEED_MORE_INFO: the specific next diagnostic to run (with
  the exact command).
- For ESCALATE: the escalation path (AWS Support, OpenSearch
  admin, Redshift admin, Snowflake admin) with the information to
  include.
- The 5-layer Firehose health check result for every diagnosis.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill
  is the Phase 2 Troubleshoot specialist for Analytics/Firehose).
- `/aws:audit-firehose-delivery-stream` for fleet-wide Firehose
  posture audit (companion to this skill's per-stream focus).
- `/aws:troubleshoot-kinesis-stream` for Kinesis Data Stream
  (not Firehose) issues - shard iterator, consumer, retention.
