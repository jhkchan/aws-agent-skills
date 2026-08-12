# Baseline (no-skill) response: tune-strategy-lowest-price-review-required

This file captures what a generic assistant produces WITHOUT the
ec2-spot-interruption-operator skill loaded.

---

To change the Spot Fleet allocation strategy from lowest-price to
capacity-optimized and add more instance types, run:

```bash
aws ec2 modify-spot-fleet-request \
  --spot-fleet-request-id sfr-batch-prod \
  --target-capacity 50 \
  --launch-template-configs '[{
    "LaunchTemplateSpecification": {
      "LaunchTemplateId": "lt-batch-prod",
      "Version": "2"
    },
    "Overrides": [
      {"InstanceType": "c5.large", "AvailabilityZone": "us-east-1a"},
      {"InstanceType": "c5.large", "AvailabilityZone": "us-east-1b"},
      {"InstanceType": "c5.large", "AvailabilityZone": "us-east-1c"},
      {"InstanceType": "m5.large", "AvailabilityZone": "us-east-1a"},
      {"InstanceType": "m5.large", "AvailabilityZone": "us-east-1b"},
      {"InstanceType": "m5.large", "AvailabilityZone": "us-east-1c"},
      {"InstanceType": "c6g.large", "AvailabilityZone": "us-east-1a"},
      {"InstanceType": "c6g.large", "AvailabilityZone": "us-east-1b"},
      {"InstanceType": "c6g.large", "AvailabilityZone": "us-east-1c"}
    ]
  }]'
```

This should help reduce interruptions. Make sure your application works
on arm64 (Graviton) instances.
