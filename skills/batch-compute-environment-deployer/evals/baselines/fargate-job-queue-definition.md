# Baseline (without skill): fargate-job-queue-definition

The model provides a basic Fargate compute environment but:

1. Does not mention that Fargate requires subnets (not just any network config)
2. Does not address platform version LATEST vs 1.0.0 differences
3. Job definition missing retry strategy and timeout configuration
4. Does not mention Fargate max vCPU limits (currently 16 vCPUs per job)
5. No IAM execution role for the Fargate task (separate from EC2 instance role)
6. Missing propagateTags configuration for tag inheritance
