---
name: secrets-manager-rotation-troubleshooter
description: 'Diagnoses AWS Secrets Manager rotation failures through a ten-category diagnostic tree: rotation Lambda errors at the database (wrong host, port, database name, credential creation), rotation schedule not triggering (EventBridge rule deleted, disabled, or wrong schedule expression), cross-account secret access denied (rotation role lacks kms:Decrypt or secretsmanager:GetSecretValue on the secret), Master Secret ARN misconfigured in the rotation template, rotation Lambda timeout (default 3s too low, or 15s insufficient for slow DB), VPC connectivity (rotation Lambda not attached to DB subnets, missing NAT/endpoint for Secrets Manager API), rotation strategy conflict (Alternating Users on a engine without CREATE USER, Single User on a twin-secret setup), twin secrets not synced across regions/accounts, rotation token missing (a caller invoked the Lambda directly without a ClientRequestToken), and superuser permissions insufficient for the rotation Lambda''s DB user. Walks symptoms to a verified root cause wi...'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and rotation configuration. Live-account diagnosis uses aws secretsmanager describe-secret, aws secretsmanager
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA | ESCALATE
  when_to_use: Diagnosing an AWS Secrets Manager secret rotation failure (rotation Lambda error, schedule not triggering, cross-account access denied, Master Secret misconfiguration, rotation Lambda timeout, VPC connectivity to the database, Alternating vs Single User strategy conflict, twin secrets not synced, rotation token missing, superuser permissions insufficient), walking a symptom to the failed layer with verify and fix commands, validating why a secret's LastRotatedDate is stale, or triaging a "secret rotation is broken" page where the root cause may be rotation Lambda, EventBridge schedule, IAM, network, KMS, or database permissions — not necessarily the rotation template itself.
  when_not_to_use: Initial rotation configuration (use the Secrets Manager console or CloudFormation rotation template setup), secret value retrieval at application runtime (use the application's SDK path), audit of all secrets lacking rotation (use secrets-manager-rotation-coverage-auditor), encryption-key rotation for the underlying CMK (use kms-key-rotation-operator), or password-policy enforcement (use iam-password-policy-auditor). This skill diagnoses rotation-time failures; it does not design rotation schedules or audit steady-state rotation posture.
  activation_triggers: ''
  invocation_schema: '''Input: either (a) a symptom description (error message from the rotation Lambda CloudWatch logs, observed behaviour such as "LastRotatedDate is 30 days ago", "rotation succeeds but applications cannot connect"), optionally paired with the secret''s describe-secret output and recent rotation Lambda logs, OR (b) a SecretId plus caller context for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA, ESCALATE} and LAYER ∈ {ROTATION_LAMBDA_TIMEOUT, ROTATION_LAMBDA_VPC, ROTATION_LAMBDA_DB_CREDENTIAL, ROTATION_LAMBDA_DB_ENDPOINT, SCHEDULE_MISSING, SCHEDULE_DISABLED, MASTER_SECRET_MISCONFIGURED, PERMISSION_ROTATION_ROLE, PERMISSION_CROSS_ACCOUNT, KMS_DECRYPT_ROLE, ROTATION_TOKEN_MISSING, SUPERUSER_INSUFFICIENT, STRATEGY_CONFLICT, TWIN_SECRETS_NOT_SYNCED, PREVIOUS_CREDENTIAL_NOT_STORED, REDSHIFT_ROTATION_FUNCTION, UNKNOWN}.'''
  invocation_example: '"# Minimal valid input (offline symptom classification):\nSymptom: \"Secret prod/db/payments-primary has not rotated in 7 days;\nLastRotatedDate is 2026-07-30. The rotation Lambda''s last execution\nlogged ''Task timed out after 3.00 seconds''.\"\nSecretId: prod/db/payments-primary\nRotationEnabled: true\nRotationLambdaARN: arn:aws:lambda:us-east-1:111111111111:function:SecretsManagerRotation-prod-db-payments\nRotationRules: {ScheduleExpression: ''rate(1d)''}\nLastRotatedDate: 2026-07-30T03:17:22Z\nOwningService: (none — customer-managed)\nKmsKeyId: alias/aws/secretsmanager\nRotationLambda LastLog: ''Task timed out after 3.00 seconds''"'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Secrets Manager, rotation, rotation Lambda, Master Secret, Alternating Users, Single User, rotation strategy, EventBridge schedule, rotation token, ClientRequestToken, cross-account secret, twin secrets, RotateSecret, rotation template, Superuser, database credential, rotation disabled, rate(1d), VPC connectivity, KMS decrypt
---

# Secrets Manager Rotation Troubleshooter

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  rotation Lambda `Task timed out` and the timeout is 3s (default)
  → `ROTATION_LAMBDA_TIMEOUT`; rotation Lambda `Task timed out` at 15s
  with a DB in another subnet → `ROTATION_LAMBDA_VPC`; rotation Lambda
  logged `AccessDenied` calling `secretsmanager:GetSecretValue` on the
  Master Secret → `PERMISSION_ROTATION_ROLE`; `LastRotatedDate` is days
  stale and the EventBridge rule is missing → `SCHEDULE_MISSING`;
  rotation Lambda logged `Could not connect to database at host ...` or
  `wrong port` → `ROTATION_LAMBDA_DB_ENDPOINT`; rotation Lambda logged
  `Master Secret ARN ... does not exist` → `MASTER_SECRET_MISCONFIGURED`;
  rotation Lambda logged `Rotating back to previous credential` on every
  attempt → `PREVIOUS_CREDENTIAL_NOT_STORED`; the Lambda was invoked
  manually without a `ClientRequestToken` → `ROTATION_TOKEN_MISSING`.
- **Always verify with a probe, never guess.** Each layer has a single
  command that proves or disproves it. A `ROOT_CAUSE_IDENTIFIED` verdict
  requires positive evidence — a failing probe that matches the symptom
  — not a process of elimination.
- **Rotation is a four-step protocol: `createSecret`, `setSecret`,
  `testSecret`, `finishSecret`.** Most rotation failures surface in
  `setSecret` (the step that issues the SQL `ALTER USER` / `CREATE USER`
  against the target database). Read the Lambda logs to identify the
  step that failed before guessing the layer.
- **Rotation strategy is set at template-deploy time, not at the
  secret.** `Alternating Users` creates a clone of the current user and
  rotates the clone's password (safer; requires `CREATE USER` +
  `GRANT`); `Single User` updates the existing user's password in place
  (atomic; requires no extra privileges but risks brief connection
  failures during the rotation step). A rotation Lambda written for one
  strategy cannot rotate a secret configured for the other without a
  code change.
- **ESCALATE for AWS-side incidents.** A regional Secrets Manager or
  Lambda outage, or an AWS Health event affecting the rotation service,
  is not customer-fixable — escalate to AWS Support and surface the
  event ARN.

## Mindset

A failing secret rotation is usually a rotation Lambda configuration,
schedule, or database-permission incident wearing a "Secrets Manager is
broken" costume. The rotation template is fine in the majority of
cases; the broken thing is the rotation Lambda's VPC attachment, its
execution role, the EventBridge rule that triggers it, the Master
Secret ARN it reads, or the database privileges of the credential it is
rotating. Senior security engineers do not start by re-deploying the
rotation template; they start with `describe-secret` and the rotation
Lambda's most recent CloudWatch log stream.

## Philosophy

Four behaviours separate a senior security engineer from a generalist
when diagnosing Secrets Manager rotation:

- **The rotation step name drives the diagnostic order.** A failure
  logged in `createSecret` indicates the Lambda could not even stage
  the new secret value (usually a KMS or permissions issue). A failure
  in `setSecret` indicates the Lambda could not apply the new
  credential to the database (usually VPC, database endpoint, or
  database privilege). A failure in `testSecret` indicates the
  credential was set but could not be verified (usually the wrong
  connection string). A failure in `finishSecret` indicates the Lambda
  could not mark the new version as `AWSCURRENT` (rare; usually a
  Secrets Manager API failure or stale `ClientRequestToken`). Routing
  by step name is the #1 accelerator in rotation incidents.
- **`LastRotatedDate` is the canonical health signal, not the
  EventBridge metric.** A rotation may invoke successfully and still
  not advance `LastRotatedDate` if the Lambda throws after `setSecret`
  but before `finishSecret`. Operators who watch the EventBridge
  invocation count assume "rotations are firing, so we're fine" while
  the secret value is stale. Always read `describe-secret.LastRotatedDate`
  and compare against `RotationRules.ScheduleExpression`.
- **The rotation Lambda's execution role is NOT the same as the
  database credential it rotates.** The execution role is the IAM
  identity the Lambda runs as; it needs `secretsmanager:GetSecretValue`
  on the secret AND on the Master Secret, plus `kms:Decrypt` on the CMK
  that encrypts them. The database credential is the value the Lambda
  reads from the Master Secret to authenticate to the database as a
  superuser. A rotation that fails with "permission denied for table
  mysql.user" is a database-privilege issue (the Master Secret's user
  is not a superuser), not an IAM issue. Confusing the two is the most
  common misdiagnosis.
- **EventBridge `rate(1d)` is the schedule, not a guarantee.**
  EventBridge schedules are best-effort: a deleted rule produces zero
  invocations; a disabled rule produces zero invocations; a rule with
  the wrong target ARN produces zero invocations on the correct Lambda.
  `describe-secret.RotationRules.ScheduleExpression` is the desired
  schedule, but the actual trigger is the EventBridge rule whose target
  is the rotation Lambda. Always verify both the secret's rotation
  config AND the EventBridge rule.

## Quick reference — symptom triage table

| Symptom phrase / log line | Most likely layer | First probe |
|---|---|---|
| `Task timed out after 3.00 seconds` (rotation Lambda default) | `ROTATION_LAMBDA_TIMEOUT` | `lambda get-function-configuration` (Timeout), CloudWatch Duration vs Timeout |
| `Task timed out after 15.00 seconds` + DB in another subnet | `ROTATION_LAMBDA_VPC` | `lambda get-function-configuration` (VpcConfig), `ec2 describe-route-tables` for the subnet |
| `Could not connect to database at host ... port ...` | `ROTATION_LAMBDA_DB_ENDPOINT` | Rotation Lambda env vars / Master Secret value (`host`, `port`, `dbname`), `rds describe-db-instances` |
| `AccessDenied` calling `secretsmanager:GetSecretValue` | `PERMISSION_ROTATION_ROLE` | `iam simulate-principal-policy` on the rotation role for `secretsmanager:GetSecretValue` on the secret ARN |
| `AccessDenied` calling `kms:Decrypt` | `KMS_DECRYPT_ROLE` | `kms describe-key`, simulate `kms:Decrypt` on the rotation role |
| `Master Secret ARN ... does not exist` or `ResourceNotFoundException` | `MASTER_SECRET_MISCONFIGURED` | Rotation Lambda env var `SECRETS_MANAGER_MASTER_ID` vs actual Master Secret ARN |
| `LastRotatedDate` is days/weeks stale; EventBridge rule missing | `SCHEDULE_MISSING` | `events describe-rule` for the rotation rule; `events list-targets-by-rule` |
| `LastRotatedDate` is stale; EventBridge rule `State: DISABLED` | `SCHEDULE_DISABLED` | `events describe-rule --name <rule> --query State` |
| `Rotating back to previous credential` on every attempt | `PREVIOUS_CREDENTIAL_NOT_STORED` | Lambda logs in the `setSecret` step; verify `AWSPREVIOUS` staging label exists |
| `Rotation request missing ClientRequestToken` | `ROTATION_TOKEN_MISSING` | CloudTrail `RotateSecret` event; check for direct Lambda invocation |
| `permission denied for table mysql.user` (or pg_roles) | `SUPERUSER_INSUFFICIENT` | Master Secret DB user's `SUPERUSER` / `rds_superuser` attribute |
| `CREATE USER failed ... already exists` (Alternating) | `STRATEGY_CONFLICT` | Rotation Lambda code: `ROTATION_STRATEGY` env var or template family |
| Redshift secret rotated but `staging_*` user creation failed | `REDSHIFT_ROTATION_FUNCTION` | Rotation Lambda uses the Redshift-specific template, not the generic MySQL one |
| Cross-account: rotation Lambda in account A cannot read secret in account B | `PERMISSION_CROSS_ACCOUNT` | Secret resource policy grants `secretsmanager:GetSecretValue` to the rotation role ARN in account A |
| Region-paired twin: `prod/db/payments` rotated but `eu-west-1/db/payments` did not | `TWIN_SECRETS_NOT_SYNCED` | Compare `LastRotatedDate` across regions; verify the second region's rotation config |
| None of the above, region-wide Secrets Manager outage | `ESCALATE` | `aws health describe-events` for `AWS_SECRETS_MANAGER` |

## Pre-flight: secret state and gather-info gate

Before running symptom-specific probes, gather the canonical secret
configuration and short-circuit on secret states that mimic rotation
failures.

### Account-wide pre-flight commands

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

### Secret-state short-circuit

| `describe-secret` field | Effect on diagnosis |
|---|---|
| `RotationEnabled: true`, `LastRotatedDate` within `RotationRules.ScheduleExpression` | Rotation is healthy; the reported symptom is not a rotation failure. Investigate application-side secret retrieval. |
| `RotationEnabled: true`, `LastRotatedDate` stale by > 1 schedule interval | Rotation is configured but not advancing. Proceed with the diagnostic tree. |
| `RotationEnabled: false` | Rotation is explicitly disabled. Either re-enable (`rotate-secret` is a no-op; use `update-secret` or the console) or note in REMEDIATION. This is the root cause if the operator expected rotation. |
| `DeletedDate` populated | The secret is scheduled for deletion. Rotation does not run on deleted secrets. Restore via `restore-secret`. |
| `VersionIdsToStages` lacks `AWSCURRENT` | The secret has no current version. Rotation will fail; this is rare but indicates a prior failed `finishSecret`. |
| `VersionIdsToStages` has `AWSPENDING` stuck | A prior rotation invocation did not finish. The next rotation will attempt to recover; if it persists, the Lambda is failing in `setSecret` or `testSecret`. |
| `OwningService` (e.g., `rds`, `redshift`, `docdb`) | The secret was created by a managed service. Some services (RDS) manage rotation automatically; verify the OwningService rotation is the one failing before diagnosing. |

If the input is malformed (missing SecretId, absent symptom
description, no caller context for live diagnosis), emit:

```text
TARGET: <secret-id or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a symptom
  description (the rotation Lambda error or observed behaviour such
  as "LastRotatedDate is 7 days old") and the SecretId.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact SecretId or
  ARN, (2) the observed symptom (rotation Lambda error log line,
  stale LastRotatedDate, or application connection failures after
  rotation), and (3) for live diagnosis, the rotation Lambda name
  and recent CloudWatch log stream.
```

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on the
observed symptom, then walk the layer-specific probes in order. **Never
emit `ROOT_CAUSE_IDENTIFIED` without a failing probe that matches the
symptom.**

### Step 0: Rotation protocol and non-obvious behaviours

These are the operational gotchas a senior security engineer knows from
rotation-incident experience:

- **The rotation Lambda implements a four-step protocol.** Secrets
  Manager invokes the Lambda with a `ClientRequestToken` and an
  `ExecutionId`. The Lambda's handler switches on the `step` parameter
  passed in the event payload: `createSecret` (stage the new value
  under `AWSPENDING`), `setSecret` (apply the credential to the
  database), `testSecret` (verify the new credential connects), and
  `finishSecret` (move `AWSCURRENT` to the new version, demote the
  prior to `AWSPREVIOUS`). The first failing step names the layer.
- **The rotation Lambda's default timeout is 3 seconds.** This is far
  too low for any database rotation that includes a connection round
  trip. The AWS-managed rotation templates set the timeout to 30s at
  deploy time, but a custom Lambda or a manually created function often
  inherits the 3s default. Rotation timeouts at exactly 3.00s almost
  always mean the timeout config was never raised from the default.
- **`rate(1d)` is the schedule expression, not a deadline.** EventBridge
  fires the rule approximately every 24 hours, but the firing window
  has up to a 1-hour jitter. Operators who report "rotation was
  supposed to fire at 03:17 but fired at 04:02" are observing the
  jitter, not a bug.
- **The Master Secret and the rotating secret are two different
  secrets.** The Master Secret contains the superuser credential the
  Lambda uses to log in to the database and rotate the rotating
  secret's user. If the Master Secret's user lacks `SUPERUSER` or
  `CREATEROLE`, the `setSecret` step fails with a database-level
  permission error — independent of any IAM permission.
- **Cross-account rotation requires BOTH the rotation role's
  identity-based policy AND the secret's resource-based policy.** Same
  account requires only the identity-based policy. A rotation role in
  account A reading a secret in account B must have
  `secretsmanager:GetSecretValue` on the secret ARN in its identity
  policy AND the secret's resource policy must list the rotation role
  ARN in account A as an allowed principal.
- **KMS decryption for the secret requires `kms:Decrypt` on the
  encryption CMK.** If the secret uses a customer-managed CMK (not the
  default `aws/secretsmanager`), the rotation role needs `kms:Decrypt`
  on that CMK to read the secret value. Rotating from the default CMK
  to a customer-managed one without updating the rotation role breaks
  every rotation. The default CMK decrypts transparently.
- **The rotation Lambda must be in the same VPC as the database OR
  have a route to it.** A Lambda that is not VPC-attached cannot reach
  a private RDS instance. A Lambda in a different VPC cannot reach the
  database without peering or a PrivateLink endpoint. This is the same
  Lambda-VPC gotcha as application Lambdas, but operators often forget
  it applies to the rotation Lambda because "rotation is managed."
- **The `AWSPENDING` staging label indicates an incomplete rotation.**
  If a rotation invocation fails mid-protocol, the new version is left
  in `AWSPENDING`. The next invocation will attempt to recover from
  the failed step. A version stuck in `AWSPENDING` for > 1 schedule
  interval indicates the Lambda is failing repeatedly; read the logs
  to find the failing step.
- **Alternating Users strategy requires the database engine to support
  user cloning.** MySQL, PostgreSQL, and Aurora support `CREATE USER`
  with `GRANT`. SQL Server uses `CREATE LOGIN` + `CREATE USER`. Oracle
  uses `CREATE USER`. Redshift rotation uses a custom template that
  creates a `staging_<user>` shadow user and re-grants permissions.
  Using the generic MySQL rotation Lambda on a Redshift cluster, or
  vice versa, fails with a SQL syntax error in `setSecret`.
- **`AWSPREVIOUS` is populated only after the first successful
  rotation.** A brand-new secret that has never rotated has only
  `AWSCURRENT`. A rotation Lambda that expects to "rotate back" to the
  previous credential on test failure will fail on the first rotation
  because there is no previous. This is rare but worth noting.

### Step 1: Symptom entry — pick the diagnostic branch

| Symptom | Branch |
|---|---|
| Rotation Lambda `Task timed out after 3.00 seconds` | Step 2 — Lambda timeout |
| Rotation Lambda `Task timed out` at > 3s; DB in another subnet/region | Step 3 — VPC connectivity |
| Rotation Lambda `Could not connect to database at host ...` / `wrong port` / `unknown database` | Step 4 — DB endpoint |
| Rotation Lambda `AccessDenied` calling `secretsmanager:GetSecretValue` / `kms:Decrypt` | Step 5 — IAM permissions |
| Rotation Lambda `Master Secret ARN ... does not exist` | Step 6 — Master Secret |
| `LastRotatedDate` stale; rotation never invoked | Step 7 — EventBridge schedule |
| Rotation Lambda logged `permission denied for table mysql.user` / `must be superuser` | Step 8 — DB superuser |
| Rotation Lambda logged `CREATE USER failed ... already exists` / `Rotating back` | Step 9 — Strategy conflict |
| Cross-account rotation Lambda cannot read secret in another account | Step 10 — Cross-account |
| Rotation invoked but `LastRotatedDate` did not advance; `AWSPENDING` stuck | Step 11 — Recovery failure |
| Region-paired twin did not rotate when primary did | Step 12 — Twin secrets |
| None of the above | Step 13 — Escalate / INSUFFICIENT_DATA |

### Step 2: Rotation Lambda timeout (default 3s)

Symptom: rotation Lambda CloudWatch logs show `Task timed out after
3.00 seconds`. `LastRotatedDate` is stale. The default Lambda timeout
is 3s; the AWS-managed rotation templates override this to 30s at
deploy time, but a manually created rotation Lambda may inherit the
default.

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

If `Maximum` Duration is at or just above the configured `Timeout`, the
function is being killed before completing the four-step protocol. If
the configured Timeout is 3, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: ROTATION_LAMBDA_TIMEOUT`.

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

### Step 3: VPC connectivity — rotation Lambda cannot reach database

Symptom: rotation Lambda logs `Could not connect to database at host
<endpoint>` or `Connection timed out` against the RDS/Aurora/Redshift
endpoint. The Lambda's Timeout is ≥ 15s but the connection never
establishes.

```bash
aws lambda get-function-configuration \
  --function-name <rotation-lambda-arn> --output json | \
  jq '.VpcConfig'
```

`VpcConfig` empty or null → the Lambda is NOT in a VPC and cannot
reach a private database. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: ROTATION_LAMBDA_VPC`. Fix: attach the Lambda to the database's
subnets (`update-function-configuration --vpc-config ...`).

If `VpcConfig` is populated, verify the subnet route table:

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

**Verdicts:**
- Lambda not VPC-attached, DB is private: ROOT_CAUSE_IDENTIFIED,
  `LAYER: ROTATION_LAMBDA_VPC`.
- Lambda in wrong subnet, no route to DB CIDR: ROOT_CAUSE_IDENTIFIED,
  `LAYER: ROTATION_LAMBDA_VPC`.
- SG egress or ingress missing the DB port: ROOT_CAUSE_IDENTIFIED,
  `LAYER: ROTATION_LAMBDA_VPC`.

### Step 4: Database endpoint — wrong host, port, or database name

Symptom: rotation Lambda logs `Could not connect to database at host
<host> port <port>` or `unknown database "<dbname>"`. The connection
establishes (no VPC issue) but authentication or routing fails.

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

Common mismatches:

| Symptom | Cause |
|---|---|
| Secret's `host` is the writer endpoint but the rotation tries to connect to a reader | Aurora reader endpoint resolves to a read-only instance; `ALTER USER` fails on read-only. Use the cluster writer endpoint. |
| Secret's `port` is 3306 but the engine is PostgreSQL (5432) | Cross-engine template confusion; the secret was created for one engine but the rotation Lambda uses another engine's template. |
| Secret's `dbname` does not exist on the DB instance | Database was renamed or never created; the connection succeeds but `USE <dbname>` fails. |
| Secret's `host` is an IP that no longer resolves | RDS failover moved the endpoint; the secret's value was never updated. Re-rotate or fix the secret value. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: ROTATION_LAMBDA_DB_ENDPOINT`.
Fix: update the secret value (or Lambda env var) to the correct host,
port, or dbname, then trigger a manual rotation.

### Step 5: IAM — rotation role lacks permissions

Symptom: rotation Lambda logs `AccessDenied` calling
`secretsmanager:GetSecretValue`, `secretsmanager:PutSecretValue`, or
`kms:Decrypt`. The Lambda runs but fails at the first Secrets Manager
API call.

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

**Verdicts:**
- Rotation role lacks `secretsmanager:GetSecretValue` on the secret or
  Master Secret: ROOT_CAUSE_IDENTIFIED,
  `LAYER: PERMISSION_ROTATION_ROLE`.
- Rotation role lacks `kms:Decrypt` on the customer-managed CMK:
  ROOT_CAUSE_IDENTIFIED, `LAYER: KMS_DECRYPT_ROLE`.
- Same-account resource policy does not matter (identity policy
  suffices); cross-account requires both — see Step 10.

### Step 6: Master Secret ARN misconfiguration

Symptom: rotation Lambda logs `ResourceNotFoundException: Master
Secret ARN ... does not exist` or `AccessDenied` reading a Master
Secret that the secret actually points to.

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

Common patterns:

| Symptom | Cause |
|---|---|
| Env var value is a secret NAME, not an ARN; cross-account rotation fails | Same-account tolerates the name; cross-account requires the full ARN with the account ID. Use the ARN. |
| Env var points to a Master Secret in a different region | Rotation Lambda cannot read cross-region without a replication setup; the Master Secret must be in the same region. |
| Env var was updated but the Lambda was not published as a new version | The Lambda alias still points to the old version with the old ARN. Publish and update the alias. |
| Master Secret was deleted but the rotation Lambda still references it | Restore the Master Secret or reconfigure rotation to use the rotating secret itself as Master (single-user strategy). |

**Verdict:** ROOT_CAUSE_IDENTIFIED,
`LAYER: MASTER_SECRET_MISCONFIGURED`. Fix: update the Lambda env var
to the correct Master Secret ARN, publish a new version, and shift the
alias.

### Step 7: EventBridge schedule — rotation never triggers

Symptom: `LastRotatedDate` is days or weeks stale. The rotation Lambda
has no recent CloudWatch log streams. The secret's
`RotationRules.ScheduleExpression` is correct (e.g., `rate(1d)`), but
nothing fires.

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

For each candidate rule:

| Field | Effect |
|---|---|
| Rule not found | The rule was deleted. **ROOT_CAUSE_IDENTIFIED**, `LAYER: SCHEDULE_MISSING`. Recreate via `events put-rule` + `put-targets`. |
| `State: DISABLED` | The rule exists but is disabled. **ROOT_CAUSE_IDENTIFIED**, `LAYER: SCHEDULE_DISABLED`. Re-enable via `events enable-rule`. |
| `ScheduleExpression` does not match `RotationRules.ScheduleExpression` | Schedule drift; the rule fires at the wrong cadence. Update via `events put-rule`. |
| Targets empty or target ARN ≠ rotation Lambda ARN | The rule fires but invokes the wrong Lambda (or no Lambda). Update via `events put-targets`. |
| Target Lambda permission missing (`lambda:InvokeFunction` for the EventBridge principal) | The rule fires but Lambda rejects the invocation. Verify via `lambda get-policy` for the resource-based statement allowing `events.amazonaws.com`. |

**Verdicts:**
- Rule deleted: ROOT_CAUSE_IDENTIFIED, `LAYER: SCHEDULE_MISSING`.
- Rule disabled: ROOT_CAUSE_IDENTIFIED, `LAYER: SCHEDULE_DISABLED`.
- Rule target wrong / missing: ROOT_CAUSE_IDENTIFIED,
  `LAYER: SCHEDULE_MISSING`.

### Step 8: Database superuser privileges insufficient

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

### Step 9: Rotation strategy conflict (Alternating vs Single User)

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

### Step 10: Cross-account secret access denied

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

### Step 11: Rotation token missing or recovery failure

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

### Step 12: Twin secrets not synced across regions

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

### Step 12b: Redshift rotation function (engine-specific template)

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

### Step 13: Escalate or INSUFFICIENT_DATA

If none of the above produced a positive root-cause match, OR the
symptom clearly indicates an AWS-side incident (region event, Secrets
Manager outage, Lambda outage), emit one of:

- **ESCALATE** — AWS-side incident. Surface the AWS Health event ARN,
  the secret's `describe-secret` output, and the relevant CloudTrail
  error. Recommend opening a Support case. Do NOT continue diagnosing;
  the cause is outside the customer's control.
- **INSUFFICIENT_DATA** — A specific probe requires operator input.
  List the missing pieces (rotation Lambda name, Master Secret ARN,
  recent CloudWatch log stream, database endpoint) and the next probe
  to run once the info is available.

## Output format

```text
TARGET: <secret-id or ARN>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA | ESCALATE
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <ROTATION_LAMBDA_TIMEOUT | ROTATION_LAMBDA_VPC |
        ROTATION_LAMBDA_DB_CREDENTIAL | ROTATION_LAMBDA_DB_ENDPOINT |
        SCHEDULE_MISSING | SCHEDULE_DISABLED |
        MASTER_SECRET_MISCONFIGURED | PERMISSION_ROTATION_ROLE |
        PERMISSION_CROSS_ACCOUNT | KMS_DECRYPT_ROLE |
        ROTATION_TOKEN_MISSING | SUPERUSER_INSUFFICIENT |
        STRATEGY_CONFLICT | TWIN_SECRETS_NOT_SYNCED |
        PREVIOUS_CREDENTIAL_NOT_STORED | REDSHIFT_ROTATION_FUNCTION |
        UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or LastRotatedDate delta>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await
  operator approval: "CONFIRM: About to <action> on <secret-id> in
  <region>. Proceed? (yes/no)"
```

### Worked example — ROTATION_LAMBDA_TIMEOUT (default 3s)

```text
TARGET: prod/db/payments-primary
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Rotation Lambda SecretRotation-prod-db-payments has Timeout=3
  (the Lambda default); CloudWatch Duration Maximum is 3.00s on every
  rotation attempt. The Lambda is killed before the four-step protocol
  can complete the setSecret step. The LastRotatedDate is 2026-07-30;
  today is 2026-08-05 — six schedule intervals have been missed.
LAYER: ROTATION_LAMBDA_TIMEOUT
EVIDENCE:
  - Symptom: LastRotatedDate is 2026-07-30T03:17:22Z; RotationRules
    is rate(1d); RotationEnabled is true.
  - Probe: aws lambda get-function-configuration returns Timeout=3,
    Runtime=python3.12, LastModified=2026-07-25 (creation; never
    reconfigured).
  - Probe: aws logs filter-log-events returns "Task timed out after
    3.00 seconds" in 6 of 6 rotation attempts in the last 24 hours;
    the preceding log line is "createSecret: staging new password".
  - Passing: VpcConfig is correctly attached to the DB subnets;
    rotation role has secretsmanager:GetSecretValue and kms:Decrypt
    on the CMK; EventBridge rule is ENABLED with the correct target.
REMEDIATION:
  1. Raise the rotation Lambda timeout to 30 seconds:
     aws lambda update-function-configuration \
       --function-name SecretRotation-prod-db-payments --timeout 30 \
       --profile <p>
  2. Trigger an immediate rotation to verify:
     aws secretsmanager rotate-secret \
       --secret-id prod/db/payments-primary \
       --rotation-rule AutomaticallyAfterDays=1 --profile <p>
  3. Verify LastRotatedDate advances within 5 minutes:
     aws secretsmanager describe-secret \
       --secret-id prod/db/payments-primary \
       --query LastRotatedDate --output text
CONFIRM: Before updating the Lambda timeout, emit and await:
  "CONFIRM: About to raise SecretRotation-prod-db-payments timeout
   to 30s. Proceed? (yes/no)"
```

### Worked example — SCHEDULE_MISSING (EventBridge rule deleted)

```text
TARGET: prod/api/github-webhook-token
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: RotationRules.ScheduleExpression is rate(1d) and
  RotationEnabled is true, but the EventBridge rule
  SecretsManager-prod-api-github-webhook-token does not exist.
  No rotation has fired in 14 days; LastRotatedDate is 2026-07-21.
LAYER: SCHEDULE_MISSING
EVIDENCE:
  - Symptom: LastRotatedDate is 2026-07-21; today is 2026-08-05.
  - Probe: aws events list-rules returns no rule matching the
    rotation Lambda's ARN as target.
  - Probe: aws logs filter-log-events on the rotation Lambda's log
    group returns zero events in the last 14 days.
  - Passing: rotation Lambda configuration is intact (Timeout=30,
    VpcConfig correct, role has GetSecretValue); the rotation role
    has not been modified since 2026-06-15.
REMEDIATION:
  1. Recreate the EventBridge rule with the rotation Lambda as
     target:
     aws events put-rule --name SecretsManager-prod-api-github-webhook-token \
       --schedule-expression "rate(1d)" --state ENABLED --profile <p>
     aws events put-targets --rule SecretsManager-prod-api-github-webhook-token \
       --targets '{"Id":"1","Arn":"<rotation-lambda-arn>"}' --profile <p>
  2. Add the resource-based permission for EventBridge to invoke the
     Lambda:
     aws lambda add-permission --function-name <rotation-lambda-name> \
       --statement-id EventBridgeInvoke --action lambda:InvokeFunction \
       --principal events.amazonaws.com \
       --source-arn arn:aws:events:<region>:<account>:rule/SecretsManager-prod-api-github-webhook-token \
       --profile <p>
  3. Trigger a manual rotation to verify the end-to-end path:
     aws secretsmanager rotate-secret --secret-id prod/api/github-webhook-token \
       --profile <p>
CONFIRM: Before recreating the rule, emit and await:
  "CONFIRM: About to recreate EventBridge rule
   SecretsManager-prod-api-github-webhook-token targeting
   <rotation-lambda>. Proceed? (yes/no)"
```

### Worked example — INSUFFICIENT_DATA

```text
TARGET: prod/auth/oauth-signing-key
VERDICT: INSUFFICIENT_DATA
REASON: The rotation Lambda's recent logs show a database connection
  error, but the secret's connection string (host, port, dbname) was
  not provided and the rotation Lambda's environment variables cannot
  be read without its name.
LAYER: UNKNOWN
EVIDENCE:
  - Observed: "LastRotatedDate is 2026-07-30; rotation Lambda logs
    'Could not connect to database'."
  - Missing: rotation Lambda name or ARN, secret value's connection
    keys (host/port/dbname), RDS instance identifier.
REMEDIATION: Re-prompt the operator for: (1) the rotation Lambda name
  or ARN (visible in describe-secret.RotationLambdaARN), (2) the
  database instance identifier (to cross-reference host/port), and
  (3) the rotation Lambda's recent CloudWatch log stream around the
  failing setSecret step.
```

## Anti-Patterns — NEVER

- NEVER declare `ROOT_CAUSE_IDENTIFIED` without a failing probe that
  matches the symptom. A "process of elimination" diagnosis erodes
  operator trust when the real cause is elsewhere.

- NEVER raise the rotation Lambda timeout above 30s without first
  ruling out VPC connectivity and DB endpoint issues. A rotation that
  "needs" 900s is almost always blocking on an unreachable database;
  raising the timeout just delays the failure and consumes Lambda
  compute budget.

- NEVER assume the rotation Lambda is in the same VPC as the database.
  Rotation is "managed" by Secrets Manager, but the Lambda runs in
  YOUR account with YOUR VPC config. Always verify `VpcConfig`.

- NEVER confuse the rotation role's IAM permissions with the Master
  Secret's database privileges. IAM permissions let the Lambda read
  the secret; database privileges let the Lambda execute `ALTER USER`.
  A "permission denied" in the Lambda logs must be routed by where the
  error originated: a CloudTrail `AccessDenied` event is IAM; a SQL
  `permission denied` is database.

- NEVER re-deploy the rotation template as the first remediation step.
  The template is rarely the cause; the rotation Lambda's config
  (timeout, VPC, role, env vars), the EventBridge schedule, and the
  database privileges are the common culprits. Re-deploying the
  template without identifying the layer burns time and may reset
  working configuration.

- NEVER trigger a manual rotation via `lambda invoke`. Direct Lambda
  invocation does not pass a `ClientRequestToken` and the Lambda will
  fail at the first step. Always use `secretsmanager rotate-secret` to
  trigger rotation; it injects the token correctly.

- NEVER assume `LastRotatedDate` advances on a successful Lambda
  invocation. The date advances only when the Lambda completes
  `finishSecret`. A Lambda that succeeds at `createSecret`,
  `setSecret`, and `testSecret` but throws in `finishSecret` will log
  success but leave `LastRotatedDate` stale and a version stuck in
  `AWSPENDING`.

- NEVER conclude a rotation is healthy just because EventBridge is
  firing. A schedule that fires but invokes a Lambda that immediately
  errors produces a healthy invocation count and a stale
  `LastRotatedDate`. Always cross-reference `LastRotatedDate` against
  `RotationRules.ScheduleExpression`.

- NEVER mix rotation template families across engines. The MySQL
  template does not work on PostgreSQL; the PostgreSQL template does
  not work on Redshift; the SQL Server template has separate Single
  User and Multi User variants. Always match the template to the
  engine AND the strategy.

- NEVER assume the Master Secret is in the same account. Cross-account
  rotation is common; the Master Secret's ARN must include the
  account ID, the resource-based policy must list the rotation role,
  and the KMS key policy must grant the rotation role if the Master is
  encrypted with a customer-managed CMK.

- NEVER assume the `AWSPREVIOUS` staging label exists on a brand-new
  secret. The first successful rotation populates `AWSPREVIOUS`; a
  rollback attempted before the first success fails with "no previous
  version available".

- NEVER rotate a secret without confirming the application will pick
  up the new value. Applications that cache the secret value at
  startup (and never call `GetSecretValue` again) will continue using
  the old credential after rotation. The rotation succeeds; the
  application breaks. Pair rotation with an application-side refresh
  pattern (polling, refresh trigger, or `SecretRotation` EventBridge
  event subscription).

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

## Deep reference: Secrets Manager rotation layer model

### Symptom → layer decision matrix (offline classification)

```
Log line / symptom                              → Layer
Task timed out after 3.00 seconds               → ROTATION_LAMBDA_TIMEOUT
Task timed out at > 3s; DB unreachable          → ROTATION_LAMBDA_VPC
Could not connect to database at host ...       → ROTATION_LAMBDA_DB_ENDPOINT
AccessDenied: secretsmanager:GetSecretValue     → PERMISSION_ROTATION_ROLE
AccessDenied: kms:Decrypt                       → KMS_DECRYPT_ROLE
Master Secret ARN ... does not exist            → MASTER_SECRET_MISCONFIGURED
LastRotatedDate stale; rule missing/disabled    → SCHEDULE_MISSING / SCHEDULE_DISABLED
permission denied for table mysql.user          → SUPERUSER_INSUFFICIENT
CREATE USER failed; already exists              → STRATEGY_CONFLICT
Rotating back to previous credential            → PREVIOUS_CREDENTIAL_NOT_STORED
Rotation request missing ClientRequestToken     → ROTATION_TOKEN_MISSING
Cross-account AccessDenied on GetSecretValue    → PERMISSION_CROSS_ACCOUNT
Twin secret LastRotatedDate drift               → TWIN_SECRETS_NOT_SYNCED
Redshift secret: pg_user does not exist         → REDSHIFT_ROTATION_FUNCTION
```

### Rotation step → layer routing

```
createSecret fails  → KMS_DECRYPT_ROLE, PERMISSION_ROTATION_ROLE,
                      MASTER_SECRET_MISCONFIGURED
setSecret fails     → ROTATION_LAMBDA_VPC, ROTATION_LAMBDA_DB_ENDPOINT,
                      ROTATION_LAMBDA_DB_CREDENTIAL, SUPERUSER_INSUFFICIENT,
                      STRATEGY_CONFLICT
testSecret fails    → ROTATION_LAMBDA_DB_ENDPOINT (wrong connection string),
                      PREVIOUS_CREDENTIAL_NOT_STORED (rollback fails)
finishSecret fails  → ROTATION_TOKEN_MISSING, AWS-side (ESCALATE)
```

### Rotation Lambda execution role minimum policy

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
      "Resource": ["<cmk-arn-if-customer-managed>"]
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream",
                  "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/<rotation-lambda>*"
    }
  ]
}
```

### EventBridge rule template for rotation

```json
{
  "Name": "SecretsManager-<secret-keyword>",
  "ScheduleExpression": "rate(1d)",
  "State": "ENABLED",
  "Targets": [{
    "Id": "1",
    "Arn": "<rotation-lambda-arn>",
    "Input": "{\"SecretId\":\"<secret-arn>\"}"
  }]
}
```

### Rotation strategy matrix

| Strategy | Template family | DB privileges required | Connection-drop risk | AWSPREVIOUS used |
|---|---|---|---|---|
| Single User | `*SingleUserRotation` | `ALTER USER` on the rotating user | Yes (brief, during ALTER) | No (same user) |
| Alternating Users | `*MultiUserRotation` | `CREATE USER`, `GRANT`, `DROP USER` | No (clone is rotated; original stays until swap) | Yes (rollback target) |
| Redshift Single | `SecretsManagerRedshiftRotationSingleUser` | `ALTER USER` | Yes | No |
| Redshift Alternating | `SecretsManagerRedshiftRotationMultiUser` | `CREATE USER`, `GRANT`, transfer ownership | No | Yes |
| Generic | `SecretsManagerRotationGeneric` | Custom (template's responsibility) | Custom | Custom |

## Recent AWS features (2024-2026)

- **Cross-account secret rotation (2024):** Secrets Manager added
  first-class support for cross-account rotation Lambda invocation,
  removing the need for a resource-based policy on the Lambda when
  the secret's resource policy already grants the rotation role.
  Diagnostically, still verify BOTH the secret resource policy AND
  the Lambda resource-based policy for older setups.
- **Rotation Lambda timeout default 30s on managed templates (2024):**
  New AWS-managed rotation templates set Timeout=30 at deploy time.
  Older deployments and custom Lambdas may still have the 3s default.
- **Redshift rotation multi-user template GA (2024-2025):** The
  `SecretsManagerRedshiftRotationMultiUser` template reached GA after
  a long preview; previously Redshift rotation was single-user only.
- **EventBridge scheduler vs EventBridge rules for rotation (2025):**
  Secrets Manager can now use EventBridge Scheduler (not just
  EventBridge rules) to trigger rotation. Scheduler provides
  one-time schedules and finer-grained timing. Older setups still use
  rules; both are valid. Verify which one is in use before diagnosing
  a missing trigger.
- **Secrets Manager automatic rotation conflict detection (2025):**
  Secrets Manager surfaces a `RotationRules.Attempts` field and
  emits a `RotationFailed` EventBridge event when a rotation step
  fails repeatedly. Subscribe to this event for proactive alerting.

## Domain

AWS CloudOps / Secrets Manager, Rotation Lambda, Database Credential
Lifecycle, EventBridge Scheduling, Cross-Account IAM, and Customer
Managed Key encryption.

## AWS documentation

- **AWS Secrets Manager User Guide — Rotating secrets** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html
- **Rotation Lambda templates** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/reference_available-rotation-templates.html
- **Rotation function internals (four-step protocol)** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets_lambda-app-set-up.html
- **Cross-account rotation** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets_create-generic-template.html
- **Twin secrets and replication** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/create-manage-multi-region-secrets.html
- **EventBridge rules for rotation** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotate-secrets_schedule.html
- **KMS key policy for Secrets Manager** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/security-encryption.html
- **AWS Lambda execution role for rotation** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets-required-permissions.html
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
