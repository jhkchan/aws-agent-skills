# Eval prompt: idle-alb-detection

Optimise the following Elastic Load Balancer for cost. Walk all
optimization dimensions (idle detection, LCU analysis, consolidation,
CLB migration, data transfer, access logs) and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, ACTION_STEPS).

## Scenario

An ALB named `api-staging-old` has been in the account for 6 months.
It appears to be unused.

## Known facts

- ALB name: `api-staging-old`
- Region: us-east-1, VPC: vpc-prod
- Listeners: 1 x HTTPS:443
- Target groups: 2 (both with 0 registered targets)
- CloudWatch metrics (14-day):
  - RequestCount: average 23/day (mostly automated health checks)
  - HealthyHostCount: 0 for 14 consecutive days
  - ConsumedLCUs: average 0.3 (minimal, from health-check traffic)
- Cost Explorer: $22.15/month ($16.43 base + ~$5.72 LCU charges)
- Route 53: no records point to this ALB's DNS name
- The ALB was created 6 months ago for a staging environment that
  has since been decommissioned

## Symptom

The FinOps team has flagged this ALB in a cost review. It has zero
traffic and zero targets, yet costs $22.15/month.
