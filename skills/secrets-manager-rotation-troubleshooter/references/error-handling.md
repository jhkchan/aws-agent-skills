# Error Handling — Secrets Manager Rotation Troubleshooter

Pre-flight safety checks and per-layer remediation guidance moved out of the SKILL.md body. Loaded on demand.


## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-function-configuration`, `rotate-secret`, `put-rule`,
  `put-targets`, `enable-rule`, `add-permission`, `update-secret`,
  `put-resource-policy`), emit and await operator approval. Do NOT
  execute the CLI until the operator confirms.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`describe-secret`, `get-resource-policy`,
  `get-function-configuration`, `filter-log-events`, `describe-rule`,
  `list-targets-by-rule`, `describe-route-tables`,
  `describe-security-groups`, `describe-key`,
  `simulate-principal-policy`, `lookup-events`,
  `describe-db-instances`, `describe-clusters`). Do not perform
  state-changing operations as diagnostic probes.

- **`rotate-secret` triggers an immediate rotation.** It does not
  block waiting for completion. Verify success by polling
  `LastRotatedDate` (should advance within 5 minutes) and the Lambda's
  CloudWatch log stream.

- **`update-function-configuration --timeout`** is safe; raising the
  timeout does not cause disruption. The next rotation invocation uses
  the new timeout.

- **`update-function-configuration --vpc-config`** triggers an ENI
  re-creation. Plan outside traffic peaks; the rotation Lambda may be
  unavailable for 30-60 seconds.

- **`events put-rule` / `put-targets`** is non-disruptive if the rule
  did not exist; if the rule exists and is being updated, the change
  applies at the next schedule window.

- **`events enable-rule`** immediately resumes the schedule; the next
  firing happens at the next schedule window, not immediately. Trigger
  a manual rotation to validate before the window.

- **`lambda add-permission`** is additive; it does not affect existing
  permissions. Safe to call without a confirmation if the operator
  has approved the broader remediation.

- **Secret value updates (`update-secret`)** change the `AWSCURRENT`
  version immediately. Applications reading the secret will see the
  new value on the next `GetSecretValue` call. Confirm the application
  is prepared to consume the new value before updating.

- **Resource-based policy changes (`put-resource-policy`)** affect
  every consumer of the secret. Tighten policy gradually; never
  deny-by-default without confirming no application depends on the
  secret.

- **Bulk remediation batch limit.** If the diagnosis identifies the
  same root cause across multiple secrets (e.g., a deleted EventBridge
  rule affecting every secret in a rotation schedule group), batch
  remediation into groups of at most 5 secrets, emit a single CONFIRM
  per batch, and verify between batches.

## Remediation guidance

### For ROTATION_LAMBDA_TIMEOUT

```bash
aws lambda update-function-configuration \
  --function-name <rotation-lambda-arn> --timeout 30 --profile <p>
aws secretsmanager rotate-secret --secret-id <arn-or-name> --profile <p>
```

Target: 30s for routine rotations. 60s only if the database genuinely
takes that long (large `GRANT` operations, slow Aurora writer
failover). Avoid 900s — investigate the underlying latency instead.

### For ROTATION_LAMBDA_VPC

```bash
# Attach the Lambda to the database's subnets and SG
aws lambda update-function-configuration \
  --function-name <rotation-lambda-arn> \
  --vpc-config SubnetIds=<db-subnet-1>,<db-subnet-2>,SecurityGroupIds=<lambda-sg> \
  --profile <p>
```

Confirm the SG rules: Lambda SG egress to DB port; DB SG ingress from
Lambda SG on the DB port.

### For ROTATION_LAMBDA_DB_ENDPOINT

Update the secret value (preferred — the application and rotation
Lambda both read from the same source of truth):

```bash
aws secretsmanager put-secret-value \
  --secret-id <arn-or-name> \
  --secret-string '{"engine":"mysql","host":"<correct-host>","port":3306,"dbname":"<correct-db>","username":"app_user","password":"<current-password>"}' \
  --profile <p>
```

For Aurora, prefer the cluster writer endpoint over the instance
endpoint to survive failover.

### For SCHEDULE_MISSING

```bash
aws events put-rule --name SecretsManager-<secret-keyword> \
  --schedule-expression "rate(1d)" --state ENABLED --profile <p>
aws events put-targets --rule SecretsManager-<secret-keyword> \
  --targets file://targets.json --profile <p>
aws lambda add-permission --function-name <rotation-lambda-name> \
  --statement-id <unique-sid> --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:<region>:<account>:rule/SecretsManager-<secret-keyword> \
  --profile <p>
```

### For SCHEDULE_DISABLED

```bash
aws events enable-rule --name SecretsManager-<secret-keyword> --profile <p>
```

### For MASTER_SECRET_MISCONFIGURED

```bash
aws lambda update-function-configuration \
  --function-name <rotation-lambda-arn> \
  --environment Variables={SECRETS_MANAGER_MASTER_ID=<correct-master-arn>} \
  --profile <p>
aws lambda publish-version --function-name <rotation-lambda-arn> --profile <p>
aws lambda update-alias --name <rotation-alias> \
  --function-version <new> --profile <p>
```

### For PERMISSION_ROTATION_ROLE

```bash
aws iam put-role-policy --role-name <rotation-role-name> \
  --policy-name SecretsManagerRotationAccess \
  --policy-document '<JSON with secretsmanager:GetSecretValue,
    PutSecretValue, DescribeSecret on the secret ARN and Master Secret
    ARN>' --profile <p>
aws secretsmanager rotate-secret --secret-id <arn-or-name> --profile <p>
```

### For KMS_DECRYPT_ROLE

```bash
aws iam put-role-policy --role-name <rotation-role-name> \
  --policy-name KMSDecryptForSecretsManager \
  --policy-document '<JSON with kms:Decrypt on the CMK ARN>' \
  --profile <p>
```

### For PERMISSION_CROSS_ACCOUNT

```bash
# In the secret's owning account:
aws secretsmanager put-resource-policy \
  --secret-id <secret-arn-in-account-B> \
  --policy file://cross-account-policy.json --profile <account-B>
```

If a customer-managed CMK is in use, also update the CMK key policy in
account B to grant the rotation role in account A.

### For ROTATION_TOKEN_MISSING

Always trigger rotation via `secretsmanager rotate-secret`, not via
`lambda invoke`:

```bash
aws secretsmanager rotate-secret --secret-id <arn-or-name> --profile <p>
```

### For SUPERUSER_INSUFFICIENT

On the database directly:

```sql
-- MySQL / Aurora-MySQL:
GRANT CREATE USER, UPDATE ON mysql.user TO '<master-user>'@'%';
-- or for full superuser (RDS only — no root@localhost):
GRANT SELECT, INSERT, UPDATE, DELETE ON mysql.* TO '<master-user>'@'%';

-- PostgreSQL / Aurora-PostgreSQL:
ALTER ROLE "<master-user>" CREATEROLE;
-- Aurora-PostgreSQL: grant the rds_superuser role if appropriate.

-- SQL Server:
ALTER SERVER ROLE sysadmin ADD MEMBER <master-user>;

-- Oracle:
GRANT ALTER USER TO <master-user>;
```

### For STRATEGY_CONFLICT

Re-deploy the rotation Lambda with the correct template family. The
template families are listed in the AWS-managed serverless rotation
templates (Serverless Application Repository):

- `SecretsManagerRDSMySQLRotation` / `SecretsManagerRDSPostgreSQLRotation`
  (Single User)
- `SecretsManagerRDSMySQLRotationMultiUser` /
  `SecretsManagerRDSPostgreSQLRotationMultiUser` (Alternating Users)
- `SecretsManagerRedshiftRotationSingleUser` /
  `SecretsManagerRedshiftRotationMultiUser` (Redshift-specific)
- `SecretsManagerRDSSQLServerRotationSingleUser` /
  `SecretsManagerRDSSQLServerRotationMultiUser` (SQL Server)
- `SecretsManagerRDSOracleRotationSingleUser` /
  `SecretsManagerRDSOracleRotationMultiUser` (Oracle)
- `SecretsManagerMongoDBRotationSingleUser` /
  `SecretsManagerMongoDBRotationMultiUser` (DocumentDB-compatible)
- `SecretsManagerRotationGeneric` (custom engine — implement the
  four-step protocol)

### For TWIN_SECRETS_NOT_SYNCED

```bash
# If the twin is a managed replica:
aws secretsmanager replicate-secret-to-regions \
  --secret-id <primary-arn> \
  --add-replica-regions Region=<secondary-region> \
  --force-overwrite-replica-secret --profile <p>

# If the twin is an independent secret, re-enable its rotation:
aws secretsmanager rotate-secret --secret-id <twin-arn> \
  --rotation-rule AutomaticallyAfterDays=1 --profile <p>
```
