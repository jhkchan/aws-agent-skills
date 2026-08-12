# Eval prompt: burstable-credit-exhaustion

Right-size the following EC2 instance for cost. Walk the burstable
instance (t-family) credit exhaustion decision tree and emit the
standard right-sizing block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

InstanceId: i-burstable-credit-exhaustion
InstanceType: t3.large
Architecture: x86_64
Region: us-east-1
Pricing: On-Demand (standard credit mode)
TerminationProtection: false

Metrics (last 14 days):
  - CPUUtilization avg: 78%, p95: 95%
  - MemoryUtilization avg: 50% (CWAgent mem_used_percent)
  - CPUCreditBalance: trending from 144 to 12 over 14 days
  - CPUSurplusCreditBalance: 0 (not yet in Unlimited)

Compute Optimizer finding: NotOptimized (insufficient data)

Workload context: CI/CD runner (Jenkins agent). Sustained high CPU
during builds (8 hours/day at 85%+ CPU). Docker-based builds using
x86 images.
