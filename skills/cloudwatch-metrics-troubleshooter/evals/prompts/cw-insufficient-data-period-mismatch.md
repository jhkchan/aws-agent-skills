# Eval prompt: cw-insufficient-data-period-mismatch

Diagnose the following CloudWatch alarm state. Walk the
INSUFFICIENT_DATA_ALARM decision tree and emit the standard VERDICT
block.

## Scenario

A CloudWatch alarm named `LowHeartbeat` is persistently in
`INSUFFICIENT_DATA` state. The operator believes the metric is broken.

## Known facts

- `aws cloudwatch describe-alarms --alarm-names LowHeartbeat` shows:
  - Namespace: `MyApp/Health`
  - MetricName: `Heartbeat`
  - Dimensions: `ServiceName=worker`
  - Period: 60
  - EvaluationPeriods: 5
  - Statistic: `Sum`
  - Threshold: 1
  - ComparisonOperator: `GreaterThanOrEqualToThreshold`
  - TreatMissingData: `missing`
- The emitter writes one `Heartbeat` data point every 5 minutes (it
  polls a health endpoint on a 5-minute schedule).
- `aws cloudwatch get-metric-statistics` with the alarm's exact
  parameters over the last 15 minutes returns 3 data points (one per
  5-minute emission).
- `list-metrics --namespace MyApp/Health --metric-name Heartbeat`
  returns the metric with dimension `ServiceName=worker` (correct).

## Symptom

The alarm has been INSUFFICIENT_DATA for over an hour. The metric is
emitting correctly at its 5-minute cadence.
