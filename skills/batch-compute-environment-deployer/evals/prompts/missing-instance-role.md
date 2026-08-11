# Eval: missing-instance-role

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — no instance role specified; EC2 instances cannot register with ECS agent

## Prompt

Create an AWS Batch EC2 compute environment named batch-ec2-env
in us-east-1. BEST_FIT_PROGRESSIVE. Instance types m5.large,
m5.xlarge. No instance role specified. Min vCPUs 0, max 128.
Subnets subnet-aaa11122. Security group sg-batch111. Create job
queue my-queue priority 100.
