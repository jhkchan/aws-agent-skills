# Eval: spot-placement-score

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — maintain fleet, priceCapacityOptimized, placement score pre-checked, ODCR used-first for 5 On-Demand units

## Prompt

Create a maintain Spot Fleet in us-east-1 with
priceCapacityOptimized. Target capacity 30 vcpu, with 5
On-Demand units from capacity reservations. Instance types:
m5.large, m5a.large, c5.large across us-east-1a, us-east-1b,
us-east-1c. Pre-check Spot placement scores before creating.
Use capacity reservations first for the On-Demand portion.
Launch template lt-web-v3 (version 1). IAM role
AWSServiceRoleForEC2SpotFleet verified. Account: 123456789012.
