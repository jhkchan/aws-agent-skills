# Eval prompt: low-ri-coverage-steady-state

Optimise the following EC2 Reserved Instance / Savings Plans portfolio
for cost. Walk all commitment dimensions (coverage, utilization, term,
payment, vehicle) and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, ACTION_STEPS).

## Scenario

An EC2 fleet of 50 m5.large (Linux) instances runs 24/7 in us-east-1.

## Known facts

- Fleet: 50 x m5.large (Linux), us-east-1, running 24/7
- 90-day minimum instance count: 48
- Current RI coverage: 40% (20 instances covered by 1-year Standard
  RIs, No Upfront)
- RI utilization: 97%
- No Savings Plans in use
- Cost Explorer: $3,504/month on on-demand for the 30 uncovered
  instances ($0.096/h x 730h x 30 = ~$2,102; plus the 20 covered
  instances' RI cost)
- The fleet has been stable for 6 months with no planned migration
- On-demand rate for m5.large (Linux, us-east-1): $0.096/h

## Symptom

The FinOps team has identified that 60% of the steady-state fleet is
running on-demand. They want to close the coverage gap and maximise
savings.
