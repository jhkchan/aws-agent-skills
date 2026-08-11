# Eval: capacity-rebalance-enabled

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — maintain fleet, capacityOptimized, GPU instances, capacity rebalance with launch, 100 vcpu target

## Prompt

Create a maintain Spot Fleet for ML training in us-east-1.
Use capacityOptimized allocation strategy. Target capacity
100 vcpu. Instance types: g4dn.xlarge, g4dn.2xlarge across
us-east-1a, us-east-1b, us-east-1c. Enable capacity rebalance
with launch replacement. InstanceInterruptionBehavior
terminate. Launch template lt-ml-training (version 2). IAM
service role AWSServiceRoleForEC2SpotFleet verified. Tags:
Workload=ml-training. Account: 123456789012.
