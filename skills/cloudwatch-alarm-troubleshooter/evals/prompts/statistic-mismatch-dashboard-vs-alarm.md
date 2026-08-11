# Eval prompt: statistic-mismatch-dashboard-vs-alarm

Diagnose the CloudWatch alarm issue for the following alarm. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `ApiLatencyAlarm` stays in OK state even though the p99
latency dashboard clearly shows sustained spikes above 500ms during
the afternoon traffic peak.

```text
AlarmName: ApiLatencyAlarm
StateValue: OK
Namespace: AppMetrics
MetricName: RequestLatency
Dimensions: [{Name: Service, Value: orders-api}]
Period: 60
Statistic: Average
Threshold: 500
ComparisonOperator: GreaterThanThreshold
EvaluationPeriods: 5
DatapointsToAlarm: 5
TreatMissingData: missing

Dashboard query: AppMetrics RequestLatency p99 over 1-minute periods
for Service=orders-api.

get-metric-data with Statistic: Average returns values in the
80-180ms range (well under the 500ms threshold).
get-metric-data with ExtendedStatistic: p99 returns values in the
400-1200ms range, with sustained windows above 500ms during the peak.

Operator's intent: "alert when any sustained window has p99 latency
above 500ms."
```

The dashboard breaches but the alarm stays OK. Identify why the alarm
does not reflect what the dashboard shows.
