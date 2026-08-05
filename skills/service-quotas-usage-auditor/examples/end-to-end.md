# End-to-end usage scenario: service-quotas-usage-auditor

A walkthrough showing the skill auditing an EC2 On-Demand vCPU quota that
has both an approaching limit (85% utilization) and a denied increase
request, demonstrating severity aggregation, the applied-vs-default
reasoning, and the PENDING-vs-applied distinction.

## Input (user prompt)

> Audit our EC2 service quotas before the Black Friday capacity expansion.
> We need to know if we'll hit any limits.

```yaml
Audit tag: ec2-capacity-audit
Service code: ec2
Quota code: L-1212C26A
Quota name: Running On-Demand Standard instances
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
  - Status: DENIED, RequestedValue: 2000, Created: 2026-06-15
  - Status: PENDING, RequestedValue: 1500, Created: 2026-07-28
```

## Expected behavior

1. Classifies the quota as **APPROACHING_LIMIT** — utilization is 85%
   (Step 1), which takes precedence over all other findings. Any new
   instance launch during the capacity expansion may fail with
   `LimitExceededException`.
2. Notes the denied increase request (Step 2c reasoning) in FINDINGS — a
   prior request to 2000 was rejected, and the new pending request to
   1500 has not yet taken effect. The applied quota remains 1000.
3. Emits specific CLI remediation: open a support case for the pending
   request, switch non-critical workloads to Spot Instances (separate
   quota), and distribute across regions.

## Expected output

```text
QUOTA: L-1212C26A (Running On-Demand Standard instances)
SERVICE: ec2
VERDICT: APPROACHING_LIMIT
REASON: Utilization is at 85% of the applied quota (850/1000 vCPUs).
A prior increase to 2000 was DENIED; a new request to 1500 is PENDING but
has not taken effect — the applied value remains 1000 (Step 1).
UTILIZATION: 850/1000 (85%) [default: 1000] [unit: vCPUs]
FINDINGS:
  - [APPROACHING_LIMIT] 850/1000 vCPUs (85%) — new instance launches may fail with LimitExceededException (Step 1)
  - [CONFIG_GAP] Increase to 2000 DENIED on 2026-06-15; replacement request to 1500 is PENDING — no capacity headroom confirmed (Step 2c)
REMEDIATION:
  1. Escalate the PENDING request (1500 vCPUs) via AWS support with Black Friday workload justification.
  2. Switch non-critical workloads to Spot Instances (separate quota: L-34DBAA49).
  3. Distribute across regions — us-east-1 quota does not apply to us-west-2 or eu-west-1.
  4. Do NOT compute utilization against the PENDING requested value (1500) — the applied value is still 1000.
```
