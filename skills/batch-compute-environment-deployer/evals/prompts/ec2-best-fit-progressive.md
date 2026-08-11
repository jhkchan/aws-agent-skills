# Eval: ec2-best-fit-progressive

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — EC2 compute environment, BEST_FIT_PROGRESSIVE, launch template, job queue with priority

## Prompt

Create an AWS Batch EC2 compute environment named batch-ec2-prod
in us-east-1. Use BEST_FIT_PROGRESSIVE allocation strategy.
Instance types: m5.large, m5.xlarge, m5.2xlarge. Instance role
arn:aws:iam::123456789012:instance-profile/batch-instance-profile.
Launch template batch-custom-lt. Min vCPUs 0, max 256, desired 0.
Subnets subnet-aaa11122, subnet-bbb22233. Security group
sg-batch111. Create a job queue production-queue with priority 500
referencing this compute environment. Tags: Environment=production.
