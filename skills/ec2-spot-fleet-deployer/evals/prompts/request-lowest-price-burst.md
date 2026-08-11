# Eval: request-lowest-price-burst

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — request fleet (one-time), lowestPrice with InstancePoolsToUseCount 4, 4 types x 4 AZs, no replacement

## Prompt

I need a one-time Spot Fleet request for a burst HPC job in
us-east-1. Use lowestPrice with InstancePoolsToUseCount 4.
Target capacity 50 instances. Instance types: c5.large,
c5a.large, c5n.large, m5.large across us-east-1a, us-east-1b,
us-east-1c, us-east-1d. Fleet type request. Launch template
lt-hpc001 (version 1). IAM role
AWSServiceRoleForEC2SpotFleet exists. Account: 123456789012.
