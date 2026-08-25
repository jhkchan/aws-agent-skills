# Firehose Configuration and Output Formats — Metric Stream Deployer

Deep reference on Kinesis Data Firehose delivery stream configuration
for metric streams (S3 destination, buffering hints, compression,
KMS encryption), the JSON and OpenTelemetry output formats (record
schemas, field mappings, consumer compatibility), and Firehose
lifecycle operations (create, update destination, monitoring). Loaded
on demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Firehose delivery stream fundamentals

### Why Firehose is the transport

CloudWatch metric streams push to a Kinesis Data Firehose delivery
stream. Firehose buffers and delivers to S3 (or other destinations
like HTTP endpoints, Redshift, Elasticsearch, etc., but S3 is the
standard for metric streams).

```text
CloudWatch metrics (push every 1 min)
  → Firehose (buffer: 1-128 MB / 60-900 s)
  → S3 (GZIP/Snappy/ZIP/HADOOP-SNAPPY compression)
  → Athena / third-party tools
```

Firehose is required because CloudWatch metric streams do NOT write
directly to S3 — they write to Firehose, which handles buffering,
compression, and delivery.

### Creating the Firehose delivery stream

```bash
aws firehose create-delivery-stream \
  --delivery-stream-name "cw-metrics-to-s3" \
  --delivery-stream-type DirectPut \
  --s3-destination-configuration '{
    "RoleARN": "arn:aws:iam::123456789012:role/FirehoseS3Role",
    "BucketARN": "arn:aws:s3:::my-cloudwatch-metrics",
    "Prefix": "cloudwatch-metrics/!{timestamp:yyyy/MM/dd}/",
    "ErrorOutputPrefix": "cloudwatch-metrics-errors/!{firehose:error-output-type}/!{timestamp:yyyy/MM/dd}/",
    "BufferingHints": {"SizeInMBs": 5, "IntervalInSeconds": 300},
    "CompressionFormat": "GZIP",
    "EncryptionConfiguration": {
      "KMSEncryptionConfig": {
        "AWSKMSKeyARN": "arn:aws:kms:us-east-1:123456789012:key/abc123"
      }
    }
  }' \
  --region us-east-1
```

**Critical fields:**

| Field | Purpose | Default |
|---|---|---|
| `DeliveryStreamType` | Must be `DirectPut` for metric streams | n/a |
| `RoleARN` | Firehose's own IAM role (NOT the metric stream role) | n/a |
| `BucketARN` | S3 destination bucket | n/a |
| `Prefix` | S3 key prefix (supports timestamp partitioning) | n/a |
| `BufferingHints.SizeInMBs` | Buffer size before flush (1-128 MB) | 5 MB |
| `BufferingHints.IntervalInSeconds` | Max buffer time before flush (60-900 s) | 300 s |
| `CompressionFormat` | GZIP (recommended), Snappy, ZIP, HADOOP-SNAPPY, UNCOMPRESSED | GZIP |
| `EncryptionConfiguration` | SSE-KMS key for Firehose-level encryption | none |

### Buffering hints — the latency knob

Firehose flushes data to S3 when EITHER the buffer size OR the buffer
interval is reached, whichever comes first.

```text
Low-traffic metric stream:
  Buffer size: 5 MB
  Interval: 300 s (5 min)
  → metric data arrives at ~1 MB / min for a small namespace
  → buffer size not reached after 5 min
  → interval triggers flush every 5 minutes
  → S3 latency: ~5 minutes

High-traffic metric stream:
  Buffer size: 5 MB
  Interval: 300 s (5 min)
  → metric data arrives at ~10 MB / min for a large namespace
  → buffer size reached in ~30 seconds
  → size triggers flush every ~30 seconds
  → S3 latency: ~30 seconds (faster than interval suggests)
```

**Tuning for different use cases:**

| Use case | Size (MB) | Interval (s) | Effect |
|---|---|---|---|
| Near-real-time dashboards | 1 | 60 | Fastest delivery; many small S3 objects |
| Operational monitoring | 5 | 120 | Balanced |
| Long-term archival / Athena | 64 | 900 | Fewer, larger files; efficient for queries |
| Default (leave as-is) | 5 | 300 | Reasonable middle ground |

**For Athena queries:** larger files are more efficient because Athena
charges per S3 PUT and per byte scanned. Use 64 MB / 900 s for Athena
workloads. For dashboards, use 1-5 MB / 60-120 s.

### Partitioning for Athena

Use Hive-style partitioning in the S3 prefix for efficient Athena
queries:

```
"Prefix": "cloudwatch-metrics/!{timestamp:yyyy/MM/dd}/"
```

This creates partitions like:
```
s3://my-cloudwatch-metrics/cloudwatch-metrics/2026/08/11/
```

In Athena, run `MSCK REPAIR TABLE` to load new partitions, or use
Athena partition projection for automatic partition discovery.

### Firehose IAM role

The Firehose delivery stream has its OWN IAM role (separate from the
metric stream's role). This role allows Firehose to write to S3 and
use the KMS key.

**Firehose role trust policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "firehose.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

**Firehose role permissions:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:AbortMultipartUpload", "s3:GetBucketLocation", "s3:GetObject", "s3:ListBucket", "s3:ListBucketMultipartUploads", "s3:PutObject"],
      "Resource": [
        "arn:aws:s3:::my-cloudwatch-metrics",
        "arn:aws:s3:::my-cloudwatch-metrics/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["kms:GenerateDataKey", "kms:Decrypt"],
      "Resource": "arn:aws:kms:us-east-1:123456789012:key/abc123",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "s3.us-east-1.amazonaws.com"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": ["logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/kinesisfirehose/*:log-stream:*"
    }
  ]
}
```

**Two distinct IAM roles — do not confuse them:**

1. **Metric stream role** (CWMetricStreamRole): assumed by
   `cloudwatch.amazonaws.com`, has `firehose:PutRecord` on the
   delivery stream.
2. **Firehose role** (FirehoseS3Role): assumed by
   `firehose.amazonaws.com`, has `s3:PutObject` on the bucket and
   `kms:GenerateDataKey` on the KMS key.

Both are needed. Missing either causes silent failure.

## Output formats

### JSON output format

The JSON output format emits each metric data point as an embedded JSON
record inside a Firehose record. The schema is:

```json
{
  "metric_stream_name": "ProductionMetricStream",
  "namespace": "AWS/EC2",
  "metric_name": "CPUUtilization",
  "dimensions": {
    "InstanceId": "i-aaa111bb222"
  },
  "timestamp": 1716000000,
  "value": 42.5,
  "unit": "Percent",
  "account_id": "123456789012"
}
```

Records are newline-delimited (one JSON object per line), so the
output file is JSONL (JSON Lines), NOT a JSON array. This matters for
downstream parsing:

```text
{"metric_stream_name":"ProductionMetricStream","namespace":"AWS/EC2",...}
{"metric_stream_name":"ProductionMetricStream","namespace":"AWS/EC2",...}
{"metric_stream_name":"ProductionMetricStream","namespace":"AWS/Lambda",...}
```

**For Athena:** create a table with `SerDe` set to
`org.openx.data.jsonserde.JsonSerDe` and `INPUTFORMAT` as
`org.apache.hadoop.mapred.TextInputFormat`.

**For custom processing (Lambda/Spark):** read the file line by line
and parse each line as a JSON object.

### OpenTelemetry output format

The OpenTelemetry output format encodes metrics as OTLP (OpenTelemetry
Protocol) gauge and sum data points. This format is compatible with
OpenTelemetry collectors and third-party observability platforms.

The OTLP format groups metrics into ResourceMetrics, ScopeMetrics,
and Metric records. Each Firehose record contains one or more OTLP
ExportMetricsServiceRequest protobuf messages (base64-encoded) or JSON
representations depending on the Firehose configuration.

**When to use OpenTelemetry format:**
- Forwarding to Datadog, NewRelic, Grafana, Splunk, or any
  OpenTelemetry-compatible backend
- Using an OpenTelemetry collector in the pipeline
- Standardizing on OpenTelemetry as the org-wide observability format

**When to use JSON format:**
- AWS-native tools (Athena, QuickSight)
- Custom processing with standard JSON tooling
- Simpler debugging (human-readable)

### Format-specific statistics

In JSON format, each statistic value is a separate record. For
example, if you request `Average`, `Sum`, and `SampleCount` for a
metric, you get three records per data point (one per statistic). The
`value` field contains the statistic value.

In OpenTelemetry format, statistics map to data point types:
- `Sum` → Sum data point (monotonic or non-monotonic)
- `Average`, `Min`, `Max`, `SampleCount` → Gauge data points
- Percentiles → gauge data points with explicit percentile annotation

## Firehose monitoring

| CloudWatch metric | Namespace | What it tells you |
|---|---|---|
| `DeliveryToS3.Success` | AWS/Firehose | Records successfully delivered to S3 |
| `DeliveryToS3.DataFreshness` | AWS/Firehose | Age of oldest record in buffer (seconds) |
| `DataReadFromKinesisStream.Bytes` | AWS/Firehose | Bytes read (for Kinesis-as-source, not metric streams) |
| `PutRecord.Bytes` | AWS/Firehose | Bytes received from CloudWatch |
| `PutRecord.Requests` | AWS/Firehose | Put requests from CloudWatch |

**Alarm on `DeliveryToS3.DataFreshness`:** if data freshness exceeds
your expected latency (e.g., 600 seconds for a 300-second buffer),
data is stuck in Firehose.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "firehose-metric-stream-stale" \
  --metric-name "DeliveryToS3.DataFreshness" \
  --namespace "AWS/Firehose" \
  --statistic "Maximum" \
  --period 300 \
  --threshold 600 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions "Name=DeliveryStreamName,Value=cw-metrics-to-s3" \
  --evaluation-periods 1 \
  --alarm-actions "<sns-topic-arn>" \
  --region us-east-1
```

## Terraform example

```hcl
resource "aws_kinesis_firehose_delivery_stream" "metric_stream" {
  name        = "cw-metrics-to-s3"
  destination = "s3"

  s3_configuration {
    role_arn   = aws_iam_role.firehose.arn
    bucket_arn = aws_s3_bucket.metrics.arn

    prefix              = "cloudwatch-metrics/!{timestamp:yyyy/MM/dd}/"
    error_output_prefix = "cloudwatch-metrics-errors/!{firehose:error-output-type}/!{timestamp:yyyy/MM/dd}/"

    buffering_size = 5
    buffering_interval = 300

    compression_format = "GZIP"

    encryption_configuration {
      kms_key_arn = aws_kms_key.metrics.arn
    }
  }
}

resource "aws_cloudwatch_metric_stream" "main" {
  name          = "ProductionMetricStream"
  role_arn      = aws_iam_role.metric_stream.arn
  delivery_stream_arn = aws_kinesis_firehose_delivery_stream.metric_stream.arn
  output_format = "json"

  include_filter {
    namespace = "AWS/EC2"
  }

  include_filter {
    namespace = "AWS/Lambda"
  }

  statistics = ["Average", "Sum", "SampleCount"]

  tags = {
    Environment = "production"
  }
}
```

## Step 2 — Firehose ARN configuration CLI (create Firehose + put-metric-stream) (moved from SKILL.md)

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

## Step 5 — Output format examples (JSON record, OpenTelemetry) (moved from SKILL.md)

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

## Step 9 — Firehose buffering update CLI (update-destination) (moved from SKILL.md)

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
