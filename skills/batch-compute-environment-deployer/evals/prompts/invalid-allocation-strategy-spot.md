# Eval: invalid-allocation-strategy-spot

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — BEST_FIT does not support spot; spot requires SPOT_CAPACITY_OPTIMIZED

## Prompt

Create an AWS Batch spot compute environment named batch-spot-env
in us-east-1 with BEST_FIT allocation strategy. Instance types
m5.large, m5.xlarge. Max vCPUs 500. Instance role
arn:aws:iam::123456789012:instance-profile/batch-instance-profile.
Spot fleet role
arn:aws:iam::123456789012:role/aws-service-role/spotfleet.amazonaws.com/AWSServiceRoleForEC2SpotFleet.
Subnets subnet-aaa11122. SG sg-batch111.
