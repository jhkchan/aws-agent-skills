# Diagnostic Commands — Secrets Manager Rotation Troubleshooter

Pre-flight, gather-info, and per-step probe command listings moved out of the SKILL.md body. Loaded on demand.


## Account-wide pre-flight commands

```bash
# 1. Secret description (RotationEnabled, RotationLambdaARN,
#    RotationRules, LastRotatedDate, LastAccessedDate, KmsKeyId,
#    OwningService, VersionIdsToStages, DeletedDate)
aws secretsmanager describe-secret \
  --secret-id <arn-or-name> --output json

# 2. Recent rotation Lambda log events
aws logs filter-log-events \
  --log-group-name /aws/lambda/<rotation-lambda-name> \
  --start-time $(date -u -v-24H +%s)000 \
  --filter-pattern '"setSecret" OR "createSecret" OR "testSecret" OR "finishSecret" OR "timed out" OR "AccessDenied" OR "permission denied" OR "Could not connect"' \
  --output json

# 3. Secret resource-based policy (cross-account grants)
aws secretsmanager get-resource-policy \
  --secret-id <arn-or-name> --output json 2>/dev/null || \
  echo "No resource-based policy"

# 4. Rotation Lambda configuration (Timeout, VpcConfig, Role, Environment)
aws lambda get-function-configuration \
  --function-name <rotation-lambda-arn> --output json

# 5. EventBridge rules targeting the rotation Lambda
aws events list-rules --output json | \
  jq '.Rules[] | select(.Name | test("Rotation|<secret-keyword>"))'

# 6. AWS Health (regional events)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```

## Pre-flight: secret-state short-circuit

| `describe-secret` field | Effect on diagnosis |
|---|---|
| `RotationEnabled: true`, `LastRotatedDate` within `RotationRules.ScheduleExpression` | Rotation is healthy; the reported symptom is not a rotation failure. Investigate application-side secret retrieval. |
| `RotationEnabled: true`, `LastRotatedDate` stale by > 1 schedule interval | Rotation is configured but not advancing. Proceed with the diagnostic tree. |
| `RotationEnabled: false` | Rotation is explicitly disabled. Either re-enable (`rotate-secret` is a no-op; use `update-secret` or the console) or note in REMEDIATION. This is the root cause if the operator expected rotation. |
| `DeletedDate` populated | The secret is scheduled for deletion. Rotation does not run on deleted secrets. Restore via `restore-secret`. |
| `VersionIdsToStages` lacks `AWSCURRENT` | The secret has no current version. Rotation will fail; this is rare but indicates a prior failed `finishSecret`. |
| `VersionIdsToStages` has `AWSPENDING` stuck | A prior rotation invocation did not finish. The next rotation will attempt to recover; if it persists, the Lambda is failing in `setSecret` or `testSecret`. |
| `OwningService` (e.g., `rds`, `redshift`, `docdb`) | The secret was created by a managed service. Some services (RDS) manage rotation automatically; verify the OwningService rotation is the one failing before diagnosing. |

## Step 2: Rotation Lambda timeout — probes and fix
```bash
aws lambda get-function-configuration \
  --function-name <rotation-lambda-arn> --output json | \
  jq '{Timeout, MemorySize, Runtime, LastModified}'
```

Cross-reference against CloudWatch Duration:

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=<rotation-lambda-name> \
  --start-time $(date -u -v-24H +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

```bash
# Fix:
aws lambda update-function-configuration \
  --function-name <rotation-lambda-arn> --timeout 30 --profile <p>
```

**Note:** If the timeout is already 30s and the Lambda still times out,
the rotation Lambda is blocking on the database (VPC, slow query) or on
Secrets Manager API (rare). Jump to Step 3 (VPC) or Step 4 (DB
endpoint) before raising the timeout further. Raising the timeout to
900s when the database is unreachable just delays the failure.

## Step 3: VPC connectivity — probes
```bash
aws lambda get-function-configuration \
  --function-name <rotation-lambda-arn> --output json | \
  jq '.VpcConfig'
```

```bash
aws ec2 describe-route-tables \
  --filters Name=association.subnet-id,Values=<subnet-from-vpc-config> \
  --output json | jq '.RouteTables[].Routes'
```

- For a database in the same VPC: the route table must have a local
  route to the database's CIDR.
- For a database in a peered VPC: the route table must have a route to
  the peered VPC's CIDR via the peering connection.
- For a database reached via PrivateLink: the route table must have a
  route to the endpoint ENI.

Also verify the Lambda's Security Group allows outbound to the
database port (3306 for MySQL/Aurora-MySQL, 5432 for PostgreSQL/Aurora-
PostgreSQL, 1433 for SQL Server, 1521 for Oracle, 5439 for Redshift),
and the database's Security Group allows inbound from the Lambda's SG.

```bash
aws ec2 describe-security-groups --group-ids <lambda-sg> --output json | \
  jq '.SecurityGroups[].IpPermissionsEgress'

aws ec2 describe-security-groups --group-ids <db-sg> --output json | \
  jq '.SecurityGroups[].IpPermissions'
```

## Step 4: Database endpoint — probes
The connection string lives in either the rotation Lambda's environment
variables OR in the secret value itself (the rotating secret's
`host`/`port`/`dbname` keys). The AWS-managed rotation templates read
these keys from the secret value; custom templates may use env vars.

```bash
# Inspect the rotation Lambda env vars (look for host/port/dbname)
aws lambda get-function-configuration \
  --function-name <rotation-lambda-arn> --output json | \
  jq '.Environment.Variables'

# Verify the secret value's connection keys (requires GetSecretValue
# permission; only the host/port/dbname are non-sensitive)
aws secretsmanager get-secret-value \
  --secret-id <arn-or-name> --query SecretString --output text | \
  jq '{host, port, dbname, engine, username}'
```

Cross-reference against the actual database:

```bash
aws rds describe-db-instances \
  --db-instance-identifier <id> --output json | \
  jq '.DBInstances[0] | {Endpoint: .Endpoint, DBInstanceStatus, Engine, DBName}'

aws redshift describe-clusters \
  --cluster-identifier <id> --output json | \
  jq '.Clusters[0] | {Endpoint: .Endpoint, NodeType, DBName}'
```

## Step 5: IAM permissions — probes
```bash
# Get the rotation role ARN
aws lambda get-function-configuration \
  --function-name <rotation-lambda-arn> --output json | jq '.Role'

# Simulate the role against the secret and Master Secret
aws iam simulate-principal-policy \
  --policy-source-arn <rotation-role-arn> \
  --action-names secretsmanager:GetSecretValue secretsmanager:PutSecretValue secretsmanager:DescribeSecret \
  --resource-arns <secret-arn> <master-secret-arn> \
  --output json --profile <p>

# If the secret uses a customer-managed CMK:
aws iam simulate-principal-policy \
  --policy-source-arn <rotation-role-arn> \
  --action-names kms:Decrypt \
  --resource-arns <cmk-arn> \
  --output json --profile <p>
```

`implicitDeny` = the role's identity policy lacks the action.
`explicitDeny` = a Deny statement in SCP, permissions boundary, or
session policy matches.

For the Secrets Manager API:

```bash
# CloudTrail lookup for the exact denied API
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetSecretValue \
  --start-time $(date -u -v-1H +%s) --end-time $(date -u +%s) \
  --output json | \
  jq '.Events[] | select(.CloudTrailEvent | contains("<rotation-role-name>"))'
```

## Step 6: Master Secret ARN — probes
The Master Secret ARN is configured in the rotation Lambda's
environment variable (typically `SECRETS_MANAGER_MASTER_ID` or
`MASTER_ARN`, depending on the template version). It can also be
passed in the rotation event payload.

```bash
aws lambda get-function-configuration \
  --function-name <rotation-lambda-arn> --output json | \
  jq '.Environment.Variables'

# Verify the Master Secret exists
aws secretsmanager describe-secret \
  --secret-id <master-secret-arn-from-env> --output json
```

## Step 7: EventBridge schedule — probes
```bash
# List rules whose target is the rotation Lambda
aws events list-targets-by-rule \
  --rule <rule-name> --output json 2>/dev/null

# Find the rule by listing all rules and searching for the rotation Lambda
aws events list-rules --output json | \
  jq --arg arn "<rotation-lambda-arn>" \
    '.Rules[] | select(.Name | test("SecretsManager|Rotation|<secret-keyword>"; "i")) | {Name, State, ScheduleExpression, Arn}'

# For each candidate rule, verify the target
aws events list-targets-by-rule --rule <rule-name> --output json
```

## Step 8: Database superuser privileges insufficient (full deep dive)

Symptom: rotation Lambda logs `permission denied for table mysql.user`
(MySQL), `must be superuser to create role` (PostgreSQL), or
`ALTER LOGIN failed; user does not have permission` (SQL Server). The
connection establishes but the `ALTER USER` / `CREATE USER` statement
fails.

The Master Secret's database user must have sufficient privileges to
rotate the rotating secret's user:

- MySQL / Aurora-MySQL: `SUPER` or the specific `CREATE USER` +
  `UPDATE on mysql.user` privilege. Aurora also recognises the
  `rds_superuser` role.
- PostgreSQL / Aurora-PostgreSQL: `CREATEROLE` + membership in the
  target user's parent role. RDS uses `rds_superuser` for the
  bootstrap user.
- SQL Server: `sysadmin` server role (or `ALTER ANY LOGIN`).
- Oracle: `ALTER USER` system privilege (typically the master account).
- Redshift: `superuser` flag on the user (Redshift rotation uses
  `CREATE USER staging_<x>` and `GRANT`).

```bash
# Read the Master Secret's username
aws secretsmanager get-secret-value \
  --secret-id <master-secret-arn> --query SecretString --output text | \
  jq '.username'

# Verify the user's privileges (run on the database directly, or via
# an audit session):
# MySQL:
#   SELECT user, host, Super_priv FROM mysql.user WHERE user='<master-user>';
# PostgreSQL:
#   SELECT rolname, rolcreaterole, rolsuper FROM pg_roles WHERE rolname='<master-user>';
# SQL Server:
#   SELECT name, type_desc FROM master.sys.server_principals WHERE name='<master-user>';
```

**Verdict:** ROOT_CAUSE_IDENTIFIED,
`LAYER: SUPERUSER_INSUFFICIENT`. Fix: grant the Master Secret's user
the required privilege on the database, then trigger a manual rotation
to verify.

## Step 9: Rotation strategy conflict (full deep dive)

Symptom: rotation Lambda logs `CREATE USER failed ... already exists`
(Alternating, on the second rotation), `ALTER USER failed; cannot
modify own password` (Single User, when the Lambda authenticates as the
rotating user instead of the Master), or `Rotating back to previous
credential` on every attempt.

The rotation strategy is baked into the rotation Lambda's code, not
into the secret's metadata. The AWS-managed templates come in two
families per engine:

- **Single User** (`MySQLSingleUserRotation`, `PostgreSQLSingleUserRotation`):
  the Lambda authenticates as the Master, runs `ALTER USER <rotating>
  IDENTIFIED BY '<new-password>'`. Atomic; one connection drop during
  the rotation step. No `AWSPREVIOUS` is meaningful because the user
  is the same.
- **Alternating Users** (`MySQLMultiUserRotation`, `PostgreSQLMultiUserRotation`):
  the Lambda clones the rotating user to `<user>_clone`, sets the new
  password on the clone, swaps the application's connection string,
  and disables the old user. Safer for active connections; requires
  `CREATE USER` + `GRANT`.

```bash
# Identify the rotation Lambda's template family
aws lambda get-function-configuration \
  --function-name <rotation-lambda-arn> --output json | \
  jq '.Environment.Variables | .SECRETS_MANAGER_ROTATION_TYPE
      // .ROTATION_STRATEGY // .FUNCTION_TYPE // "unknown"'

# Inspect the Lambda's description for the template hint
aws lambda get-function-configuration \
  --function-name <rotation-lambda-arn> --output json | \
  jq '.Description'
```

Common patterns:

| Symptom | Cause |
|---|---|
| Lambda is Single-User template but the secret has `username=app_user` and the application expects `app_user_clone` | The application was wired for Alternating; the Lambda was deployed as Single. Re-deploy the rotation Lambda with the Alternating template. |
| Lambda is Alternating template, DB engine does not support user cloning (e.g., Redshift with the MySQL template) | Cross-engine template confusion; use the engine-specific template. |
| Rotation succeeds but the application breaks because the clone user's grants differ from the original | `GRANT` step in the Alternating template missed a privilege; the clone has fewer permissions than the original. Compare `SHOW GRANTS FOR <user>` and `<user>_clone`. |
| "Rotating back to previous credential" on every attempt | The `testSecret` step fails (new credential does not connect), triggering the rollback path. The rollback requires `AWSPREVIOUS` to exist; on the first rotation, there is no previous, so the rollback itself fails. Investigate the `testSecret` failure first. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: STRATEGY_CONFLICT`. Fix:
re-deploy the rotation Lambda with the template family matching the
secret's strategy, OR reconfigure the secret's strategy to match the
Lambda.

## Step 10: Cross-account secret access denied (full deep dive)

Symptom: rotation Lambda in account A reads a secret in account B
(or vice versa). Lambda logs `AccessDenied` calling
`secretsmanager:GetSecretValue` even though the role's identity policy
includes the action.

Cross-account requires BOTH sides:

```bash
# Side 1: rotation role identity policy (in account A)
aws iam simulate-principal-policy \
  --policy-source-arn <rotation-role-arn-in-account-A> \
  --action-names secretsmanager:GetSecretValue secretsmanager:DescribeSecret \
  --resource-arns <secret-arn-in-account-B> \
  --output json --profile <account-A-profile>

# Side 2: secret resource-based policy (in account B)
aws secretsmanager get-resource-policy \
  --secret-id <secret-arn-in-account-B> --output json \
  --profile <account-B-profile>
```

The resource policy must include a statement allowing the rotation
role's ARN in account A:

```json
{
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::<account-A>:role/<rotation-role>" },
  "Action": ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
  "Resource": "<secret-arn-in-account-B>"
}
```

If the KMS key is also in account B, the rotation role needs
`kms:Decrypt` on the CMK AND the CMK's key policy must grant the
rotation role.

**Verdict:** ROOT_CAUSE_IDENTIFIED,
`LAYER: PERMISSION_CROSS_ACCOUNT`. Fix: add the missing principal to
the secret's resource-based policy (and the KMS key policy if a
customer-managed CMK is in use).

## Step 11: Rotation token missing or recovery failure (full deep dive)

Symptom: rotation Lambda was invoked manually (via `lambda invoke` or
the console's "Test" button) without a `ClientRequestToken`. Lambda
logs `Rotation request missing ClientRequestToken` or `ExecutionId
not provided`. Alternatively, a `AWSPENDING` version is stuck and the
recovery invocation also fails.

Secrets Manager invokes the rotation Lambda with both a
`ClientRequestToken` (the version ID that will become `AWSCURRENT`) and
an `ExecutionId` (a per-rotation UUID). A manual invocation omits both;
the Lambda cannot proceed.

```bash
# Verify the most recent RotateSecret invocation
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=RotateSecret \
  --start-time $(date -u -v-24H +%s) --end-time $(date -u +%s) \
  --output json | \
  jq '.Events[] | select(.CloudTrailEvent | contains("<secret-arn>"))'

# Check the secret's staging labels for a stuck AWSPENDING
aws secretsmanager describe-secret \
  --secret-id <arn-or-name> --output json | \
  jq '.VersionIdsToStages'
```

If a version is stuck in `AWSPENDING`, trigger a fresh rotation; the
Lambda will attempt to recover from the failed step:

```bash
aws secretsmanager rotate-secret \
  --secret-id <arn-or-name> --rotation-rule AutomaticallyAfterDays=1 \
  --profile <p>
```

**Verdicts:**
- Manual invocation without token: ROOT_CAUSE_IDENTIFIED,
  `LAYER: ROTATION_TOKEN_MISSING`. Fix: trigger rotation via
  `rotate-secret` (not via direct Lambda invoke).
- Recovery fails repeatedly: investigate the failing step (Step 1 of
  this tree) — the recovery is not the root cause, the underlying
  step failure is.

## Step 12: Twin secrets not synced across regions (full deep dive)

Symptom: the primary-region secret rotates (`LastRotatedDate` is fresh)
but a region-paired twin in another region does not. The application
in the second region reads stale credentials and fails.

Twin secrets are typically maintained via Secrets Manager replication
(`replicate-secret-to-regions`) or via an application-level sync
process. Verify both:

```bash
# Primary region
aws secretsmanager describe-secret \
  --secret-id <primary-arn> --region <primary-region> --output json | \
  jq '{LastRotatedDate, VersionIdsToStages}'

# Secondary region
aws secretsmanager describe-secret \
  --secret-id <secondary-arn> --region <secondary-region> --output json | \
  jq '{LastRotatedDate, VersionIdsToStages, PrimaryRegion: .PrimaryRegion}'
```

If `PrimaryRegion` is populated, the secondary is a read-replica that
should auto-sync within minutes of the primary's rotation. If
`LastRotatedDate` differs by more than 1 hour, the replication is
failing — investigate the replication status:

```bash
aws secretsmanager describe-secret \
  --secret-id <primary-arn> --region <primary-region> --output json | \
  jq '.ReplicationStatus'
```

If `PrimaryRegion` is empty (the twin is not a managed replica), the
twin is a separate secret with its own rotation config. Verify the
twin's `RotationEnabled` and `RotationLambdaARN` independently.

**Verdict:** ROOT_CAUSE_IDENTIFIED,
`LAYER: TWIN_SECRETS_NOT_SYNCED`. Fix: re-establish replication
(`replicate-secret-to-regions` with `ForceOverwriteReplicaSecret=true`)
or re-enable the twin's rotation config.

## Step 12b: Redshift rotation function (full deep dive)

Symptom: rotation Lambda for a Redshift secret fails in `setSecret`
with a SQL syntax error or `relation "pg_user" does not exist`.

Redshift uses a different rotation template than PostgreSQL despite
sharing the port (5439 vs 5432). The Redshift template creates a
`staging_<user>` shadow user, rotates its password, and re-grants
permissions. Using the PostgreSQL template on a Redshift cluster fails
because Redshift does not support all PostgreSQL system catalog tables.

```bash
# Verify the rotation Lambda's handler/description identifies it as Redshift
aws lambda get-function-configuration \
  --function-name <rotation-lambda-arn> --output json | \
  jq '{Description, Handler, Environment: .Environment.Variables}'

# Verify the secret's engine
aws secretsmanager get-secret-value \
  --secret-id <arn-or-name> --query SecretString --output text | \
  jq '.engine'
```

If the Lambda is a generic PostgreSQL template and the secret's engine
is `redshift`, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: REDSHIFT_ROTATION_FUNCTION`. Fix: re-deploy the rotation
Lambda with the Redshift-specific rotation template.
