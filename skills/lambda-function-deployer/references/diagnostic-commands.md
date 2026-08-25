# Diagnostic and verification commands — lambda-function-deployer

> Content moved verbatim from SKILL.md during progressive-disclosure
> restructuring. Load on demand.

## Step 13: verification commands (moved from SKILL.md)

```bash
# Function configuration
aws lambda get-function-configuration --function-name <name>

# Execution role policy
aws iam list-attached-role-policies --role-name <role>
aws iam list-inline-role-policies --role-name <role>

# VPC config (if applicable)
aws lambda get-function-configuration --function-name <name> --query 'VpcConfig'

# Event invoke config (destinations)
aws lambda get-function-event-invoke-config --function-name <name>

# Concurrency
aws lambda get-function-concurrency --function-name <name>
aws lambda get-provisioned-concurrency-config --function-name <name> --qualifier <alias>

# Layers
aws lambda get-function-configuration --function-name <name> --query 'Layers'

# Code signing config
aws lambda get-function-code-signing-config --function-name <name>

# Log group retention
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/<name>

# Test invocation
aws lambda invoke --function-name <name> --payload '{}' /tmp/response.json
cat /tmp/response.json
```

## Pre-flight safety checks (moved from SKILL.md)

- **Confirm the function name is available:**
  `aws lambda get-function-configuration --function-name <name>` — if it
  returns 200, confirm whether you intend to update an existing function
  vs create new.

- **Confirm the execution role exists and has the correct trust policy:**
  ```bash
  aws iam get-role --role-name <role> --query 'Role.AssumeRolePolicyDocument'
  ```
  The trust policy MUST include `"Service": "lambda.amazonaws.com"` with
  `"Action": "sts:AssumeRole"`. Without this, the function creation
  fails with `InvalidParameterValueException`.

- **Confirm the caller has `iam:PassRole` on the execution role.**
  `CreateFunction` requires `iam:PassRole` to attach the role. A missing
  `iam:PassRole` permission causes `AccessDeniedException`.

- **For VPC functions, confirm subnets are private and span multiple AZs:**
  ```bash
  aws ec2 describe-subnets --subnet-ids subnet-aaa subnet-bbb \
    --query 'Subnets[].{AZ:AvailabilityZone,Public:MapPublicIpOnLaunch}'
  ```
  All subnets should be private (`MapPublicIpOnLaunch: false`) and span
  at least 2 AZs.

- **For ECR functions, confirm the image exists:**
  ```bash
  aws ecr describe-images --repository-name <repo> --image-ids imageTag=latest
  ```

- **For code-signed functions, confirm the signing profile is active:**
  ```bash
  aws signer get-signing-profile --profile-name <profile>
  ```

- **Pre-create the CloudWatch log group with retention BEFORE the first
  invocation** to avoid unbounded log accumulation:
  ```bash
  aws logs create-log-group --log-group-name /aws/lambda/<name>
  aws logs put-retention-policy --log-group-name /aws/lambda/<name> --retention-in-days 30
  ```

- **For existing functions, capture current configuration for rollback:**
  ```bash
  aws lambda get-function-configuration --function-name <name> --output json > /tmp/<name>-config-backup.json
  aws lambda get-function-code-signing-config --function-name <name> --output json > /tmp/<name>-signing-backup.json
  ```

