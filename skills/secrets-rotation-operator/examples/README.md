# End-to-end usage scenario: secrets-rotation-operator

A walkthrough showing the skill planning an enable-rotation operation on
an RDS PostgreSQL secret, with all pre-checks passing and the operator
confirming at the CONFIRM gate. Contrasted with the BLOCKED case where
reserved concurrency = 0 silently disables the rotation Lambda.

## Input (user prompt)

> We have an RDS PostgreSQL secret `prod/payments-db-credentials` and we
> want to enable rotation. The Lambda
> `SecretsManagerRDSPostgreSQLRotation` is already deployed. Schedule
> every 30 days. Rotate immediately to verify.

```json
{
  "Operation": "enable-rotation",
  "Secret": "prod/payments-db-credentials",
  "RotationLambda": "arn:aws:lambda:us-east-1:111111111111:function:SecretsManagerRDSPostgreSQLRotation",
  "Schedule": "AutomaticallyAfterDays=30",
  "RotateImmediately": true,
  "SecretMetadata": {
    "RotationEnabled": false,
    "KmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/payments-cmk",
    "OwningService": "rds"
  },
  "LambdaMetadata": {
    "State": "Active",
    "Timeout": 30,
    "ReservedConcurrentExecutions": 5,
    "VpcConfig": {
      "SubnetIds": ["subnet-aaa", "subnet-bbb"],
      "SecurityGroupIds": ["sg-lambda-rotation"]
    }
  },
  "LambdaResourcePolicy": {
    "Allows": "Principal: secretsmanager.amazonaws.com, Action: lambda:InvokeFunction"
  },
  "IamRolePolicies": [
    "SecretsManagerRotation",
    "AWSLambdaVPCAccessExecutionRole",
    "rds-db:connect on arn:aws:rds-db:us-east-1:111111111111:dbuser:db-ABCDEFGHIJKLMNOP/postgres",
    "kms:Decrypt on arn:aws:kms:us-east-1:111111111111:key/payments-cmk"
  ],
  "NetworkChecks": {
    "DbSgIngress": "sg-rds-prod allows sg-lambda-rotation on port 5432",
    "Routing": "OK"
  }
}
```

## Skill output

```text
OPERATION: enable-rotation
VERDICT: READY
TARGET: prod/payments-db-credentials (rotation Lambda:
        arn:aws:lambda:us-east-1:111111111111:function:SecretsManagerRDSPostgreSQLRotation)
PRE_CHECKS:
  - [PASS] Secret exists, not in recovery window, not a replica
  - [PASS] Rotation Lambda State: Active (python3.12, timeout 30s)
  - [PASS] Lambda resource-based policy allows lambda:InvokeFunction
    from secretsmanager.amazonaws.com
  - [PASS] Reserved concurrency: 5 (>= 1)
  - [PASS] Execution role has SecretsManagerRotation policy
  - [PASS] Execution role has AWSLambdaVPCAccessExecutionRole for VPC ENI
  - [PASS] Execution role has rds-db:connect on
    arn:aws:rds-db:us-east-1:111111111111:dbuser:db-ABCDEFGHIJKLMNOP/postgres
  - [PASS] KMS key arn:aws:kms:us-east-1:111111111111:key/payments-cmk
    Enabled; policy grants Lambda role kms:Decrypt
  - [PASS] Lambda VpcConfig subnets route to DB subnets
  - [PASS] DB security group sg-rds-prod allows ingress from
    sg-lambda-rotation on port 5432
  - [PASS] RotationRules.AutomaticallyAfterDays: 30 (in [1, 365])
STEPS:
  1. CONFIRM: About to enable rotation on prod/payments-db-credentials
     with Lambda SecretsManagerRDSPostgreSQLRotation, schedule every 30
     days, in account 111111111111 region us-east-1. This will trigger
     an IMMEDIATE rotation (Secrets Manager rotates once when rotation
     is enabled). Proceed? (yes/no)
  2. aws secretsmanager rotate-secret \
       --secret-id prod/payments-db-credentials \
       --rotation-lambda-arn arn:aws:lambda:us-east-1:111111111111:function:SecretsManagerRDSPostgreSQLRotation \
       --rotation-rules AutomaticallyAfterDays=30
  3. aws logs tail /aws/lambda/SecretsManagerRDSPostgreSQLRotation \
       --follow --since 2m
POST_VERIFY:
  - (pending execution)
  - aws secretsmanager describe-secret --secret-id \
      prod/payments-db-credentials → LastRotatedDate advanced to ~now
  - aws secretsmanager list-secret-version-ids --secret-id \
      prod/payments-db-credentials → no version in AWSPENDING
  - Application login with new AWSCURRENT credential: success
NOTES:
  - Secrets Manager triggers the FIRST rotation immediately when you call
    rotate-secret with --rotation-lambda-arn. Watch the four steps
    (createSecret, setSecret, testSecret, finishSecret) complete in
    CloudWatch before relying on the schedule.
  - Set up a CloudWatch alarm on the RotationFailed metric:
    aws cloudwatch put-metric-alarm \
      --alarm-name payments-rotation-failed \
      --metric-name RotationFailed --namespace AWS/SecretsManager \
      --dimensions Name=SecretId,Value=prod/payments-db-credentials \
      --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold \
      --period 300 --evaluation-periods 1
```

## Contrast — BLOCKED case (reserved concurrency = 0)

If the operator had specified a Lambda with
`ReservedConcurrentExecutions: 0`, the pre-check gate would fire and no
CLI would execute:

```text
OPERATION: trigger-rotation
VERDICT: BLOCKED
TARGET: prod/orders-service-token (rotation Lambda:
        arn:aws:lambda:us-east-1:111111111111:function:OrdersServiceTokenRotation)
PRE_CHECKS:
  - [PASS] Secret exists, RotationEnabled: true
  - [PASS] Lambda State: Active
  - [PASS] No version stuck in AWSPENDING
  - [FAIL] ReservedConcurrentExecutions: 0 — Lambda is functionally
    disabled. Every invocation is throttled. CloudWatch shows Throttles
    metric spikes at the scheduled rotation time, but no error logs
    (the invocation never runs). This is the stealth failure mode.
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
NOTES:
  - Root cause: Lambda reserved concurrency is 0. The Lambda appears
    Active in every status check, but Secrets Manager's rotation
    trigger is throttled on every scheduled rotation.
  - Fix: set reserved concurrency to at least 1, then trigger a manual
    rotation to verify:
    aws lambda put-function-concurrency \
      --function-name OrdersServiceTokenRotation \
      --reserved-concurrent-executions 5
    aws secretsmanager rotate-secret --secret-id prod/orders-service-token
  - After the fix, verify LastRotatedDate advances:
    aws secretsmanager describe-secret --secret-id prod/orders-service-token \
      --query 'LastRotatedDate'
```

## What the skill caught that a generic assistant misses

1. **Pre-check gate before any CLI executes.** A generic assistant emits
   the rotate-secret command directly. The skill runs deterministic
   pre-checks (Lambda state, role policy chain, KMS, VPC reachability,
   reserved concurrency) and BLOCKS before triggering a rotation that
   would silently fail.

2. **Stealth throttle detection.** A generic assistant looks at Lambda
   `State: Active` and concludes the Lambda is healthy. The skill checks
   `get-function-concurrency` separately — reserved concurrency = 0 is a
   stealth kill switch that produces no error logs.

3. **The four-step rotation contract.** A generic assistant says "trigger
   rotation and verify." The skill names each step (createSecret,
   setSecret, testSecret, finishSecret) so the operator knows what to
   watch for in CloudWatch Logs.

4. **Immediate-rotation warning.** A generic assistant omits that calling
   `rotate-secret --rotation-lambda-arn` triggers the FIRST rotation
   immediately. The skill surfaces this so the operator is ready to
   watch the Lambda logs.

5. **CloudWatch alarm recommendation.** A generic assistant omits
   ongoing monitoring. The skill emits the `RotationFailed` metric alarm
   as a post-verification step.

6. **Stuck AWSPENDING awareness.** A generic assistant omits what to do
   if the rotation partially completes. The skill references the
   recover-pending operation for the next failure mode.

7. **Cross-account policy pair.** A generic assistant omits the
   cross-account pattern (Lambda resource policy + secret resource
   policy + KMS key policy). The skill surfaces all three sides of the
   grant for cross-account setups.

## Slash-command invocation

```
/aws:operate-secrets-rotation
```

Or via the orchestrator:

```
/aws:pipeline
You: "enable rotation on prod/payments-db-credentials"
```

The orchestrator emits
`[Phase: Operate | Skills routed: secrets-rotation-operator]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "enable rotation on prod/payments-db-credentials"
# [Phase: Operate | Skills routed: secrets-rotation-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the rotation completes:

```bash
# Verify the new version is AWSCURRENT and no AWSPENDING remains
aws secretsmanager describe-secret --secret-id prod/payments-db-credentials \
  --profile default \
  --query '{LastRotated:LastRotatedDate,Versions:VersionIdsToStages}'

# Confirm application can connect with the new credential
PGPASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id prod/payments-db-credentials \
  --version-stage AWSCURRENT --query SecretString --output text \
  --profile default | jq -r .password) \
  psql -h <db-host> -p 5432 -U postgres -d payments \
  -c "SELECT 1;"

# Set up rotation-failure alarm
aws cloudwatch put-metric-alarm \
  --alarm-name payments-rotation-failed \
  --metric-name RotationFailed \
  --namespace AWS/SecretsManager \
  --dimensions Name=SecretId,Value=prod/payments-db-credentials \
  --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold \
  --period 300 --evaluation-periods 1 \
  --profile default
```
