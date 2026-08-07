# Baseline (no-skill) response: service-role-missing-sourcearn

This file captures what a generic assistant produces WITHOUT the
iam-role-deployer skill loaded — the contrast that proves the skill flags
a Lambda trust policy without SourceArn/SourceAccount as an unscoped
lateral-movement vector (PREREQUISITES_MISSING) instead of proceeding.

---

Here's the shared Lambda role:

Trust policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

Permissions: S3 GetObject on sensitive-data bucket and DynamoDB Scan on
all tables.

Commands:
1. aws iam create-role --role-name shared-lambda-role --assume-role-policy-document file://trust.json
2. aws iam put-role-policy --role-name shared-lambda-role --policy-name app-perms --policy-document file://perms.json

Attach this role to your my-app-processor Lambda function and it will
have the S3 and DynamoDB permissions.
