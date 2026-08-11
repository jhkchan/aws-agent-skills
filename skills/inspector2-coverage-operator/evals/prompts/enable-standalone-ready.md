# Eval prompt: enable-standalone-ready

Plan the following Amazon Inspector v2 enablement and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, STATE, NOTES).

Operation: enable
Account: 111111111111
Region: us-east-1
Resource types: EC2, ECR, LAMBDA

```json
{
  "OrgConfig": {
    "describe-organization-configuration": {
      "autoEnable": {"ec2": false, "ecr": false, "lambda": false},
      "delegatedAdminAccountId": null,
      "maxAccountLimitReached": false
    },
    "batch-get-account-status.111111111111": {
      "ec2": "DISABLED",
      "ecr": "DISABLED",
      "lambda": "DISABLED"
    },
    "ec2.describe-instances": {
      "running_instances": 12
    },
    "ssm.describe-instance-information": {
      "online_instances": 12,
      "ping_status": "Online"
    },
    "ecr.describe-repositories": {
      "count": 4
    },
    "lambda.list-functions": {
      "count": 8,
      "runtimes": ["python3.12", "python3.12", "python3.12", "python3.12", "python3.12", "nodejs20.x", "nodejs20.x", "nodejs20.x"]
    },
    "caller_iam": {
      "role": "InspectorOperatorRole",
      "permissions": ["inspector2:Enable"]
    }
  }
}
```
