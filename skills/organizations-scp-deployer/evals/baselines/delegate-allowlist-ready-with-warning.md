# Baseline (no-skill) response: delegate-allowlist-ready-with-warning

This file captures what a generic assistant produces WITHOUT the
organizations-scp-deployer skill loaded.

---

To use an allowlist strategy, create an SCP with the approved
services and attach it to the root, then detach FullAWSAccess:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*", "s3:*", "rds:*", "lambda:*", "iam:*", "logs:*",
        "kms:*", "dynamodb:*", "sns:*", "sqs:*", "sts:*",
        "secretsmanager:*", "ssm:*", "efs:*"
      ],
      "Resource": "*"
    }
  ]
}
```

```bash
aws organizations create-policy --content file://scp.json \
  --name allowlist-approved-services --type SERVICE_CONTROL_POLICY
aws organizations attach-policy --policy-id <id> --target-id r-abc1
aws organizations detach-policy --policy-id <FullAWSAccess-id> \
  --target-id r-abc1
```
