# Eval prompt: denied-increase-config-gap

Audit the following Service Quotas snapshot for utilization risk. Emit the
standard VERDICT block (QUOTA, SERVICE, VERDICT, REASON, UTILIZATION,
FINDINGS, REMEDIATION).

Audit tag: denied-increase-config-gap
Service code: ec2
Quota code: L-1212C26A
Quota name: Running On-Demand Standard instances [denied-increase-config-gap]
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
Current utilization: 600
CloudWatch alarm configured: true (threshold: 80%, SNS topic: quota-alerts)
Quota increase request history:
  - Status: DENIED, RequestedValue: 2000, Created: 2025-06-15
