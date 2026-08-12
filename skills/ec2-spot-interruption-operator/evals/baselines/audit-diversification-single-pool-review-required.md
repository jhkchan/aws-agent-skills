# Baseline (no-skill) response: audit-diversification-single-pool-review-required

This file captures what a generic assistant produces WITHOUT the
ec2-spot-interruption-operator skill loaded.

---

Your Spot Fleet sfr-single-tenant-jobs has limited diversification. It
only uses the c5 instance family across 2 AZs, which increases the risk
of interruptions. The fleet is also only fulfilling 12 out of 20 target
capacity.

To improve diversification, add more instance families (like m5, c6g)
and more AZs (like us-east-1c). You should also consider switching from
the lowest-price allocation strategy to capacity-optimized:

```bash
aws ec2 modify-spot-fleet-request \
  --spot-fleet-request-id sfr-single-tenant-jobs \
  --target-capacity 20
```

The high interruption count (38 in 30 days) suggests the current
configuration is not resilient enough.
