# Eval prompt: ec2-overprovisioned-low-confidence-inferred-memory

Audit the following Compute Optimizer finding for the EC2 instance. Emit the
standard VERDICT block (RESOURCE, VERDICT, REASON, RISK, FINDINGS, REMEDIATION).

Resource type: EC2 instance
Instance ARN: arn:aws:ec2:us-east-1:111111111111:instance/i-ec2-overprovisioned-low-confidence
Current instance type: m5.xlarge
Finding: Overprovisioned
Finding reasons: ["CPUOverprovisioned"]
Utilization metrics:
  - name: CPU, statistic: Maximum, value: 12.0, source: CloudWatch
  (Memory metric ABSENT — CloudWatch Agent not installed; memory usage inferred from instance type specifications)
Recommendation options:
  - rank: 1, instanceType: t3.medium, performanceRisk: 4, savingsOpportunity: { savingsPercentage: 70.0, estimatedMonthlySavings: 95.0 }
Last refresh timestamp: 2026-07-26
