# Eval prompt: well-configured-anomaly-ok

Audit the following CloudWatch alarm configuration for blind spots. Emit the
standard VERDICT block (ALARM, VERDICT, REASON, FINDINGS, REMEDIATION).

Alarm name: well-configured-anomaly-ok
Alarm type: MetricAlarm
State: OK

Configuration:
  Metrics:
    - Id: e1
      Expression: ANOMALY_DETECTION_BAND(m1, 2)
      Label: Latency anomaly band (stdev=2)
    - Id: m1
      MetricStat:
        Metric:
          Namespace: AWS/ApplicationELB
          MetricName: TargetResponseTime
          Dimensions: [{Name: LoadBalancer, Value: app/prod-alb/1234567890}]
        Period: 300
        Stat: Average
      ReturnData: true
  EvaluationPeriods: 3
  DatapointsToAlarm: 2
  ComparisonOperator: GreaterThanUpperThreshold
  Threshold: 0
  TreatMissingData: breaching
  ActionsEnabled: true
  AlarmActions: [arn:aws:sns:us-east-1:111111111111:latency-anomaly-alerts]
  OKActions: [arn:aws:sns:us-east-1:111111111111:latency-anomaly-cleared]
  InsufficientDataActions: [arn:aws:sns:us-east-1:111111111111:monitoring-alerts]
