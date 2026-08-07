# Baseline (no-skill) response: lambda-service-role-scoped

This file captures what a generic assistant produces WITHOUT the
iam-role-deployer skill loaded — the contrast that proves the skill adds
structure (deterministic VERDICT, SourceArn/SourceAccount conditions,
least-privilege checklist, simulate-principal-policy verification).

---

Here's the IAM role for your Lambda function:

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

Permissions:
- Attach AWSLambdaBasicExecutionRole
- Add S3 read permission for the bucket
- Add DynamoDB write permission for the table

Commands:
1. aws iam create-role --role-name my-app-lambda-role --assume-role-policy-document file://trust.json
2. aws iam attach-role-policy --role-name my-app-lambda-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
3. aws iam put-role-policy --role-name my-app-lambda-role --policy-name app-permissions --policy-document file://perms.json

This should give your Lambda function the permissions it needs.
