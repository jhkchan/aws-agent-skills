# Eval prompt: ec2-underprovisioned-cpu-memory

Audit the following Compute Optimizer finding for the EC2 instance. Emit the
standard VERDICT block (RESOURCE, VERDICT, REASON, RISK, FINDINGS, REMEDIATION).

Resource type: EC2 instance
Instance ARN: arn:aws:ec2:us-east-1:111111111111:instance/i-ec2-underprovisioned-cpu-memory
Current instance type: t3.small
Finding: Underprovisioned
Finding reasons: ["CPUUnderprovisioned", "MemoryUnderprovisioned"]
Utilization metrics:
  - name: CPU, statistic: Maximum, value: 97.0, source: CloudWatch
  - name: Memory, statistic: Maximum, value: 92.0, source: CloudWatchAgent
  - name: NetworkIn, statistic: Average, value: 1.2, source: CloudWatch
Recommendation options:
  - rank: 1, instanceType: t3.large, performanceRisk: 1, savingsOpportunity: { savingsPercentage: 0.0, estimatedMonthlySavings: -45.0 }
Last refresh timestamp: 2026-07-30
