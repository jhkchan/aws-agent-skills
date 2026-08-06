# Eval prompt: static-threshold-variable-traffic

Audit the following CloudWatch alarm configuration for blind spots. Emit the
standard VERDICT block (ALARM, VERDICT, REASON, FINDINGS, REMEDIATION).

Alarm name: static-threshold-variable-traffic
Alarm type: MetricAlarm
State: OK

Configuration:
  Namespace: AWS/ApiGateway
  MetricName: Count
  Dimensions: [{Name: ApiName, Value: prod-checkout-api}]
  Statistic: Sum
  Period: 300
  EvaluationPeriods: 1
  DatapointsToAlarm: 1
  ComparisonOperator: LessThanThreshold
  Threshold: 100
  TreatMissingData: breaching
  ActionsEnabled: true
  AlarmActions: [arn:aws:sns:us-east-1:111111111111:traffic-alerts]
  OKActions: []
  InsufficientDataActions: [arn:aws:sns:us-east-1:111111111111:monitoring-alerts]
