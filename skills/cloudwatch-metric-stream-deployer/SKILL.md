---
name: cloudwatch-metric-stream-deployer
description: >-
  Deploys Amazon CloudWatch Metric Streams with production defaults:
  stream creation (name, output format), Kinesis Data Firehose ARN
  configuration, metric namespace filter (include/exclude filter),
  statistics (Average, Sum, SampleCount, Min, Max, p99, etc.),
  output format (JSON or OpenTelemetry), Firehose to S3 delivery
  pipeline, CloudWatch to Kinesis Data Firehose to S3 continuous
  export, cross-account metric streaming, cost-per-metric-stream
  pricing awareness, CloudWatch API (PutMetricStream, GetMetricStream,
  DeleteMetricStream, ListMetricStreams), stream statistics auto-
  aggregation, IAM role permissions (cloudwatch.amazonaws.com service
  principal writing to Firehose, Firehose writing to S3 with KMS),
  Firehose buffering latency (1-5 minute delivery delay), and the
  cost-benefit tradeoff vs GetMetricData API polling (metric streams
  are cost-effective for >1000 metrics). Emits a READY_TO_DEPLOY
  checklist with verification commands or PREREQUISITES_MISSING with
  a specific gap citation. Use when creating a CloudWatch metric
  stream, exporting metrics to S3 continuously, replacing GetMetricData
  polling with a stream, streaming metrics in JSON or OpenTelemetry
  format, filtering by namespace, or configuring cross-account metric
  streaming. Triggers: create cloudwatch metric stream, metric stream
  firehose, cloudwatch to s3 metrics, metric stream namespace filter,
  metric stream opentelemetry, metric stream json, cloudwatch export
  metrics, metric stream cost, replace getmetricdata polling.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with cloudwatch,
  firehose, iam, and s3 access. Works with Terraform
  aws_cloudwatch_metric_stream resource and CloudFormation
  AWS::CloudWatch::MetricStream templates.
keywords:
  - aws
  - cloudwatch
  - metric stream
  - metrics
  - kinesis data firehose
  - firehose
  - s3 delivery
  - output format
  - json
  - opentelemetry
  - namespace filter
  - statistics
  - average
  - sum
  - samplecount
  - p99
  - getmetricdata
  - putmetricstream
  - cross-account
  - cloudops
  - deploy
tags:
  - aws
  - cloudwatch
  - metric-stream
  - metrics
  - firehose
  - opentelemetry
  - cloudops
  - deploy
  - observability
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Management
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - cloudwatch
    - metric-stream
    - metrics
    - firehose
    - opentelemetry
    - cloudops
    - deploy
    - observability
  dependencies:
    - aws-orchestrator
  keywords:
    - create cloudwatch metric stream
    - metric stream firehose
    - cloudwatch to s3 metrics
    - metric stream namespace filter
    - metric stream opentelemetry
    - metric stream json
    - cloudwatch export metrics
    - metric stream cost
    - replace getmetricdata polling
  when_to_use: >-
    Invoke when the user wants to create a CloudWatch metric stream —
    continuously export CloudWatch metrics to S3 via Kinesis Data
    Firehose, replace GetMetricData API polling with a stream, filter
    by namespace (include/exclude), choose JSON or OpenTelemetry
    output format, configure statistics (Average, Sum, p99),
    configure cross-account metric streaming, or understand metric
    stream cost (per-metric pricing). Do NOT invoke for CloudWatch
    Logs subscriptions (use logs skills), CloudWatch dashboards
    (use dashboard skills), CloudWatch alarms (use alarm skills), or
    X-Ray tracing (use tracing skills).
---

# CloudWatch Metric Stream Deployer

An AWS CloudOps agent skill that deploys Amazon CloudWatch Metric
Streams with correct defaults. The skill walks the operator through
the Firehose-ARN pipeline, namespace filtering, statistics selection,
output format (JSON/OpenTelemetry), role permissions, and the cost-
benefit tradeoff vs GetMetricData polling, captures the configuration,
explains why each default matters, and emits a READY_TO_DEPLOY
checklist with copy-pasteable verification commands.

## Activation keywords

create CloudWatch metric stream, metric stream Firehose, CloudWatch to
S3 metrics, metric stream namespace filter, metric stream
OpenTelemetry, metric stream JSON, CloudWatch export metrics, metric
stream cost, replace GetMetricData polling.

## STRICT output contract

When this skill is invoked with a metric-stream-deployment request
(create a metric stream, export metrics to S3 continuously, replace
API polling with a stream, filter by namespace, choose output format),
the agent MUST respond with the READY_TO_DEPLOY checklist defined in
the "Output format" section using the literal all-caps labels
`METRIC_STREAM:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing (Firehose does not exist, IAM role
lacks permission, S3 bucket missing), the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the checklist
(marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Pipeline architecture | CloudWatch → Firehose → S3 |
| Step 2 — Firehose ARN configuration | Delivery stream binding |
| Step 3 — Namespace filter (include/exclude) | Cost control |
| Step 4 — Statistics (Average, Sum, p99, etc.) | Aggregation |
| Step 5 — Output format (JSON vs OpenTelemetry) | Schema choice |
| Step 6 — IAM role permissions | cloudwatch → firehose → s3 chain |
| Step 7 — Cross-account metric streaming | Multi-account observability |
| Step 8 — Cost model (per-metric pricing) | Cost vs GetMetricData polling |
| Step 9 — Firehose buffering latency (1-5 min) | Delivery delay |
| Step 10 — CloudWatch API operations | PutMetricStream lifecycle |
| Step 11 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/firehose-and-output-formats.md | Firehose + format detail |
| references/filters-and-cost.md | Filtering + cost detail |

## Mindset

**One-line takeaway:** A CloudWatch metric stream continuously exports
CloudWatch metrics to a destination (Kinesis Data Firehose → S3 by
default) without API polling. It replaces individual `GetMetricData`
calls with a push-based pipeline. The namespace filter controls cost
(only stream the namespaces you need). Firehose buffering adds 1-5
minutes of delivery delay.

Three misconceptions dominate metric stream misdesign at provisioning
time:

- **"Metric streams and GetMetricData polling are interchangeable."**
  They are not. GetMetricData is a pull-based API with per-call
  pricing — cost scales linearly with the number of API calls needed
  to retrieve all metrics. Metric streams are push-based with per-
  metric pricing — cost scales with the number of unique metrics
  streamed. For >1000 metrics, metric streams are almost always
  cheaper. For <100 metrics queried occasionally, GetMetricData may be
  cheaper.

- **"The namespace filter is a convenience, not a cost control."** It
  IS the primary cost control. Metric streams charge per metric per
  month. Streaming every namespace in a busy account can mean hundreds
  of thousands of metrics. Use the include filter to stream only the
  namespaces you actually export to S3 (e.g., `AWS/EC2`, `AWS/Lambda`,
  `ApplicationMetrics`).

- **"Firehose delivers metrics in real-time."** It does not. Firehose
  buffers data based on buffer size (1-128 MB) and buffer interval
  (60-900 seconds). The default buffering adds 1-5 minutes of latency.
  For real-time alerting, use CloudWatch alarms directly — do NOT pipe
  a metric stream into an alerting pipeline.

## Configuration dependency graph (novel heuristic)

Metric stream configurations are NOT independent. The Firehose
delivery stream must exist and point to an S3 destination before the
metric stream can be created. The IAM role must allow CloudWatch to
write to Firehose. The S3 bucket must allow Firehose to write. Use
this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure | Enables downstream |
|---|---|---|---|
| S3 bucket | bucket exists | without KMS, data unencrypted at rest | the destination |
| Firehose delivery stream | S3 bucket exists; Firehose role allows s3:PutObject | Firehose silently buffers and retries; data not delivered until buffer flushes | the transport |
| IAM role (cloudwatch → firehose) | role with `firehose:PutRecord` / `PutRecordBatch` trust `cloudwatch.amazonaws.com` | without trust policy, metric stream shows "running" but delivers nothing | the write permission |
| Metric stream | Firehose ARN; IAM role ARN | stream enters "running" immediately; first data appears after 1-5 min buffering | the continuous export |
| Namespace filter | n/a (configured at stream creation) | include filter with zero matching namespaces = no data; exclude filter with all namespaces excluded = no data | cost scoping |
| Statistics | n/a (configured at stream creation) | omitting statistics defaults to ALL, which may include unnecessary stats per metric | per-metric output |
| Output format | n/a (configured at stream creation) | JSON vs OpenTelemetry are not interchangeable downstream; choose based on consumer | schema |

**The IAM-role-trust-policy row is the one a baseline model misses.**
The metric stream enters "running" status even if the IAM role's trust
policy does not include `cloudwatch.amazonaws.com`. CloudWatch cannot
write to Firehose, but the stream does not error — it silently
delivers nothing. Always verify the trust policy.

## Expert heuristic: metric streams vs GetMetricData polling

```text
Decision: metric stream vs GetMetricData polling

  Number of metrics to retrieve:
    ├── <100 metrics, queried occasionally
    │     → GetMetricData (per-call pricing; few calls = low cost)
    ├── 100-1000 metrics, queried regularly
    │     → Evaluate both (cost crossover zone)
    │     → GetMetricData: cost = calls × metrics-per-call × pricing
    │     → Metric stream: cost = unique metrics × per-metric pricing
    └── >1000 metrics, continuous export needed
          → Metric stream (per-metric pricing; far cheaper at scale)
          → Also avoids GetMetricData throttling (20-50 TPS limit)

  Use case:
    ├── Continuous export to S3 for long-term storage / analytics
    │     → Metric stream (push-based; no polling needed)
    ├── Real-time alerting (< 1 min latency)
    │     → CloudWatch alarms directly (NOT metric stream)
    ├── Periodic dashboard refresh (every 5 min)
    │     → GetMetricData (pull-based; dashboard queries on demand)
    └── Third-party monitoring (Datadog, NewRelic, Grafana)
          → Metric stream with OpenTelemetry output format
```

**Key implication:** metric streams replace GetMetricData polling for
continuous, high-volume metric export. They do NOT replace CloudWatch
alarms for real-time alerting (the buffering delay is too high).

## Expert heuristic: namespace filter controls cost

```text
Namespace filter:
  ├── Include filter (recommended for cost control)
  │     "IncludeFilter": [{"Namespace": "AWS/EC2"}, {"Namespace": "AWS/Lambda"}]
  │     → only metrics in these namespaces are streamed
  │     → cost = sum of unique metrics in included namespaces
  │
  ├── Exclude filter (use when you want everything EXCEPT noisy namespaces)
  │     "ExcludeFilter": [{"Namespace": "AWS/Logs"}]
  │     → all namespaces EXCEPT these are streamed
  │     → cost = sum of unique metrics in all non-excluded namespaces
  │
  ├── No filter (stream everything — most expensive)
  │     → every metric in the account is streamed
  │     → busy account: 100k+ metrics → high cost
  │
  └── Include + Exclude (both can be specified)
        → include takes precedence; exclude refines within included
```

**Key implication:** the namespace filter is the PRIMARY cost control
for metric streams. Always start with an include filter listing only
the namespaces you need. Streaming everything is the most expensive
option.

## Expert heuristic: Firehose buffering adds 1-5 minutes of latency

```text
Firehose buffering (S3 destination):
  ├── Buffer size: 1-128 MB (default: 5 MB)
  ├── Buffer interval: 60-900 seconds (default: 300 seconds)
  └── Data is flushed when EITHER threshold is reached

  Latency:
    Low-traffic metric stream: buffer interval dominates → ~5 min delay
    High-traffic metric stream: buffer size dominates → ~1 min delay

  This means:
    ├── Metric stream data in S3 is 1-5 minutes behind real-time
    ├── DO NOT use metric stream output for real-time alerting
    ├── DO use CloudWatch alarms directly for alerting
    └── DO use metric stream for historical analysis, long-term storage
```

**Key implication:** reduce buffer interval to 60 seconds for faster
delivery at the cost of more S3 PUT requests (smaller files). Increase
buffer size for fewer, larger files (more efficient for Athena
queries). The default 5 MB / 300 seconds is a reasonable middle
ground.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| S3 bucket exists | Firehose destination must exist | `aws s3api head-bucket --bucket <bucket>` |
| Firehose delivery stream exists | Metric stream targets a Firehose ARN | `aws firehose describe-delivery-stream --delivery-stream-name <name>` |
| Firehose S3 destination configured | Firehose must point to the S3 bucket | `aws firehose describe-delivery-stream --delivery-stream-name <name> --query 'DeliveryStreamDescription.Destinations[0].S3DestinationDescription'` |
| IAM role for CloudWatch → Firehose | CloudWatch needs firehose:PutRecord permission | `aws iam get-role --role-name <role-name>` |
| Trust policy includes cloudwatch.amazonaws.com | CloudWatch must be allowed to assume the role | `aws iam get-role --role-name <role-name> --query 'Role.AssumeRolePolicyDocument'` |
| KMS key on S3 bucket (recommended) | SSE-KMS for production data | `aws s3api get-bucket-encryption --bucket <bucket>` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Pipeline architecture

The metric stream pipeline is:

```text
CloudWatch metrics
  → Metric Stream (continuous export)
  → Kinesis Data Firehose (buffering + delivery)
  → S3 bucket (long-term storage)
  → Athena / QuickSight / third-party tools (querying)
```

CloudWatch pushes metrics to Firehose. Firehose buffers and writes to
S3. The metric stream itself is the configuration that binds
CloudWatch to a Firehose ARN with a namespace filter and output
format.

## Step 2 — Firehose ARN configuration

The metric stream targets a Firehose delivery stream ARN. The Firehose
must already exist and be configured with an S3 destination.

```bash
# Create the Firehose delivery stream (if not already existing)
aws firehose create-delivery-stream \
  --delivery-stream-name "cw-metrics-to-s3" \
  --delivery-stream-type DirectPut \
  --s3-destination-configuration '{
    "RoleARN": "arn:aws:iam::123456789012:role/FirehoseS3Role",
    "BucketARN": "arn:aws:s3:::my-cloudwatch-metrics",
    "Prefix": "cloudwatch-metrics/",
    "BufferingHints": {"SizeInMBs": 5, "IntervalInSeconds": 300},
    "CompressionFormat": "GZIP",
    "EncryptionConfiguration": {"KMSEncryptionConfig": {"AWSKMSKeyARN": "arn:aws:kms:us-east-1:123456789012:key/abc123"}}
  }' \
  --region us-east-1
```

**Create the metric stream referencing the Firehose:**

```bash
aws cloudwatch put-metric-stream \
  --name "ProductionMetricStream" \
  --firehose-arn "arn:aws:firehose:us-east-1:123456789012:deliverystream/cw-metrics-to-s3" \
  --role-arn "arn:aws:iam::123456789012:role/CWMetricStreamRole" \
  --output-format "json" \
  --include-filters '[{"Namespace":"AWS/EC2"},{"Namespace":"AWS/Lambda"}]' \
  --statistics "Average Sum SampleCount" \
  --region us-east-1
```

## Step 3 — Namespace filter (include/exclude)

The namespace filter is the PRIMARY cost control. Use it to stream
only the namespaces you need.

**Include filter (recommended):**

```bash
aws cloudwatch put-metric-stream \
  --name "ProductionMetricStream" \
  --firehose-arn "arn:aws:firehose:us-east-1:123456789012:deliverystream/cw-metrics-to-s3" \
  --role-arn "arn:aws:iam::123456789012:role/CWMetricStreamRole" \
  --output-format "json" \
  --include-filters '[{"Namespace":"AWS/EC2"},{"Namespace":"AWS/Lambda"},{"Namespace":"AWS/RDS"}]' \
  --region us-east-1
```

**Exclude filter (stream everything except):**

```bash
aws cloudwatch put-metric-stream \
  --name "ProductionMetricStream" \
  --firehose-arn "arn:aws:firehose:us-east-1:123456789012:deliverystream/cw-metrics-to-s3" \
  --role-arn "arn:aws:iam::123456789012:role/CWMetricStreamRole" \
  --output-format "json" \
  --exclude-filters '[{"Namespace":"AWS/Logs"}]' \
  --region us-east-1
```

**Critical:** omitting both filters streams ALL namespaces — the most
expensive option. Always start with an include filter.

## Step 4 — Statistics

The `--statistics` parameter controls which statistic values are
emitted per metric. Available statistics: `Average`, `Sum`,
`SampleCount`, `Min`, `Max`, and percentiles (`p99`, `p95`, `p50`,
etc.).

```bash
aws cloudwatch put-metric-stream \
  --name "ProductionMetricStream" \
  --firehose-arn "..." \
  --role-arn "..." \
  --output-format "json" \
  --statistics "Average Sum SampleCount Min Max" \
  --region us-east-1
```

**Critical:** omitting `--statistics` defaults to ALL statistics,
which multiplies the output volume per metric. Only request the
statistics you actually need.

**Stream statistics auto-aggregation:** CloudWatch automatically
aggregates high-resolution metrics (1-second, 5-second, 10-second) to
1-minute granularity before streaming. You do NOT need to configure
aggregation — it is handled by CloudWatch.

## Step 5 — Output format (JSON vs OpenTelemetry)

| Format | Description | Use case |
|---|---|---|
| `json` | CloudWatch JSON format (embedded JSON in Firehose records) | AWS-native tools, Athena queries, custom processing |
| `opentelemetry` | OpenTelemetry 1.1.0 format | Third-party tools (Datadog, NewRelic, Grafana, Splunk) |

**JSON output example:**

```json
{
  "metric_stream_name": "ProductionMetricStream",
  "namespace": "AWS/EC2",
  "metric_name": "CPUUtilization",
  "dimensions": {"InstanceId": "i-aaa111bb222"},
  "timestamp": 1716000000,
  "value": 42.5,
  "unit": "Percent"
}
```

**OpenTelemetry output:** metrics are encoded as OTLP gauge / sum
data points. Choose this when forwarding to OpenTelemetry-compatible
backends.

## Step 6 — IAM role permissions

The IAM role chain is:

```text
cloudwatch.amazonaws.com (assumes role)
  → role has firehose:PutRecord, firehose:PutRecordBatch on the Firehose ARN
  → Firehose role has s3:PutObject on the S3 bucket
  → Firehose role has kms:GenerateDataKey on the KMS key (if SSE-KMS)
```

**CloudWatch → Firehose role trust policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "cloudwatch.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

**CloudWatch → Firehose role permissions:**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["firehose:PutRecord", "firehose:PutRecordBatch"],
    "Resource": "arn:aws:firehose:us-east-1:123456789012:deliverystream/cw-metrics-to-s3"
  }]
}
```

**Critical:** the trust policy MUST include
`cloudwatch.amazonaws.com`. Without it, the metric stream enters
"running" status but delivers nothing — a silent failure.

## Step 7 — Cross-account metric streaming

For multi-account observability, use a metric stream in each account
delivering to a central S3 bucket (or central Firehose) in an
observability account.

```text
Account A (workload) → Metric Stream → Firehose → S3 (Account A)
Account B (workload) → Metric Stream → Firehose → S3 (Account B)
Account C (observability) ← Athena/QuickSight queries cross-account

OR (centralized):

Account A → Metric Stream → Firehose (Account C) → S3 (Account C)
Account B → Metric Stream → Firehose (Account C) → S3 (Account C)
Account C (observability) ← all metrics centralized
```

For centralized delivery, the Firehose in the observability account
must allow cross-account writes. The CloudWatch role in each workload
account needs `firehose:PutRecord` permission on the cross-account
Firehose ARN, and the Firehose resource policy (or the role) must
allow the workload account principal.

## Step 8 — Cost model (per-metric pricing)

Metric streams charge per unique metric per month.

```text
Cost = (number of unique metrics streamed) × (per-metric monthly rate)

Example (us-east-1 approximate):
  AWS/EC2 with 100 instances × 5 metrics each = 500 unique metrics
  AWS/Lambda with 50 functions × 10 metrics each = 500 unique metrics
  Total: 1000 unique metrics
  Cost: 1000 × $0.003/metric = $3.00/month

Compare to GetMetricData polling:
  1000 metrics × 4 queries/hour × 24 hours × 30 days = 2,880,000 API calls
  Cost: 2,880,000 × $0.01/1k = $28.80/month

  Metric stream is ~90% cheaper at this scale.
```

**Cost control levers:**
1. Use include filter to reduce unique metric count
2. Reduce statistics count (each statistic per metric adds to volume)
3. Use exclude filter to drop noisy namespaces (e.g., `AWS/Logs`)

## Step 9 — Firehose buffering latency (1-5 min)

Firehose buffers data before writing to S3. This adds delivery delay.

```bash
# Configure buffering (lower interval = faster delivery, more PUTs)
aws firehose update-destination \
  --delivery-stream-name "cw-metrics-to-s3" \
  --current-delivery-stream-version-id "1" \
  --destination-id "destinationId-000000000001" \
  --s3-destination-update '{
    "BufferingHints": {"SizeInMBs": 5, "IntervalInSeconds": 60},
    "CompressionFormat": "GZIP"
  }' \
  --region us-east-1
```

**Tradeoff:**
- Lower interval (60s): faster delivery, more S3 PUT requests, smaller
  files (less efficient for Athena)
- Higher interval (900s): slower delivery, fewer PUTs, larger files
  (more efficient for Athena)

For metric streams used for dashboards, use 60-120 seconds. For
long-term archival, use 300-900 seconds.

## Step 10 — CloudWatch API operations

| API | Purpose |
|---|---|
| `PutMetricStream` | Create a new metric stream |
| `GetMetricStream` | Retrieve a metric stream's configuration |
| `ListMetricStreams` | List all metric streams in the region |
| `DeleteMetricStream` | Delete a metric stream |
| `StartMetricStreams` | Resume a stopped stream |
| `StopMetricStreams` | Temporarily stop a stream (billing pauses) |

```bash
# Get stream configuration
aws cloudwatch get-metric-stream --name "ProductionMetricStream" --region us-east-1

# List all streams
aws cloudwatch list-metric-streams --region us-east-1

# Stop a stream (pause billing)
aws cloudwatch stop-metric-streams --names "ProductionMetricStream" --region us-east-1

# Delete a stream
aws cloudwatch delete-metric-stream --name "ProductionMetricStream" --region us-east-1
```

## Step 11 — Recent features

- **OpenTelemetry 1.1.0 output format (2023-2024):** metric streams
  now support OpenTelemetry output for direct integration with third-
  party observability platforms (Datadog, NewRelic, Grafana, Splunk).
- **Cross-account metric streaming (2023-2024):** metric streams can
  deliver to Firehose delivery streams in different accounts, enabling
  centralized observability without per-account S3 buckets.
- **Percentile statistics (2023-2024):** metric streams now support
  percentile statistics (p99, p95, p50) in addition to standard
  statistics.
- **Statistics filtering (2024-2025):** the `--statistics` parameter
  now allows selecting specific statistics, reducing output volume per
  metric.
- **Terraform provider (2024-2025):** the `aws_cloudwatch_metric_stream`
  Terraform resource now supports `include_filter`, `exclude_filter`,
  `statistics`, and `output_format`.

## NEVER do these things

1. **NEVER use a metric stream for real-time alerting (< 1 min).**
   Firehose buffering adds 1-5 minutes of delay. Use CloudWatch alarms
   directly for alerting.

2. **NEVER omit the namespace filter for cost-sensitive workloads.**
   Without a filter, ALL metrics in the account are streamed — the
   most expensive option. Always start with an include filter.

3. **NEVER create a metric stream without verifying the IAM role trust
   policy.** The trust policy MUST include `cloudwatch.amazonaws.com`.
   Without it, the stream shows "running" but delivers nothing — a
   silent failure.

4. **NEVER use GetMetricData polling for >1000 metrics when continuous
   export is needed.** Metric streams are cheaper at scale and avoid
   API throttling.

5. **NEVER omit the `--statistics` parameter when you only need
   specific stats.** Omitting it defaults to ALL statistics, which
   multiplies output volume per metric and increases cost.

6. **NEVER configure Firehose with a 900-second buffer when near-real-
   time delivery is needed.** Use 60-120 seconds for dashboards; 300+
   seconds for archival.

7. **NEVER use JSON output format for OpenTelemetry-compatible
   backends.** Use the `opentelemetry` output format for third-party
   tools. JSON is for AWS-native tools.

8. **NEVER assume metric stream data is immediately available in S3.**
   The first data appears after 1-5 minutes of Firehose buffering.

9. **NEVER create a Firehose without SSE-KMS for production metric
   data.** Use a customer-managed KMS key on both the S3 bucket and
   the Firehose encryption configuration.

10. **NEVER forget to stop or delete unused metric streams.** Metric
    streams bill per unique metric even if no one is consuming the
    data. Use `StopMetricStreams` to pause billing.

## Output format

```text
METRIC_STREAM: <stream-name> → <firehose-name> → s3://<bucket>/<prefix>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] S3 bucket: s3://<bucket>/<prefix> (SSE-KMS) | MISSING [✗]
  [✓|✗] Firehose delivery stream: <firehose-name> (S3 destination) | MISSING [✗]
  [✓|✗] IAM role: <role-name> (trust: cloudwatch.amazonaws.com, perms: firehose:PutRecord)
  [✓|✗] Namespace filter: IncludeFilter=[<namespaces>] | ExcludeFilter=[<namespaces>] | None (all)
  [✓|✗] Statistics: <list> | ALL (default)
  [✓|✗] Output format: json | opentelemetry
  [✓|✗] Firehose buffering: <size>MB / <interval>s (latency: ~<N> min)
  [✓|✗] Cost estimate: <N> unique metrics × $<rate> = $<monthly>/month
  [✓|✗] Cross-account: <none | source-account → dest-account>
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws cloudwatch get-metric-stream --name <stream-name> --region <region>
  aws cloudwatch list-metric-streams --region <region>
  aws firehose describe-delivery-stream --delivery-stream-name <firehose-name> --region <region>
  aws s3 ls s3://<bucket>/<prefix> --region <region> | head -5
```

### Worked example — JSON metric stream with include filter and SSE-KMS

```text
METRIC_STREAM: ProductionMetricStream → cw-metrics-to-s3 → s3://my-cloudwatch-metrics/cloudwatch-metrics/
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] S3 bucket: s3://my-cloudwatch-metrics/cloudwatch-metrics/ (SSE-KMS, key arn:aws:kms:us-east-1:123456789012:key/abc123)
  [✓] Firehose delivery stream: cw-metrics-to-s3 (S3 destination, GZIP, 5MB/300s buffer)
  [✓] IAM role: CWMetricStreamRole (trust: cloudwatch.amazonaws.com, perms: firehose:PutRecord/PutRecordBatch)
  [✓] Namespace filter: IncludeFilter=[AWS/EC2, AWS/Lambda, AWS/RDS]
  [✓] Statistics: Average Sum SampleCount Min Max
  [✓] Output format: json
  [✓] Firehose buffering: 5MB / 300s (latency: ~5 min)
  [✓] Cost estimate: ~1500 unique metrics × $0.003 = ~$4.50/month
  [✓] Cross-account: none
  [✓] Tags: Environment=production, Owner=cloudops
VERIFICATION_COMMANDS:
  aws cloudwatch get-metric-stream --name ProductionMetricStream --region us-east-1
  aws cloudwatch list-metric-streams --region us-east-1
  aws firehose describe-delivery-stream --delivery-stream-name cw-metrics-to-s3 --region us-east-1
  aws s3 ls s3://my-cloudwatch-metrics/cloudwatch-metrics/ --region us-east-1 | head -5
```

## Error handling

- **Stream shows "running" but no data in S3:** the IAM role trust
  policy does not include `cloudwatch.amazonaws.com`, or the role
  lacks `firehose:PutRecord` permission. Verify the trust policy and
  permissions. Check CloudTrail for `AccessDenied` from
  `cloudwatch.amazonaws.com`.
- **Data delayed by >5 minutes:** Firehose buffer interval is set too
  high (e.g., 900 seconds), or the metric stream is low-traffic (buffer
  size not reached, so interval dominates). Reduce buffer interval.
- **Stream cost higher than expected:** no namespace filter (streaming
  ALL metrics), or too many statistics requested. Add an include
  filter and reduce the statistics list.
- **Firehose not delivering to S3:** Firehose role lacks
  `s3:PutObject` on the bucket, or KMS key policy lacks
  `kms:GenerateDataKey` for the Firehose role. Check Firehose
  CloudWatch metrics (`DeliveryToS3.Success`).
- **GetMetricData throttling when migrating:** if migrating from
  GetMetricData polling, the old polling may still be running. Disable
  the old polling jobs after the metric stream is verified.

## Domain

AWS CloudOps / Amazon CloudWatch Metric Streams, Continuous Metric
Export, and Observability Data Pipeline Management.

## AWS documentation

- **CloudWatch Metric Streams** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CloudWatch_Metric_Streams.html
- **Create metric stream** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricStream.html
- **Firehose delivery** — https://docs.aws.amazon.com/firehose/latest/dev/basic-create.html
- **Namespace filters** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CloudWatch-Metric-Stream-Filter.html
- **Output formats** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CloudWatch-Metric-Stream-Formats.html
- **Metric stream pricing** — https://aws.amazon.com/cloudwatch/pricing/
- **Cross-account streaming** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CrossAccountMetricStreams.html
- **OpenTelemetry format** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Metric-Streams-OTel.html
