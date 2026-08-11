# Eval prompt: action-sns-policy-missing

Diagnose the CloudWatch alarm issue for the following alarm. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `ProductionDiskSpaceAlarm` fires (we see it on the dashboard
in ALARM state), but the on-call Slack channel received zero
notifications in the last 24 hours despite 4 ALARM transitions.

```text
AlarmName: ProductionDiskSpaceAlarm
StateValue: ALARM
Namespace: CWAgent
MetricName: disk_used_percent
Dimensions: [{Name: host, Value: prod-web-1}, {Name: path, Value: /}]
Period: 60
Statistic: Average
Threshold: 90
ComparisonOperator: GreaterThanThreshold
EvaluationPeriods: 3
DatapointsToAlarm: 3
AlarmActions: [arn:aws:sns:us-east-1:111111111111:OpsNotifications]
TreatMissingData: missing

describe-alarm-history StateHistory shows 4 OK -> ALARM transitions
in the last 24 hours.
describe-alarm-history --history-type Action returns NO entries in
the last 24 hours.

SNS topic OpsNotifications policy (created via Terraform):
  Statements allow EventBridge sns:Publish and the CI/CD user
  sns:Publish. There is NO statement granting
  cloudwatch.amazonaws.com sns:Publish.

SNS topic works otherwise: a test publish from the CLI delivers to
the Slack subscription within 2 seconds.
```

The alarm transitions to ALARM correctly, but no notification reaches
Slack. Identify whether the failure is on the alarm side or the action
target side, and emit the diagnostic block.
