# Advanced Patterns (load on demand) — CloudWatch Metrics Troubleshooter

Expert edge cases, the list-metrics-first heuristic deep dive, and recent AWS features moved verbatim from SKILL.md. The symptom-category tables and root-cause catalog remain in SKILL.md.


---

## Mindset — three facts that make metrics troubleshooting different (moved from SKILL.md)

Three facts make CloudWatch metrics troubleshooting different from
generic service debugging:

- **`get-metric-statistics` returns empty for many reasons, only one
  of which is "metric doesn't exist."** The metric may exist with
  different dimensions, a different namespace, or only at a coarser
  period. `list-metrics` is the source of truth for what exists;
  `get-metric-statistics` returns what is queryable for a specific
  (Namespace, MetricName, Dimensions, Period, Statistics) tuple. An
  empty `get-metric-statistics` response does NOT mean the metric does
  not exist — it means the query did not match.

- **Statistics transform the underlying data points.** A metric
  collected at 1-minute resolution as `Sum` can be queried as `Sum`,
  `Average`, `Maximum`, `Minimum`, or `SampleCount` — but only if the
  underlying `PutMetricData` calls supplied `Value` (single) or
  `Values` + `Counts` (multi). Statistic mismatch is the most common
  "unexpected value" cause: an operator expects the average of `Sum`
  data and queries `Sum` against an aggregated period.

- **Custom metrics have three independent failure modes: emission
  failure, ingestion denial, and parsing failure.** The CloudWatch
  agent may not emit (config error), the IAM role may deny
  `cloudwatch:PutMetricData`, or the Embedded Metric Format (EMF) blob
  may be malformed and silently dropped. Each failure mode has a
  different diagnostic path — the symptom ("metric not arriving") is
  the same.

---

## Expert edge cases (moved from SKILL.md)

These patterns represent genuine, non-obvious CloudWatch metrics
failure modes that a senior operator would catch but a generalist
would miss.

### `list-metrics` pagination hides dimensions

`list-metrics` paginates. A `--namespace <ns> --metric-name <m>` query
may return dimensions that fit in the first page, but the operator's
specific dimension combination is on a later page. Always page through
with `--next-token` or filter further. Conversely, `list-metrics` may
return a dimension combination that has no data points because the
emitter stopped using that dimension — `list-metrics` reflects the
metric registry, not recent data.

### EMF silent-drop is invisible without raw log inspection

When an EMF blob is malformed, CloudWatch Logs ingests the log line
(the blob appears in `filter-log-events`) but does NOT extract a
metric. There is no error event, no CloudTrail entry, no metric in
`PutMetricData`-denied class. The only diagnostic is to read the
actual blob and validate the `_aws.CloudWatchMetrics` structure
manually. Operators often spend hours looking for an IAM denial that
does not exist.

### High-resolution metrics have a 1-second floor and quota limits

`StorageResolution: 1` emits a high-resolution metric queryable at
Period 1. But the `PutMetricData` API has a separate quota for
high-resolution data points per second. A workload bursting thousands
of high-resolution metrics per second will silently drop data points
without an error event. The diagnostic is the `ThrottledRequests`
metric in `AWS/CloudWatch` for the emitter's account.

### Cross-account observability requires both sides

Cross-account CloudWatch (the "monitoring account" / "source account"
pattern) requires configuration on BOTH accounts: the source account
must enable metric sharing, and the monitoring account must have a
link to the source. Operators often configure only one side and see
empty metrics in the monitoring account. The diagnostic is
`aws cloudwatch list-metric-streams` and the source account's
`PutMetricData`-sharing setting.

### `TreatMissingData` defaults to `missing`

If an alarm has no explicit `TreatMissingData` setting, it defaults to
`missing` — the alarm stays in INSUFFICIENT_DATA indefinitely for
sparse metrics. This is the most common cause of permanently
INSUFFICIENT_DATA alarms for legitimate "absence is good" metrics like
error counts. The fix is to set `TreatMissingData: notBreaching`
explicitly.

### Container Insights metrics have a 60-second aggregation delay

Container Insights aggregates per minute. Even after enabling, metrics
take 3-5 minutes to appear. Operators often re-enable repeatedly,
assuming the first enable failed. The diagnostic is patience plus
verifying `runningTasksCount` / pod count > 0 on the cluster.

### Metric math `ID` collisions produce silent nulls

In a metric math expression, each `Id` must be unique within the
dashboard / alarm. A duplicate `Id` causes one branch to silently
overwrite the other, producing a null in the math result. The
diagnostic is to read the alarm / dashboard definition and verify
uniqueness.

### CloudWatch agent `metrics` section is required even if logs work

A common confusion: the CloudWatch agent is running, logs are
arriving in CloudWatch Logs, but no metrics appear. The agent has two
independent sections in its config: `logs` (which produces log events)
and `metrics` (which produces custom metrics). Working logs do NOT
imply working metrics — the `metrics` section may be missing or
misconfigured. Always read both sections of `amazon-cloudwatch-agent.json`.

### Period alignment can shift values across the boundary

`get-metric-statistics` aligns Period buckets to wall-clock boundaries
(Period 300 aligns to 5-minute bucket edges). A metric emitted at
14:02:30 falls in the 14:00–14:05 bucket. An operator comparing the
metric to a chart with 14:00 / 14:05 / 14:10 ticks sees the value at
14:00, not 14:02. This is the bucket-edge alignment gotcha.

---

## Expert heuristic — "Run list-metrics before get-metric-statistics" (moved from SKILL.md)

The single most common diagnostic mistake is running
`get-metric-statistics`, getting an empty response, and concluding
"the metric is broken." An empty response means the query did not
match — the metric may exist with different dimensions, namespace, or
at a coarser period.

Always run `list-metrics` FIRST:

```bash
aws cloudwatch list-metrics --namespace <ns> --metric-name <m>
```

- If `list-metrics` returns the metric with the exact dimensions:
  the query-side parameters are correct — investigate Period,
  Statistic, time window, and `Unit`.
- If `list-metrics` returns the metric with DIFFERENT dimensions or
  namespace: the operator's query is wrong — align it.
- If `list-metrics` returns NOTHING for the namespace + metric name:
  the emitter is not emitting — investigate the emission path.

Quick reference for "where does my metric live":

| Symptom | Likely namespace | Likely dimensions |
|---|---|---|
| EC2 instance CPU | AWS/EC2 | InstanceId |
| ECS service CPU | AWS/ECS or ECS/ContainerInsights | ClusterName + ServiceName |
| EKS pod CPU | ContainerInsights | ClusterName + Namespace + PodName (via agent) |
| Lambda function errors | AWS/Lambda | FunctionName |
| DynamoDB throttling | AWS/DynamoDB | TableName |
| S3 bucket size | AWS/S3 | BucketName + StorageType |
| ALB 5xx | AWS/ApplicationELB | LoadBalancer + TargetGroup |
| API Gateway 4xx | AWS/ApiGateway | ApiName + Stage |
| Custom application | (user-defined) | (user-defined) |

When in doubt, run `list-metrics --metric-name <m>` WITHOUT
`--namespace` to discover every namespace that publishes the metric.

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Cross-account observability (2024 GA):** a monitoring account can
  query metrics, logs, and traces from source accounts. Requires
  configuration on BOTH sides. Troubleshoot with
  `aws cloudwatch list-metric-streams` and the source account's
  sharing setting.
- **CloudWatch Metric Streams (2024 enhancements):** stream metrics
  to Kinesis Data Firehose (and downstream to S3, Datadog, etc.).
  Troubleshoot via the metric stream's `LastFailureCode` and
  `LastFailureMessage`.
- **CloudWatch agent unified telemetry (2024-2025):** the agent now
  supports OpenTelemetry-format metrics in addition to StatsD. The
  agent config section determines which format is emitted; mixed
  configs can produce duplicate metrics.
- **Embedded Metric Format (EMF) for Lambda (2024 GA):** Lambda
  extensions can emit EMF blobs directly via the runtime API.
  Troubleshoot via the Lambda extension logs and the EMF blob
  structure.
- **Container Insights Enhanced (EKS, 2024-2025):** a newer
  observability mode that emits per-pod metrics without the classic
  agent. Troubleshoot via the Amazon CloudWatch Observability EKS
  add-on.
- **RUM custom events (2024-2025):** RUM supports richer custom
  events via `dispatch`. Troubleshoot via the app monitor's ingest
  role and the `PutRumAppEvents` CloudTrail events.
- **High-resolution metric quota (2025):** the per-account
  PutMetricData quota for high-resolution metrics was raised. Verify
  via Service Quotas `cloudwatch.PutMetricData` (high resolution).
