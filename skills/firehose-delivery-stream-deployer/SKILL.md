---
name: firehose-delivery-stream-deployer
description: 'Provisions Kinesis Data Firehose delivery streams with production defaults: source selection (Direct PUT, Kinesis Data Stream, Amazon MSK, CloudWatch Logs), Lambda transformation for ETL, format conversion (Parquet/ORC/JSON via dynamic schema), S3 destination (prefix patterns, error prefix, buffering hints), OpenSearch destination, HTTP endpoint destination (Splunk/custom), Redshift destination (COPY via S3 staging), backup configuration, retry and duration settings, CloudWatch logging, and server-side encryption (KMS). Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Firehose delivery stream, configuring S3/OpenSearch/Redshift/HTTP destinations, setting up Lambda transformation, or enabling Parquet format conversion. Triggers: create firehose delivery stream, firehose s3 destination, firehose lambda transformation, firehose parquet conversion, firehose opensearch destination, firehose redshift destination, firehose splunk http endpoint, firehose buffering hints.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with firehose, s3, lambda, iam, and kms access. Works with Terraform aws_kinesis_firehose_delivery_stream resources and CloudFormation AWS::KinesisFirehose::DeliveryStream templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, kinesis, firehose, delivery-stream, cloudops, deploy, analytics, provisioning, s3-destination, lambda-transformation, parquet, kms-encryption
  dependencies: aws-orchestrator
  keywords: aws, kinesis, firehose, delivery stream, cloudops, deploy, provisioning, s3 destination, opensearch, redshift, lambda transformation, parquet, format conversion, buffering hints, kms encryption
  when_to_use: Invoke when the user wants to create a Kinesis Data Firehose delivery stream, configure S3/OpenSearch/Redshift/HTTP endpoint destinations, set up Lambda transformation for ETL, enable Parquet or ORC format conversion, configure buffering hints, or set up KMS encryption. Do NOT invoke for Kinesis Data Streams (use kinesis-stream-deployer), Kinesis Data Analytics (use kinesis-analytics-deployer), or Firehose auditing/troubleshooting.
---

# Firehose Delivery Stream Deployer

An AWS CloudOps agent skill that provisions Kinesis Data Firehose
delivery streams with correct defaults. The skill walks the operator
through source selection (Direct PUT, Kinesis Data Stream, MSK,
CloudWatch Logs), processing/transformation (Lambda function for ETL),
format conversion (Parquet/ORC/JSON via dynamic schema), destination
selection (S3, OpenSearch, HTTP endpoint, Redshift), backup
configuration, buffering hints, retry/duration settings, CloudWatch
logging, and server-side encryption (KMS), captures data pipeline
decisions, explains why each default matters, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create Firehose delivery stream, Firehose S3 destination, Firehose
Lambda transformation, Firehose Parquet conversion, Firehose
OpenSearch destination, Firehose Redshift destination, Firehose Splunk
HTTP endpoint, Firehose buffering hints.

## STRICT output contract

When this skill is invoked with a Firehose-provisioning request
(create a delivery stream, configure a destination, set up Lambda
transformation, enable format conversion, or a partial configuration),
the agent MUST respond with the READY_TO_DEPLOY checklist defined in
the "Output format" section using the literal all-caps labels
`FIREHOSE:`, `VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`.
Do NOT preface the checklist with prose, headings, or disclaimers —
emit the block as the first lines of the response. This contract is
what assertion-based evals and downstream provisioning pipelines rely
on; deviating from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Source selection | Direct PUT vs Kinesis Stream vs MSK vs CW Logs |
| Step 2 — Lambda transformation | ETL processing |
| Step 3 — Format conversion | Parquet/ORC/JSON via dynamic schema |
| Step 4 — S3 destination | Prefix patterns, error prefix, buffering |
| Step 5 — OpenSearch destination | Index management, retry |
| Step 6 — HTTP endpoint destination | Splunk/custom endpoints |
| Step 7 — Redshift destination | COPY via S3 staging |
| Step 8 — Backup configuration | Source record backup |
| Step 9 — Buffering hints | Latency vs cost trade-off |
| Step 10 — Retry and duration | Error handling |
| Step 11 — CloudWatch logging | Error logging |
| Step 12 — Server-side encryption (KMS) | Encryption at rest |
| Step 13 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/destinations-and-buffering.md | Destination + buffering detail |
| references/transformation-and-encryption.md | Lambda + KMS detail |

## Mindset

**One-line takeaway:** A Firehose delivery stream is a fully managed
ETL pipeline that ingests data from a source, optionally transforms it
via Lambda, optionally converts the format (Parquet/ORC), and delivers
it to a destination (S3, OpenSearch, HTTP endpoint, Redshift).
Buffering hints control the latency-vs-cost trade-off. The source,
transformation, and destination must all be configured correctly for
data to flow end-to-end.

Three misconceptions dominate Firehose misdesign at provisioning time:

- **"Buffering hints don't matter."** They do. Buffering hints
  (SizeInMBs and IntervalInSeconds) control when Firehose flushes
  buffered data to the destination. Too low = frequent small writes
  (high cost from many small S3 objects, high OpenSearch indexing
  overhead). Too high = high latency. A baseline model often leaves
  defaults without considering the trade-off.

- **"Lambda transformation and format conversion are
  interchangeable."** They are NOT. Lambda transformation runs custom
  code on each batch of records (any transformation logic). Format
  conversion is a built-in feature that converts JSON to Parquet or
  ORC using a Glue table schema — no code needed. They CAN be used
  together (Lambda transforms, then format conversion serializes to
  Parquet), but the data flow order matters.

- **"S3 prefix patterns are cosmetic."** They are not. S3 prefix
  patterns (Hive-style `year=!{timestamp:yyyy}/month=!{timestamp:MM}/`)
  determine how data is partitioned in S3. Partitioning affects Athena
  query performance (partition pruning), Glue crawler efficiency, and
  cost (scanning less data). A flat prefix means every query scans all
  data.

## Configuration dependency graph (novel heuristic)

Firehose configurations are NOT independent. The source must be
configured before the stream can receive data. Lambda transformation
must reference an existing Lambda function. Format conversion requires
a Glue table schema. The destination type determines backup and retry
behavior. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Delivery stream | source config valid; destination config valid | stream is CREATING then ACTIVE; cannot deliver until ACTIVE | the stream ARN for producers |
| Source (Direct PUT) | none | producers use PutRecord/PutRecordBatch API | data ingestion |
| Source (Kinesis Stream) | Kinesis Data Stream exists | stream must be in same region; Firehose reads via enhanced fan-out or polling | stream-to-firehose pipe |
| Source (MSK) | MSK cluster exists; topic identified | Firehose reads from MSK topic directly | MSK-to-firehose pipe |
| Source (CloudWatch Logs) | CW Logs subscription filter | subscription filter sends to Firehose | log-to-firehose pipe |
| Lambda transformation | Lambda function exists; IAM role permits invoke | Lambda receives records, returns transformed + failed records | custom ETL processing |
| Format conversion (Parquet/ORC) | Glue database + table with schema; IAM role permits Glue | conversion uses the Glue table schema; wrong schema = malformed output | columnar format for analytics |
| S3 destination | S3 bucket exists; IAM role permits S3 write | prefix pattern determines partitioning; error prefix catches failed records | S3 data lake delivery |
| OpenSearch destination | OpenSearch domain exists; IAM role permits write | index name must be valid; retry buffer holds failed writes | OpenSearch indexing |
| HTTP endpoint destination | endpoint URL accessible; API key/auth configured | Firehose POSTs batches; endpoint must ACK within timeout | Splunk / custom delivery |
| Redshift destination | Redshift cluster exists; S3 staging bucket; COPY command | Firehose stages to S3 then issues COPY; username/password or IAM auth | Redshift loading |
| Backup configuration | S3 bucket for backup | source record backup (pre-transformation); failed record backup | data recovery |
| KMS encryption | KMS key exists; IAM role permits kms:Decrypt | encryption at rest for buffered data and S3 delivery | encryption compliance |
| CloudWatch logging | CW log group exists; IAM role permits logs | error logging enabled per destination type | operational visibility |

**The buffering-hints + format-conversion row is the one a baseline
model misses.** Buffering hints interact with format conversion: if
buffering is too small, the Parquet writer produces many tiny files
(row group overhead dominates). If buffering is too large, latency
increases. The correct tuning depends on the format and downstream
query patterns.

**Cross-dependency gotchas:**
- Lambda transformation runs BEFORE format conversion. If Lambda
  returns malformed JSON, format conversion to Parquet fails silently
  (records go to the error prefix).
- The IAM role for the delivery stream must trust firehose.amazonaws.com
  and have permissions for ALL configured destinations, Lambda, Glue,
  and KMS as applicable.
- S3 prefix patterns use Firehose-specific expression syntax
  (`!{timestamp:yyyy}`, `!{partitionKeyFromQuery:...}`). Using the
  wrong syntax produces literal folder names instead of dynamic
  partitions.

## Expert heuristic: buffering hints trade-off (latency vs cost)

A baseline model says "use default buffering." The correct heuristic
recognizes that buffering hints are a tunable trade-off between
delivery latency and cost (number of destination writes).

```text
Buffering hints (S3 destination):
  SizeInMBs:    1-128 MB (default 5 MB for S3; 64 MB for Parquet)
  IntervalInSeconds: 60-900 seconds (default 300)

  LOW buffering (1 MB / 60s):
    → Many small S3 objects (high PUT cost, many tiny Parquet files)
    → Low latency (data delivered quickly)
    → Bad for Athena (many small files = slow queries)
    → Good for real-time dashboards

  HIGH buffering (128 MB / 900s):
    → Few large S3 objects (low PUT cost, optimal Parquet row groups)
    → High latency (up to 15 minutes)
    → Good for Athena (fewer files = faster queries)
    → Bad for real-time dashboards

  RECOMMENDED for Parquet (Athena下游):
    SizeInMBs: 64-128 MB (Parquet row group optimization)
    IntervalInSeconds: 300-900s

  RECOMMENDED for OpenSearch:
    SizeInMBs: 5 MB (avoid bulk indexing overhead)
    IntervalInSeconds: 60-300s
```

**Key implication:** for S3 destinations queried by Athena, use larger
buffers (64-128 MB) to produce fewer, larger Parquet files. For
OpenSearch destinations, use smaller buffers (5 MB) to reduce indexing
latency. The defaults are rarely optimal.

## Expert heuristic: Lambda transformation blueprints

Lambda transformation processes each batch of records. The Lambda
function receives a base64-encoded payload and must return transformed
records plus any failed records.

```text
Lambda transformation flow:
  Firehose → batch of records → Lambda invocation
    → Lambda transforms each record (parse, enrich, filter)
    → Lambda returns: { records: [...], droppedRecords: [...] }
    → Transformed records continue to format conversion / destination
    → Dropped records are silently discarded (enable backup to retain)

  Common transformation blueprints:
    1. JSON parsing + field extraction (data normalization)
    2. Enrichment (add GeoIP, lookup reference data)
    3. Filtering (drop records not matching criteria)
    4. Format conversion prep (ensure records are valid JSON for Parquet)
    5. Aggregation (combine multiple records into one)
```

**Key implication:** if using format conversion to Parquet, the Lambda
transformation MUST output valid JSON that matches the Glue table
schema. Malformed JSON from Lambda causes format conversion to fail —
records go to the S3 error prefix, not the main prefix.

## Expert heuristic: S3 partition projection via Hive-style prefix

S3 prefix patterns determine data partitioning. Hive-style prefixes
enable Athena partition pruning and Glue partition projection.

```text
Flat prefix (BAD for analytics):
  S3 key: my-bucket/data/2024-01-15-10-30-00-recordId.parquet
  → Every Athena query scans ALL files (no partition pruning)
  → Slow queries, high cost

Hive-style prefix (GOOD for analytics):
  S3 prefix: my-bucket/data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/
  S3 key: my-bucket/data/year=2024/month=01/day=15/2024-01-15-10-30-00-recordId.parquet
  → Athena can prune by year/month/day (scan less data)
  → Glue crawler auto-discovers partitions
  → Partition projection can auto-populate partitions

Error prefix (for failed records):
  Error prefix: my-bucket/errors/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/
  → Failed records separated by error type and date
```

**Key implication:** always use Hive-style partitioned prefixes for
S3 destinations queried by Athena. The Firehose expression syntax
(`!{timestamp:yyyy}`) is specific to Firehose — do not use generic
template variables.

## Prerequisites (verify before provisioning)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| S3 bucket exists (S3/Redshift destination) | Firehose delivers to S3; Redshift stages via S3 | `aws s3api head-bucket --bucket <name>` |
| OpenSearch domain exists (OpenSearch destination) | Firehose writes to an OpenSearch index | `aws opensearch describe-domain --domain-name <name>` |
| Redshift cluster exists (Redshift destination) | Firehose issues COPY from S3 staging | `aws redshift describe-clusters` |
| Lambda function exists (if transformation) | Firehose invokes Lambda for ETL | `aws lambda get-function --function-name <name>` |
| Glue database + table (if format conversion) | Parquet/ORC conversion uses Glue schema | `aws glue get-table --database-name <db> --name <table>` |
| KMS key exists (if SSE enabled) | Encryption at rest for buffered data | `aws kms describe-key --key-id <key-id>` |
| IAM role with firehose trust policy | Firehose assumes the role for all service access | Verify trust policy and permissions |
| CloudWatch log group (if logging enabled) | Error logging destination | `aws logs describe-log-groups` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Source selection

| Source type | How it works | When to use |
|---|---|---|
| Direct PUT | Producers call PutRecord/PutRecordBatch API | Custom producers, API Gateway, CloudWatch Logs subscription, IoT |
| Kinesis Data Stream | Firehose reads from a KDS stream | Existing KDS pipeline needing delivery |
| Amazon MSK | Firehose reads from MSK topic directly | Kafka-based streaming, no consumer management |
| CloudWatch Logs | Subscription filter sends logs to Firehose | Log processing, SIEM ingestion |

**Direct PUT (most common):** no source configuration needed beyond
the type. Producers use the Firehose API.

**Kinesis Data Stream:** specify the stream ARN. Firehose can use
enhanced fan-out (recommended for high throughput) or polling.

## Step 2 — Lambda transformation

Lambda transformation runs custom ETL on each batch. Configure the
Lambda function ARN and a buffer size (1-128 MB) that controls batch
size.

```bash
# In the Firehose config:
ProcessingConfiguration:
  Enabled: true
  Processors:
    - Type: Lambda
      Parameters:
        - ParameterName: LambdaArn
          ParameterValue: arn:aws:lambda:us-east-1:123456789012:function:firehose-transform
        - ParameterName: BufferSizeInMBs
          ParameterValue: "3"
        - ParameterName: RoleArn
          ParameterValue: arn:aws:iam::123456789012:role/FirehoseStreamRole
```

**Lambda output contract:** the function must return a JSON object with
`records` (each with `recordId`, `result: Ok/Dropped`, and `data` as
base64). Records marked `Dropped` are silently discarded.

**Key implication:** if using format conversion to Parquet, the Lambda
output MUST be valid JSON matching the Glue table schema. Malformed
JSON causes conversion failure.

## Step 3 — Format conversion (Parquet/ORC/JSON)

Format conversion uses a Glue table schema to serialize records to
columnar formats (Parquet, ORC) — no code needed.

```bash
# In the S3 destination config:
DataFormatConversionConfiguration:
  Enabled: true
  InputFormatConfiguration:
    Deserializer:
      OpenXJsonSerDe: {}
  OutputFormatConfiguration:
    Serializer:
      ParquetSerDe: {}  # or OrcSerDe
  SchemaConfiguration:
    DatabaseName: my_glue_db
    TableName: my_glue_table
    RoleArn: arn:aws:iam::123456789012:role/FirehoseStreamRole
    Region: us-east-1
```

**Requirements:**
- Glue database and table must exist with the correct schema.
- The IAM role must have `glue:GetTable` permissions.
- Input records must be valid JSON (if using Lambda transformation,
  ensure the output is valid JSON).
- Buffering hints should be larger for Parquet (64-128 MB) to produce
  optimal row group sizes.

## Step 4 — S3 destination

The most common destination. Configure bucket ARN, prefix, error
prefix, buffering hints, compression, and encryption.

```bash
S3DestinationConfiguration:
  RoleARN: arn:aws:iam::123456789012:role/FirehoseStreamRole
  BucketARN: arn:aws:s3:::my-data-lake
  Prefix: "data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/"
  ErrorOutputPrefix: "errors/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/"
  BufferingHints:
    SizeInMBs: 64
    IntervalInSeconds: 300
  CompressionFormat: UNCOMPRESSED  # SNAPPY/GZIP/ZIP for non-Parquet
  EncryptionConfiguration:
    KMSEncryptionConfig:
      AWSKMSKeyARN: arn:aws:kms:us-east-1:123456789012:key/abc123
```

**Prefix patterns:** use Hive-style partitioning for Athena
compatibility. Use `!{timestamp:yyyy}`, `!{timestamp:MM}`,
`!{timestamp:dd}`, `!{timestamp:HH}` for time-based partitioning.

**Compression:** for Parquet format conversion, leave compression as
UNCOMPRESSED (Parquet has built-in compression). For JSON, use GZIP or
SNAPPY.

## Step 5 — OpenSearch destination

Firehose writes to an OpenSearch index. Configure domain ARN, index
name, index rotation, retry, and S3 backup.

```bash
ElasticsearchDestinationConfiguration:
  RoleARN: arn:aws:iam::123456789012:role/FirehoseStreamRole
  DomainARN: arn:aws:es:us-east-1:123456789012:domain/my-domain
  IndexName: logs
  IndexRotationPeriod: OneDay  # NoRotation/OneHour/OneDay/OneWeek/OneMonth
  TypeName: _doc
  BufferingHints:
    IntervalInSeconds: 300
    SizeInMBs: 5
  RetryOptions:
    DurationInSeconds: 300
  S3BackupMode: FailedDocumentsOnly
  S3Configuration:
    RoleARN: arn:aws:iam::123456789012:role/FirehoseStreamRole
    BucketARN: arn:aws:s3:::firehose-opensearch-backup
    Prefix: "failed/"
```

**Retry:** failed writes to OpenSearch are retried for up to
`DurationInSeconds`. After that, failed documents go to the S3 backup
bucket.

## Step 6 — HTTP endpoint destination (Splunk/custom)

Firehose POSTs batches to an HTTP endpoint (Splunk, Datadog, custom).

```bash
HttpEndpointDestinationConfiguration:
  EndpointConfiguration:
    Url: https://splunk.example.com:8088/services/collector
    AccessKey: my-splunk-hec-token
  RoleARN: arn:aws:iam::123456789012:role/FirehoseStreamRole
  S3Configuration:
    RoleARN: arn:aws:iam::123456789012:role/FirehoseStreamRole
    BucketARN: arn:aws:s3:::firehose-splunk-backup
  BufferingHints:
    IntervalInSeconds: 60
    SizeInMBs: 5
  RetryOptions:
    DurationInSeconds: 300
```

**Endpoint ACK:** the endpoint must return HTTP 200 within 30 seconds.
Non-200 responses trigger retry.

## Step 7 — Redshift destination

Firehose stages data to S3, then issues a COPY command to Redshift.

```bash
RedshiftDestinationConfiguration:
  RoleARN: arn:aws:iam::123456789012:role/FirehoseStreamRole
  ClusterJDBCURL: jdbc:redshift://my-cluster.abc123.us-east-1.redshift.amazonaws.com:5439/mydb
  CopyCommand:
    DataTableName: my_table
    CopyOptions: "FORMAT AS JSON 'auto'"
  Username: admin
  Password: <password>
  S3Configuration:
    RoleARN: arn:aws:iam::123456789012:role/FirehoseStreamRole
    BucketARN: arn:aws:s3:::firehose-redshift-staging
    Prefix: "staging/"
```

**The COPY command** loads the staged S3 data into the Redshift table.
Configure `CopyOptions` based on the data format (JSON, CSV, Parquet).

## Step 8 — Backup configuration

Firehose can back up source records (pre-transformation) or failed
records (post-transformation delivery failure).

| Backup mode | What it backs up | Destination |
|---|---|---|
| `SourceRecord` (S3 dest) | All source records before transformation | S3 backup bucket |
| `FailedDocumentsOnly` (OpenSearch/HTTP dest) | Records that failed delivery | S3 backup bucket |
| `FailedDataOnly` (Redshift dest) | Records that failed COPY | S3 backup bucket |

**Recommendation:** always enable backup for production streams. The
backup bucket should be separate from the main delivery bucket.

## Step 9 — Buffering hints (latency vs cost trade-off)

| Destination | Recommended SizeInMBs | Recommended IntervalInSeconds | Rationale |
|---|---|---|---|
| S3 (JSON) | 5-15 MB | 300s | Balance object size vs latency |
| S3 (Parquet) | 64-128 MB | 300-900s | Larger row groups = better compression + Athena performance |
| OpenSearch | 5 MB | 60-300s | Smaller batches reduce indexing overhead |
| HTTP endpoint | 5 MB | 60s | Low latency for downstream SIEM |
| Redshift | 64-128 MB | 300-900s | Fewer, larger COPY operations |

**Too-small buffering for Parquet = many tiny files.** Each tiny
Parquet file has row group overhead. Athena scanning many tiny files is
slow and expensive. Aim for 64+ MB per Parquet file.

## Step 10 — Retry and duration settings

| Setting | Default | Range | Effect |
|---|---|---|---|
| `RetryOptions.DurationInSeconds` | 300 | 0-7200 | How long Firehose retries failed writes before giving up |
| S3 backpressure | automatic | N/A | Firehose handles S3 throttling internally |

After the retry duration expires, failed records go to the backup/error
S3 prefix.

## Step 11 — CloudWatch logging

Firehose logs delivery errors to CloudWatch Logs. Each destination type
has its own log stream prefix.

```bash
# Enable logging in the delivery stream config
--extended-config (via CloudWatch logging)
```

Enable CloudWatch logging to capture format conversion errors,
Lambda transformation errors, and destination delivery failures.

## Step 12 — Server-side encryption (KMS)

Firehose supports KMS encryption for data at rest (in the buffer before
delivery) and for S3 delivery.

```bash
# In the S3 destination config:
EncryptionConfiguration:
  KMSEncryptionConfig:
    AWSKMSKeyARN: arn:aws:kms:us-east-1:123456789012:key/abc123

# Or use NoEncryptionConfig for unencrypted (not recommended)
```

**The IAM role must have kms:Decrypt and kms:GenerateDataKey
permissions** for the specified KMS key.

## Step 13 — Recent features

- **Parquet and ORC format conversion (2023-2024):** Built-in format
  conversion using Glue table schemas — no custom code needed. Enables
  direct Firehose-to-Athena pipelines with columnar formats.

- **MSK as a direct source (2023-2024):** Firehose can read directly
  from Amazon MSK topics without a separate consumer. Simplifies
  Kafka-to-S3/OpenSearch pipelines.

- **CloudWatch Logs subscription to Firehose (2023-2024):** Direct
  subscription filter integration for log processing and SIEM
  ingestion. No Lambda intermediary needed.

- **Partition projection support (2024-2025):** Hive-style S3 prefixes
  with `!{timestamp:...}` expressions enable Athena partition
  projection auto-population, eliminating the need for manual partition
  management.

- **HTTP endpoint destination enhancements (2024-2025):** Improved
  Splunk HEC integration with buffered delivery and per-record
  metadata support. Extended timeout for slow endpoints.

- **Enhanced fan-out for KDS source (2024-2025):** Firehose can use
  enhanced fan-out consumers when reading from Kinesis Data Streams,
  providing dedicated throughput for high-volume pipelines.

## NEVER do these things

1. **NEVER use default buffering hints for Parquet destinations.** The
   default 5 MB produces many tiny Parquet files with row group
   overhead. Use 64-128 MB for Parquet to produce optimal file sizes
   for Athena.

2. **NEVER use a flat S3 prefix for analytics destinations.** A flat
   prefix (`data/`) means Athena scans all files. Use Hive-style
   partitioned prefixes (`data/year=!{timestamp:yyyy}/month=.../`)
   for partition pruning.

3. **NEVER assume Lambda transformation and format conversion are
   interchangeable.** Lambda runs custom code per batch; format
   conversion uses a Glue schema. They can be used together (Lambda
   transforms, then conversion serializes to Parquet), but the Lambda
   output must be valid JSON matching the Glue schema.

4. **NEVER deploy without a backup configuration in production.**
   Without backup, failed records are lost. Configure
   `FailedDocumentsOnly` backup at minimum.

5. **NEVER use the same S3 bucket for main delivery and backup.**
   Failed records should go to a separate bucket or prefix for easier
   reprocessing. Mixing them complicates downstream ETL.

6. **NEVER leave encryption disabled for sensitive data.** Configure
   KMS encryption for both the Firehose buffer and S3 delivery. The
   IAM role must have kms:Decrypt and kms:GenerateDataKey permissions.

7. **NEVER forget the IAM role trust policy.** The delivery stream IAM
   role must trust `firehose.amazonaws.com` and have permissions for
   ALL configured destinations, Lambda (if transformation), Glue (if
   format conversion), and KMS (if encryption).

8. **NEVER use GZIP compression with Parquet format conversion.**
   Parquet has built-in compression. Set CompressionFormat to
   UNCOMPRESSED when using format conversion. GZIP is for JSON/CSV.

9. **NEVER assume CloudWatch Logs subscription works without the
   correct IAM role.** The subscription filter needs a role that
   permits `firehose:PutRecordBatch`. Verify the trust policy and
   permissions.

10. **NEVER set retry duration too low for flaky destinations.** The
    default 300s may be too short for OpenSearch under load. Increase
    `DurationInSeconds` (up to 7200s) for destinations with transient
    failures.

## Output format

```text
FIREHOSE: <stream-name> (<source> → <destination>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Source: Direct PUT | Kinesis Stream (<stream-name>) | MSK (<cluster>/<topic>) | CloudWatch Logs
  [✓|✗] Lambda transformation: enabled (<function-arn>, buffer <N>MB) | disabled
  [✓|✗] Format conversion: Parquet (Glue <db>/<table>) | ORC | JSON (no conversion)
  [✓|✗] Destination: S3 (<bucket>, prefix <prefix>) | OpenSearch (<domain>, index <index>) | HTTP (<url>) | Redshift (<cluster>)
  [✓|✗] Buffering hints: <size>MB / <interval>s (tuned for <format/destination>)
  [✓|✗] S3 prefix: Hive-style partitioned (<pattern>) | flat
  [✓|✗] Error prefix: <error-prefix>
  [✓|✗] Compression: <format> (UNCOMPRESSED for Parquet)
  [✓|✗] Backup: <mode> → <backup-bucket> | disabled
  [✓|✗] Retry: <duration>s
  [✓|✗] CloudWatch logging: enabled | disabled
  [✓|✗] KMS encryption: enabled (<key-arn>) | disabled
  [✓|✗] IAM role: <role-arn> (trust: firehose.amazonaws.com)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws firehose describe-delivery-stream --delivery-stream-name <name> --region <region>
  aws firehose describe-delivery-stream --delivery-stream-name <name> --query 'DeliveryStreamDescription.DeliveryStreamStatus' --region <region>
```

### Worked example — S3 Parquet with Lambda transformation

```text
FIREHOSE: events-to-s3-parquet (Direct PUT → S3)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Source: Direct PUT
  [✓] Lambda transformation: enabled (arn:aws:lambda:us-east-1:123456789012:function:firehose-transform, buffer 3MB)
  [✓] Format conversion: Parquet (Glue analytics/events_table)
  [✓] Destination: S3 (arn:aws:s3:::my-data-lake, prefix data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/)
  [✓] Buffering hints: 128MB / 300s (tuned for Parquet — optimal row group size)
  [✓] S3 prefix: Hive-style partitioned (year/month/day)
  [✓] Error prefix: errors/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/
  [✓] Compression: UNCOMPRESSED (Parquet has built-in compression)
  [✓] Backup: FailedDocumentsOnly → arn:aws:s3:::firehose-backup
  [✓] Retry: 300s
  [✓] CloudWatch logging: enabled
  [✓] KMS encryption: enabled (arn:aws:kms:us-east-1:123456789012:key/abc123)
  [✓] IAM role: arn:aws:iam::123456789012:role/FirehoseStreamRole (trust: firehose.amazonaws.com)
  [✓] Tags: Environment=production, Pipeline=events
VERIFICATION_COMMANDS:
  aws firehose describe-delivery-stream --delivery-stream-name events-to-s3-parquet --region us-east-1
  aws firehose describe-delivery-stream --delivery-stream-name events-to-s3-parquet --query 'DeliveryStreamDescription.DeliveryStreamStatus' --region us-east-1
```

## Error handling

### Records going to error prefix with format conversion
- Lambda transformation outputting invalid JSON that does not match
  the Glue table schema. Verify the Lambda function returns valid JSON
  with fields matching the Glue table columns.

### Many tiny S3 files (high cost, slow Athena)
- Buffering hints too low for Parquet. Increase SizeInMBs to 64-128 MB
  for Parquet destinations to produce fewer, larger files.

### OpenSearch delivery falling behind
- Buffering hints too high for OpenSearch. Decrease to 5 MB and
  IntervalInSeconds to 60-300s. Also check OpenSearch cluster health.

### Firehose stream stuck in CREATING
- IAM role missing permissions for destination, Glue, or KMS. Verify
  the role trust policy and all required permissions.

### CloudWatch Logs subscription not delivering
- Subscription filter IAM role missing
  `firehose:PutRecordBatch` permission, or the Firehose stream not in
  ACTIVE state.

## Domain

AWS CloudOps / Kinesis Data Firehose Delivery Stream Provisioning &
Data Pipeline Automation.

## AWS documentation

- **Firehose Guide** — https://docs.aws.amazon.com/firehose/latest/dev/what-is-this-service.html
- **Create delivery stream** — https://docs.aws.amazon.com/firehose/latest/dev/basic-create.html
- **S3 destination** — https://docs.aws.amazon.com/firehose/latest/dev/create-destination.html#create-destination-s3
- **OpenSearch destination** — https://docs.aws.amazon.com/firehose/latest/dev/create-destination.html#create-destination-opensearch
- **Lambda transformation** — https://docs.aws.amazon.com/firehose/latest/dev/data-transformation.html
- **Format conversion** — https://docs.aws.amazon.com/firehose/latest/dev/data-conversion.html
- **Buffering hints** — https://docs.aws.amazon.com/firehose/latest/dev/basic-deliver.html#buffering-hints
- **S3 prefix patterns** — https://docs.aws.amazon.com/firehose/latest/dev/s3-prefixes.html
- **KMS encryption** — https://docs.aws.amazon.com/firehose/latest/dev/encryption.html
- **HTTP endpoint destination** — https://docs.aws.amazon.com/firehose/latest/dev/httpdeliveryrequestresponse.html
