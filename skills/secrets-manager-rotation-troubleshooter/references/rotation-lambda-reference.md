# Rotation Lambda Reference Guide

Supplementary reference for the Secrets Manager Rotation
Troubleshooter skill. Loaded on-demand when a diagnostic needs
rotation Lambda internals, the four-step protocol contract, Lambda
configuration defaults, or CloudTrail lookup patterns for rotation
APIs.

## Rotation Lambda protocol contract

Secrets Manager invokes the rotation Lambda with an event payload
containing a `ClientRequestToken` (the version ID that will become
`AWSCURRENT`) and a `step` parameter. The Lambda's handler switches
on `step`:

```python
def lambda_handler(event, context):
    arn = event['SecretId']
    token = event['ClientRequestToken']
    step = event['Step']

    if step == 'createSecret':
        create_secret(arn, token)
    elif step == 'setSecret':
        set_secret(arn, token)
    elif step == 'testSecret':
        test_secret(arn, token)
    elif step == 'finishSecret':
        finish_secret(arn, token)
    else:
        raise ValueError("Invalid step")
```

### Step semantics

| Step | Action | Failure layer if it fails |
|---|---|---|
| `createSecret` | Generate a new secret value; stage it as `AWSPENDING` via `PutSecretValue`. Reads the Master Secret to obtain the DB superuser credential. | `PERMISSION_ROTATION_ROLE`, `KMS_DECRYPT_ROLE`, `MASTER_SECRET_MISCONFIGURED` |
| `setSecret` | Apply the new credential to the database (`ALTER USER`, `CREATE USER`, or `CREATE LOGIN`). Connects to the DB using the Master Secret's credential. | `ROTATION_LAMBDA_VPC`, `ROTATION_LAMBDA_DB_ENDPOINT`, `ROTATION_LAMBDA_DB_CREDENTIAL`, `SUPERUSER_INSUFFICIENT`, `STRATEGY_CONFLICT` |
| `testSecret` | Connect to the DB with the new credential; verify it works. Optional rollback path on failure. | `ROTATION_LAMBDA_DB_ENDPOINT` (wrong connection string), `PREVIOUS_CREDENTIAL_NOT_STORED` (rollback fails) |
| `finishSecret` | Move `AWSCURRENT` to the new version; demote the prior version to `AWSPREVIOUS`. Calls `UpdateSecretVersionStage`. | `ROTATION_TOKEN_MISSING`, AWS-side (ESCALATE) |

Secrets Manager invokes the Lambda once per step (four invocations
per rotation cycle). Each invocation is a separate Lambda execution
with its own CloudWatch log stream. Read the most recent four log
streams in chronological order to follow a full rotation cycle.

### Recovery from a failed mid-protocol rotation

If the Lambda throws during `setSecret` or `testSecret`, the new
version remains in `AWSPENDING`. The next rotation invocation will
attempt to recover:

1. Secrets Manager calls `createSecret` again. The Lambda checks if
   `AWSPENDING` already exists for the token; if so, it skips
   generation.
2. The Lambda retries `setSecret` (the typical failure point).
3. If `setSecret` succeeds, the protocol continues to `testSecret`
   and `finishSecret`.

A version stuck in `AWSPENDING` for more than one schedule interval
indicates the recovery is also failing. Read the Lambda logs to find
the failing step.

## Rotation Lambda default configuration

| Property | Default | Notes |
|---|---|---|
| Timeout | 3 seconds | AWS-managed rotation templates override this to 30s at deploy time. Custom Lambdas may inherit the default. |
| MemorySize | 256 MB | Adequate for the AWS-managed templates; raise for custom templates that load heavy DB drivers. |
| Runtime | python3.12 (current) | Older templates may use python3.9 or python3.10; verify the runtime is not deprecated. |
| VpcConfig | (none) | Must be set to the database's subnets if the DB is in a VPC. |
| Environment.Variables | engine-specific | `SECRETS_MANAGER_SECRET_ID`, `SECRETS_MANAGER_MASTER_ID`, `ROTATION_STRATEGY` (or `SECRETS_MANAGER_ROTATION_TYPE`). |

## CloudTrail lookup patterns for rotation failures

```bash
# Find the most recent RotateSecret invocation by Secrets Manager
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=RotateSecret \
  --start-time $(date -u -v-1H +%s) --end-time $(date -u +%s) \
  --output json | \
  jq '.Events[] | select(.CloudTrailEvent | contains("<secret-arn>"))'

# Find GetSecretValue AccessDenied events for the rotation role
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetSecretValue \
  --start-time $(date -u -v-1H +%s) --end-time $(date -u +%s) \
  --output json | \
  jq '.Events[] | select(.CloudTrailEvent | contains("<rotation-role-name>"))'

# Find PutSecretValue failures (finishSecret step)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutSecretValue \
  --start-time $(date -u -v-24H +%s) --end-time $(date -u +%s) \
  --output json | \
  jq '.Events[] | select(.CloudTrailEvent | contains("<secret-arn>")) | select(.CloudTrailEvent | contains("errorCode"))'
```

The CloudTrail event contains:

- `eventName`: the API called (`RotateSecret`, `GetSecretValue`,
  `PutSecretValue`, `UpdateSecretVersionStage`).
- `errorMessage` / `errorCode`: the denial reason
  (`AccessDenied`, `ResourceNotFoundException`).
- `requestParameters.secretId` / `secretId`: the secret ARN.
- `requestParameters.versionStage`: `AWSCURRENT`, `AWSPENDING`,
  `AWSPREVIOUS`.
- `sourceIPAddress`: the Lambda ENI IP (useful for SG / endpoint
  policy diagnosis).
- `userIdentity.sessionContext.sessionIssuer.arn`: the rotation role
  ARN — critical for cross-account diagnosis.

## Lambda execution role minimum policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:DescribeSecret",
        "secretsmanager:GetSecretValue",
        "secretsmanager:PutSecretValue",
        "secretsmanager:UpdateSecretVersionStage"
      ],
      "Resource": [
        "<rotating-secret-arn>",
        "<master-secret-arn>"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt"],
      "Resource": ["<cmk-arn-if-customer-managed>"],
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "secretsmanager.<region>.amazonaws.com"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/<rotation-lambda>*"
    }
  ]
}
```

Notes:
- `kms:Decrypt` is needed ONLY if the secret uses a customer-managed
  CMK. The default `aws/secretsmanager` key decrypts transparently.
- For NetworkManager / VPC-attached Lambdas, the role also needs
  `ec2:CreateNetworkInterface`, `ec2:DeleteNetworkInterface`,
  `ec2:DescribeNetworkInterfaces` (typically via the
  `AWSLambdaVPCAccessExecutionRole` managed policy).
- For cross-account rotation, the secret's resource-based policy (in
  the owning account) must also list the rotation role ARN.

## Secrets Manager API summary for rotation

| API | Purpose | Cost unit |
|---|---|---|
| `RotateSecret` | Triggers an immediate rotation; injects `ClientRequestToken` | per API call |
| `CancelRotateSecret` | Cancels a rotation in progress (rarely needed) | per API call |
| `DescribeSecret` | Returns rotation config, `LastRotatedDate`, `VersionIdsToStages` | per API call |
| `GetSecretValue` | Returns the secret value (decrypted) | per API call + per-secret monthly |
| `PutSecretValue` | Stages a new version (used by `createSecret`) | per API call |
| `UpdateSecretVersionStage` | Moves staging labels (used by `finishSecret`) | per API call |
| `GetResourcePolicy` | Returns the resource-based policy | per API call |
| `PutResourcePolicy` | Sets the resource-based policy (cross-account grants) | per API call |
| `ReplicateSecretToRegions` | Creates / updates a multi-region replica | per API call |

## EventBridge rule template for rotation

```bash
# Create the rule
aws events put-rule \
  --name SecretsManager-<secret-keyword> \
  --schedule-expression "rate(1d)" \
  --state ENABLED \
  --profile <p>

# Add the rotation Lambda as target (the Input must include SecretId)
cat > /tmp/targets.json <<EOF
[{
  "Id": "1",
  "Arn": "<rotation-lambda-arn>",
  "Input": "{\"SecretId\":\"<secret-arn>\"}"
}]
EOF
aws events put-targets \
  --rule SecretsManager-<secret-keyword> \
  --targets file:///tmp/targets.json --profile <p>

# Grant EventBridge permission to invoke the Lambda
aws lambda add-permission \
  --function-name <rotation-lambda-name> \
  --statement-id EventBridgeInvoke-<secret-keyword> \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:<region>:<account>:rule/SecretsManager-<secret-keyword> \
  --profile <p>
```

Verify the rule is firing:

```bash
aws events describe-rule --name SecretsManager-<secret-keyword> \
  --query '{State, ScheduleExpression, LastTriggered: Arn}' --output json

# Triggered invocations appear in the Lambda's CloudWatch metrics
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=<rotation-lambda-name> \
  --start-time $(date -u -v-24H +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Sum --output json
```

## KMS key matrix for Secrets Manager

| KmsKeyId | Rotation role needs `kms:Decrypt`? |
|---|---|
| `alias/aws/secretsmanager` (default, AWS-managed) | No — Secrets Manager decrypts transparently using the service-managed key. |
| Customer-managed CMK | Yes — `kms:Decrypt` on the CMK ARN; the CMK's key policy must also grant the Secrets Manager service principal and the rotation role. |

When migrating from AWS-managed to customer-managed CMK, the rotation
role MUST get `kms:Decrypt` BEFORE the KmsKeyId update. Otherwise
every rotation fails at `createSecret` with `AccessDeniedException`
on `kms:Decrypt`.

## AWS Health event categories that affect Secrets Manager rotation

| Category | Likely impact |
|---|---|
| `AWS_SECRETS_MANAGER` | Region-wide Secrets Manager degradation; rotation API calls fail. |
| `AWS_LAMBDA_SERVICE` | Rotation Lambda invocations fail; rotation cannot proceed. |
| `AWS_KMS` | Secrets encrypted with a customer-managed CMK fail to decrypt; rotation fails at `createSecret`. |
| `AWS_RDS` / `AWS_REDSHIFT` | Database unavailable; rotation fails at `setSecret`. |
| `AWS_EVENTBRIDGE` | Schedule rules do not fire; rotation does not trigger. |

Always probe `aws health describe-events` for regional issues before
declaring a customer-side root cause during a wide-impact incident.
