# Baseline (no-skill) — missing-iam-role

> This is the response a model produces **without** the skill
> definition. It provides CLI commands without checking for the IAM
> service-linked role, so the fleet request will fail at runtime
> with a permission error that the baseline does not anticipate.
> Does not emit the READY_TO_DEPLOY or PREREQUISITES_MISSING
> checklist format. Generated for with-skill-vs-baseline comparison.

---

To create a Spot Fleet:

```bash
aws ec2 request-spot-fleet \
  --spot-fleet-request-config '{
    "AllocationStrategy": "priceCapacityOptimized",
    "TargetCapacity": 10,
    "LaunchSpecifications": [{
      "InstanceType": "m5.large",
      "ImageId": "ami-0abc"
    }]
  }'
```

Check the console for the fleet status.
