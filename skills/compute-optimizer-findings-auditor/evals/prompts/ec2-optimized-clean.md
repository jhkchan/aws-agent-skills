# Eval prompt: ec2-optimized-clean

Audit the following Compute Optimizer finding for the EC2 instance. Emit the
standard VERDICT block (RESOURCE, VERDICT, REASON, RISK, FINDINGS, REMEDIATION).

Resource type: EC2 instance
Instance ARN: arn:aws:ec2:us-east-1:111111111111:instance/i-ec2-optimized-clean
Current instance type: c5.xlarge
Finding: Optimized
Finding reasons: []
Utilization metrics:
  - name: CPU, statistic: Maximum, value: 60.0, source: CloudWatch
  - name: Memory, statistic: Maximum, value: 55.0, source: CloudWatchAgent
  - name: NetworkIn, statistic: Average, value: 0.8, source: CloudWatch
Recommendation options: []
Last refresh timestamp: 2026-07-31
