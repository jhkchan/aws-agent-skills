# Eval prompt: pending-increase-still-high

Audit the following Service Quotas snapshot for utilization risk. Emit the
standard VERDICT block (QUOTA, SERVICE, VERDICT, REASON, UTILIZATION,
FINDINGS, REMEDIATION).

Audit tag: pending-increase-still-high
Service code: ec2
Quota code: L-1212C26A
Quota name: Running On-Demand Standard instances [pending-increase-still-high]
Applied quota value: 1000
AWS default quota value: 1000
Unit: vCPUs
Adjustable: true
GlobalQuota: false
UsageMetric:
  MetricNamespace: AWS/Usage
  MetricName: ResourceCount
  Dimensions:
    - {Name: Service, Value: EC2}
    - {Name: Resource, Value: vCPU}
    - {Name: Type, Value: Resource}
    - {Name: Class, Value: Standard/OnDemand}
  StatisticType: Sum
Current utilization: 850
CloudWatch alarm configured: true (threshold: 80%, SNS topic: quota-alerts)
Quota increase request history:
  - Status: PENDING, RequestedValue: 2000, Created: 2026-07-28
