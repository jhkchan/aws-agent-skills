# Eval prompt: underutilized-ri-after-migration

Optimise the following EC2 Reserved Instance portfolio for cost. Walk
all commitment dimensions and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
ACTION_STEPS).

## Scenario

A fleet previously ran 20 c5.xlarge instances. The team purchased
Standard RIs but has since migrated to c6i.xlarge. The RIs are now
underutilized.

## Known facts

- Previous fleet: 20 x c5.xlarge (Linux), us-east-1
- Active RIs: 15 x 3-year Standard RIs (All Upfront) for c5.xlarge
- RI purchase date: 18 months ago (18 months remaining on 3-year term)
- Current fleet: 12 x c5.xlarge remaining (rest migrated to c6i.xlarge)
- RI utilization: 55% (only 8 of 15 RIs are used by the remaining
  c5 instances)
- 7 Standard RIs are being paid for but not consumed
- These are Standard RIs (NOT Convertible) — they cannot be exchanged
- No Savings Plans exist
- The c6i.xlarge fleet (8 instances) is running on-demand

## Symptom

The FinOps team has noticed the RI utilization dropped from 100% to
55% after the migration. They want to recover the wasted commitment
value and cover the new c6i fleet.
