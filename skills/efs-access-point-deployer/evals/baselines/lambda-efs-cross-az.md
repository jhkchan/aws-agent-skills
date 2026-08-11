# Baseline (no-skill) — lambda-efs-cross-az

> This is the response a model produces **without** the skill definition.
> It applies the Lambda file-system config without flagging that the
> function's subnet in use1-az2 has no corresponding mount target —
> cold starts in that AZ will silently time out at the 50s EFS mount
> timeout with no error in the function's own metrics. Generated for
> with-skill-vs-baseline comparison.

---

To configure the Lambda function with EFS:

1. Update the function's VPC and file-system config:
```bash
aws lambda update-function-configuration \
  --function-name file-processor \
  --vpc-config SubnetIds=subnet-aaa,subnet-bbb,SecurityGroupIds=sg-efs \
  --file-system-configs Arn=arn:aws:elasticfilesystem:us-east-1:123456789012:access-point/fsap-9999aaaa2222,LocalMountPath=/mnt/efs
```

2. Verify the file-system config:
```bash
aws lambda get-function-configuration \
  --function-name file-processor \
  --query 'fileSystemConfigs'
```

The function will mount /mnt/efs in both subnets.
