# Eval prompt: tune-strategy-lowest-price-review-required

Plan the following Spot Fleet allocation strategy change and diversification
expansion, then emit the standard VERDICT block (OPERATION, VERDICT, TARGET,
PRE_CHECKS, STEPS, POST_VERIFY, NOTES).

Operation: tune-replacement-strategy
Spot Fleet: sfr-batch-prod

```json
{
  "CurrentConfig": {
    "AllocationStrategy": "lowestPrice",
    "InstancePoolsToUseCount": 1,
    "TargetCapacity": 50,
    "FulfilledCapacity": "47 (3 recently interrupted)",
    "InstanceTypes": ["c5.large", "m5.large"],
    "AZs": ["us-east-1a", "us-east-1b"]
  },
  "ProposedConfig": {
    "AllocationStrategy": "capacity-optimized",
    "InstanceTypes": ["c5.large", "m5.large", "c6g.large (Graviton)"],
    "AZs": ["us-east-1a", "us-east-1b", "us-east-1c"]
  },
  "BatchWorkload": "containerized Python jobs",
  "Arm64Support": "unverified"
}
```
