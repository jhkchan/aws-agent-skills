# Eval prompt: missing-data-default-treatmissing

Audit the following CloudWatch alarm configuration for blind spots. Emit the
standard VERDICT block (ALARM, VERDICT, REASON, FINDINGS, REMEDIATION).

Alarm name: missing-data-default-treatmissing
Alarm type: MetricAlarm
State: OK

Configuration:
  Namespace: App/CheckoutService
  MetricName: ErrorCount
  Dimensions: [{Name: Environment, Value: prod}]
  Statistic: Sum
  Period: 60
  EvaluationPeriods: 5
  DatapointsToAlarm: 1
  ComparisonOperator: GreaterThanThreshold
  Threshold: 10
  TreatMissingData: (not set — defaults to missing)
  ActionsEnabled: true
  AlarmActions: [arn:aws:sns:us-east-1:111111111111:on-call-critical]
  OKActions: []
  InsufficientDataActions: []
