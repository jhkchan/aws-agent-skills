# Allocation Strategies & Instance Selection

## Strategy Comparison

| Strategy | Type | Description | Spot Support |
|---|---|---|---|
| BEST_FIT | EC2 | Picks the cheapest instance that fits, does not scale out | No |
| BEST_FIT_PROGRESSIVE | EC2 | Picks additional instance types beyond the cheapest to fulfill capacity | Yes |
| SPOT_CAPACITY_OPTIMIZED | EC2 | Picks spot instances from pools with lowest interruption risk | Yes |

## BEST_FIT_PROGRESSIVE Deep Dive
- Steps up instance types by price when the cheapest is unavailable
- Ideal for heterogeneous pools (m5 + c5 + r5)
- Supports launch template overrides for custom AMIs
- Min vCPUs should be 0 for cost scaling; max caps spend

## SPOT_CAPACITY_OPTIMIZED
- Uses Spot Placement Score internally to select interruption-resistant pools
- Requires spot fleet role: `arn:aws:iam::<acct>:role/aws-service-role/spotfleet.amazonaws.com/AWSServiceRoleForEC2SpotFleet`
- Always pair with an On-Demand fallback CE in the same job queue
- Fallback CE order determines priority (order 1 = primary)

## Instance Role Requirements
- EC2 CEs require an instance profile with `AmazonEC2ContainerServiceforEC2Role`
- The instance role is what allows ECS agent registration on Batch-managed instances
- Fargate CEs do NOT need an instance role (execution role instead)
