# Dimension, Period, and Statistic Quick Reference

A focused quick-reference for the three most common alarm
misconfiguration surfaces. Loaded when the diagnostic needs to
cross-check dimension case, period alignment, or statistic selection
without opening the full configuration reference.

## Dimension case-sensitivity — worked examples

CloudWatch does no normalisation on dimension values. Each of these is
a DIFFERENT metric:

| Alarm dimension value | Emitted dimension value | Match? |
|---|---|---|
| `fn-orders-api` | `fn-orders-api` | Yes (exact) |
| `Fn-Orders-API` | `fn-orders-api` | No (case) |
| `fn_orders_api` | `fn-orders-api` | No (underscore vs hyphen) |
| `fn-orders-api ` (trailing space) | `fn-orders-api` | No (whitespace) |
| `FN-ORDERS-API` | `fn-orders-api` | No (case) |

### Common AWS service dimension quirks

| Service / Namespace | Dimension name | Case rule |
|---|---|---|
| AWS/Lambda | `FunctionName` | Matches the function name exactly (case-sensitive) |
| AWS/EC2 | `InstanceId` | Matches `i-0abc123def456` exactly |
| AWS/DynamoDB | `TableName` | Matches the table name exactly |
| AWS/S3 | `BucketName` | Matches the bucket name exactly |
| AWS/RDS | `DBInstanceIdentifier` | Matches the DB instance identifier |
| CWAgent | `host` | Matches the `host` tag from the agent config |

The dimension NAME (Key) is also case-sensitive. `FunctionName` and
`functionname` are different dimension names.

## Period alignment — when does Period break the alarm?

| Metric native resolution | Alarm Period | Result |
|---|---|---|
| 60s (standard) | 1 | INSUFFICIENT_DATA — no sub-60s points |
| 60s (standard) | 10 | INSUFFICIENT_DATA — not a multiple of 60 |
| 60s (standard) | 60 | Works — 1:1 mapping |
| 60s (standard) | 300 | Works — aggregates 5 points |
| 60s (standard) | 3600 | Works — aggregates 60 points |
| 1s (high-resolution) | 1 | Works — 1:1 mapping |
| 1s (high-resolution) | 10 | Works — aggregates 10 points |
| 1s (high-resolution) | 60 | Works — aggregates 60 points (smooths spikes) |
| 1s (high-resolution) | 300 | Works — aggregates 300 points |

Rule: the alarm Period must be >= the metric's native resolution AND
a multiple of it. The only failure modes are Period < native
resolution or Period not a multiple.

## Statistic selection — what does each aggregation show?

Given the same raw metric points (e.g., 5 request-latency samples in
a period: 50ms, 80ms, 120ms, 500ms, 200ms):

| Statistic | Value | What it emphasises |
|---|---|---|
| `Average` | 190ms | The "typical" experience; smooths outliers |
| `Maximum` | 500ms | The worst single request; surfaces spikes |
| `Minimum` | 50ms | The best single request; rarely useful for alerting |
| `Sum` | 950ms | Total latency; useful for cost/throughput, not alerting |
| `SampleCount` | 5 | Number of requests; throughput |
| `p50` (median) | 120ms | The middle value; typical experience |
| `p95` | ~440ms | Tail latency; 5% of requests exceed this |
| `p99` | ~498ms | Extreme tail; 1% of requests exceed this |
| `TM99` | ~137ms | Trimmed mean (drops top/bottom 0.5%); robust p99 alternative |

### When to use which statistic for alerting

| Operator intent | Correct statistic |
|---|---|
| "Alert when ANY single request is slow" | `Maximum` or `p99` via `--extended-statistic` |
| "Alert when the typical request is slow" | `Average` or `p50` |
| "Alert when throughput drops" | `SampleCount` with a `LessThanThreshold` |
| "Alert when total error count spikes" | `Sum` on the Errors metric |
| "Alert on sustained latency degradation" | `Average` over a longer `EvaluationPeriods` window |

A frequent misconfiguration: alarm on `Average` for latency when the
operator's intent is "alert when any single request is slow." Average
smooths single-request spikes; `Maximum` or `p99` is the right choice.

## put-metric-alarm quick template

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name <name> \
  --namespace <ns> \
  --metric-name <m> \
  --dimensions Name=<d1>,Value=<v1> Name=<d2>,Value=<v2> \
  --period <p> \
  --statistic <Sum|Average|Maximum|Minimum|SampleCount> \
  --extended-statistic <p99|TM99|...> \  # mutually exclusive with --statistic
  --threshold <t> \
  --comparison-operator <op> \
  --evaluation-periods <n> \
  --datapoints-to-alarm <m> \             # must be <= evaluation-periods
  --treat-missing-data <missing|breaching|notBreaching|ignore> \
  --alarm-actions <action-arn-1> <action-arn-2> \
  --ok-actions <action-arn> \
  --insufficient-data-actions <action-arn> \
  --profile <p>
```

Always emit CONFIRM before executing; include the diff (old vs new
value) in the prompt. Verify dimensions against `list-metrics` output
character-by-character before applying.
