# Eval prompt: audit-diversification-single-pool-review-required

Audit the Spot Fleet diversification coverage and emit the standard VERDICT
block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY, NOTES).

Operation: audit-diversification
Spot Fleet: sfr-single-tenant-jobs

```json
{
  "SpotFleetConfig": {
    "AllocationStrategy": "lowestPrice",
    "InstancePoolsToUseCount": 1,
    "TargetCapacity": 20,
    "FulfilledCapacity": "12 (40% unfulfilled — capacity constraints)"
  },
  "LaunchTemplateOverrides": [
    {"InstanceType": "c5.large", "AvailabilityZone": "us-east-1a"},
    {"InstanceType": "c5.large", "AvailabilityZone": "us-east-1b"},
    {"InstanceType": "c5.xlarge", "AvailabilityZone": "us-east-1a"},
    {"InstanceType": "c5.xlarge", "AvailabilityZone": "us-east-1b"}
  ],
  "DiversificationSummary": {
    "UniqueInstanceFamilies": 1,
    "UniqueAZs": 2,
    "GravitonFamilies": 0
  },
  "InterruptionHistory": {
    "TotalInterruptions30Days": 38,
    "MostInterruptedPool": "c5.large/us-east-1a (14 interruptions)"
  },
  "SpotPlacementScore": {
    "Score": 3,
    "Context": "marginal — high risk"
  }
}
```
