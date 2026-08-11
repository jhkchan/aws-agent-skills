# Baseline (without skill): missing-instance-role

The model does not flag the missing instance role:

1. Proceeds with compute environment creation without an instance role
2. Does NOT identify that EC2 instances need an instance profile to register with the ECS agent
3. Does not mention that Batch-managed instances require ecsInstanceRole with AmazonEC2ContainerServiceforEC2Role policy
4. No mention that without the instance role, compute environment will be VALID but jobs will fail at container provisioning
