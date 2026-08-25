# Namespace Filters and Cost Model — Metric Stream Deployer

Deep reference on namespace filtering (include/exclude filter
semantics, multi-namespace filters, namespace wildcards), the metric
stream cost model (per-metric pricing, how unique metrics are counted,
cost optimization strategies), and the cost-benefit analysis vs
GetMetricData API polling. Loaded on demand by the skill — kept out
of the main SKILL.md body so the provisioning procedure stays
scannable.

## Namespace filter fundamentals

### Include filter — stream only specified namespaces

The include filter is the PRIMARY cost control. Use it to stream only
the namespaces you actually need.

```bash
aws cloudwatch put-metric-stream \
  --name "ProductionMetricStream" \
  --firehose-arn "arn:aws:firehose:us-east-1:123456789012:deliverystream/cw-metrics-to-s3" \
  --role-arn "arn:aws:iam::123456789012:role/CWMetricStreamRole" \
  --output-format "json" \
  --include-filters '[{"Namespace":"AWS/EC2"},{"Namespace":"AWS/Lambda"},{"Namespace":"AWS/RDS"}]' \
  --region us-east-1
```

Each entry in the `--include-filters` array specifies a namespace to
include. You can list multiple namespaces. Only metrics in those
namespaces are streamed.

**How unique metrics are counted per namespace:**

```text
AWS/EC2 namespace:
  100 EC2 instances
  5 standard metrics per instance (CPUUtilization, NetworkIn, NetworkOut, DiskReadOps, DiskWriteOps)
  → 100 × 5 = 500 unique metrics

AWS/Lambda namespace:
  50 Lambda functions
  10 metrics per function (Invocations, Errors, Throttles, Duration, ConcurrentExecutions, etc.)
  → 50 × 10 = 500 unique metrics

Total with include filter [AWS/EC2, AWS/Lambda]: 1000 unique metrics
```

A "unique metric" is defined as a unique combination of:
- Namespace
- MetricName
- All dimension key-value pairs

Two EC2 instances each reporting `CPUUtilization` count as TWO unique
metrics (because the `InstanceId` dimension differs).

### Exclude filter — stream all except specified namespaces

The exclude filter is useful when you want everything EXCEPT known
noisy namespaces.

```bash
aws cloudwatch put-metric-stream \
  --name "OpsAllExceptLogs" \
  --firehose-arn "..." \
  --role-arn "..." \
  --output-format "json" \
  --exclude-filters '[{"Namespace":"AWS/Logs"}]' \
  --region us-east-1
```

**Cost warning:** exclude filters stream ALL non-excluded namespaces.
In a busy account, this can mean tens or hundreds of thousands of
unique metrics. Only use exclude filters if you have a small, known
set of namespaces to drop and everything else is genuinely needed.

### Include + exclude together

You can specify both `--include-filters` and `--exclude-filters`. The
include filter runs first (selecting namespaces), then the exclude
filter removes specific namespaces from the included set. In practice,
using both is rarely needed — one or the other usually suffices.

### No filter — stream everything

Omitting both filters streams ALL metrics in the account. This is the
most expensive option. In a production account with many services,
this can mean 100,000+ unique metrics.

**The skill ALWAYS recommends starting with an include filter.** Only
use no filter if you have an explicit reason (e.g., you genuinely need
every metric for compliance archival).

## Cost model

### Per-metric pricing

Metric streams charge per unique metric per month. The pricing varies
by region but is approximately $0.003 per metric per month (us-east-1,
as of 2026 — always check the official pricing page for current
rates).

```text
Monthly cost = unique_metrics × per_metric_rate

Examples (us-east-1 approximate):
  1,000 metrics  × $0.003 = $3.00/month
  10,000 metrics × $0.003 = $30.00/month
  100,000 metrics × $0.003 = $300.00/month
```

**Additional costs:**
- Firehose: ~$0.029 per GB ingested (data volume from CloudWatch to
  Firehose)
- S3: storage cost for the metric data (~$0.023 per GB for Standard)
- KMS: $1.00 per key per month + $0.03 per 10,000 requests (if using
  customer-managed key)

**Total cost example (1000 metrics, 5 GB/month data volume):**
- Metric stream: $3.00
- Firehose: 5 GB × $0.029 = $0.15
- S3: 5 GB × $0.023 = $0.12
- KMS: $1.00 + negligible
- **Total: ~$4.27/month**

### How unique metrics are counted

A unique metric is a unique combination of:
1. Namespace
2. MetricName
3. All dimension key-value pairs

```text
Metric: AWS/EC2 / CPUUtilization / {InstanceId=i-aaa111}     → unique metric #1
Metric: AWS/EC2 / CPUUtilization / {InstanceId=i-bbb222}     → unique metric #2
Metric: AWS/EC2 / CPUUtilization / {InstanceId=i-aaa111, AutoScalingGroupName=asg-1} → unique metric #3
  (different dimension set = different metric)
```

**Implication:** adding dimensions increases the unique metric count.
For example, if you publish a custom metric with a per-request
dimension (e.g., `RequestId`), each request creates a new unique
metric — extremely expensive. Use high-cardinality dimensions ONLY
when necessary.

### Cost optimization strategies

1. **Use include filter to reduce unique metric count.** Only stream
   the namespaces you need. This is the #1 cost lever.

2. **Reduce statistics count.** Each statistic per metric adds to the
   output volume (and in JSON format, a separate record). If you only
   need `Average` and `Sum`, do not request `Min`, `Max`,
   `SampleCount`, and `p99`.

3. **Use exclude filter to drop noisy namespaces.** `AWS/Logs` and
   some container metrics namespaces can generate thousands of
   metrics. Exclude them if not needed.

4. **Consolidate custom metrics.** If you publish custom metrics with
   per-instance dimensions, consider aggregating at the publisher
   level (e.g., emit a single fleet-wide metric instead of per-
   instance).

5. **Stop streams when not needed.** Use `StopMetricStreams` to pause
   billing for streams that are only needed during business hours or
   specific investigation windows.

6. **Use S3 lifecycle rules.** Transition old metric data to
   Glacier/Deep Archive after 30-90 days to reduce S3 storage cost.

## Cost-benefit: metric streams vs GetMetricData polling

### GetMetricData cost model

GetMetricData charges per metric per data point retrieved:

```text
Cost = metric_data_points × per_data_point_rate

metric_data_points = number_of_metrics × number_of_queries × data_points per query

Example:
  1000 metrics, queried every 5 minutes for 30 days:
  1000 × (30 days × 24 hours × 12 queries/hour) = 1000 × 8640 = 8,640,000 data points
  Cost: 8,640,000 × $0.01/1,000 = $86.40/month
```

### Comparison table

| Metric count | Query frequency | GetMetricData cost | Metric stream cost | Winner |
|---|---|---|---|---|
| 100 | Every 5 min | ~$8.64/month | ~$0.30/month + Firehose | Metric stream (cheaper) |
| 1,000 | Every 5 min | ~$86.40/month | ~$3.00/month + Firehose | Metric stream (much cheaper) |
| 10,000 | Every 5 min | ~$864/month | ~$30/month + Firehose | Metric stream (30x cheaper) |
| 100 | Once per hour | ~$0.72/month | ~$0.30/month + Firehose | Tie (Firehose overhead) |
| 10 | Once per day | ~$0.003/month | ~$0.03/month + Firehose | GetMetricData (cheaper) |

**Rule of thumb:** for >1000 metrics with continuous export needs,
metric streams are almost always cheaper. For <100 metrics queried
infrequently, GetMetricData may be cheaper (no Firehose overhead).

### Other benefits of metric streams beyond cost

1. **No API throttling.** GetMetricData has a TPS limit (20-50 TPS
   depending on account). For large-scale metric retrieval, you will
   hit throttling. Metric streams have no such limit — they are push-
   based.

2. **No missed data points.** GetMetricData polling can miss data
   points if polling fails or is delayed. Metric streams capture every
   data point.

3. **Continuous export.** Metric streams provide a continuous feed to
   S3 for long-term storage, compliance archival, or historical
   analysis. GetMetricData is pull-based and requires a polling loop.

4. **Multi-consumer.** Once data is in S3, multiple tools can consume
   it (Athena, QuickSight, Spark, third-party tools). GetMetricData
   serves one consumer at a time.

### When to stick with GetMetricData

- **Real-time alerting.** Metric stream + Firehose adds 1-5 minutes
  of latency. For sub-minute alerting, use CloudWatch alarms directly
  (which read metrics in near-real-time).
- **Small metric count, infrequent queries.** <100 metrics queried a
  few times per day. The Firehose overhead makes metric streams more
  expensive.
- **On-demand ad-hoc queries.** If you need to query arbitrary metrics
  on-demand (e.g., during incident investigation), GetMetricData is
  simpler than searching S3.

## Common cost pitfalls

### Pitfall 1: no namespace filter in a busy account

A user creates a metric stream with no filter in a production account
running dozens of AWS services. The stream captures hundreds of
thousands of unique metrics, generating a bill of $300+ per month.

**Fix:** always use an include filter. Start with 2-3 critical
namespaces and expand only if needed.

### Pitfall 2: high-cardinality custom metrics

A user publishes custom metrics with per-request dimensions (e.g.,
`RequestId`, `TransactionId`). Each request creates a new unique
metric. The metric stream bill explodes.

**Fix:** aggregate custom metrics at the publisher level. Use
low-cardinality dimensions (e.g., `ServiceName`, `Environment`) rather
than per-request dimensions. Use CloudWatch Logs Insights for per-
request analysis instead.

### Pitfall 3: all statistics when only one is needed

A user creates a metric stream without specifying `--statistics`,
defaulting to ALL statistics. Each metric generates 5-7 records per
data point (one per statistic). The Firehose data volume and S3
storage cost multiply by 5-7x.

**Fix:** specify only the statistics you need. If you only need
`Average`, request only `Average`.

### Pitfall 4: forgetting to stop or delete unused streams

A user creates a metric stream for a temporary investigation, then
forgets to delete it. The stream continues to bill per metric per
month even though no one is consuming the data.

**Fix:** set up a billing alarm on CloudWatch metric stream costs.
Use `StopMetricStreams` to pause streams not in active use. Tag
streams with `Temporary=true` and audit them regularly.

## Step 3 — Namespace filter CLI (include / exclude) (moved from SKILL.md)

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

## Step 4 — Statistics selection CLI (moved from SKILL.md)

```bash
aws cloudwatch put-metric-stream \
  --name "ProductionMetricStream" \
  --firehose-arn "..." \
  --role-arn "..." \
  --output-format "json" \
  --statistics "Average Sum SampleCount Min Max" \
  --region us-east-1
```
