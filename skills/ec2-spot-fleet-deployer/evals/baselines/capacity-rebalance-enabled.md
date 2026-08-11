# Baseline (no-skill) — capacity-rebalance-enabled

> This is the response a model produces **without** the skill
> definition. It suggests lowestPrice instead of capacityOptimized
> for a long-running workload, does not configure capacity
> rebalance, does not explain the rebalance lifecycle or the launch
> replacement strategy, and does not emit the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

To create a Spot Fleet for ML training:

```bash
aws ec2 request-spot-fleet \
  --spot-fleet-request-config '{
    "AllocationStrategy": "lowestPrice",
    "TargetCapacity": 100,
    "LaunchSpecifications": [{
      "InstanceType": "g4dn.xlarge",
      "ImageId": "ami-0abcdef"
    }]
  }'
```

Make sure your instances have GPU drivers installed.
