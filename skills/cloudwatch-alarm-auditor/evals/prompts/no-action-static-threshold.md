# Eval prompt: no-action-static-threshold

Audit the following CloudWatch alarm configuration for blind spots. Emit the
standard VERDICT block (ALARM, VERDICT, REASON, FINDINGS, REMEDIATION).

Alarm name: no-action-static-threshold
Alarm type: MetricAlarm
State: OK

Configuration:
  Namespace: AWS/EC2
  MetricName: CPUUtilization
  Dimensions: [{Name: InstanceId, Value: i-0123456789abcdef0}]
  Statistic: Average
  Period: 300
  EvaluationPeriods: 3
  DatapointsToAlarm: 2
  ComparisonOperator: GreaterThanThreshold
  Threshold: 80
  TreatMissingData: notBreaching
  ActionsEnabled: true
  AlarmActions: []
  OKActions: []
  InsufficientDataActions: []
