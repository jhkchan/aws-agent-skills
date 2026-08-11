---
name: kinesis-firehose-troubleshooter
description: >-
  Diagnoses Amazon Kinesis Data Firehose delivery stream failures
  via a systematic 8-symptom decision tree: delivery to S3 fails
  (bucket deleted, KMS key policy, bucket region mismatch), data
  transformation Lambda fails (Lambda timeout, exception, resource
  policy), delivery lag (buffering hints too large, Lambda slow,
  throttling), data format conversion fails (incorrect JSON, Hive
  SerDe mismatch for Parquet/ORC), delivery to OpenSearch fails
  (cluster unreachable, auth failure, circuit breaker), delivery to
  Redshift fails (COPY command failure, staging bucket issue), and
  latest destinations (Firehose to Snowflake, HTTP endpoint, Splunk
  delivery). Maps each symptom to root cause via diagnostic commands
  and specific fixes. Emits ROOT_CAUSE_FOUND with a fix plan,
  NEED_MORE_INFO with the next diagnostic, or ESCALATE with the
  escalation path. Use when Firehose is failing to deliver, lagging,
  transforming incorrectly, or a downstream destination returns
  errors.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline diagnosis. Live-
  account troubleshooting uses aws firehose describe-delivery-
  stream, list-tags-for-stream, list-delivery-streams, start-
  delivery-stream-encryption, stop-delivery-stream-encryption,
  aws logs filter-log-events, aws lambda get-function,
  get-policy, invoke, aws s3api head-bucket, get-bucket-location,
  aws opensearch describe-domain, describe-domain-health, aws
  redshift describe-clusters, aws kms describe-key, get-key-policy,
  aws cloudwatch get-metric-statistics, and CloudTrail queries
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - Kinesis
  - Kinesis Data Firehose
  - delivery stream
  - delivery to S3 fails
  - delivery lag
  - data transformation Lambda
  - Lambda processing
  - data format conversion
  - Parquet
  - ORC
  - Hive SerDe
  - OpenSearch delivery
  - Redshift COPY
  - Snowflake delivery
  - HTTP endpoint delivery
  - Splunk HEC
  - circuit breaker
  - buffering hints
  - KMS key policy
  - staging bucket
tags: [kinesis, firehose, analytics, troubleshoot, delivery-stream, lambda, opensearch, redshift, diagnostic]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Analytics
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
  when_to_use: >-
    Diagnosing a Kinesis Data Firehose delivery stream that is
    failing to deliver, lagging, transforming incorrectly, or
    one of the downstream destinations returns errors. Covers
    the eight primary symptom categories: delivery to S3 fails,
    data transformation Lambda fails, delivery lag, data format
    conversion fails (Parquet/ORC), delivery to OpenSearch fails,
    delivery to Redshift fails, and latest destinations (Firehose
    to Snowflake, HTTP endpoint, Splunk). Use when CloudWatch
    shows DeliveryToS3.Success dropping, Firehose logs show
    Lambda transformation errors, ORC/Parquet conversion
    produces 0-byte objects, the OpenSearch destination returns
    429s, or the Redshift COPY command fails.
  activation_triggers:
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
  invocation_schema: >-
    Input: either (a) a delivery-stream-name with observed
    symptom (delivery-to-s3-fails / lambda-fails / delivery-lag
    / format-conversion-fails / opensearch-fails / redshift-fails
    / latest-destination-fails), optionally with a destination
    type (s3 / opensearch / redshift / snowflake / http-endpoint
    / splunk), OR (b) live-account diagnostic output from
    describe-delivery-stream, get-metric-statistics, filter-log-
    events, etc. Output: deterministic DIAGNOSIS block per
    stream - SYMPTOM/ROOT_CAUSE/EVIDENCE/LAYER_CHECK/FIX/
    VERDICT - where VERDICT is ROOT_CAUSE_FOUND (cause identified
    + fix actionable), NEED_MORE_INFO (specific next diagnostic
    cited), or ESCALATE (requires AWS Support or out-of-band
    action).
---

# Kinesis Data Firehose Troubleshooter

## Mindset

A Firehose delivery stream is a four-stage pipeline: **ingest**
(the PutRecord API or Kinesis Stream source), **transform**
(optional Lambda processing), **convert** (optional format
conversion to Parquet/ORC via Glue catalog), and **deliver**
(the destination: S3, OpenSearch, Redshift, Snowflake, HTTP
endpoint, Splunk). Most "Firehose failing" tickets are one stage
failing silently while the others report healthy. Diagnose the
stage first, then the destination-specific config.

- **The 5-layer health check is the upstream gate.** Firehose does not surface all failures as delivery-stream `ACTIVE` status changes; a Lambda transform or destination can fail while the stream stays green. Diagnose by layer: source, transform, convert, deliver, observability.
- **CloudWatch metrics are per-destination.** `DeliveryToS3.Success`, `DeliveryToOpenSearch.Success`, `DeliveryToRedshift.Success` are separate metrics. Verify the metric matching the configured destination, not just `DeliveryToS3.Success`.
- **`describe-delivery-stream` is the source of truth.** It returns the full destination config, Lambda ARN, buffering hints, and the S3 backup bucket. The console shows a summary; the API returns the exact JSON the service is using.

## Quick navigation

| You want to... | Go to |
|---|---|
| Run the 5-layer health check first (recommended) | Step 1 |
| Diagnose delivery to S3 fails | Step 2 |
| Diagnose data transformation Lambda fails | Step 3 |
| Diagnose delivery lag (high DataFreshness) | Step 4 |
| Diagnose data format conversion fails (Parquet/ORC) | Step 5 |
| Diagnose delivery to OpenSearch fails | Step 6 |
| Diagnose delivery to Redshift fails | Step 7 |
| Diagnose latest destinations (Snowflake / HTTP / Splunk) | Step 8 |
| Map symptom to root cause quickly | Appendix A |
| Avoid misdiagnosis pitfalls | Anti-Patterns |

## STRICT output contract

Every diagnosis MUST emit the exact DIAGNOSIS block with all fields
populated (no empty fields, no omitted sections, no reordering).
All five LAYER_CHECK lines (Source, Transform, Convert, Deliver,
Observability) are mandatory - even when the failure is destination-
specific.

Verdict-specific rules:
- `ROOT_CAUSE_FOUND` -> ROOT_CAUSE names a single specific cause; EVIDENCE cites at least one failing API signal or metric; FIX is actionable CLI.
- `NEED_MORE_INFO` -> ROOT_CAUSE is "Pending diagnosis - <what is known>"; NEXT_STEP cites the exact next command.
- `ESCALATE` -> ESCALATION_PATH names the recipient and the out-of-band action required.

```text
DIAGNOSIS: <reference>
DELIVERY_STREAM: <stream-name>
DESTINATION: <s3 | opensearch | redshift | snowflake | http-endpoint | splunk | lambda>
SYMPTOM: DeliveryToS3Fails | LambdaFails | DeliveryLag | FormatConversionFails | OpenSearchFails | RedshiftFails | LatestDestinationFails
ROOT_CAUSE: <specific cause cited>
EVIDENCE:
  - <diagnostic signal 1>
  - <diagnostic signal 2>
LAYER_CHECK:
  - Source: <PASS | FAIL - reason>
  - Transform: <PASS | FAIL - reason | N/A>
  - Convert: <PASS | FAIL - reason | N/A>
  - Deliver: <PASS | FAIL - reason>
  - Observability: <PASS | FAIL - reason>
FIX:
  - <action 1 with CLI snippet>
  - <action 2 ...>
VERIFICATION:
  - <command to confirm fix>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
NEXT_STEP: <if NEED_MORE_INFO, the specific next diagnostic>
ESCALATION_PATH: <if ESCALATE, the recommended path>
```

## Critical rules at a glance

1. **Run the 5-layer health check FIRST.** Before any destination-specific diagnosis, confirm: (1) source is feeding records, (2) Lambda transform (if any) is not erroring, (3) format conversion (if any) is producing non-zero output, (4) destination is reachable and accepting writes, (5) CloudWatch logging is enabled so you have evidence.
2. **Verify the per-destination metric.** `DeliveryToS3.Success` is irrelevant when the destination is OpenSearch. Use the metric matching the configured destination.
3. **`describe-delivery-stream` returns the live config.** The console may lag or show stale state; the API returns the actual JSON Firehose is using.
4. **Lambda transforms cap output at 6 MB.** A record that grows during transformation (enrichment, JSON expansion) can exceed the cap and be dropped silently to S3 backup.
5. **DataFreshness is the lag indicator.** A spike in `DeliveryToS3.DataFreshnessSec` means the destination is not keeping up with ingestion. Buffering hints and Lambda duration are the usual culprits.

## NEVER (top 5)

- **NEVER** diagnose a Firehose failure without first running the 5-layer health check. Most "delivery fails" tickets are coverage gaps in the transform Lambda, the KMS key policy, or the destination reachability.
- **NEVER** assume the delivery-stream status `ACTIVE` means records are being delivered. `ACTIVE` only means the stream config is accepted; per-record delivery failures are surfaced via CloudWatch metrics and S3 backup, not status.
- **NEVER** confuse a Lambda transform timeout with a Firehose bug. Firehose invokes the transform with the configured buffer (1-3 MB or 60-900 sec); a Lambda slower than the buffer cadence produces backpressure, not a Firehose failure.
- **NEVER** assume Parquet/ORC conversion is working because objects land in S3. Conversion can produce 0-byte objects if the input JSON is malformed or the Glue table schema does not match the data. Always verify object size, not just object count.
- **NEVER** emit `VERDICT: NEED_MORE_INFO` without a `NEXT_STEP` naming a specific diagnostic command. Generic phrases like "investigate further" are not acceptable.

## Expert heuristic

- If `DeliveryToS3.Success` drops to 0 instantly after a config change, the failure is **IAM, KMS, or bucket policy** (Step 2). Check CloudTrail for `AccessDenied` on `s3:PutObject` or `kms:GenerateDataKey`.
- If `DeliveryToS3.DataFreshnessSec` spikes without a drop in `Success`, the failure is **buffering hints or Lambda duration** (Step 4). The destination eventually catches up; data is just delayed.
- If Parquet objects land but query engines return empty results, the failure is **SerDe / Glue schema mismatch** (Step 5). The bytes are written but unreadable.
- If only OpenSearch destination fails with `429 Too Many Requests`, the failure is **OpenSearch write throttling** or the Firehose circuit breaker (default: 5 minutes of sustained writes). Scale the OpenSearch cluster or raise the circuit-breaker window.
- If Redshift COPY fails consistently at the same step, the failure is **column-count mismatch, encoding, or the staging-bucket IAM grant** (Step 7). Look in `STL_LOAD_ERRORS`.
- If Snowflake / HTTP endpoint / Splunk destinations fail, the failure is usually **credentials, network reachability, or the endpoint's auth model** (Step 8) - these do not exercise S3 KMS or Lambda layers.

## Pre-flight: data requirements

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

## Process - Diagnostic decision tree (apply in order)

### Step 0: Expert knowledge - non-obvious Firehose behaviors

- **`describe-delivery-stream` returns the live config including all destination sub-fields.** The console collapses sub-config; the API returns `S3DestinationUpdate`, `ExtendedS3DestinationUpdate`, `RedshiftDestinationUpdate`, `ElasticsearchDestinationUpdate`, `AmazonopensearchserviceDestinationUpdate`, `SnowflakeDestinationUpdate`, `HttpEndpointDestinationUpdate`, `SplunkDestinationUpdate` as separate blocks.
- **Firehose never silently drops records without leaving a trace.** Failed records go to S3 backup (if enabled) or surface as `DeliveryTo*.Success < 100`. Always enable CloudWatch logging + S3 backup before debugging.
- **Lambda transforms are invoked with buffered batches, not single records.** Buffering hints control cadence: 1-3 MB or 60-900 sec. A Lambda slower than the buffer cadence produces backpressure, not single-record failures.
- **Lambda transform output is capped at 6 MB per invocation.** Records that grow during enrichment (JSON expansion, join with reference data) can exceed this cap. The entire batch is dropped to S3 backup if the response exceeds 6 MB.
- **Data format conversion uses Glue Data Catalog schema.** If the Glue table schema does not match the input JSON, conversion produces 0-byte Parquet/ORC objects that look successful on `DeliveryToS3.Success` but are unreadable by Athena or other engines.
- **Parquet/ORC conversion requires the input to be valid JSON.** CSV or raw text input to a conversion-enabled stream is rejected; the records go to S3 error backup. The `InputFormatConfiguration.Deserializer` must be a `OpenXJsonSerDe` or `HiveJsonSerDe`.
- **OpenSearch destination uses a circuit breaker.** If Firehose receives 429 (Too Many Requests) from OpenSearch for sustained periods, it engages a circuit breaker that pauses delivery for a sliding window. Default circuit breaker: `5 minutes` of sustained failures; recovery requires sustained success.
- **OpenSearch auth uses either IAM signing or basic auth (master user).** Mixed-mode failures are common: the Firehose role has IAM signing but the domain uses fine-grained access control with a master user - Firehose needs both.
- **Redshift destination uses a staging S3 bucket + COPY command.** The COPY runs as the Redshift cluster's IAM role, not Firehose's. The cluster role must have `s3:GetObject` on the staging bucket. Most Redshift delivery failures are staging-bucket IAM or COPY column mismatches.
- **KMS key policy must grant the Firehose service principal.** `delivery.stream.amazonaws.com` needs `kms:GenerateDataKey` and `kms:Decrypt` on the key. A key policy that allows only the customer account root will deny Firehose even though the key is "enabled."
- **S3 bucket region must match the Firehose region.** Cross-region buckets are not supported by Firehose (with the explicit exception of S3 backup with a separate bucket). A bucket-region mismatch produces `AccessDenied` on `PutObject`.
- **Firehose to Snowflake uses a private Snowflake endpoint, not the public account URL.** Verify the `SnowflakeDestinationConfiguration.PrivateLinkVPCEId` and the Snowflake integration grant. Most Snowflake destination failures are private-link unreachable or integration not granted.
- **HTTP endpoint delivery retries with exponential backoff.** After the configured max retries, records go to S3 error backup. The endpoint must return HTTP 200 within the configured timeout.
- **Splunk destination uses HEC (HTTP Event Collector) tokens.** The token is stored in Secrets Manager; the Firehose role must have `secretsmanager:GetSecretValue`. An expired or rotated token produces 403 from Splunk.
- **Buffering hints affect both latency and cost.** Larger buffers (e.g., 128 MB / 900 sec) reduce S3 PUT costs but increase `DataFreshness`. Smaller buffers reduce latency but multiply S3 requests. Always tune for the workload, not the defaults.
- **Firehose does not support in-place config edits to a destination.** Use `update-destination` with the current version ID; concurrent updates conflict with `VersionId does not match`.
- **Dynamic partitioning (2024) uses Lambda-derived partition keys.** A Lambda that returns no partition key causes records to route to the default prefix only. Verify the `DynamicPartitioningConfiguration` and the Lambda metadata returned.

### Step 1: The 5-layer Firehose health check (run FIRST)

Before any destination-specific diagnosis, confirm all five layers.
A failing layer invalidates all downstream diagnosis.

**Layer 1 - Source (records are arriving):**

```bash
aws firehose describe-delivery-stream --delivery-stream-name <stream-name> \
  --query 'DeliveryStreamDescription.[DeliveryStreamStatus,DeliveryStreamType,Source.KinesisStreamSourceConfiguration]' --output table
aws cloudwatch get-metric-statistics --namespace AWS/Firehose \
  --metric-name IncomingBytes --dimensions Name=DeliveryStreamName,Value=<stream-name> \
  --start-time $(date -u -v-15M +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Sum --output table
```

For Kinesis-stream source, also verify the source stream is alive:

```bash
aws kinesis describe-stream-summary --stream-name <source-stream-name> \
  --query 'StreamDescriptionSummary.[StreamStatus,RetentionPeriodHours,OpenShardCount]' --output table
```

**Layer 2 - Transform (Lambda is not erroring):**

```bash
aws firehose describe-delivery-stream --delivery-stream-name <stream-name> \
  --query 'DeliveryStreamDescription.Destinations[0].<destination-block>.ProcessingConfiguration' --output table
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Errors --dimensions Name=FunctionName,Value=<lambda-function-name> \
  --start-time $(date -u -v-15M +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Sum --output table
aws logs filter-log-events --log-group-name /aws/lambda/<lambda-function-name> \
  --filter-pattern "ERROR" --start-time $(date -u -v-15M +%s)000 --output table
```

**Layer 3 - Convert (format conversion producing non-zero output):**

```bash
aws firehose describe-delivery-stream --delivery-stream-name <stream-name> \
  --query 'DeliveryStreamDescription.Destinations[0].ExtendedS3DestinationDescription.DataFormatConversionConfiguration' --output table
aws s3api list-objects-v2 --bucket <bucket> --prefix <prefix> \
  --query 'Contents[*].[Key,Size,LastModified]' --output table | head -20
```

**Layer 4 - Deliver (destination reachable and accepting writes):**

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Firehose \
  --metric-name <DeliveryToS3|DeliveryToOpenSearch|DeliveryToRedshift>.Success \
  --dimensions Name=DeliveryStreamName,Value=<stream-name> \
  --start-time $(date -u -v-15M +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Average --output table
```

For OpenSearch, also verify domain health:

```bash
aws opensearch describe-domain-health --domain-name <domain-name> \
  --query 'DomainStatus.[ClusterConfig.DedicatedMasterEnabled,ClusterConfig.InstanceType,ClusterHealth] ' --output table
```

**Layer 5 - Observability (logging is enabled):**

```bash
aws firehose describe-delivery-stream --delivery-stream-name <stream-name> \
  --query 'DeliveryStreamDescription.Destinations[0].<destination-block>.CloudWatchLoggingOptions' --output table
aws logs describe-log-groups --log-group-name-prefix /aws/kinesisfirehose/<stream-name> --output table
```

Flags: `Enabled: false` on CloudWatch logging means you are blind
to per-record errors. Enable before debugging further.

**If any layer fails, fix the layer FIRST.** Most Firehose failures
resolve when logging, IAM, or KMS is restored. Specifically:
- Layer 1 fails -> source stream paused or no PutRecord traffic.
- Layer 2 fails -> Lambda errors or timeouts; check Lambda logs.
- Layer 3 fails -> Glue schema mismatch or non-JSON input; check object size.
- Layer 4 fails -> destination unreachable, IAM gap, or KMS denial.
- Layer 5 fails -> CloudWatch logging disabled; enable before continuing.

### Step 2: Diagnose delivery to S3 fails

**Symptom:** `DeliveryToS3.Success` drops below 100% or objects
stop landing in the S3 bucket.

```bash
aws firehose describe-delivery-stream --delivery-stream-name <stream-name> \
  --query 'DeliveryStreamDescription.Destinations[0].ExtendedS3DestinationDescription.[BucketARN,RoleARN,BufferingHints,EncryptionConfiguration]' --output table
aws s3api head-bucket --bucket <bucket-name>
aws s3api get-bucket-location --bucket <bucket-name>
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=PutObject \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --query 'Events[*].[EventTime,Username,ResourceName]' --output table | grep -i <bucket>
```

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Bucket deleted | `head-bucket` returns `404` / `NoSuchBucket` | Recreate the bucket; or update-destination to a new bucket |
| Bucket region mismatch | `get-bucket-location` returns a region other than the Firehose region | Move the bucket to the Firehose region; cross-region S3 is not supported |
| KMS key disabled / rotated | `kms describe-key` shows `KeyState: Disabled` or `PendingDeletion` | Re-enable or recreate the key; update `EncryptionConfiguration.KMSEncryptionConfig` |
| KMS key policy denies Firehose | `get-key-policy` does not grant `kms:GenerateDataKey` to `delivery.stream.amazonaws.com` | Add a statement allowing `kms:GenerateDataKey`, `kms:Decrypt` for `ServicePrincipal: firehose.amazonaws.com` |
| Bucket policy denies Firehose role | Bucket policy `Statement` lacks `s3:PutObject` for the Firehose role ARN | Add `s3:PutObject`, `s3:AbortMultipartUpload`, `s3:ListBucketMultipartUploads` to the bucket policy |
| Firehose role lacks `s3:PutObject` | `simulate-principal-policy` returns `Denied` for `s3:PutObject` on the bucket | Attach / extend the Firehose role policy |
| Object prefix has invalid characters | Prefix contains `//`, leading `/`, or forbidden chars | Fix the prefix in `update-destination` |
| Multipart upload never completed | Object key fragments in `_InProgress/`; `CompleteMultipartUpload` denied | Add `s3:CompleteMultipartUpload`; check S3 lifecycle for `_ABORTED_` |

**VERDICT:** ROOT_CAUSE_FOUND when CloudTrail / IAM check
identifies a specific cause; NEED_MORE_INFO when the bucket and
IAM are correct but writes still fail (capture CloudTrail for the
exact `errorMessage`).

### Step 3: Diagnose data transformation Lambda fails

**Symptom:** `DeliveryToS3.Success` is healthy but transformed
records are wrong, dropped to S3 backup, or Lambda errors spike.

```bash
aws firehose describe-delivery-stream --delivery-stream-name <stream-name> \
  --query 'DeliveryStreamDescription.Destinations[0].<destination-block>.ProcessingConfiguration' --output table
aws lambda get-function --function-name <lambda-function-name> \
  --query 'Configuration.[Runtime,Timeout,MemorySize,Role]' --output table
aws lambda get-policy --function-name <lambda-function-name> --query 'Policy' --output text
aws logs filter-log-events --log-group-name /aws/lambda/<lambda-function-name> \
  --filter-pattern "ERROR Task timed out" --start-time $(date -u -v-1H +%s)000 --output table
```

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Lambda timeout | CloudWatch `Duration` near `Timeout`; log shows "Task timed out after X seconds" | Increase Lambda `Timeout` (max 900s); or reduce buffer size |
| Lambda exception | Log shows stack trace; `Errors` metric > 0 | Fix the handler code; common causes: JSON parse, missing field, ref-data fetch failure |
| Lambda response > 6 MB | S3 backup receives full batches; log shows "response payload exceeds 6 MB" | Reduce buffer size; or compress / trim records in the handler |
| Lambda resource policy lacks Firehose invoke | `get-policy` lacks `lambda:InvokeFunction` for `firehose.amazonaws.com` | Add `lambda:InvokeFunction` permission with principal `firehose.amazonaws.com`, source-arn = stream ARN |
| Lambda role lacks downstream access | Logs show `AccessDenied` on DynamoDB / S3 ref-data | Attach the required actions to the Lambda role |
| Lambda runtime deprecated | `Runtime: nodejs14.x` or `python3.7`; deprecation warning | Upgrade to a supported runtime (nodejs20.x, python3.12) |
| Lambda concurrency limit hit | CloudWatch `Throttles` > 0 | Raise reserved / account concurrency; or reduce buffer flush rate |
| Mismatched buffer vs Lambda duration | Buffer flush every 60s but Lambda `Timeout: 30s` for a 50 MB batch | Reduce buffer size or raise Lambda `Timeout` |
| Lambda returns malformed response | Log shows "Invalid output format" | Return `{ records: [{ recordId, result: 'Ok', data: base64 }], ... }` exactly per the Firehose transform protocol |

**VERDICT:** ROOT_CAUSE_FOUND when Lambda log identifies a specific
cause; NEED_MORE_INFO when Lambda errors are intermittent (sample
the handler code or ref-data source).

### Step 4: Diagnose delivery lag (high DataFreshness)

**Symptom:** `DeliveryToS3.DataFreshnessSec` spikes; records land
in S3 minutes or hours late.

```bash
aws firehose describe-delivery-stream --delivery-stream-name <stream-name> \
  --query 'DeliveryStreamDescription.Destinations[0].<destination-block>.BufferingHints' --output table
aws cloudwatch get-metric-statistics --namespace AWS/Firehose \
  --metric-name DeliveryToS3.DataFreshnessSec \
  --dimensions Name=DeliveryStreamName,Value=<stream-name> \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Average,Maximum --output table
```

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Buffering hints too large | `BufferingHints.SizeInMBs: 128` and `IntervalInSeconds: 900`; low-traffic stream | Reduce `SizeInMBs` to 5-10 or `IntervalInSeconds` to 60-300 |
| Lambda processing slow | Lambda `Duration` consistently > buffer flush interval | Increase Lambda memory (proportional CPU); parallelize processing; or reduce buffer size |
| Firehose throttled on `PutRecord` | Source-side `ThrottledRecords` > 0; `WriteThroughputBytes` flat | Request a limit increase; or shard the stream |
| Destination backpressure (OpenSearch 429) | OpenSearch `429` count > 0 in Firehose logs; circuit breaker engaged | Scale OpenSearch cluster; raise Firehose `IndexRotationPeriod` |
| KMS throttling | KMS `ThrottledRequests` > 0 | Request KMS RPS limit increase; or use AWS managed key |
| S3 503 Slow Down | S3 `5xx` rate elevated; `CompleteMultipartUpload` latency up | Use a higher-cardinality prefix; reduce PUT rate per partition |
| Network path latency | Cross-AZ or cross-region hops (VPN / PrivateLink) | Co-locate Firehose and destination in the same region and AZ group |

**VERDICT:** ROOT_CAUSE_FOUND when metric correlation identifies a
specific cause; NEED_MORE_INFO when DataFreshness spikes are
intermittent and uncorrelated with any single metric (instrument
per-stage timing in the Lambda transform).

### Step 5: Diagnose data format conversion fails (Parquet/ORC)

**Symptom:** objects land in S3 but Athena / engines return empty
or 0-byte objects; `DeliveryToS3.Success` shows healthy.

```bash
aws firehose describe-delivery-stream --delivery-stream-name <stream-name> \
  --query 'DeliveryStreamDescription.Destinations[0].ExtendedS3DestinationDescription.DataFormatConversionConfiguration' --output table
aws glue get-table --database-name <db> --name <table> \
  --query 'Table.[StorageDescriptor.Columns,Parameters]' --output table
aws s3api head-object --bucket <bucket> --key <prefix>/<latest-object> --query 'ContentLength' --output text
aws logs filter-log-events --log-group-name /aws/kinesisfirehose/<stream-name> \
  --filter-pattern "FormatConversion" --output table
```

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Input not valid JSON | Firehose log: "Input record is not valid JSON"; records to S3 error backup | Fix the producer to emit JSON; or change deserializer to OpenXJsonSerDe with tolerance |
| Glue schema mismatch | `get-table` columns do not match JSON keys; Athena returns nulls | Update the Glue table schema to match the data; or fix the producer |
| Hive SerDe mismatch (ORC vs Parquet) | OutputFormat set to ORC but writer config is Parquet; or vice versa | Align `OutputFormatConfiguration.Format` with the Glue table `TableType` and SerDe |
| Timestamp format wrong | Athena returns nulls on `timestamp` columns; Firehose log: "Invalid timestamp" | Add `TimestampFormats` to the SerDe (e.g., `yyyy-MM-dd HH:mm:ss.SSSSSS`) |
| Case sensitivity mismatch | JSON keys `snake_case` but Glue columns `CamelCase` | Set `CaseInsensitive` on the SerDe or rename Glue columns |
| Nested object not parsed | Glue `struct` type but input is a string-encoded JSON | Add `Mapping` or use a different SerDe; or pre-parse in Lambda transform |
| 0-byte objects | `head-object ContentLength: 0` | Conversion rejected the whole batch; check the S3 error backup and the Glue schema |
| Unsupported SerDe (CSV) | `InputFormatConfiguration.Deserializer` is `LazySimpleSerDe` (CSV) but output is Parquet | Use `OpenXJsonSerDe` for JSON-only inputs to Parquet/ORC conversion |

**VERDICT:** ROOT_CAUSE_FOUND when Glue schema vs input diff
identifies a specific cause; NEED_MORE_INFO when input is valid
JSON and schema matches but conversion still fails (sample a
record from the source and run it through the Glue crawler).

### Step 6: Diagnose delivery to OpenSearch fails

**Symptom:** `DeliveryToOpenSearch.Success` drops below 100%;
OpenSearch index missing recent documents.

```bash
aws firehose describe-delivery-stream --delivery-stream-name <stream-name> \
  --query 'DeliveryStreamDescription.Destinations[0].AmazonopensearchserviceDestinationDescription.[DomainARN,IndexName,RoleARN,TypeName,S3BackupMode]' --output table
aws opensearch describe-domain --domain-name <domain-name> \
  --query 'DomainStatus.[Endpoints,ClusterConfig.InstanceType,ClusterConfig.InstanceCount,EncryptionAtRestOptions.Enabled]' --output table
aws cloudwatch get-metric-statistics --namespace AWS/Firehose \
  --metric-name DeliveryToOpenSearch.Success \
  --dimensions Name=DeliveryStreamName,Value=<stream-name> \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Average --output table
```

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Cluster unreachable | `describe-domain` shows `Endpoints: null` or processing; Firehose log: `Connection refused` | Wait for domain to finish processing; or check VPC endpoint reachability |
| Auth failure - IAM | OpenSearch access policy does not allow the Firehose role | Add the Firehose role to the domain access policy with `es:ESHttpPost` |
| Auth failure - basic | Domain uses master-user auth; Firehose not configured with correct credentials | Configure `ClusterEndpoint` + `Username`/`Password` (Secrets Manager) |
| Fine-grained access control (FGAC) | Firehose role lacks the backend role mapping | Map the Firehose role to the appropriate OpenSearch role via the security plugin |
| OpenSearch 429 (Too Many Requests) | `429` count in Firehose logs; circuit breaker engaged | Scale the cluster (more / larger instances); or shard the Firehose destination |
| Circuit breaker tripped | Delivery resumes after sustained success; `Success: 0` for the breaker window | Same as 429; raise the breaker window via AWS Support if needed |
| Index name invalid | Index name has uppercase or invalid char; `400 Bad Request` | Use lowercase, no special chars; use `IndexRotationPeriod` for time-based indices |
| Document mapping conflict | Field type changes between records; OpenSearch rejects | Map fields explicitly in the index template; or use dynamic templates |
| VPC OpenSearch without Firehose VPC config | Firehose in a different VPC; private network unreachable | Put Firehose in the same VPC as OpenSearch; or use a transit gateway |
| KMS key policy (encryption-at-rest) | Key policy does not grant the Firehose role | Add `kms:GenerateDataKey`, `kms:Decrypt` for the Firehose role |
| OpenSearch health yellow/red | `describe-domain-health` shows `Yellow`/`Red` | Resolve shard allocation; free disk space; or restart unhealthy nodes |

**VERDICT:** ROOT_CAUSE_FOUND when access policy / OpenSearch
health identifies a specific cause; NEED_MORE_INFO when auth is
correct and the cluster is green but deliveries still fail
(capture the exact HTTP response code from Firehose logs).

### Step 7: Diagnose delivery to Redshift fails

**Symptom:** `DeliveryToRedshift.Success` drops; Redshift tables
missing recent data.

```bash
aws firehose describe-delivery-stream --delivery-stream-name <stream-name> \
  --query 'DeliveryStreamDescription.Destinations[0].RedshiftDestinationDescription.[ClusterJDBCURL,CopyCommand,RoleARN,Username,S3Configuration]' --output table
aws redshift describe-clusters --cluster-identifier <cluster-id> \
  --query 'Clusters[0].[ClusterStatus,ClusterAvailabilityStatus,NodeType,NumberOfNodes]' --output table
aws logs filter-log-events --log-group-name /aws/kinesisfirehose/<stream-name> \
  --filter-pattern "COPY" --output table
```

Connect to Redshift and check the load errors:

```sql
SELECT query, filename, line_number, colname, type, err_reason
FROM stl_load_errors
WHERE start_time > dateadd(hour, -1, getdate())
ORDER BY start_time DESC LIMIT 20;
```

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Redshift cluster paused / unavailable | `describe-clusters` shows `paused`, `available` with no active connections, or `resizing` | Resume the cluster; wait for resize; or use a Multi-AZ cluster |
| JDBC URL unreachable | Firehose log: `Connection refused` | Verify the security group allows the Firehose subnet to TCP/5439; or use Firehose-in-VPC |
| Credentials invalid | Firehose log: `Authentication failed` | Update `Username` + `Password` (Secrets Manager); rotate |
| COPY column mismatch | `stl_load_errors` shows `Extra column(s)` / `Missing column(s)` | Align the `CopyCommand.DataTableColumns` with the table schema |
| Encoding / format invalid | `stl_load_errors` shows `Invalid digit, Value '.', ... ` | Fix the producer format; or set `COPY ... ACCEPTANYDATE` / `TRIMBLANKS` / `NULL AS` |
| Staging bucket IAM gap | Firehose delivers to staging; COPY fails with `S3ServiceException: Access Denied` | Grant the **Redshift cluster role** (not Firehose role) `s3:GetObject` on the staging bucket |
| Staging bucket deleted | `head-bucket` on staging bucket returns 404 | Recreate staging bucket; or `update-destination` to a new staging bucket |
| Staging bucket region mismatch | Staging bucket in a different region than Redshift | Move staging bucket to the Redshift region |
| COPY timeout | `stl_load_errors` shows large file; COPY duration > Firehose retry window | Split files (smaller Firehose buffer); or use `COPY ... MAXERROR 100` with monitoring |
| Date / timestamp format | `stl_load_errors` shows `Invalid timestamp format` | Set `COPY ... FORMAT AS CSV` and `timeformat AS 'YYYY-MM-DD HH:MI:SS'` |
| KMS key for staging bucket | Redshift cluster role lacks `kms:Decrypt` on the staging bucket key | Add the Redshift cluster role to the staging bucket KMS key policy |

**VERDICT:** ROOT_CAUSE_FOUND when `stl_load_errors` identifies a
specific cause; NEED_MORE_INFO when the COPY appears to succeed
but rows are missing (check the Redshift workload manager and
transaction commits).

### Step 8: Diagnose latest destinations (Snowflake / HTTP / Splunk)

**Symptom:** Firehose to Snowflake / HTTP endpoint / Splunk returns
errors; `DeliveryTo*.Success` drops.

```bash
aws firehose describe-delivery-stream --delivery-stream-name <stream-name> \
  --query 'DeliveryStreamDescription.Destinations[0].[SnowflakeDestinationDescription,HttpEndpointDestinationDescription,SplunkDestinationDescription]' --output table
aws logs filter-log-events --log-group-name /aws/kinesisfirehose/<stream-name> \
  --filter-pattern "ERROR" --output table
```

#### Snowflake destination

| Cause | Diagnostic signal | Fix |
|---|---|---|
| PrivateLink VPC endpoint unreachable | Firehose log: `Connection timed out` to Snowflake VPCe | Verify the `PrivateLinkVPCEId`; ensure Firehose VPC can route to it |
| Snowflake integration not granted | Snowflake `SHOW INTEGRATIONS` shows the Firehose integration as not granted to the user / role | `GRANT USAGE ON INTEGRATION <name> TO ROLE <role>;` in Snowflake |
| Snowflake user / role mismatch | `AccountName` / `UserRole` in Firehose config does not match Snowflake | Update `update-destination --snowflake-destination-configuration` |
| Key-pair auth invalid | Snowflake log: `JWT token invalid` | Rotate the key pair; update Secrets Manager |
| Staging bucket (Snowflake) deleted | Firehose log: `Access Denied` on internal staging | Recreate the staging bucket (Firehose-managed) |
| `CustomSql` rejected by Snowflake | Firehose log: `SQL compilation error` | Fix the `CustomSql` MERGE / COPY statement |

#### HTTP endpoint destination

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Endpoint returns non-200 | Firehose log: `Endpoint returned 500` / `401` / `403` | Fix the endpoint; verify auth header |
| Endpoint timeout | Firehose log: `Request timed out after X ms` | Raise the `EndpointConfiguration.AccessKey` and endpoint timeout; or scale the endpoint |
| Endpoint URL unreachable | Firehose log: `Connection refused` / DNS resolution failed | If endpoint is private, put Firehose in a VPC with route to it |
| Access key mismatch | Firehose sends wrong access key; endpoint returns 401 | Update `AccessKey` in `update-destination` |
| Buffer / retry exhaustion | Firehose log: `Max retries exhausted` | Raise retries; investigate endpoint health |
| Malformed request | Firehose log: `400 Bad Request` | Match the endpoint's expected schema (the Firehose HTTP record format) |

#### Splunk destination

| Cause | Diagnostic signal | Fix |
|---|---|---|
| HEC token invalid / expired | Firehose log: `403 Forbidden` from Splunk | Rotate the token; update Secrets Manager |
| Secrets Manager access denied | Firehose log: `AccessDenied` on `secretsmanager:GetSecretValue` | Add `secretsmanager:GetSecretValue` on the secret to the Firehose role |
| HEC endpoint unreachable | Firehose log: `Connection refused` | Verify Splunk HEC URL; if Splunk is private, put Firehose in a VPC |
| Splunk indexer queue full | Firehose log: `503 Service Unavailable` | Scale Splunk indexers; raise HEC `maxThreads` |
| HEC ACK disabled | Splunk `inputs.conf` has `ack = 0`; Firehose retries never confirm | Enable HEC ack on the Splunk side |
| SSL / TLS mismatch | Firehose log: `SSL handshake failed` | Verify Splunk certificate chain; or set `S3BackupMode` for retry |

**VERDICT:** ROOT_CAUSE_FOUND when Firehose log + destination
check identifies a specific cause; NEED_MORE_INFO when the
endpoint accepts but reports no data (sample the payload from
S3 backup).

## Output format

The output block template above is the authoritative structure.
Violating any rule is a misdiagnosis. Three worked examples follow.

### Worked example - ROOT_CAUSE_FOUND, DeliveryToS3Fails (KMS gap)

```text
DIAGNOSIS: prod-firehose-s3
DELIVERY_STREAM: prod-events-delivery
DESTINATION: s3 (extended)
SYMPTOM: DeliveryToS3Fails
ROOT_CAUSE: KMS key policy on arn:aws:kms:us-east-1:111111111111:key/abc123
            does not grant the Firehose service principal
            kms:GenerateDataKey. The key policy allows only the
            customer account root.
EVIDENCE:
  - CloudTrail PutObject events for the Firehose role show errorMessage: "AccessDenied: kms:GenerateDataKey on arn:aws:kms:us-east-1:111111111111:key/abc123"
  - aws kms get-key-policy: Statement Principal = {"AWS": "arn:aws:iam::111111111111:root"} only
LAYER_CHECK:
  - Source: PASS - IncomingBytes > 0; stream type DirectPut
  - Transform: N/A - no Lambda processing configured
  - Convert: N/A - no format conversion
  - Deliver: FAIL - KMS key policy denies Firehose service principal
  - Observability: PASS - CloudWatch logging enabled
FIX:
  - Add the Firehose service principal to the KMS key policy:
    aws kms put-key-policy --key-id arn:aws:kms:us-east-1:111111111111:key/abc123 --policy-name default --policy '{"Id":"firehose-key-policy","Version":"2012-10-17","Statement":[{"Sid":"Enable IAM permissions","Effect":"Allow","Principal":{"AWS":"arn:aws:iam::111111111111:root"},"Action":"kms:*","Resource":"*"},{"Sid":"Allow Firehose","Effect":"Allow","Principal":{"Service":"firehose.amazonaws.com"},"Action":["kms:GenerateDataKey","kms:Decrypt"],"Resource":"*"}]}'
  - No Firehose-side change; the key policy is the only gap.
VERIFICATION:
  - aws cloudwatch get-metric-statistics --namespace AWS/Firehose --metric-name DeliveryToS3.Success --dimensions Name=DeliveryStreamName,Value=prod-events-delivery --start-time $(date -u -v-15M +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 60 --statistics Average --output table
  - Expect: Average >= 1.0 within 5-10 minutes of the key policy update.
VERDICT: ROOT_CAUSE_FOUND
NEXT_STEP: None
ESCALATION_PATH: None
```

### Worked example - NEED_MORE_INFO, DeliveryLag (intermittent)

```text
DIAGNOSIS: prod-firehose-lag
DELIVERY_STREAM: prod-events-delivery
DESTINATION: s3
SYMPTOM: DeliveryLag
ROOT_CAUSE: Pending diagnosis - DataFreshnessSec spikes at
            irregular intervals. Buffering hints are 64 MB /
            900 sec which is reasonable for the traffic level.
            Need per-stage timing in the Lambda transform to
            identify whether the lag is Lambda-bound or
            destination-bound.
EVIDENCE:
  - get-metric-statistics DeliveryToS3.DataFreshnessSec: spikes to 600-900 sec every ~30 min
  - BufferingHints: SizeInMBs=64, IntervalInSeconds=900
  - DeliveryToS3.Success: 100% (no drops)
  - Lambda Errors metric: 0
LAYER_CHECK:
  - Source: PASS - IncomingBytes steady
  - Transform: PASS (no errors) - but duration distribution unknown
  - Convert: N/A
  - Deliver: PASS - Success 100%
  - Observability: PASS
FIX: (pending root cause)
VERIFICATION: (pending fix)
VERDICT: NEED_MORE_INFO
NEXT_STEP: Enable Lambda Insights and capture per-invocation
  duration distribution:
    aws logs filter-log-events --log-group-name /aws/lambda/<fn> --filter-pattern "REPORT"
  Concurrently, query for KMS throttling:
    aws cloudwatch get-metric-statistics --namespace AWS/KMS --metric-name ThrottledRequests --dimensions Name=KeyId,Value=<key-id> --start-time $(date -u -v-3H +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Sum --output table
  If duration spikes correlate with the DataFreshness spikes, the
  Lambda is the bottleneck. If KMS ThrottledRequests spikes, the
  limit is the bottleneck.
ESCALATION_PATH: If timing does not correlate with any single
  metric, escalate to AWS Support with the delivery-stream-name
  and the DataFreshness spike timestamps.
```

### Worked example - ESCALATE, OpenSearchFails (cluster red)

```text
DIAGNOSIS: prod-firehose-opensearch
DELIVERY_STREAM: prod-events-to-opensearch
DESTINATION: opensearch
SYMPTOM: OpenSearchFails
ROOT_CAUSE: OpenSearch domain prod-events-search is in RED
            cluster health. Shard allocation is failing because
            two data nodes are out of disk (free storage below
            the watermark). Firehose cannot deliver until the
            cluster returns to GREEN or YELLOW.
EVIDENCE:
  - describe-domain-health: ClusterHealth=Red
  - OpenSearch ClusterStatus shows 2/5 nodes with free_storage_below_watermark
  - DeliveryToOpenSearch.Success: 0% for the last 45 minutes
  - Firehose log: circuit breaker engaged after 5 minutes of sustained 429
LAYER_CHECK:
  - Source: PASS - IncomingBytes steady
  - Transform: N/A
  - Convert: N/A
  - Deliver: FAIL - OpenSearch cluster red, Firehose circuit breaker engaged
  - Observability: PASS
FIX: Cannot remediate from Firehose side alone - the OpenSearch
  cluster needs disk cleanup, node expansion, or index lifecycle
  action. The Firehose circuit breaker will recover automatically
  once OpenSearch returns to sustained success, but the cluster
  state change requires OpenSearch admin action.
VERIFICATION: After OpenSearch returns to GREEN:
  aws opensearch describe-domain-health --domain-name prod-events-search --query 'DomainStatus.ClusterHealth' --output text --profile opensearch-admin
  Expect: Green. Then Firehose circuit breaker will reset within the configured window.
VERDICT: ESCALATE
NEXT_STEP: Provide the OpenSearch admin with this remediation:
  1. Identify oversized indices: GET _cat/indices?v&s=store.size:desc
  2. Delete or snapshot old indices via the Index State Management policy
  3. Add EBS storage or instance count to free disk above the watermark
ESCALATION_PATH: OpenSearch domain administrator must restore
  prod-events-search to GREEN. Firehose will resume automatically
  once the circuit breaker window clears.
```

## Anti-Patterns - NEVER do these things

- NEVER diagnose a Firehose failure without first running the 5-layer health check. Most "delivery fails" tickets are coverage gaps in the transform Lambda, KMS key policy, or destination reachability.
- NEVER assume the delivery-stream status `ACTIVE` means records are being delivered. `ACTIVE` only means the stream config is accepted; per-record delivery failures are surfaced via CloudWatch metrics and S3 backup, not status.
- NEVER confuse a Lambda transform timeout with a Firehose bug. Firehose invokes the transform with the configured buffer; a Lambda slower than the buffer cadence produces backpressure, not a Firehose failure.
- NEVER assume Parquet/ORC conversion is working because objects land in S3. Conversion can produce 0-byte objects if the input JSON is malformed or the Glue table schema does not match the data. Always verify object size, not just object count.
- NEVER emit `VERDICT: NEED_MORE_INFO` without a `NEXT_STEP` naming a specific diagnostic command. Generic phrases like "investigate further" are not acceptable.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE** before any state-changing operation (`update-destination`, `start-delivery-stream-encryption`, `stop-delivery-stream-encryption`, `create-delivery-stream`, `delete-delivery-stream`).
- **`update-destination` blast radius:** the change applies to all in-flight records; snapshot `describe-delivery-stream --output json` BEFORE the update.
- **KMS key policy changes:** always print the existing policy first (`get-key-policy --output json`); never overwrite without a backup.
- **OpenSearch / Redshift / Snowflake / Splunk destination changes:** these credentials live in Secrets Manager; verify the secret ARN and rotation state before `update-destination`.
- **Cross-account work:** confirm the Firehose role has the cross-account trust and the destination account has the resource policy before diagnosing the destination side.

## Appendix A - Symptom-to-cause map (quick reference)

| Symptom | Most common root cause | Verify via |
|---|---|---|
| DeliveryToS3Fails - bucket deleted | `head-bucket` 404 | `s3api head-bucket` |
| DeliveryToS3Fails - bucket region mismatch | `get-bucket-location` different region | `s3api get-bucket-location` |
| DeliveryToS3Fails - KMS denied | CloudTrail `kms:GenerateDataKey` AccessDenied | `kms get-key-policy` |
| DeliveryToS3Fails - bucket policy | Firehose role lacks `s3:PutObject` | `simulate-principal-policy` |
| LambdaFails - timeout | Lambda log "Task timed out"; Duration ~ Timeout | CloudWatch Lambda metrics + logs |
| LambdaFails - exception | Lambda `Errors > 0`; stack trace in logs | `filter-log-events "ERROR"` |
| LambdaFails - 6 MB cap | S3 backup gets full batches; "response payload exceeds 6 MB" | Firehose logs |
| LambdaFails - resource policy | Firehose cannot invoke Lambda | `lambda get-policy` |
| DeliveryLag - buffering | `BufferingHints` 128MB / 900s on low-traffic stream | `describe-delivery-stream` |
| DeliveryLag - Lambda slow | Lambda Duration > buffer flush interval | Lambda Insights |
| DeliveryLag - OpenSearch 429 | Circuit breaker engaged; `429` count | Firehose logs + OpenSearch metrics |
| DeliveryLag - KMS throttling | KMS `ThrottledRequests > 0` | KMS metrics |
| FormatConversionFails - non-JSON | Firehose log "Input record is not valid JSON" | Firehose logs |
| FormatConversionFails - schema mismatch | Glue columns do not match JSON keys | `glue get-table` |
| FormatConversionFails - 0 bytes | `head-object ContentLength: 0` | `s3api head-object` |
| OpenSearchFails - auth | OpenSearch access policy lacks Firehose role | OpenSearch access policy |
| OpenSearchFails - 429 | OpenSearch throttling; circuit breaker | Firehose logs |
| OpenSearchFails - cluster red | `describe-domain-health` Red | OpenSearch API |
| RedshiftFails - COPY | `stl_load_errors` shows column / format | Redshift SQL |
| RedshiftFails - staging IAM | Cluster role lacks `s3:GetObject` | `iam simulate-principal-policy` |
| Snowflake - PrivateLink | Firehose log "Connection timed out" | Firehose logs + Snowflake `SHOW INTEGRATIONS` |
| Snowflake - integration not granted | `GRANT USAGE ON INTEGRATION` missing | Snowflake SQL |
| HTTP - non-200 | Firehose log "Endpoint returned 500/401/403" | Firehose logs |
| HTTP - timeout | Firehose log "Request timed out" | Firehose logs + endpoint metrics |
| Splunk - HEC token | `403 Forbidden` from Splunk; Secrets Manager access denied | Firehose logs + Splunk indexer metrics |
| Splunk - indexer queue | `503 Service Unavailable`; HEC `maxThreads` exhausted | Splunk metrics |

## Recent AWS features (2024-2026)

- **Firehose to Snowflake (GA 2024):** Native destination supporting Snowflake PrivateLink VPC endpoints and key-pair auth via Secrets Manager. Verify `SnowflakeDestinationConfiguration.PrivateLinkVPCEId` and the Snowflake integration grant. Most failures are private-link unreachable or integration not granted.
- **HTTP endpoint delivery (expanded 2024-2025):** Generic HTTP endpoint destination now supports custom headers, retry policy, and per-record success/failure reporting. Verify the endpoint returns 200 within the configured timeout; retries back up to S3 error backup after exhaustion.
- **Splunk delivery enhancements (2024-2025):** HEC ack support, buffered retry, and Secrets Manager token rotation. Verify HEC `ack = 1` on the Splunk side; Firehose relies on ack to confirm writes.
- **Dynamic partitioning (2024-2025):** Lambda-derived partition keys enable S3 partition-on-the-fly. A Lambda that returns no partition key routes all records to the default prefix; verify `DynamicPartitioningConfiguration.RetryDuration`.
- **Parquet / ORC conversion via Glue (2024-2026):** Improved SerDe support including `OpenXJsonSerDe` case-insensitivity, `TimestampFormats`, and nested struct handling. Verify the Glue table schema matches the producer JSON exactly.
- **Firehose within a VPC (2024-2025):** Firehose can now deliver to private destinations (OpenSearch in VPC, private HTTP endpoints, Snowflake PrivateLink) without a NAT gateway. Verify the Firehose VPC config and the destination security group allows Firehose subnets.
- **Multi-AZ delivery + enhanced CloudWatch metrics (2025-2026):** Multi-AZ delivery for high-throughput streams; per-destination `DataFreshness`, `ThrottledRecords`, and per-Lambda-invocation duration are now available. Verify the dashboard uses the correct per-destination metric.

## AWS documentation

- **Amazon Kinesis Data Firehose Developer Guide** - https://docs.aws.amazon.com/firehose/latest/dev/what-is-this-service.html
- **Firehose delivery stream creation** - https://docs.aws.amazon.com/firehose/latest/dev/basic-create.html
- **Firehose data transformation** - https://docs.aws.amazon.com/firehose/latest/dev/data-transformation.html
- **Firehose data format conversion** - https://docs.aws.amazon.com/firehose/latest/dev/data-conversion.html
- **Firehose destinations (OpenSearch / Redshift / Snowflake / Splunk / HTTP)** - https://docs.aws.amazon.com/firehose/latest/dev/create-destination.html
- **Firehose HTTP endpoint request/response** - https://docs.aws.amazon.com/firehose/latest/dev/httpdeliveryrequestresponse.html
- **Monitoring Firehose with CloudWatch** - https://docs.aws.amazon.com/firehose/latest/dev/monitoring-with-cloudwatch-metrics.html
- **Firehose troubleshooting** - https://docs.aws.amazon.com/firehose/latest/dev/troubleshooting.html
- **Firehose IAM roles** - https://docs.aws.amazon.com/firehose/latest/dev/controlling-access.html
- **API Reference** - https://docs.aws.amazon.com/firehose/latest/APIReference/
- **CLI Reference** - https://docs.aws.amazon.com/cli/latest/reference/firehose/
