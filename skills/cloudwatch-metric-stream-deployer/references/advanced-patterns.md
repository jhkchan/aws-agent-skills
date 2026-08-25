# Advanced Patterns (load on demand) — CloudWatch Metric Stream Deployer

Provisioning-time misconceptions and recent feature changes moved verbatim from SKILL.md. The decision trees (streams vs polling, filter scope, buffering latency) remain in SKILL.md.


---

## Mindset — three misconceptions that dominate metric stream misdesign (moved from SKILL.md)

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

---

## Step 11 — Recent features (moved from SKILL.md)

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
