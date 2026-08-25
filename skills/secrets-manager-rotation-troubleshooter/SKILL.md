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
Full diagnostic mindset (rotation incidents are Lambda config, schedule, or DB-permission incidents, not template bugs): [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the senior-engineer framing.

## Philosophy
The four senior-engineer behaviours (rotation step name drives diagnostic order, LastRotatedDate is the canonical health signal, execution role vs DB credential, rate(1d) is a schedule not a guarantee): [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when routing by rotation step name.

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
Account-wide pre-flight commands 1-6 (describe-secret, rotation Lambda log filter, get-resource-policy, get-function-configuration, EventBridge rules, AWS Health): [references/diagnostic-commands.md](references/diagnostic-commands.md).
Run these before any symptom-specific probe.

### Secret-state short-circuit
The secret-state short-circuit table (healthy vs stale vs RotationEnabled:false vs DeletedDate vs missing AWSCURRENT vs AWSPENDING stuck vs OwningService): [references/diagnostic-commands.md](references/diagnostic-commands.md).
Consult it right after describe-secret to short-circuit mimics.

If the input is malformed (missing SecretId, absent symptom
description, no caller context for live diagnosis), emit:

The INSUFFICIENT_DATA re-prompt template for malformed/missing input: [references/worked-examples.md](references/worked-examples.md).
Emit it whenever required context is missing.

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on the
observed symptom, then walk the layer-specific probes in order. **Never
emit `ROOT_CAUSE_IDENTIFIED` without a failing probe that matches the
symptom.**

### Step 0: Rotation protocol and non-obvious behaviours
The ten non-obvious behaviours (four-step protocol, 3s default timeout, schedule jitter, Master Secret vs rotating secret, cross-account dual policy, CMK decrypt, Lambda-VPC attachment, AWSPENDING recovery, Alternating engine support, AWSPREVIOUS on first rotation): [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when the failing step is unclear.

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

Probes (lambda get-function-configuration Timeout/Memory/Runtime, CloudWatch Duration statistics vs configured Timeout): [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the timeout probes.

If `Maximum` Duration is at or just above the configured `Timeout`, the
function is being killed before completing the four-step protocol. If
the configured Timeout is 3, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: ROTATION_LAMBDA_TIMEOUT`.

Fix command (lambda update-function-configuration --timeout 30) plus the do-not-just-raise-the-timeout note: [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when applying the ROTATION_LAMBDA_TIMEOUT fix.

### Step 3: VPC connectivity — rotation Lambda cannot reach database

Symptom: rotation Lambda logs `Could not connect to database at host
<endpoint>` or `Connection timed out` against the RDS/Aurora/Redshift
endpoint. The Lambda's Timeout is ≥ 15s but the connection never
establishes.

Probes (lambda get-function-configuration VpcConfig, subnet route tables, Lambda/DB security groups): [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the VPC probes.

`VpcConfig` empty or null → the Lambda is NOT in a VPC and cannot
reach a private database. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: ROTATION_LAMBDA_VPC`. Fix: attach the Lambda to the database's
subnets (`update-function-configuration --vpc-config ...`).

If `VpcConfig` is populated, verify the subnet route table:

Route-table reading guide (local route, peered VPC, PrivateLink ENI) and security-group checks per DB port: [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when VpcConfig is populated but the DB is unreachable.

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

Connection-string probes (Lambda env vars, secret value host/port/dbname, rds describe-db-instances, redshift describe-clusters): [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to cross-reference the database endpoint.

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

IAM probes (rotation role ARN, simulate-principal-policy for GetSecretValue/PutSecretValue/DescribeSecret and kms:Decrypt, CloudTrail lookup for the denied API) plus implicitDeny vs explicitDeny reading: [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand on any AccessDenied symptom.

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

Master Secret probes (Lambda env vars SECRETS_MANAGER_MASTER_ID / MASTER_ARN, describe-secret on the Master ARN): [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when the Master Secret is suspect.

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

Schedule probes (list-targets-by-rule, list-rules filtered for the rotation Lambda, per-rule target verification): [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when LastRotatedDate is stale.

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
Step 8 deep dive (engine-by-engine privilege requirements, Master Secret username read, SUPERUSER_INSUFFICIENT verdict and fix): [references/diagnostic-commands.md](references/diagnostic-commands.md) and [references/error-handling.md](references/error-handling.md).
Branch when the Lambda logs `permission denied for table mysql.user` or `must be superuser`.

### Step 9: Rotation strategy conflict (Alternating vs Single User)
Step 9 deep dive (Single vs Alternating template families, ROTATION_STRATEGY env probes, STRATEGY_CONFLICT patterns and verdict): [references/diagnostic-commands.md](references/diagnostic-commands.md).
Branch when the Lambda logs `CREATE USER failed ... already exists` or `Rotating back`.

### Step 10: Cross-account secret access denied
Step 10 deep dive (cross-account simulate + get-resource-policy probes, required resource-policy statement, KMS key policy, PERMISSION_CROSS_ACCOUNT verdict): [references/diagnostic-commands.md](references/diagnostic-commands.md).
Branch when a rotation Lambda in account A cannot read a secret in account B.

### Step 11: Rotation token missing or recovery failure
Step 11 deep dive (CloudTrail RotateSecret lookup, AWSPENDING staging-label check, recovery rotation, ROTATION_TOKEN_MISSING verdict): [references/diagnostic-commands.md](references/diagnostic-commands.md).
Branch on manual invocation without a ClientRequestToken or a stuck AWSPENDING.

### Step 12: Twin secrets not synced across regions
Step 12 deep dive (primary/secondary describe-secret comparison, ReplicationStatus, TWIN_SECRETS_NOT_SYNCED verdict and fix): [references/diagnostic-commands.md](references/diagnostic-commands.md).
Branch when a region-paired twin did not rotate with the primary.

### Step 12b: Redshift rotation function (engine-specific template)
Step 12b deep dive (Redshift-specific handler and engine probes, REDSHIFT_ROTATION_FUNCTION verdict): [references/diagnostic-commands.md](references/diagnostic-commands.md).
Branch when a Redshift secret fails in setSecret with a SQL syntax error.

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
Full worked example (recreate deleted EventBridge rule + add-permission + verify rotation): [references/worked-examples.md](references/worked-examples.md).
The ROTATION_LAMBDA_TIMEOUT example above is the primary worked example.

### Worked example — INSUFFICIENT_DATA
Full INSUFFICIENT_DATA worked example (missing Lambda name, connection keys, RDS identifier, re-prompt): [references/worked-examples.md](references/worked-examples.md).
Load on demand when required context is missing.

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
Full safety guidance (confirm gate, read-only-first, rotate-secret non-blocking, vpc-config ENI recreation, batch limit of 5): [references/error-handling.md](references/error-handling.md).
Load on demand before any state-changing CLI.

## Remediation guidance
Per-layer fix and verify commands (ROTATION_LAMBDA_TIMEOUT, VPC, DB_ENDPOINT, SCHEDULE_MISSING/DISABLED, MASTER_SECRET, PERMISSION_ROTATION_ROLE, KMS_DECRYPT_ROLE, CROSS_ACCOUNT, TOKEN, SUPERUSER, STRATEGY_CONFLICT, TWIN_SECRETS): [references/error-handling.md](references/error-handling.md).
Load on demand after a ROOT_CAUSE_IDENTIFIED verdict.

## Deep reference: Secrets Manager rotation layer model
The full layer model (symptom-to-layer decision matrix, rotation-step-to-layer routing, execution-role minimum policy, EventBridge rule template, rotation strategy matrix): [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for offline classification or template details.

## Recent AWS features (2024-2026)
Recent AWS features 2024-2026 (cross-account rotation, 30s default on managed templates, Redshift multi-user GA, EventBridge Scheduler, RotationFailed events): [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when a trigger mechanism looks new.

## References (load on demand)

- [Diagnostic commands](references/diagnostic-commands.md) — account-wide pre-flight gather-info commands, the secret-state short-circuit table, and every step's probe commands (Steps 2-12b)
- [Worked examples](references/worked-examples.md) — SCHEDULE_MISSING and INSUFFICIENT_DATA worked examples plus the malformed-input re-prompt template
- [Error handling](references/error-handling.md) — pre-flight safety checks before state-changing CLIs and per-layer remediation guidance with fix and verify commands
- [Advanced patterns](references/advanced-patterns.md) — mindset, philosophy, Step 0 non-obvious behaviours, the rotation layer model, recent AWS features (2024-2026)
- [Rotation Lambda reference](references/rotation-lambda-reference.md) — rotation Lambda internals, four-step protocol contract, configuration defaults
- [Rotation strategy reference](references/rotation-strategy-reference.md) — Alternating vs Single User strategy and rotation template family detail

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
