# Baseline (no-skill) — request-lowest-price-burst

> This is the response a model produces **without** the skill
> definition. It uses lowestPrice without InstancePoolsToUseCount,
> omits the fleet type distinction (request vs maintain), does not
> explain that request fleets do not replace interrupted instances,
> and does not emit the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

Here's how to request a Spot Fleet for HPC:

```bash
aws ec2 request-spot-fleet \
  --spot-fleet-request-config '{
    "AllocationStrategy": "lowestPrice",
    "TargetCapacity": 50,
    "LaunchSpecifications": [
      { "InstanceType": "c5.large", "ImageId": "ami-0abc" },
      { "InstanceType": "c5a.large", "ImageId": "ami-0abc" }
    ]
  }'
```

Wait for the instances to launch.
