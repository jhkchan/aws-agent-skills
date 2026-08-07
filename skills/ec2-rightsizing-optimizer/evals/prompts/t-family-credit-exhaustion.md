# Eval prompt: t-family-credit-exhaustion

Optimize the EC2 instance configuration for cost and performance. Walk
the rightsizing decision matrix and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

InstanceId: i-t-family-credit-exhaustion
Current instance type: t3.large
Region: us-east-1
Pricing: On-Demand

Utilization metrics (last 30 days, CWAgent reporting):
  - CPUUtilization: avg=35%, max=80% (CloudWatch)
  - CPUCreditBalance: chronically < 30, frequently drops to 0 during
    business hours
  - MemoryUtilization: avg=45%, max=55% (CloudWatchAgent)
  - NetworkIn: avg=0.3 MB/s, max=0.5 MB/s

Compute Optimizer finding: Underprovisioned
Finding reasons: ["CPUUnderprovisioned"]

Workload context: PHP web application serving business-hours traffic.
Users report intermittent 5x latency spikes during peak hours;
CloudWatch shows CPUCreditBalance hits 0 during these spikes, then
performance drops to the 20% baseline.
