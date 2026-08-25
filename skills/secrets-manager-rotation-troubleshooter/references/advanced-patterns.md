# Advanced Patterns — Secrets Manager Rotation Troubleshooter

Mindset, philosophy, expert-knowledge deep dives, the rotation layer model, and recent-feature notes moved out of the SKILL.md body. Loaded on demand.


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

## Step 0: Rotation protocol and non-obvious behaviours

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
