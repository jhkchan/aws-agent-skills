# CloudWatch Logs Pricing and Retention Reference

Supplementary reference for the CloudWatch Logs Cost Optimizer skill.
Loaded on-demand when detailed pricing math, retention tier selection,
Firehose cost comparison, metric filter syntax, or vended log
destination comparison is needed.

## CloudWatch Logs pricing (us-east-1, 2026, USD)

### Ingestion pricing

| Component | Rate | Notes |
|---|---|---|
| Log ingestion (data volume) | $0.50/GB | Charged per GB ingested, not per event |
| PutLogEvents (API requests) | $0.40/million requests | Charged per API call regardless of event count |

### Storage pricing

| Component | Rate | Notes |
|---|---|---|
| Log storage | $0.03/GB-month | Charged for stored data at current retention |

### Logs Insights pricing

| Component | Rate | Notes |
|---|---|---|
| Data scanned | $0.005/GB | Charged per GB scanned, NOT per GB returned |

### Other pricing components

| Component | Rate | Notes |
|---|---|---|
| Metric filters | $0.00 (free) | Compute at ingestion; no scan cost |
| Subscription filters | $0.00 (free filter) | Destination ingestion billed separately |
| Data protection policies | $0.00 (free) | Masking at ingestion; no charge |
| Embedded Metric Format (EMF) | $0.00 (free extraction) | Log event still incurs ingestion + storage |

### Free tier

- No free tier for CloudWatch Logs ingestion or storage in standard
  accounts. Some new-account promotions include limited free ingestion.

### Duration billing precision

CloudWatch Logs charges ingestion by the byte (accumulated to GB).
PutLogEvents request charges are per-call. There is no sub-call rounding
— each API invocation counts as one request.

## Retention tier matrix

| RetentionInDays | Setting name | Typical use case | Storage cost trajectory |
|---|---|---|---|
| 0 (null) | Never expire | Unintended default | Grows indefinitely |
| 1 | 1 day | Ephemeral debug logs | Capped at ~1 day of ingest |
| 3 | 3 days | Short debugging window | Capped at ~3 days |
| 5 | 5 days | Workweek debugging | Capped at ~5 days |
| 7 | 1 week | Standard operational | Capped at ~7 days |
| 14 | 2 weeks | Extended debugging | Capped at ~14 days |
| 30 | 1 month | Monthly review cycle | Capped at ~30 days |
| 60 | 2 months | Extended investigation | Capped at ~60 days |
| 90 | 3 months | Quarterly compliance | Capped at ~90 days |
| 120 | 4 months | Mid-term retention | Capped at ~120 days |
| 150 | 5 months | Mid-term retention | Capped at ~150 days |
| 180 | 6 months | Semi-annual compliance | Capped at ~180 days |
| 365 | 1 year | Annual compliance | Capped at ~365 days |
| 400 | 13 months | Extended compliance | Capped at ~400 days |
| 545 | 18 months | Compliance + buffer | Capped at ~545 days |
| 731 | 2 years | SOC2 / financial | Capped at ~731 days |
| 1097 | 3 years | HIPAA / long compliance | Capped at ~1097 days |
| 1827 | 5 years | Extended regulatory | Capped at ~1827 days |
| 2192 | 6 years | Tax / legal archive | Capped at ~2192 days |
| 2557 | 7 years | SOX / long regulatory | Capped at ~2557 days |
| 2922 | 8 years | Extended regulatory | Capped at ~2922 days |
| 3288 | 9 years | Extended regulatory | Capped at ~3288 days |
| 3653 | 10 years | Maximum CW Logs retention | Capped at ~10 years |

**Key rule:** retention > 90 days in CloudWatch Logs is almost always
cheaper in S3 via Firehose. Retention > 365 days should ALWAYS be in S3
with Glacier lifecycle.

## Firehose cost comparison

### Firehose pricing (us-east-1, 2026)

| Component | Rate | Notes |
|---|---|---|
| Data ingested | $0.029/GB | One-time delivery fee per GB |
| Format conversion (if enabled) | Included | No extra charge for JSON/Parquet |
| S3 destination storage | $0.023/GB-month (Standard) | Standard S3 pricing |

### Crossover analysis: CloudWatch Logs vs Firehose → S3

| Retention needed | CW Logs cost (per GB ingested) | Firehose+S3 cost (per GB ingested) | Winner |
|---|---|---|---|
| 7 days | $0.50 + $0.007 = $0.507 | $0.029 + $0.005 = $0.034 | Firehose, but CW Logs needed for real-time queries |
| 30 days | $0.50 + $0.03 = $0.53 | $0.029 + $0.023 = $0.052 | Firehose, but CW Logs needed for operational queries |
| 90 days | $0.50 + $0.09 = $0.59 | $0.029 + $0.069 = $0.098 | Firehose |
| 180 days | $0.50 + $0.18 = $0.68 | $0.029 + $0.035 (GIR) = $0.064 | Firehose (5x cheaper) |
| 365 days | $0.50 + $0.365 = $0.865 | $0.029 + $0.012 (GIR) = $0.041 | Firehose (20x cheaper) |
| 730 days (2yr) | $0.50 + $0.73 = $1.23 | $0.029 + $0.024 (GIR+Glacier) = $0.053 | Firehose (23x cheaper) |
| 1095 days (3yr) | $0.50 + $1.095 = $1.595 | $0.029 + $0.033 (Deep Archive) = $0.062 | Firehose (25x cheaper) |

### S3 storage class pricing for log archives

| Storage class | $/GB-month | Retrieval cost | Use case |
|---|---|---|---|
| Standard | $0.023 | $0.0007/GB (free first GB) | First 30-90 days, frequent queries |
| Standard-IA | $0.0125 | $0.01/GB | Infrequent access (monthly queries) |
| Glacier Instant Retrieval | $0.012 | $0.03/GB | Quarterly queries, fast retrieval |
| Glacier Flexible Retrieval | $0.0036 | $0.03/GB + time | Annual queries, 1-5 min retrieval |
| Glacier Deep Archive | $0.00099 | $0.02/GB + 12h retrieval | Compliance only, never queried |
| Intelligent-Tiering | $0.023 (auto-tier) | Varies | Unknown access patterns |

### Recommended S3 lifecycle policy for log archives

```
Transition rules:
  Day 0-90:     S3 Standard ($0.023/GB-month)
  Day 90-365:   Glacier Instant Retrieval ($0.012/GB-month)
  Day 365+:     Glacier Deep Archive ($0.00099/GB-month)

Expiration: Per compliance requirement (e.g., 2557 days for SOX 7-year)
```

## Metric filter syntax reference

Metric filters use a pattern language distinct from Logs Insights CWL.

### Pattern types

| Pattern | Syntax | Example | Matches |
|---|---|---|---|
| Literal string | `"text"` | `"ERROR"` | Log events containing ERROR |
| Word boundary | `ERROR` (no quotes) | `timeout` | Events with timeout as a word |
| Wildcard | `"ERR*"` | `"ERR*"` | Events starting with ERR |
| JSON extraction | `{$.field=value}` | `{$.level="error"}` | JSON logs with level=error |
| Space-delimited | `[w1, w2, ...]` | `[timestamp, level, msg]` | Tokenized log format |
| Negation | `"ERROR" "timeout"` | `"ERROR" "timeout"` | Both terms present |

### Metric transformation

```json
{
  "metricName": "ErrorCount",
  "metricNamespace": "AppMetrics",
  "metricValue": "1",
  "defaultValue": "0"
}
```

For value extraction (e.g., response time from JSON):

```json
{
  "metricName": "ResponseTime",
  "metricNamespace": "AppMetrics",
  "metricValue": "$.duration",
  "defaultValue": "0",
  "unit": "Milliseconds"
}
```

### Limitations vs Logs Insights

| Feature | Metric filters | Logs Insights |
|---|---|---|
| Real-time computation | YES (at ingestion) | NO (on-demand scan) |
| Cost per query | $0.00 | $0.005/GB scanned |
| Aggregation functions | count, sum (value extraction) | count, sum, avg, min, max, pct, stdev |
| Group by dimension | Limited (one dimension via dimensions) | Full group-by support |
| Regex | Limited | Full regex support |
| Time range | Continuous (real-time metrics) | Arbitrary time window |
| Pattern complexity | Simple patterns only | Complex multi-line queries |

## Vended log destination comparison

| Log source | CW Logs cost | S3 direct cost | S3 + Athena query cost |
|---|---|---|---|
| VPC Flow Logs (50 GB/day) | $750/mo ingest + $45/mo storage | $0.023/GB-month S3 + Firehose $43/mo | $2.50/query (100 GB scan) |
| Route53 Resolver (100 GB/day) | $1,500/mo ingest + $90/mo storage | $69/mo S3 + $87/mo Firehose | $5.00/query (200 GB scan) |
| WAF logs (20 GB/day) | $300/mo ingest + $18/mo storage | $14/mo S3 + $17/mo Firehose | $1.00/query (40 GB scan) |

For vended logs above ~10 GB/day, S3 delivery is almost always cheaper.
For logs queried daily via Insights, keep in CW Logs for query speed.

## PutLogEvents batching math

```
events_per_hour = <total events from all sources in the hour>
requests_per_hour = ceil(events_per_hour / batch_count)
monthly_requests = requests_per_hour × 730
monthly_cost = monthly_requests / 1,000,000 × $0.40

Example (100 hosts, 12M events/hour total):
  batch_count = 1000:  12,000 requests/hr → 8,760,000/mo → $3.50/mo (per 1000 events/host/hr)
  batch_count = 10000: 1,200 requests/hr  → 876,000/mo   → $0.35/mo
  Saving: $3.15/mo per host × 100 hosts = $315/mo fleet-wide
```

Note: the fleet-level request count depends on per-host event volume and
agent sync timing. Use CloudWatch `PutLogEvents` API metric or Cost
Explorer `Usages` for actual request counts.

## Regional pricing multipliers

Approximate multiplier vs us-east-1 for CloudWatch Logs.

| Region | Multiplier | Notes |
|---|---|---|
| us-east-1, us-east-2, us-west-2 | 1.00x | Baseline |
| us-west-1 | 1.05x | Slight premium |
| eu-west-1, eu-west-2, eu-central-1 | 1.10-1.15x | EU premium |
| ap-southeast-1, ap-southeast-2 | 1.12-1.18x | APAC premium |
| ap-northeast-1 (Tokyo) | 1.10-1.15x | |
| ap-south-1 (Mumbai) | 1.15-1.25x | |
| sa-east-1 (São Paulo) | 1.35-1.50x | Highest premium |
| af-south-1 (Cape Town) | 1.30-1.45x | |

Always re-check via the AWS Pricing API for production estimates.

## Extended NEVER list (supplementary anti-patterns)

- NEVER reduce CloudWatch Logs retention below the compliance minimum
  without written confirmation from the compliance team.

- NEVER assume `RetentionInDays: 0` means "0 days." It means NEVER
  expire. This is the most dangerous billing misunderstanding.

- NEVER recommend converting a Logs Insights query to a metric filter
  without verifying the query's aggregation is expressible in filter
  syntax. Avg, percentile, and stdev are NOT supported as metric filter
  transforms.

- NEVER recommend Firehose → S3 without including the Firehose + S3
  storage cost in the projected total. The saving is real but must be
  stated with full cost transparency.

- NEVER recommend VPC Flow Logs to S3 without warning the operator that
  real-time Logs Insights queries on those logs will no longer be
  available. Athena has 1-30 second query latency, not sub-second.

- NEVER recommend increasing agent `batch_count` to maximum (10000)
  without confirming the application can tolerate up to 60 seconds of
  in-flight log data loss on agent crash.

- NEVER forget that subscription filters COPY log events. Each
  subscription filter destination pays its own ingestion. Cross-account
  aggregation via CW Logs → CW Logs doubles the ingestion charge.

- NEVER assume CloudWatch Logs data protection policies reduce ingestion
  cost. They reduce stored bytes (masked fields are shorter) but the
  full event is received before masking.

- NEVER recommend S3 Glacier Deep Archive for logs that may need to be
  queried within 12 hours. Deep Archive retrieval takes 12-48 hours.

- NEVER batch-update more than 10 log groups in a single output block.
