# Eval prompt: trackable-missing-alarm

Audit the following Service Quotas snapshot for utilization risk. Emit the
standard VERDICT block (QUOTA, SERVICE, VERDICT, REASON, UTILIZATION,
FINDINGS, REMEDIATION).

Audit tag: trackable-missing-alarm
Service code: lambda
Quota code: L-B99A9384
Quota name: Concurrent executions [trackable-missing-alarm]
Applied quota value: 1000
AWS default quota value: 1000
Unit: Count
Adjustable: true
GlobalQuota: false
UsageMetric:
  MetricNamespace: AWS/Usage
  MetricName: ResourceCount
  Dimensions:
    - {Name: Service, Value: Lambda}
    - {Name: Resource, Value: Function}
    - {Name: Type, Value: Resource}
  StatisticType: Maximum
Current utilization: 400
CloudWatch alarm configured: false
Quota increase request history: (none)
