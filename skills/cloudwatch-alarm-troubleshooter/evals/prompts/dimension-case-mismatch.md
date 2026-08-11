# Eval prompt: dimension-case-mismatch

Diagnose the CloudWatch alarm issue for the following alarm. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `HighErrorRateAlarm` has been in `INSUFFICIENT_DATA` for 3
days. The Lambda function `fn-orders-api` is clearly emitting Errors
— we can see them on the dashboard.

```text
AlarmName: HighErrorRateAlarm
StateValue: INSUFFICIENT_DATA
Namespace: AWS/Lambda
MetricName: Errors
Dimensions: [{Name: FunctionName, Value: Fn-Orders-API}]
Period: 300
Statistic: Sum
Threshold: 5
ComparisonOperator: GreaterThanThreshold
EvaluationPeriods: 1
DatapointsToAlarm: 1
TreatMissingData: missing

Metric evidence: dashboard (dimensionless query on AWS/Lambda Errors)
shows non-zero values for fn-orders-api every 5 minutes for the last
24 hours.

list-metrics output for AWS/Lambda Errors includes:
  {Namespace: AWS/Lambda, MetricName: Errors,
   Dimensions: [{Name: FunctionName, Value: fn-orders-api}]}

get-metric-data with the alarm's exact dimension set
(FunctionName=Fn-Orders-API) returns Values: [].
get-metric-data with the corrected dimension
(FunctionName=fn-orders-api) returns Values: [3, 1, 0, 7, 2].
```

The dimensionless dashboard query returns points, but the alarm's
dimension-scoped query does not. Identify the root cause and emit the
diagnostic block.
