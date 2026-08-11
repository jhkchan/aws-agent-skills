# Baseline (no-skill) — spot-placement-score

> This is the response a model produces **without** the skill
> definition. It does not know about Spot placement score API,
> does not configure On-Demand Capacity Reservations integration,
> uses instances count instead of vcpu for mixed types, and does
> not emit the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Here's a Spot Fleet with some On-Demand instances:

```bash
aws ec2 request-spot-fleet \
  --spot-fleet-request-config '{
    "AllocationStrategy": "lowestPrice",
    "TargetCapacity": 30,
    "OnDemandTargetCapacity": 5,
    "LaunchSpecifications": [
      { "InstanceType": "m5.large", "ImageId": "ami-0abc" },
      { "InstanceType": "c5.large", "ImageId": "ami-0abc" }
    ]
  }'
```

The fleet will use 5 On-Demand and 25 Spot.
