# Eval prompt: spot-mip-capacity-rebalance-ready

Design a deployment plan for an Auto Scaling Group with Mixed Instances
Policy and scaling. Emit the standard VERDICT block (POLICY_SPEC,
VERDICT, CHECKLIST, VERIFICATION_COMMANDS).

Requirements:

- ASG name: spot-worker-asg
- ASG exists, multi-AZ across 3 AZs, EC2 health checks, Min=2
  Desired=4 Max=10
- Launch template: worker-template v2 (valid)
- Mixed Instances Policy with 3 instance type overrides:
  - m5.large
  - m5a.large
  - m4.large
- InstancesDistribution:
  - OnDemandPercentageAboveBaseCapacity: 30
  - OnDemandBaseCapacity: 1
  - SpotAllocationStrategy: capacity-optimized
- Capacity rebalance: enabled
- Warm pool: Stopped, min 2, ReuseOnScaleIn true
- Target tracking on ASGAverageCPUUtilization at target 60.0
- Region: us-east-1

Additional context: this is a Spot-heavy async worker pool. The team
previously lost capacity to Spot interruptions; capacity rebalance and
the warm pool are meant to absorb those events without cold starts.
