# Secrets Manager Rotation Diagnostic Procedures Reference

Load this reference when diagnosing a failed rotation. The procedures
below are the canonical sequences for each symptom archetype, with the
read-only diagnostic commands and the CLI to fix each root cause.

## Decision tree — which diagnostic archetype

| Symptom | Use | Why |
|---|---|---|
| `RotationEnabled: true` but `LastRotatedDate` null > 1 interval | **Never-rotated** | Every rotation silently failing; investigate Lambda |
| `LastRotatedDate` overdue > 1 interval | **Intermittent failure** | Some rotations succeed, some fail |
| Version stuck in `AWSPENDING` | **Stuck rotation** | setSecret/testSecret failed mid-flight; recover the pending version |
| `LastChangedDate` more recent than `LastRotatedDate` | **Out-of-band edit** | Credential manually changed; next rotation will fail |
| CloudWatch shows `Throttles` spike, no error logs | **Stealth throttle** | Reserved concurrency = 0 or account pool exhausted |
| CloudWatch shows `AccessDeniedException` | **Permission gap** | Lambda role or key policy missing a grant |
| CloudWatch shows `Task timed out` | **Timeout** | Increase timeout; database rotation needs >= 30s |
| Replica secret in error state | **Replica sync failure** | Primary rotation succeeded but replica did not sync |
| Rotation enabled on a `DeletedDate` secret | **Recovery-window** | Secret about to be purged; restore first |

## Procedure: Never-rotated secret

**Symptom:** `RotationEnabled: true` AND `LastRotatedDate: null` AND
rotation has been enabled for > 1 `AutomaticallyAfterDays` interval.

**Diagnostics:**

```bash
# 1. Confirm rotation config
aws secretsmanager describe-secret --secret-id <name> \
  --query '{RotationEnabled:RotationEnabled,Lambda:RotationLambdaARN,
            Rules:RotationRules,LastRotated:LastRotatedDate,
            LastChanged:LastChangedDate,Next:NextRotationDate}'

# 2. Check Lambda state (if RotationLambdaARN is set)
aws lambda get-function-configuration \
  --function-name <lambda> \
  --query '{State:State,Timeout:Timeout,Role:Role,
            Reserved:ReservedConcurrentExecutions}'

# 3. Check reserved concurrency (separate API call)
aws lambda get-function-concurrency --function-name <lambda>

# 4. Check Lambda resource-based policy (does Secrets Manager have invoke?)
aws lambda get-policy --function-name <lambda>

# 5. Check the last invocations and their results
aws logs filter-log-events \
  --log-group-name /aws/lambda/<lambda> \
  --filter-pattern ERROR \
  --limit 20 \
  --start-time $(($(date +%s) - 86400 * 30))000

# 6. Check CloudWatch metrics for Throttles
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions Name=FunctionName,Value=<lambda> \
  --start-time $(date -u -v-30d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Sum
```

**Common findings and fixes:**

| Finding | Fix |
|---|---|
| `RotationLambdaARN: null` | Re-run `rotate-secret --rotation-lambda-arn <arn> --rotation-rules ...` |
| Lambda `State: Deleted` or `ResourceNotFoundException` | Recreate the Lambda from the managed template, then `rotate-secret --rotation-lambda-arn <new-arn>` |
| Lambda `State: Inactive` (container image with deleted base, or deployment package removed) | Redeploy the function code |
| `ReservedConcurrentExecutions: 0` | `put-function-concurrency --reserved-concurrent-executions 1` |
| Resource-based policy missing `secretsmanager.amazonaws.com` | `lambda add-permission --principal secretsmanager.amazonaws.com --action lambda:InvokeFunction --source-arn <secret-arn>` |
| `RotationRules.AutomaticallyAfterDays > 365` (invalid) | `rotate-secret --rotation-rules AutomaticallyAfterDays=30` |
| No log entries at all (Lambda never invoked) | Resource-based policy missing; or the EventBridge schedule is misconfigured. Fix the resource policy first. |

## Procedure: Intermittent rotation failure

**Symptom:** `LastRotatedDate` is set but overdue > 1 interval. The
Lambda sometimes succeeds, sometimes fails.

**Diagnostics:**

```bash
# 1. Recent invocation errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/<lambda> \
  --filter-pattern ERROR \
  --start-time $(($(date +%s) - 86400 * 14))000 \
  --limit 50

# 2. Check Lambda timeout
aws lambda get-function-configuration \
  --function-name <lambda> --query 'Timeout'

# 3. Check target resource state (RDS example)
aws rds describe-db-instances --db-instance-identifier <id> \
  --query 'DBInstances[0].{Status:DBInstanceStatus,
            Class:DBInstanceClass,Engine:Engine}'

# 4. Check VPC reachability
aws ec2 describe-security-groups \
  --group-ids <lambda-sg> \
  --query 'SecurityGroups[0].IpPermissions'
aws ec2 describe-security-groups \
  --group-ids <db-sg> \
  --query 'SecurityGroups[0].IpPermissions'

# 5. Check Secrets Manager RotationFailed events in CloudWatch
aws logs filter-log-events \
  --log-group-name /aws/secretsmanager/<name> \
  --filter-pattern "Rotation Failed" \
  --start-time $(($(date +%s) - 86400 * 14))000 \
  --limit 20
```

**Common findings:**

| Finding | Fix |
|---|---|
| Intermittent `Task timed out after 30 seconds` on a busy DB | Increase timeout to 60s; investigate DB slowness |
| Intermittent `ConnectionRefused` on Aurora failover | Lambda retries within the 24h window; if failover takes longer, rotation is missed. Increase timeout. |
| `OperationalError: too many connections` | Lambda connection pool exhaustion. Set a connection limit; the rotation only needs one connection. |
| `Throttles` metric spike during account-wide Lambda surge | Set reserved concurrency on the rotation Lambda to 1-5 to guarantee availability |

## Procedure: Stuck AWSPENDING version

**Symptom:** `VersionIdsToStages` shows a version in `AWSPENDING`.

**Diagnostics:**

```bash
# 1. List all versions and stages
aws secretsmanager list-secret-version-ids --secret-id <name> \
  --query 'Versions[*].[VersionId,LastAccessedDate,VersionStages]'

# 2. Read both AWSPENDING and AWSCURRENT values (decrypted)
aws secretsmanager get-secret-value --secret-id <name> \
  --version-id <pending-version-id> --query 'SecretString' --output text
aws secretsmanager get-secret-value --secret-id <name> \
  --version-stage AWSCURRENT --query 'SecretString' --output text

# 3. Find CloudWatch errors for the stuck rotation
aws logs filter-log-events \
  --log-group-name /aws/lambda/<lambda> \
  --filter-pattern '"<pending-version-id>"' \
  --start-time $(($(date +%s) - 86400 * 7))000 \
  --limit 20
```

**Determine which credential is live:**

Use the secret's `host`, `port`, `username` + the password from each
version to test a connection:

```bash
# Test AWSPENDING credential (DO NOT log the password)
PGPASSWORD=<pending-password> psql \
  -h <host> -p <port> -U <username> -d <dbname> \
  -c "SELECT 1;"

# Test AWSCURRENT credential
PGPASSWORD=<current-password> psql \
  -h <host> -p <port> -U <username> -d <dbname> \
  -c "SELECT 1;"
```

**If AWSPENDING connects (it is the live credential):** promote it.

```bash
aws secretsmanager update-secret-version-stage \
  --secret-id <name> \
  --version-stage AWSCURRENT \
  --move-to-version-id <pending-version-id> \
  --remove-from-version-id <current-version-id>
```

**If AWSCURRENT still connects (it is the live credential):** cancel the
pending version.

```bash
aws secretsmanager update-secret-version-stage \
  --secret-id <name> \
  --version-stage AWSPENDING \
  --remove-from-version-id <pending-version-id>
```

**If NEITHER connects:** the password was changed out-of-band. Determine
the actual current password (e.g., from the operator who changed it), set
the secret value to match, then trigger a fresh rotation:

```bash
aws secretsmanager put-secret-value \
  --secret-id <name> \
  --secret-string '{"host":"...","port":5432,"username":"app","password":"<actual-current-password>"}' \
  --version-stages AWSCURRENT

aws secretsmanager update-secret-version-stage \
  --secret-id <name> \
  --version-stage AWSPENDING \
  --remove-from-version-id <pending-version-id>

aws secretsmanager rotate-secret --secret-id <name>
```

## Procedure: Out-of-band credential change

**Symptom:** `LastChangedDate` more recent than `LastRotatedDate`. The
DBA ran `ALTER USER` directly.

**Risk:** the next scheduled rotation will fail at `setSecret` because
the Lambda authenticates with `AWSCURRENT`, which no longer matches.

**Fix:**

```bash
# 1. Verify the live credential value (operator must supply)
aws secretsmanager get-secret-value --secret-id <name> \
  --version-stage AWSCURRENT --query 'SecretString' --output text
# Compare with the actual DB password.

# 2. If they don't match, update the AWSCURRENT value
aws secretsmanager put-secret-value \
  --secret-id <name> \
  --secret-string '<new-json-with-actual-password>' \
  --version-stages AWSCURRENT

# 3. Trigger a rotation to verify the chain works end-to-end
aws secretsmanager rotate-secret --secret-id <name>

# 4. Verify LastRotatedDate advances
aws secretsmanager describe-secret --secret-id <name> \
  --query 'LastRotatedDate'
```

## Procedure: Stealth throttle (reserved concurrency = 0)

**Symptom:** Lambda shows `State: Active`, no error logs, but
`LastRotatedDate` does not advance. CloudWatch shows `Throttles` metric
spikes at the scheduled rotation time.

**Diagnostic:**

```bash
aws lambda get-function-concurrency --function-name <lambda>
# If ReservedConcurrentExecutions: 0, the Lambda is functionally disabled.
```

**Fix:**

```bash
aws lambda put-function-concurrency \
  --function-name <lambda> \
  --reserved-concurrent-executions 5

# Trigger a rotation to confirm
aws secretsmanager rotate-secret --secret-id <name>
```

## Procedure: Replica sync failure

**Symptom:** Primary rotation succeeded; one or more replicas show a
stale `LastRotatedDate` or do not have the new version.

**Diagnostic:**

```bash
# In each replica region
aws secretsmanager describe-secret --secret-id <name> --region <replica-region> \
  --query '{LastRotated:LastRotatedDate,PrimaryRegion:PrimaryRegion,
            Versions:VersionIdsToStages}'
```

Replicas should reflect the primary's `AWSCURRENT` version ID within
1-5 seconds. If they don't:

- Verify the replica's KMS key is `Enabled` (customer-managed keys are
  region-specific; the replica needs its own CMK).
- Verify there is no `BlockReplication` field set on the primary.
- For `ForceOverwriteReplicaSecret` (regional failover DR), use this
  command on the promoted replica — not for routine rotation:

```bash
aws secretsmanager put-secret-value \
  --secret-id <name> \
  --secret-string '<value>' \
  --force-overwrite-replica-secret
```

## Procedure: Cross-account rotation Lambda

**Symptom:** Lambda in account B; secret in account A. Rotation fails
with `AccessDeniedException`.

**Diagnostic checklist:**

1. In account B (Lambda account): `aws lambda get-policy --function-name
   <lambda>` — verify `secretsmanager.amazonaws.com` (or account A's ID
   via `source-account`) is in the resource-based policy.
2. In account A (Secret account): `aws secretsmanager get-resource-policy
   --secret-id <name>` — verify the Lambda role ARN in account B is
   granted `secretsmanager:GetSecretValue`, `PutSecretValue`,
   `UpdateSecretVersionStage`, `DescribeSecret`.
3. In account B (Lambda account): the Lambda's execution role identity-
   based policy MUST grant the same actions on the cross-account secret
   ARN. Both sides of the grant are required.
4. In account A (Secret account): the KMS key (if customer-managed)
   policy MUST grant the Lambda role ARN in account B `kms:Decrypt`.

**Fix template — secret resource policy (account A):**

```bash
aws secretsmanager put-resource-policy \
  --secret-id <name> \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::BBBBBBBBBBBB:role/<lambda-role>"},
      "Action": [
        "secretsmanager:DescribeSecret",
        "secretsmanager:GetSecretValue",
        "secretsmanager:PutSecretValue",
        "secretsmanager:UpdateSecretVersionStage"
      ],
      "Resource": "*"
    }]
  }'
```

**Fix template — KMS key policy (account A):**

```bash
aws kms put-key-policy --key-id <kms-id> --policy-name default \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      <existing-statements>,
      {
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::BBBBBBBBBBBB:role/<lambda-role>"},
        "Action": ["kms:Decrypt", "kms:DescribeKey"],
        "Resource": "*"
      }
    ]
  }'
```

## Diagnostic command quick-reference

| Goal | Command |
|---|---|
| Rotation status | `aws secretsmanager describe-secret --secret-id <id>` |
| Version stages | `aws secretsmanager list-secret-version-ids --secret-id <id>` |
| Resource-based policy | `aws secretsmanager get-resource-policy --secret-id <id>` |
| Secret value (decrypted) | `aws secretsmanager get-secret-value --secret-id <id> --version-stage AWSCURRENT` |
| Lambda state | `aws lambda get-function-configuration --function-name <lambda>` |
| Lambda resource policy | `aws lambda get-policy --function-name <lambda>` |
| Lambda reserved concurrency | `aws lambda get-function-concurrency --function-name <lambda>` |
| Lambda role policies | `aws iam list-attached-role-policies --role-name <role>` + `aws iam list-role-policies --role-name <role>` |
| KMS key state | `aws kms describe-key --key-id <id>` |
| KMS key policy | `aws kms get-key-policy --key-id <id> --policy-name default` |
| Lambda logs (errors) | `aws logs filter-log-events --log-group-name /aws/lambda/<lambda> --filter-pattern ERROR --limit 20` |
| Lambda metrics (throttles) | `aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Throttles --dimensions Name=FunctionName,Value=<lambda> ...` |
| RotationFailed events | `aws logs filter-log-events --log-group-name /aws/secretsmanager/<name> --filter-pattern "Rotation Failed"` |
| Trigger manual rotation | `aws secretsmanager rotate-secret --secret-id <id>` |
| Promote AWSPENDING | `aws secretsmanager update-secret-version-stage --secret-id <id> --version-stage AWSCURRENT --move-to-version-id <pending> --remove-from-version-id <current>` |
| Cancel AWSPENDING | `aws secretsmanager update-secret-version-stage --secret-id <id> --version-stage AWSPENDING --remove-from-version-id <pending>` |
| Update rotation config | `aws secretsmanager rotate-secret --secret-id <id> --rotation-lambda-arn <arn> --rotation-rules AutomaticallyAfterDays=30` |

## Failure-mode to operation routing

| Failure mode | Recommended operation | Notes |
|---|---|---|
| Lambda never invoked, no errors | diagnose-rotation | Resource-based policy missing; or reserved concurrency = 0 |
| Lambda invoked, errors | diagnose-rotation | Match the error pattern to the failure-mode table |
| AWSPENDING stuck | recover-pending | Determine live credential first |
| Rotation enabled but no Lambda ARN | enable-rotation | Populate `RotationLambdaARN` |
| Schedule invalid (>365, malformed cron) | update-config | Reset `AutomaticallyAfterDays` or `ScheduleExpression` |
| Cross-account `AccessDeniedException` | diagnose-rotation | Verify both resource policies + KMS key policy |
| Replica sync failure | diagnose-rotation | Verify replica KMS key, region replication status |
| Out-of-band credential change | trigger-rotation (after manual sync) | Update AWSCURRENT to match live, then rotate |
