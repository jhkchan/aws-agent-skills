# Eval prompt: cw-wrong-statistic-sum-vs-average

Diagnose the following CloudWatch metric value mismatch. Walk the
METRIC_VALUE_UNEXPECTED decision tree and emit the standard VERDICT
block.

## Scenario

An operator has a custom metric `Latency` under namespace
`MyApp/API`. The emitter is application code calling `PutMetricData`
with one data point per request, where `Value` is the latency in
milliseconds for that single request.

## Known facts

- The operator's `get-metric-statistics` query:
  - Namespace: `MyApp/API`
  - MetricName: `Latency`
  - Statistic: `Sum`
  - Period: 60
  - Window: last 5 minutes
  - Result: values in the range 5000-8000 (the operator expected
    50-80 ms)
- Re-running with Statistic `Average` over the same parameters
  returns values in the 50-80 ms range.
- Re-running with Statistic `SampleCount` returns values around 100
  per minute.
- `list-metrics --namespace MyApp/API --metric-name Latency` returns
  the metric with no dimensions (emitter does not set any).

## Symptom

The operator's "average latency" dashboard cell shows values around
5000-8000 ms but the operator expected ~50-80 ms. They believe the
metric is broken.
