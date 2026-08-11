# Baseline (no-skill) response: spot-mip-capacity-rebalance-ready

This file captures what a generic assistant produces WITHOUT the
autoscaling-policy-deployer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, silent-failure awareness
for capacity rebalance on Spot-only ASGs, warm pool + rebalance race
warning, post-deploy verification commands).

---

Here's how to set up the Mixed Instances Policy and scaling:

```bash
# Update the ASG with Mixed Instances Policy
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name spot-worker-asg \
  --mixed-instances-policy '{
    "LaunchTemplate": {
      "LaunchTemplateSpecification": {"LaunchTemplateName": "worker-template", "Version": "2"},
      "Overrides": [{"InstanceType": "m5.large"}, {"InstanceType": "m5a.large"}, {"InstanceType": "m4.large"}]
    },
    "InstancesDistribution": {
      "OnDemandPercentageAboveBaseCapacity": 30,
      "OnDemandBaseCapacity": 1,
      "SpotAllocationStrategy": "capacity-optimized"
    }
  }'

# Enable capacity rebalance
aws autoscaling update-auto-scaling-group --auto-scaling-group-name spot-worker-asg --capacity-rebalance

# Warm pool
aws autoscaling put-warm-pool --auto-scaling-group-name spot-worker-asg --pool-state Stopped --min-size 2

# Target tracking
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name spot-worker-asg --policy-name cpu-target-60 \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{"PredefinedMetricSpecification":{"PredefinedMetricType":"ASGAverageCPUUtilization"},"TargetValue":60.0}'
```

This will give you a Spot-heavy ASG with rebalance and warm pool.
