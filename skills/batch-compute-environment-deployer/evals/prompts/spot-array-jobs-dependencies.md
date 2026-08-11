# Eval: spot-array-jobs-dependencies

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — spot CE with SPOT_CAPACITY_OPTIMIZED, On-Demand fallback, dual-CE job queue, array job with sequential dependency

## Prompt

Create a spot Batch compute environment batch-spot-env in
us-east-1 with SPOT_CAPACITY_OPTIMIZED. Instance types m5.large,
m5.xlarge, c5.large, c5.xlarge. Max vCPUs 1000. Spot fleet role
arn:aws:iam::123456789012:role/aws-service-role/spotfleet.amazonaws.com/AWSServiceRoleForEC2SpotFleet.
Also create an On-Demand fallback batch-ondemand-env with
BEST_FIT_PROGRESSIVE, max vCPUs 200. Create job queue
production-queue priority 500 referencing spot (order 1) and
ondemand (order 2). Submit an array job of size 100 with
sequential dependency on a preceding ingest job. Instance role
arn:aws:iam::123456789012:instance-profile/batch-instance-profile.
Subnets subnet-aaa11122, subnet-bbb22233. SG sg-batch111.
