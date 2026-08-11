# Eval prompt: convertible-ri-exchange-opportunity

Optimise the following EC2 Reserved Instance portfolio for cost. Walk
all commitment dimensions and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
ACTION_STEPS).

## Scenario

A fleet runs 30 m5.xlarge instances. The fleet was recently right-sized
from m5.large to m5.xlarge. Convertible RIs for the old size are now
underutilized.

## Known facts

- Current fleet: 30 x m5.xlarge (Linux), us-east-1, 24/7
- Previous fleet: 30 x m5.large (right-sized to m5.xlarge)
- Active RIs: 20 x Convertible RIs (1-year, Partial Upfront) for
  m5.large
- RI purchase date: 4 months ago (8 months remaining)
- RI utilization: 60% (the Convertible RIs cover m5.large, but the
  fleet now runs m5.xlarge)
- No Savings Plans exist
- The fleet has been stable at m5.xlarge for 30 days
- On-demand rate for m5.xlarge: $0.192/h (us-east-1, Linux)
- On-demand rate for m5.large: $0.096/h (us-east-1, Linux)

## Symptom

The team right-sized the fleet from m5.large to m5.xlarge for
performance reasons. The Convertible RIs are now at 60% utilization
because they cover the old (cheaper) instance size. The team wants to
restore full RI utilization.
