# CloudWatch Alarm Configuration Reference Guide

Supplementary reference for the CloudWatch Alarm Troubleshooter skill.
Loaded on-demand when a diagnostic needs the exact alarm configuration
semantics, period alignment rules, statistic aggregation behaviour,
composite rule grammar, or action-target permission matrix.

## TreatMissingData values

| Value | Behaviour on missing points | Use case |
|---|---|---|
| `missing` (default) | Alarm goes to INSUFFICIENT_DATA | The "honest" default; surfaces missing-data issues |
| `breaching` | Missing points treated as breaching | Silent-failure detection (metric stops emitting = alarm) |
| `notBreaching` | Missing points treated as not breaching | Missing data is benign (overnight quiet traffic) |
| `ignore` | Hold current state; do not evaluate | Missing data is expected and should not affect state |

`TreatMissingData: breaching` is frequently misused as a permanent
fix for a dead metric pipeline. It masks the underlying issue; pair it
with an investigation of why the metric stopped emitting.

## Native metric resolution matrix

| Metric source | Native resolution | Set via |
|---|---|---|
| AWS service metrics (AWS/Lambda, AWS/EC2, AWS/S3, AWS/DynamoDB, etc.) | 60 seconds | Automatic |
| CloudWatch Agent — standard metrics | 60 seconds | Agent default |
| CloudWatch Agent — high-resolution metrics | 1 second | Agent config per metric |
| `put-metric-data --storage-resolution 1` | 1 second | CLI flag |
| `put-metric-data` (default) | 60 seconds | Default |
| Embedded Metric Format (logs) | 1 second (settable) | EMF directive |

The alarm `Period` must be a multiple of the metric's native
resolution. `Period: 1` on a standard 60-second metric returns no
points; the alarm goes INSUFFICIENT_DATA.

## Statistic reference

| Statistic | Aggregation | Typical use | CLI flag |
|---|---|---|---|
| `Sum` | Sum of points in the period | Counts (errors, requests, bytes) | `--statistic Sum` |
| `Average` | Arithmetic mean | Latency, CPU utilisation | `--statistic Average` |
| `Maximum` | Largest value in the period | Peak latency, peak memory | `--statistic Maximum` |
| `Minimum` | Smallest value in the period | Lowest capacity | `--statistic Minimum` |
| `SampleCount` | Count of data points | Throughput / request rate | `--statistic SampleCount` |
| `p99`, `p95`, `p90`, `p99.9` | Percentile | Tail latency | `--extended-statistic p99` |
| `TM99`, `TM95`, `TM90` | Trimmed mean | Tail latency (robust to outliers) | `--extended-statistic TM99` |
| `PR(:n)` | Percentile rank | Distribution | `--extended-statistic PR(:99)` |

Switching the alarm's Statistic without re-checking the dashboard's
Statistic is the #1 source of "dashboard breaches, alarm stays OK."
Always cross-reference the two before declaring a threshold issue.

## Comparison operators

| Operator | Behaviour |
|---|---|
| `GreaterThanThreshold` | Breach when metric > threshold (strict) |
| `GreaterThanOrEqualToThreshold` | Breach when metric >= threshold |
| `LessThanThreshold` | Breach when metric < threshold (strict) |
| `LessThanOrEqualToThreshold` | Breach when metric <= threshold |
| `LessThanLowerOrGreaterThanUpperThreshold` | Anomaly band: breach outside the band |
| `LessThanLowerThreshold` | Anomaly band: breach below the lower band |
| `GreaterThanUpperThreshold` | Anomaly band: breach above the upper band |

Common gotcha: `GreaterThanThreshold` with threshold = 100 and metric
peaking at exactly 100 does NOT breach. Use
`GreaterThanOrEqualToThreshold` for inclusive comparisons.

## EvaluationPeriods vs DatapointsToAlarm

- `EvaluationPeriods`: the number of consecutive periods over which
  the alarm evaluates the metric.
- `DatapointsToAlarm`: the number of breaching datapoints within the
  EvaluationPeriods window required to transition to ALARM. Must be
  <= EvaluationPeriods.

Example: `EvaluationPeriods: 5, DatapointsToAlarm: 3` means "3 out of
the last 5 consecutive periods must breach." A single breach in 5
periods does not fire; 3 breaches in any 5-period window do.

## Composite alarm rule grammar

```
Rule := Expression
Expression := '(' Expression ')' |
              'NOT' Expression |
              Expression ('AND' | 'OR') Expression |
              'ALARM' '(' AlarmName ')' |
              'OK' '(' AlarmName ')' |
              'INSUFFICIENT' '(' AlarmName ')' |
              'TRUE' | 'FALSE'
```

`ALARM(child-name)` evaluates to true iff the named child alarm is in
ALARM state. `INSUFFICIENT(child-name)` evaluates to true iff the
child is in INSUFFICIENT_DATA.

### Truth table for INSUFFICIENT children

| Left | Right (INSUFFICIENT) | `AND` result | `OR` result |
|---|---|---|---|
| ALARM (true) | INSUFFICIENT (false-ish) | false | true |
| OK (false) | INSUFFICIENT (false-ish) | false | false |
| INSUFFICIENT (false-ish) | INSUFFICIENT (false-ish) | false | false |

INSUFFICIENT children propagate as false under both AND and OR. To
explicitly detect INSUFFICIENT children, use `INSUFFICIENT(name)` as
a predicate in the rule.

### Child name handling

Child alarm names in the Rule string are NOT auto-updated when a
child alarm is renamed. The composite silently stops matching the
renamed child. Always rewrite the Rule after renaming a child.

## Math expression reference

Each entry in `Metrics` has an `Id` (e.g., `m1`, `e1`). Expressions
reference other `Id`s by string.

### Supported functions

| Function | Description |
|---|---|
| `AVG(metricId)` | Average across periods |
| `SUM(metricId)` | Sum across periods |
| `MIN(metricId)` | Minimum across periods |
| `MAX(metricId)` | Maximum across periods |
| `STDDEV(metricId)` | Standard deviation |
| `FILL(metricId, value)` | Replace missing points with a constant |
| `ABS(metricId)` | Absolute value |
| `CEIL(metricId)` | Ceiling |
| `FLOOR(metricId)` | Floor |
| `TIME_SERIES(value, period)` | Generate a constant time series |
| `DATAPOINT_COUNT()` | Count of datapoints |

### Common math-expression failures

- `e2 / e1` where `e1` has zero points: returns no value; alarm goes
  INSUFFICIENT_DATA. Guard with `FILL(e1, 0)` or restructure.
- `m1 + m2` where `m1` and `m2` are at different periods: aggregation
  mismatch. Align periods.
- `SEARCH(...)`: dashboard-only; alarms reject it.

## Action target permission matrix

| Target | Required permission | Principal | Console auto-adds? |
|---|---|---|---|
| SNS topic | `sns:Publish` | `cloudwatch.amazonaws.com` | Yes |
| Lambda function | `lambda:InvokeFunction` | `cloudwatch.amazonaws.com` | Yes |
| Auto Scaling policy | AlarmActions must reference the policy ARN | n/a | n/a |
| SSM OpsItem | Automatic for the account's OpsCenter | n/a | n/a |
| Step Functions state machine | `states:StartExecution` | `cloudwatch.amazonaws.com` | No |

For SNS and Lambda: the console auto-adds the permission when you
create the alarm via the console. CLI, Terraform, and CloudFormation
do NOT auto-add it. Always verify the target policy after creating an
alarm via IaC.

## Alarm state transition model

```
OK → ALARM             : threshold breached for DatapointsToAlarm out
                          of EvaluationPeriods consecutive periods
ALARM → OK             : threshold not breached for EvaluationPeriods
                          consecutive periods
OK / ALARM → INSUFFICIENT_DATA : no metric points in the window
INSUFFICIENT_DATA → OK : points return AND do not breach
INSUFFICIENT_DATA → ALARM : points return AND breach,
                          OR TreatMissingData: breaching AND missing
```

## AWS Health event categories that affect CloudWatch alarms

| Category | Likely impact |
|---|---|
| `AWS_CLOUDWATCH_SERVICE` | Region-wide CloudWatch degradation; alarms may not evaluate |
| `AWS_CLOUDWATCH_METRICS` | Metric ingestion delays; alarms go INSUFFICIENT_DATA transiently |
| `AWS_SNS_SERVICE` | SNS delivery delays; alarm actions fire but notifications lag |

Always probe `aws health describe-events` for regional issues before
declaring a customer-side root cause during a wide-impact incident.
