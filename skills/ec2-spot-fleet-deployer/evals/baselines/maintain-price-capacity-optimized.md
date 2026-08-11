# Baseline (no-skill) — maintain-price-capacity-optimized

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the
> priceCapacityOptimized recommendation (defaults to
> lowestPrice), does not flag the single-pool concentration risk
> of lowestPrice, omits capacity rebalance configuration, forgets
> the IAM service role check, and does not emit the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Here's how to create a Spot Fleet:

1. Create the fleet request:
```bash
aws ec2 request-spot-fleet \
  --spot-fleet-request-config '{
    "AllocationStrategy": "lowestPrice",
    "TargetCapacity": 20,
    "LaunchSpecifications": [{
      "InstanceType": "m5.large",
      "ImageId": "ami-0abcdef1234567890"
    }]
  }'
```

2. Check the fleet status in the console.

That should work.
