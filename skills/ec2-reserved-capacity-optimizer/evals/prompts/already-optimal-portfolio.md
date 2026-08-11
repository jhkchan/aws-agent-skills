# Eval prompt: already-optimal-portfolio

Optimise the following EC2 Reserved Instance / Savings Plans portfolio
for cost. Walk all commitment dimensions and emit the standard
optimization block (TARGET, VERDICT, REASON).

## Scenario

An EC2 fleet has an already-optimized commitment portfolio. The team
wants to verify there are no further savings opportunities.

## Known facts

- Fleet: 40 x m5.2xlarge (Linux), us-east-1, running 24/7
- Active RIs: 38 x 3-year Standard RIs (All Upfront) for m5.2xlarge
  - Purchased 12 months ago
  - RI utilization: 97%
  - RI coverage: 95% (38 of 40 instances covered)
- Active Savings Plan: Compute SP (1-year, No Upfront), $5/hour
  commitment
  - SP utilization: 94%
  - Covers flexible EC2 + Fargate spend above the RI baseline
- CloudWatch alerts configured: RI utilization alarm at 80% threshold
- AWS Budget: RI coverage budget at 90% threshold
- The fleet has been stable for 12 months with no planned migration
- On-demand rate for m5.2xlarge: $0.384/h (us-east-1, Linux)

## Symptom

The FinOps team is doing a quarterly commitment review and wants to
confirm this portfolio has no further optimization opportunities.
