# Eval prompt: approaching-limit-eighty-pct

Audit the following Service Quotas snapshot for utilization risk. Emit the
standard VERDICT block (QUOTA, SERVICE, VERDICT, REASON, UTILIZATION,
FINDINGS, REMEDIATION).

Audit tag: approaching-limit-eighty-pct
Service code: vpc
Quota code: L-F678F1CE
Quota name: VPCs per Region [approaching-limit-eighty-pct]
Applied quota value: 50
AWS default quota value: 50
Unit: Count
Adjustable: true
GlobalQuota: false
UsageMetric:
  MetricNamespace: AWS/Usage
  MetricName: ResourceCount
  Dimensions:
    - {Name: Service, Value: EC2}
    - {Name: Resource, Value: vCPU}
    - {Name: Type, Value: Resource}
  StatisticType: Sum
Current utilization: 40 (applied quota: 50, utilization rate: exactly 80%)
CloudWatch alarm configured: true (threshold: 80%, SNS topic: quota-alerts)
Quota increase request history: (none)
