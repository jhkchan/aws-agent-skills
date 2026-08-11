# Eval prompt: period-misalignment-standard-metric

Diagnose the CloudWatch alarm issue for the following alarm. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `HighCpuAlarm` has been in `INSUFFICIENT_DATA` since I set
it up yesterday. The EC2 dashboard clearly shows CPUUtilization
fluctuating between 40% and 90%.

```text
AlarmName: HighCpuAlarm
StateValue: INSUFFICIENT_DATA
Namespace: AWS/EC2
MetricName: CPUUtilization
Dimensions: [{Name: InstanceId, Value: i-0abc123def456}]
Period: 1
Statistic: Average
Threshold: 80
ComparisonOperator: GreaterThanThreshold
EvaluationPeriods: 1
TreatMissingData: missing

Metric evidence: AWS/EC2 CPUUtilization is a standard-resolution
metric (60-second native storage resolution). Dashboard at 1-minute
granularity shows values 40-90%.

get-metric-data with Period: 1 returns Values: [].
get-metric-data with Period: 60 returns Values:
  [42.5, 78.1, 91.3, 65.0, 88.7].
```

The operator lowered the period to 1 for "more sensitivity." Identify
why the alarm sits in INSUFFICIENT_DATA despite the metric clearly
existing.
