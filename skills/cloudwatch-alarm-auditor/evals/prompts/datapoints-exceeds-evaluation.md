# Eval prompt: datapoints-exceeds-evaluation

Audit the following CloudWatch alarm configuration for blind spots. Emit the
standard VERDICT block (ALARM, VERDICT, REASON, FINDINGS, REMEDIATION).

Alarm name: datapoints-exceeds-evaluation
Alarm type: MetricAlarm
State: OK

Configuration:
  Namespace: AWS/RDS
  MetricName: CPUUtilization
  Dimensions: [{Name: DBInstanceIdentifier, Value: prod-db-001}]
  Statistic: Average
  Period: 300
  EvaluationPeriods: 3
  DatapointsToAlarm: 5
  ComparisonOperator: GreaterThanThreshold
  Threshold: 90
  TreatMissingData: breaching
  ActionsEnabled: true
  AlarmActions: [arn:aws:sns:us-east-1:111111111111:database-critical]
  OKActions: []
  InsufficientDataActions: [arn:aws:sns:us-east-1:111111111111:monitoring-alerts]
