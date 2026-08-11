# Eval: maintain-price-capacity-optimized

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — maintain fleet, priceCapacityOptimized, 3 types x 3 AZs, capacity rebalance with launch, IAM role verified

## Prompt

Create a maintain Spot Fleet in us-east-1 with
priceCapacityOptimized allocation strategy. Target capacity
20 vcpu. Instance types: m5.large, m5a.large, c5.large across
us-east-1a, us-east-1b, us-east-1c. Enable capacity rebalance
with launch replacement strategy. InstanceInterruptionBehavior
terminate. Launch template lt-0abc123 (version 1). IAM role
AWSServiceRoleForEC2SpotFleet exists. Tags:
Environment=production, Service=batch-processing. Account ID:
123456789012.
