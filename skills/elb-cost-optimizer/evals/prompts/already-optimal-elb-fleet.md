# Eval prompt: already-optimal-elb-fleet

Optimise the following ELB fleet for cost. Walk all optimization
dimensions and emit the standard optimization block (TARGET, VERDICT,
REASON).

## Scenario

An account has a well-optimized ELB fleet. The team wants to verify
there are no further cost savings.

## Known facts

- Region: us-east-1
- ALBs:
  - `prod-alb` (production, VPC: vpc-prod)
    - 5 path-based listener rules serving 5 microservices
    - ConsumedLCUs: average 8.0 (peak dimension: new connections at
      8.0 LCU, managed with HTTP keep-alive enabled)
    - All targets healthy, RequestCount > 50,000/day
  - `staging-alb` (staging, VPC: vpc-staging, different VPC)
    - 3 path-based listener rules serving 3 microservices
    - ConsumedLCUs: average 1.2
    - All targets healthy, RequestCount > 5,000/day
- No CLBs exist in the account
- No NLBs exist in the account
- No idle ALBs (all have > 5,000 requests/day and > 2 healthy targets)
- ALB access logs: written to S3 with lifecycle rules
  (Standard-IA at 30d, Glacier at 90d, expire at 365d)
- ACM certificates: wildcard certs in place for each environment
- ALBs in different VPCs (cannot consolidate prod and staging)

## Symptom

The FinOps team is doing a quarterly ELB cost review and wants to
confirm there are no further optimization opportunities.
