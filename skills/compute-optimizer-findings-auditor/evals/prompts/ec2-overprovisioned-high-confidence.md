# Eval prompt: ec2-overprovisioned-high-confidence

Audit the following Compute Optimizer finding for the EC2 instance. Emit the
standard VERDICT block (RESOURCE, VERDICT, REASON, RISK, FINDINGS, REMEDIATION).

Resource type: EC2 instance
Instance ARN: arn:aws:ec2:us-east-1:111111111111:instance/i-ec2-overprovisioned-high-confidence
Current instance type: m5.2xlarge
Finding: Overprovisioned
Finding reasons: ["CPUOverprovisioned", "MemoryOverprovisioned"]
Utilization metrics:
  - name: CPU, statistic: Maximum, value: 8.0, source: CloudWatch
  - name: Memory, statistic: Maximum, value: 15.0, source: CloudWatchAgent
  - name: NetworkIn, statistic: Average, value: 0.05, source: CloudWatch
Recommendation options:
  - rank: 1, instanceType: t3.large, performanceRisk: 1, savingsOpportunity: { savingsPercentage: 75.0, estimatedMonthlySavings: 150.0 }
  - rank: 2, instanceType: t3.medium, performanceRisk: 2, savingsOpportunity: { savingsPercentage: 82.0, estimatedMonthlySavings: 165.0 }
Last refresh timestamp: 2026-07-28
