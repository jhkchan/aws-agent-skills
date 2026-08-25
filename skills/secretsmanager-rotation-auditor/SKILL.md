---
name: secretsmanager-rotation-auditor
description: 'Audits AWS Secrets Manager secrets for rotation posture — rotation enablement, rotation-Lambda health (existence, execution-role permissions, VPC connectivity, invocation errors), staleness against the configured rotation interval, stuck AWSPENDING versions, and recovery-window state. Classifies each secret as UNROTATED, ROTATION_BROKEN, STALE, or OK with risk-severity and concrete remediation. Use when reviewing secret rotation health, validating rotation-Lambda wiring, investigating failed rotations, or auditing credential hygiene before compliance gates. Triggers: Secrets Manager, secret rotation, rotation Lambda, LastRotatedDate, AutomaticallyAfterDays, AWSPENDING, rotation broken, stale secret, unrotated secret, recovery window, credential hygiene, compliance check, RDS credentials, API token rotation.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf). No AWS CLI required for offline config-text classification. Live-account audits use aws secretsmanager describe-secret, list-secret-version-ids, and aws lambda get-function / get-policy (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  verdict_shape: UNROTATED | ROTATION_BROKEN | STALE | OK
  when_to_use: Reviewing a Secrets Manager secret's rotation posture, validating rotation-Lambda wiring, investigating a failed or stuck rotation, checking whether a credential is overdue, auditing credential hygiene before a compliance gate, or reviewing secrets in a recovery window.
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Secrets Manager, secret rotation, rotation Lambda, LastRotatedDate, AutomaticallyAfterDays, AWSPENDING, unrotated secret, stale secret, rotation broken, recovery window, credential hygiene, compliance, RDS credentials, API token rotation, KMS key, SecretsManagerRotation
  tags: aws, secretsmanager, cloudops, security, rotation, compliance, credential-hygiene
  dependencies: aws-orchestrator
---

# Secrets Manager Rotation Auditor

## Mindset

Audit each secret against a single question: **does the credential in this
secret actually rotate on schedule, and does the rotation succeed end-to-end?**

A secret with `RotationEnabled: true` is NOT necessarily rotating. Rotation
is a chain of four dependencies — the rotation config, the Lambda function,
the Lambda execution role + KMS key, and the target resource's reachability.
Any broken link in the chain means the secret appears "managed" to a
compliance dashboard but the credential is static in production. The most
dangerous posture is `ROTATION_BROKEN`: it creates a false sense of security
because someone enabled rotation, but the Lambda is silently failing and the
secret value has not changed since creation.

The classification logic checks the chain **in dependency order**, from the
outermost gate (is rotation even enabled?) inward (is the Lambda's
execution-role permission chain complete?), so the first failing dependency
is the root cause — not a downstream symptom.

## Quick reference

If `RotationEnabled` is `false` or absent, the secret is **UNROTATED**. If
rotation is enabled but `LastRotatedDate` is null and rotation has been
enabled for more than one interval, the secret is **ROTATION_BROKEN**
(every scheduled rotation has silently failed — this is the most commonly
missed finding). If rotation is enabled but the Lambda is deleted, inactive,
erroring on invocation, or has no execution-role permissions, the secret is
**ROTATION_BROKEN**. If a version is stuck in `AWSPENDING`, the secret is
**ROTATION_BROKEN** (rotation failed mid-flight). If rotation is enabled
and the Lambda is healthy but `LastRotatedDate` is overdue beyond
`AutomaticallyAfterDays`, the secret is **STALE**. If all checks pass and
the last rotation is within schedule, the secret is **OK**.

If `DeletedDate` is present, emit a `DELETION_FLAG` line BEFORE the VERDICT
block — the secret is in the recovery window and will be permanently purged.
Continue with the normal classification for the audit record.

See the steps below for the edge cases (null `LastRotatedDate` with
first-rotation window, recovery window, interval anomalies, multi-region
replica secrets, Lambda concurrency limits).

## Process — Classification logic (apply in order)

### Step 0: Validate input and pre-flight

**Input schema.** The skill expects these fields from `describe-secret`
output (plus optional Lambda metadata from `get-function`):

| Field | Type | Notes |
|---|---|---|
| `Name` | string | Required. |
| `RotationEnabled` | boolean | Absent = `false`. |
| `RotationLambdaARN` | string \| null | Required if rotation enabled. |
| `RotationRules.AutomaticallyAfterDays` | integer 1–365 \| null | Required if rotation enabled. |
| `LastRotatedDate` | ISO 8601 \| null | Null = never rotated. |
| `LastChangedDate` | ISO 8601 \| null | Tracks any metadata/value change. |
| `DeletedDate` | ISO 8601 \| null | Present = in recovery window. |
| `PrimaryRegion` | string \| null | Present = replica secret. |
| `VersionIdsToStages` | map\<version → [stages]\> | Check for `AWSPENDING`. |
| `KmsKeyId` | string | Absent = default `aws/secretsmanager`. |

If the secret name is missing or `RotationEnabled` is not a boolean or
`RotationRules` is not a map, output:

```text
SECRET: <name or "(unknown)">
VERDICT: ERROR
REASON: Secret config is incomplete or unparseable — cannot evaluate rotation posture.
REMEDIATION: Re-run aws secretsmanager describe-secret --secret-id <name> and provide the full output.
```

Do not attempt classification on malformed input.

**Replica pre-flight (run BEFORE Step 1).** Check `PrimaryRegion`. If
`PrimaryRegion` is set and non-null, the secret is a **replica** in a
multi-Region setup. Replicas are read-only — rotation CANNOT be enabled
on them (only the primary can rotate, and Secrets Manager returns
`InvalidParameterException` if you try). A replica with
`RotationEnabled: false` is EXPECTED, not UNROTATED. Emit and stop:
```text
SECRET: <name>
VERDICT: OK
REASON: Replica secret (PrimaryRegion: <region>). Rotation runs on the
        primary; the replica inherits the rotated value automatically.
        Audit the primary secret in <PrimaryRegion> for rotation posture.
RISK: LOW
REMEDIATION: None required on the replica. Verify rotation health on the
             primary secret in region <PrimaryRegion>.
```
Do NOT apply Steps 2–8 to a replica — doing so produces false-positive
UNROTATED or ROTATION_BROKEN classifications.

### Step 1: Recovery-window / deletion check (pre-flight flag)

If `DeletedDate` is present, the secret is in the **recovery window** —
scheduled for permanent deletion. Emit a `DELETION_FLAG` before the normal
classification block. The flag does NOT change the verdict; it adds context
that the secret will be purged and may need restoration.
```text
DELETION_FLAG: Secret "<name>" is in the recovery window (DeletedDate:
<date>, scheduled permanent deletion in <N> days). If this secret is still
used by any workload, restore it immediately: aws secretsmanager
restore-secret --secret-id <name>. If deletion is intentional, verify no
application references it before the purge date.
```

The default recovery window is 30 days (minimum 7, maximum 30), set at
deletion time via `RecoveryWindowInDays`. A secret in the recovery window
still appears in `list-secrets` and can be read until the purge date. After
purge, the secret value is irrecoverable.

Continue to Step 2 for rotation classification — even a deleted secret's
posture matters for the audit record (a deleted secret that was UNROTATED
may indicate a cleanup after a credential-theft incident).

### Step 2: Rotation not enabled — UNROTATED

If `RotationEnabled` is `false` or the field is absent, the secret has no
automatic rotation. **VERDICT: UNROTATED.**

Assign RISK by secret type (see full rationale in the Risk Matrix
below): RDS/Redshift = **CRITICAL** (CIS Benchmark 1.18), DocDB/Neptune/
AmazonMQ = **HIGH**, API tokens/OAuth = **HIGH**, SSH keys = **MODERATE**,
non-credential config secrets = **LOW**. If the secret type is `Other`
and has no rotation enabled, note that a custom rotation Lambda is
required — no AWS-managed template exists for type `Other`.

### Step 3: Rotation Lambda existence and state

If `RotationEnabled` is `true`, the secret points to a rotation Lambda via
`RotationLambdaARN`. Verify the Lambda exists and is invocable. Apply the
first matching rule:

**Step 3a: No Lambda ARN configured.** If `RotationLambdaARN` is `null`,
empty, or the string `"null"` — **VERDICT: ROTATION_BROKEN**. Rotation is
"enabled" in the config but has no Lambda to execute. This is an
inconsistent state — the `RotationEnabled` flag was set but
`RotationLambdaARN` was never populated, or was cleared after the Lambda
was deleted.

**Step 3b: Lambda function deleted (404).** If the Lambda's `State` is
`Deleted`, or the Lambda returns `ResourceNotFoundException` —
**VERDICT: ROTATION_BROKEN**, risk **CRITICAL**. The rotation config
points to a Lambda that no longer exists. Secrets Manager cannot invoke a
deleted function; every scheduled rotation silently fails. The
`LastRotatedDate` will not advance.

**Step 3c: Lambda function inactive or failed.** If the Lambda `State` is
`Failed`, `Inactive`, or `Pending` (stuck in creation) —
**VERDICT: ROTATION_BROKEN**. The function exists but cannot accept
invocations. `Inactive` Lambda functions (created from a container image
with a deleted base, or whose deployment package was removed from S3)
cannot be invoked.

**Step 3d: Lambda cross-region or cross-account.** If the `RotationLambdaARN`
contains a different region or account ID than the secret —
**VERDICT: ROTATION_BROKEN**. Secrets Manager can only invoke Lambda
functions in the same account and region as the secret. A cross-account or
cross-region ARN will produce an `AccessDeniedException` on every rotation
attempt.

### Step 4: Lambda invocation health

If the Lambda exists and is `Active`, check its last invocation result.
The Lambda's CloudWatch Logs and `LastInvocationStatus` reveal whether the
rotation is actually succeeding.

**Step 4a: Last invocation errored.** If `LastInvocation.Status` is `ERROR`
or `TIMED_OUT`, examine the error code to determine root cause:

| Error code / pattern | Root cause | Classification note |
|---|---|---|
| `AccessDeniedException` on `secretsmanager:GetSecretValue` | Lambda execution role lacks Secrets Manager permissions | The role is missing `secretsmanager:GetSecretValue` or the resource-based policy on the secret denies the Lambda role. |
| `AccessDeniedException` on `kms:Decrypt` | KMS key policy denies the Lambda role | The KMS key encrypting the secret does not grant `kms:Decrypt` to the Lambda execution role. The Lambda can read the secret ARN but cannot decrypt the value. |
| `ResourceNotFoundException` on target (RDS, Redshift) | Target resource deleted or unreachable | The database instance was deleted but the secret remains. The Lambda's `setSecret` step cannot connect because the endpoint no longer exists. |
| `TimeoutException` / `Task timed out` | Lambda timeout too short | Database rotation involves connect + authenticate + ALTER USER — large databases with slow connections may exceed the default 30s timeout. |
| `OperationError` / `ConnectionRefused` | VPC misconfiguration | Lambda subnets or security groups cannot reach the target resource (wrong subnet, missing route, security group rule missing). |
| `InvalidParameterException` on `createSecret` | Secret value template malformed | The Lambda's secret-value generation template produces invalid characters for the target (e.g., `$` in a MySQL password). |

In all error cases — **VERDICT: ROTATION_BROKEN**. The Lambda runs but
fails before completing the rotation. Note the specific error code in the
REASON field.

**Step 4b: Lambda never invoked.** If the Lambda has zero invocations AND
rotation has been enabled for longer than one interval (see Step 6 for
the freshness check) — **VERDICT: ROTATION_BROKEN**. Secrets Manager is
not triggering the Lambda. This can happen when:
- The EventBridge schedule is misconfigured or deleted.
- The Lambda resource-based policy does not allow
  `lambda:InvokeFunction` from the `secretsmanager.amazonaws.com`
  principal.
- The `RotationRules.AutomaticallyAfterDays` is set to a value greater
  than 365 (invalid — max is 365 days; Secrets Manager silently treats
  invalid values as "never schedule").
- The Lambda has **reserved concurrency set to 0** — the function
  appears `Active` but every invocation is throttled. Check with
  `aws lambda get-function-concurrency --function-name <name>`. This is
  a stealth failure: the Lambda has no error logs (the invocation never
  runs), so it looks healthy in every status check.

### Step 5: Execution-role permission chain

The rotation Lambda's execution role must have a complete permission chain
to perform the four-step rotation contract. Check each link:

**Link 1 — Secrets Manager API permissions.** The Lambda role must have
(`secretsmanager:DescribeSecret`, `secretsmanager:GetSecretValue`,
`secretsmanager:PutSecretValue`,
`secretsmanager:UpdateSecretVersionStage`) on the secret ARN. The
AWS-managed policy `SecretsManagerRotation` grants these on `"*"`. A
custom policy that scopes to the specific secret ARN is preferred but
must include all four actions.

**Link 2 — KMS decrypt permission.** If the secret is encrypted with a
customer-managed KMS key (not the default `aws/secretsmanager` key), the
Lambda role must have `kms:Decrypt` on the KMS key ARN. The default
managed key allows all principals in the account, but a customer-managed
key's policy must explicitly grant the Lambda role.

**Link 3 — VPC network access (for database targets).** If the target is
an RDS/Redshift/DocDB instance in a VPC, the Lambda must be VPC-attached
(`VpcConfig` with subnets and security groups). The Lambda execution role
must have `ec2:CreateNetworkInterface`,
`ec2:DescribeNetworkInterfaces`, `ec2:DeleteNetworkInterface` (granted by
`AWSLambdaVPCAccessExecutionRole`). The security group attached to the
Lambda must allow egress to the database's security group on the DB port.

**Link 4 — Target resource credential match.** The `AWSCURRENT` version
of the secret must contain credentials that match the target database's
actual password. If someone manually changed the DB password outside of
rotation (e.g., via `ALTER USER`), the Lambda's `setSecret` step will
fail to authenticate because it uses the `AWSCURRENT` credential to log
in before changing it.

If any link is broken — **VERDICT: ROTATION_BROKEN** with the specific
broken link cited in the REASON.

### Step 6: AWSPENDING stuck version

Check `VersionIdsToStages` for any version stuck in the `AWSPENDING`
stage. The rotation Lambda follows a four-step contract (see "Rotation
Lambda contract" below). A version in `AWSPENDING` means the rotation
failed between `setSecret` (step 2) and `finishSecret` (step 4) — the
new credential was generated and possibly applied to the target, but
never promoted to `AWSCURRENT`.

If `AWSPENDING` is present — **VERDICT: ROTATION_BROKEN**, risk **HIGH**.
The secret is in an inconsistent state: the target may have the new
credential (from `setSecret`) but the secret's `AWSCURRENT` stage still
points to the old version. Applications reading the secret get the old
password; the database has the new password — a credential mismatch that
causes authentication failures across the workload.

**Multiple `AWSPENDING` versions** indicate repeated failed rotation
attempts — each failed rotation leaves a pending version behind. Clean up
stale pending versions after fixing the root cause.

### Step 7: Freshness / staleness check

If the Lambda is healthy (Active, last invocation succeeded, no stuck
AWSPENDING), evaluate whether the last rotation is within the configured
schedule.

**Determine the effective interval:** if
`RotationRules.ScheduleExpression` is present (a cron expression like
`"rate(30 days)"` or `"cron(0 9 ? * MON *)"`), derive the interval from
it — `ScheduleExpression` OVERRIDES `AutomaticallyAfterDays`. Otherwise
use `RotationRules.AutomaticallyAfterDays` as the interval in days.

Compute: `days_since_rotation = now - LastRotatedDate` (in days).

**Step 7a: `LastRotatedDate` is null.** The secret has never been
rotated. Two sub-cases:

- **Rotation enabled for less than one interval** (using `LastChangedDate`
  or `CreatedDate` as the proxy for when rotation was enabled):
  **VERDICT: OK** with a note: "First rotation has not yet executed —
  pending initial rotation within the first `AutomaticallyAfterDays`
  window. Monitor for the first successful rotation."

- **Rotation enabled for more than one interval**: **VERDICT:
  ROTATION_BROKEN**. The Lambda should have rotated the secret at least
  once by now. A null `LastRotatedDate` with rotation enabled for
  multiple intervals means every rotation attempt has silently failed.
  The Lambda may show `State: Active` (it exists) but the invocations
  are erroring (Step 4a). This is the most commonly missed finding —
  the posture appears "managed" but no rotation has ever succeeded.

**Step 7b: `LastRotatedDate` is present and within schedule.** If
`days_since_rotation <= AutomaticallyAfterDays` — the secret is within
its rotation window. **VERDICT: OK**.

**Step 7c: `LastRotatedDate` is present and overdue.** If
`days_since_rotation > AutomaticallyAfterDays`:

Compute `overdue_ratio = days_since_rotation / AutomaticallyAfterDays`.

- `1.0 < overdue_ratio <= 2.0` — **VERDICT: STALE**, risk **MODERATE**.
  The rotation is overdue by up to one full interval. Secrets Manager
  schedules rotations with a small jitter (up to 1 hour); a few hours
  overdue is normal. Days overdue indicates the Lambda is intermittently
  failing — some rotations succeed, some fail.

- `overdue_ratio > 2.0` — **VERDICT: STALE**, risk **HIGH**. The secret
  is overdue by more than two full intervals — the rotation has been
  failing for an extended period. The credential is effectively static.
  While the Lambda still exists and may occasionally succeed, the secret
  value has not changed in a meaningful timeframe. This is functionally
  equivalent to UNROTATED from a risk perspective, but the root cause
  is a broken rotation mechanism rather than a missing one.

**Interval edge cases:**

- `AutomaticallyAfterDays` not set (null) — treat as ROTATION_BROKEN.
  Rotation is "enabled" but has no schedule. Secrets Manager requires
  `AutomaticallyAfterDays` to trigger rotation.
- `AutomaticallyAfterDays > 365` — invalid. The maximum is 365 days
  (minimum is 1). An invalid value causes Secrets Manager to never
  schedule the rotation silently.
- `LastChangedDate` is more recent than `LastRotatedDate` — someone
  manually edited the secret (metadata or value) after the last
  rotation. If the value was changed, the credential in the secret may
  no longer match the target resource. Flag as a note: "Secret was
  modified after the last rotation — verify the AWSCURRENT value matches
  the target resource credential."

### Step 8: OK

If rotation is enabled, the Lambda exists and is Active, the execution
role has the required permissions, no version is stuck in AWSPENDING,
and `LastRotatedDate` is within the configured interval —
**VERDICT: OK**, risk **LOW**.

### Output format (per secret)

If `DeletedDate` is present, ALWAYS emit a `DELETION_FLAG` line FIRST,
before the VERDICT block. If `DeletedDate` is absent, do NOT emit any
DELETION_FLAG line — simply omit it entirely and start with `SECRET:`.

Emit all output as plain text. Do NOT wrap the output in code fences
(no triple-backtick, no YAML wrapper).

Template when DeletedDate is present:
```text
DELETION_FLAG: Secret "<name>" is in the recovery window (DeletedDate:
<date>, permanent deletion in <N> days). Restore if still needed.
SECRET: <name>
VERDICT: UNROTATED | ROTATION_BROKEN | STALE | OK
REASON: <1-2 sentences citing the specific config and which step fired>
RISK: CRITICAL | HIGH | MODERATE | LOW
REMEDIATION: <specific action, or "None required" if OK>
```

Template when DeletedDate is absent:
```text
SECRET: <name>
VERDICT: UNROTATED | ROTATION_BROKEN | STALE | OK
REASON: <1-2 sentences citing the specific config and which step fired>
RISK: CRITICAL | HIGH | MODERATE | LOW
REMEDIATION: <specific action, or "None required" if OK>
```

### Multi-secret aggregation

When auditing multiple secrets in a single run, emit one VERDICT block per
secret. The aggregate posture is the worst verdict across all secrets,
where `ROTATION_BROKEN` is worse than `UNROTATED` (broken rotation is
riskier because it implies a false sense of security), `UNROTATED` is worse
than `STALE` (no rotation at all is worse than late rotation), and `STALE`
is worse than `OK`.

### Worked examples

**Recovery-window secret with no rotation (DeletedDate present):**
```text
DELETION_FLAG: Secret "payment-gateway-api-token" is in the recovery window
(DeletedDate: 2026-08-12, scheduled permanent deletion in 8 days). If this
secret is still used by any workload, restore it: aws secretsmanager
restore-secret --secret-id payment-gateway-api-token.
SECRET: payment-gateway-api-token
VERDICT: UNROTATED
REASON: Step 2 (rotation not enabled) — RotationEnabled is false and
        LastRotatedDate has never been set. The API token is static.
        HIGH risk for API tokens (unbounded credential-theft window).
RISK: HIGH
REMEDIATION: If the secret is still needed, restore it and enable rotation
             with a custom Lambda (type "Other" has no managed template).
             If deletion is intentional, verify no workload references it.
```

**Null LastRotatedDate with rotation enabled for multiple intervals (DeletedDate absent):**
```text
SECRET: legacy-oracle-credentials
VERDICT: ROTATION_BROKEN
REASON: Step 7a — RotationEnabled is true but LastRotatedDate is null and
        rotation has been enabled for ~90 days (3x the 30-day interval).
        Every scheduled rotation has silently failed. The Lambda's last
        invocation errored with ResourceNotFoundException — the target RDS
        instance was deleted on 2026-06-15.
RISK: HIGH
REMEDIATION: The target RDS instance is deleted — the Lambda cannot rotate
             against a non-existent database. Either delete the orphaned
             secret or retarget it to the replacement instance, then
             trigger a manual rotation to verify.
```

## Rotation Lambda contract (expert reference)

Secrets Manager rotation is implemented as a four-step Lambda invocation.
Secrets Manager calls the Lambda with an `event` containing `Step` field
set to one of four values. The Lambda function must implement a handler for
each:

1. **`createSecret`** — The Lambda checks whether the secret already has a
   version in `AWSPENDING` stage. If not, it generates a new secret value
   (password, API key, etc.) and calls `PutSecretValue` with the new value
   in a new version, tagged `AWSPENDING`. If `AWSPENDING` already exists
   (from a previous failed attempt), the Lambda may reuse it or generate
   a new value depending on the template implementation.

   *Fails when:* KMS key disabled (cannot encrypt the new version),
   `PutSecretValue` permission denied, or the secret-value generation
   template produces characters invalid for the target (e.g., `/` in a
   database password that breaks connection-string parsing).

2. **`setSecret`** — The Lambda reads the `AWSPENDING` version's credential
   and applies it to the target resource. For an RDS secret, this means:
   connect to the DB using the `AWSCURRENT` credential, then `ALTER USER`
   to change the password to the `AWSPENDING` value.

   *Fails when:* The `AWSCURRENT` credential no longer matches the DB
   (someone manually changed the DB password), the DB instance is deleted
   or unreachable, VPC network path is broken, or the DB rejects the new
   password (complexity policy, character encoding).

3. **`testSecret`** — The Lambda attempts to log in to the target resource
   using the `AWSPENDING` credential to verify it works. This is a
   validation step — it does not modify any state.

   *Fails when:* The credential in `AWSPENDING` doesn't match what was set
   in `setSecret` (race condition), the target enforces a connection limit
   and the Lambda can't get a connection, or the login times out.

4. **`finishSecret`** — The Lambda calls `UpdateSecretVersionStage` to move
   `AWSCURRENT` to the new version and move the old version to
   `AWSPREVIOUS`. This is the commit step — once `AWSCURRENT` moves, all
   applications reading the secret get the new credential.

   *Fails when:* `UpdateSecretVersionStage` permission denied. If this
   step fails, the secret is left with `AWSPENDING` pointing to the new
   credential (which is already live on the target) but `AWSCURRENT` still
   pointing to the old credential — a mismatch.

**A stuck `AWSPENDING` version** is the forensic signature of a rotation
that failed at step 2 or 3. The new credential may or may not be live on
the target resource (depending on whether `setSecret` completed before the
failure), but the secret's `AWSCURRENT` stage was never updated.

## Expert knowledge — rotation scheduling and failure modes

This section consolidates non-obvious AWS-specific behaviors that affect
rotation correctness. Each subsection addresses a distinct failure domain.

### Rotation scheduler internals

Secrets Manager schedules rotations using an internal EventBridge-based
scheduler, not a customer-visible EventBridge rule. The scheduler evaluates
`RotationRules.AutomaticallyAfterDays` and opens a rotation window on the
calculated day. Key behaviors:

- **Rotation window:** `RotationRules.Duration` (ISO 8601, default `"PT24H"`)
  defines how long the window stays open. If the Lambda does not complete
  within this window, the rotation is abandoned and retried on the next
  schedule tick. A Lambda timeout shorter than the actual rotation duration
  causes the invocation to fail, but the window remains open for a retry —
  if no retry succeeds within 24 hours, the rotation is skipped.

- **Scheduling jitter:** Secrets Manager does not rotate at the exact second
  of `LastRotatedDate + AutomaticallyAfterDays`. It rotates within a window
  starting at midnight UTC on the scheduled day. A few hours of delay is
  normal; days of delay indicate a problem.

- **`NextRotationDate` field:** Secrets Manager populates this in
  `describe-secret` output when rotation is enabled and scheduled. If
  `NextRotationDate` is absent while `RotationEnabled` is true, the
  scheduler has not been initialized — this can happen immediately after
  enabling rotation or when `AutomaticallyAfterDays` is invalid.

### Lambda concurrency limits and rotation

The rotation Lambda is subject to standard Lambda concurrency limits
(account-level reserved and unreserved concurrency). If the function has
**reserved concurrency set to 0** (a common misconfiguration when someone
"pauses" a function), Secrets Manager's invocation is throttled and the
rotation fails silently. Similarly, if the **account's unreserved
concurrency pool is exhausted** by other functions at the moment of
rotation, the invocation is throttled.

Check with:
```bash
aws lambda get-function-concurrency --function-name <rotation-lambda>
aws lambda get-account-settings --query 'AccountLimit'
```

A rotation Lambda should have a **minimum reserved concurrency of 1** to
guarantee the rotation invocation is never throttled by unrelated traffic.

### Multi-region replica secrets

Secrets created with multi-Region replication (`PrimaryRegion` set) have a
primary secret and one or more replica secrets. **Rotation can only run
against the primary** — replica secrets are read-only copies synchronized
from the primary. If you attempt to enable rotation on a replica, Secrets
Manager returns an `InvalidParameterException`.

When auditing multi-Region secrets:
- Verify rotation on the **primary** only. Replicas inherit the rotated
  value automatically.
- The rotation Lambda must be deployed in the **primary region**.
- The `ForceOverwriteReplicaSecret` parameter on `UpdateSecret` /
  `PutSecretValue` controls whether replica overwrites are forced during
  regional outages. This is an advanced DR setting — flag if present.

### SecretsManagerRotation managed policy scope

The AWS-managed `SecretsManagerRotation` policy grants
`secretsmanager:*` on `"*"` (all secrets in the account). This is itself
over-permissive — a compromised rotation Lambda could read or modify any
secret. For production, replace it with a custom policy scoped to the
specific secret ARN:
```json
{
  "Effect": "Allow",
  "Action": [
    "secretsmanager:DescribeSecret",
    "secretsmanager:GetSecretValue",
    "secretsmanager:PutSecretValue",
    "secretsmanager:UpdateSecretVersionStage"
  ],
  "Resource": "arn:aws:secretsmanager:<region>:<account>:secret:<name>-??????"
}
```
The six-character suffix (`-??????`) is required because Secrets Manager
auto-appends a random 6-character alphanumeric to the secret name in the ARN.

### HostedRotationLambda and ScheduleExpression

Two newer features affect how rotation is configured and audited:

- **`RotationRules.ScheduleExpression`** (added 2023): a cron-style
  expression (`"rate(7 days)"` or `"cron(0 9 ? * MON *)"`). When present,
  it OVERRIDES `AutomaticallyAfterDays` — the scheduler uses the cron
  expression. If both are set, `ScheduleExpression` wins. When auditing
  freshness, use `ScheduleExpression` (if present) to compute the expected
  interval, not `AutomaticallyAfterDays`.

- **`HostedRotationLambda`** (added 2024): Secrets Manager can create and
  manage the rotation Lambda for you (no customer-owned function). The
  `RotationLambdaARN` points to an AWS-managed function. This removes the
  execution-role and permission-chain failure modes for Steps 3–5 — the
  function is always `Active`, the permissions are always correct, and
  the function code is maintained by AWS. When the ARN contains
  `secretsmanager` in the function name or matches the hosted pattern,
  skip the execution-role checks (Step 5) — they are managed by AWS.

### CloudTrail events for rotation monitoring

`describe-secret` does NOT surface rotation Lambda errors — it returns
only metadata. To diagnose rotation failures, use CloudTrail and
CloudWatch Logs:

- `CreateSecret`, `UpdateSecret`, `PutSecretValue`,
  `UpdateSecretVersionStage` — logged in CloudTrail under
  `secretsmanager.amazonaws.com`. A successful `finishSecret` shows
  `UpdateSecretVersionStage` moving `AWSCURRENT`.
- `RotationFailed` — a CloudWatch Events (EventBridge) event emitted by
  Secrets Manager when a rotation fails. Pattern:
  `{"source":["aws.secretsmanager"],"detail-type":["Secret Rotation Failed"]}`.
- The Lambda's own CloudWatch Logs (`/aws/lambda/<function-name>`) contain
  the actual error — `Task timed out`, `AccessDeniedException`, etc.

### Secrets Manager rotation quotas

- Maximum 10 concurrent rotations per account per region (soft limit,
  adjustable via quota increase). Beyond this, rotations are queued.
- `RotationRules.AutomaticallyAfterDays`: minimum 1, maximum 365.
- `RotationRules.Duration`: ISO 8601 duration, default `"PT24H"`,
  maximum `"PT24H"`.
- A single Lambda function can serve as the rotation function for
  multiple secrets — but this is a blast-radius risk if the function
  breaks. Monitor the function, not just individual secrets.

## Risk / severity matrix (emit exactly one RISK per secret)

| Verdict | Condition | Risk |
|---|---|---|
| ROTATION_BROKEN | Lambda deleted (404) | CRITICAL |
| ROTATION_BROKEN | `AWSPENDING` stuck version | HIGH |
| ROTATION_BROKEN | Never rotated (null `LastRotatedDate`, enabled >1 interval) | HIGH |
| ROTATION_BROKEN | Lambda invocation erroring (permission denied, target deleted, timeout) | HIGH |
| ROTATION_BROKEN | No Lambda ARN configured | HIGH |
| UNROTATED | RDS / Redshift / DBCluster credentials (no rotation) | CRITICAL |
| UNROTATED | API tokens / OAuth (no rotation) | HIGH |
| UNROTATED | SSH keys / custom credentials (no rotation) | MODERATE |
| UNROTATED | Non-credential secrets (config, feature flags) | LOW |
| STALE | `overdue_ratio > 2.0` (more than 2x interval overdue) | HIGH |
| STALE | `1.0 < overdue_ratio <= 2.0` (up to 1 interval overdue) | MODERATE |
| OK | Within schedule, Lambda healthy | LOW |

**UNROTATED risk-by-secret-type rationale:**

| Secret type / target | Risk | Rationale |
|---|---|---|
| `AWS::RDS::DBInstance`, `AWS::RDS::DBCluster` | CRITICAL | Static DB passwords — theft window is unbounded. CIS AWS Foundations Benchmark 1.18. |
| `AWS::Redshift::Cluster` | CRITICAL | Same as RDS — static data-warehouse credentials. |
| `AWS::DocDB::DBCluster`, `AWS::Neptune::DBCluster`, `AWS::AmazonMQ::Broker` | HIGH | Managed-DB credentials — blast radius narrower than RDS but still high. |
| API tokens / OAuth / third-party (type `Other`) | HIGH | Static API keys — theft window is unbounded; most providers recommend 30–90 day rotation. |
| SSH keys, TLS private keys (type `Other`) | MODERATE | Typically rotated via config management, not Secrets Manager rotation Lambda. |
| Non-credential secrets (feature flags, static config) | LOW | Not credentials — rotation provides no security benefit. |

**AWS-provided rotation Lambda templates** (secret types with built-in
support — all others require a custom Lambda implementing the four-step
contract):

- `AWS::RDS::DBInstance` — MySQL, PostgreSQL, Oracle, SQL Server
  (templates differ by engine; Oracle uses `MasterSecret` rotation for
  multi-user mode).
- `AWS::RDS::DBCluster` — Aurora MySQL, Aurora PostgreSQL.
- `AWS::Redshift::Cluster`.
- `AWS::DocDB::DBCluster`.
- `AWS::AmazonMQ::Broker` (ActiveMQ).
- `AWS::Neptune::DBCluster`.
- Type `Other` — no managed template; user must author a custom Lambda.

## Anti-Patterns — NEVER

- NEVER classify a secret with `RotationEnabled: false` as anything other
  than **UNROTATED**. The secret has no rotation mechanism — the credential
  is static and will remain static until rotation is configured and the
  first rotation succeeds. `LastChangedDate` is NOT a substitute for
  `LastRotatedDate` — it tracks any metadata change, not credential
  rotation.

- NEVER omit the `DELETION_FLAG` line when `DeletedDate` is present in
  the input. The flag MUST appear as a separate line BEFORE the VERDICT
  block, using the exact keyword `DELETION_FLAG:`. A secret in the
  recovery window is days from permanent, irrecoverable deletion —
  omitting the flag causes an auditor to miss the time-critical
  restore-or-verify decision.

- NEVER emit a `DELETION_FLAG` line when `DeletedDate` is absent. If
  the secret is not in the recovery window, there is no flag — start
  directly with `SECRET:`. A spurious placeholder flag clutters the
  output and signals that the auditor is mechanically templating rather
  than reasoning about the config.

- NEVER wrap the VERDICT output in code fences. The output must be
  plain text so downstream parsers and CI gates can extract the
  VERDICT, RISK, and REMEDIATION fields reliably.

- NEVER classify a secret as **OK** when `LastRotatedDate` is null and
  rotation has been enabled for more than one `AutomaticallyAfterDays`
  interval. A null `LastRotatedDate` after multiple intervals means every
  scheduled rotation has silently failed. The Lambda may show `State:
  Active` (it exists as a resource), but its invocations are erroring.
  This is **ROTATION_BROKEN**, not OK.

- NEVER assume `RotationEnabled: true` means the secret is actually
  rotating. Rotation is a four-link dependency chain (config -> Lambda ->
  role/KMS -> target reachability). A single broken link makes the entire
  chain fail silently. Always verify `LastRotatedDate` advanced within the
  last interval — that is the only proof a rotation succeeded.

- NEVER treat `AWSPENDING` as a benign transient state. A version stuck in
  `AWSPENDING` means the rotation failed mid-flight. The target resource
  may have the new credential (if `setSecret` completed) while the secret's
  `AWSCURRENT` still points to the old value — a live credential mismatch
  that will cause application authentication failures.

- NEVER confuse `LastChangedDate` with `LastRotatedDate`.
  `LastChangedDate` tracks ANY modification to the secret (description,
  tags, rotation config, manual value edit). `LastRotatedDate` tracks
  ONLY the rotation event (the `finishSecret` step that moved
  `AWSCURRENT`). A secret with a recent `LastChangedDate` but an old
  `LastRotatedDate` was manually edited, not rotated.

- NEVER recommend enabling rotation without specifying the Lambda function
  ARN and the rotation interval. Setting `RotationEnabled: true` without
  `RotationLambdaARN` creates an inconsistent state where the config says
  "rotating" but there is no Lambda to invoke — every dashboard will
  report rotation as enabled while the credential remains static.

- NEVER assume the default KMS key (`aws/secretsmanager`) is in use.
  Customer-managed KMS keys have their own key policy that must
  explicitly grant `kms:Decrypt` to the Lambda execution role. If the
  key policy is missing the grant, the Lambda can call
  `GetSecretValue` (the API succeeds) but receives ciphertext it cannot
  decrypt — the error surfaces as an opaque `DecryptionFailureException`
  in the Lambda logs, not in the Secrets Manager API response.

- NEVER ignore a Lambda timeout under 30 seconds for database rotation
  targets. The `setSecret` step must connect to the database, authenticate,
  and execute `ALTER USER` — on large or slow databases (cross-AZ, heavy
  load, connection pool exhaustion), this can take 10-20 seconds. The
  default Lambda timeout of 3 seconds is insufficient. The recommended
  minimum is 30 seconds; for Aurora clusters with many instances, use
  60 seconds.

- NEVER delete a stuck `AWSPENDING` version without first verifying whether
  the credential it contains is live on the target resource. If `setSecret`
  completed before the rotation failed, the `AWSPENDING` credential is the
  actual password on the database — deleting the version does not change
  the DB password, but it loses the only record of what that password is.
  First determine which credential is live (the `AWSPENDING` value or the
  `AWSCURRENT` value) by testing a connection to the target.

- NEVER assume cross-account or cross-region rotation Lambda ARNs work.
  Secrets Manager invokes the Lambda via a resource-based policy grant.
  It can only invoke functions in the same account and region as the
  secret. A cross-account ARN will fail with `AccessDeniedException` on
  every rotation attempt.

- NEVER overlook the `lambda:InvokeFunction` resource-based policy on the
  Lambda. Secrets Manager invokes the Lambda as the
  `secretsmanager.amazonaws.com` service principal. The Lambda's
  resource-based policy must include:
  `Principal: { Service: secretsmanager.amazonaws.com }, Action:
  lambda:InvokeFunction`. Without this, Secrets Manager cannot trigger
  the rotation even if the Lambda exists and is Active.

- NEVER ignore Lambda reserved-concurrency=0 on a rotation Lambda. Setting
  reserved concurrency to 0 is functionally equivalent to disabling the
  function — no invocations are accepted, including Secrets Manager's
  rotation trigger. The function appears `Active` in every status check,
  but every invocation is throttled. This is a subtle misconfiguration
  that produces null `LastRotatedDate` with no visible Lambda error
  (the throttle is recorded in CloudWatch as a `ThrottledReason`
  invocation metric, not as a Lambda error log).

- NEVER attempt to rotate a replica secret in a multi-Region setup.
  Replicas are read-only — only the primary can be rotated. If rotation
  is failing on what appears to be a correctly configured secret, check
  whether it is a replica (`PrimaryRegion` is set and the secret's region
  differs). Rotation must run against the primary in the primary region.

- NEVER assume the `SecretsManagerRotation` managed policy is secure by
  default. It grants `secretsmanager:*` on `"*"` — the rotation Lambda
  can read or modify every secret in the account. For least-privilege,
  scope a custom policy to the specific secret ARN. This is both a
  security hardening step and a blast-radius limiter if the Lambda is
  compromised.

- NEVER overlook stale IAM policy versions when diagnosing permission
  errors. An inline policy edited to add `secretsmanager:GetSecretValue`
  creates a new policy version, but the old version may still be the
  default if it was never set as active. Check with
  `aws iam get-policy-version --policy-arn <arn> --version-id vN` and
  confirm `IsDefaultVersion: true` on the version containing the fix.
  The same applies to managed policy attachments — detaching a managed
  policy from the role does not revoke already-issued STS sessions until
  they expire (up to 12 hours for role sessions).

- NEVER conflate KMS key rotation with secret rotation. AWS KMS
  automatic key rotation (enabled via `kms:EnableKeyRotation`) rotates
  the backing key material annually — it does NOT re-encrypt existing
  secret versions. Old secret versions remain encrypted under the
  previous key material and remain decryptable. KMS key rotation is a
  defense-in-depth measure; it does NOT change when the secret's
  `LastRotatedDate` advances or make the credential itself rotate. If a
  customer-managed key was recently rotated, verify the key policy still
  grants `kms:Decrypt` to the Lambda role — key rotation preserves the
  policy, but a manually-created new key (distinct from automatic
  rotation) requires re-granting all principals.

- NEVER use `AutomaticallyAfterDays` as the freshness interval when
  `RotationRules.ScheduleExpression` is present. When a cron schedule
  expression is configured, it OVERRIDES `AutomaticallyAfterDays` — the
  scheduler uses the cron expression exclusively. Computing freshness
  against `AutomaticallyAfterDays` in this case produces incorrect
  overdue ratios and false STALE classifications. Always check for
  `ScheduleExpression` first; if present, derive the expected interval
  from the cron expression (e.g., `"rate(7 days)"` → 7-day interval).

- NEVER trigger `aws secretsmanager rotate-secret` as the FIRST
  remediation step for a ROTATION_BROKEN or STALE secret without first
  diagnosing and fixing the root cause (deleted Lambda, broken
  permissions, unreachable target, reserved-concurrency=0). Forcing an
  immediate rotation on a broken chain produces another failed rotation,
  potentially another stuck `AWSPENDING` version, and does not advance
  `LastRotatedDate`. Fix the root cause first, THEN trigger a manual
  rotation to verify the fix.

## Pre-flight safety checks (run before any remediation CLI)

- **Read-only discovery first.** Before modifying anything, list all
  secrets and their rotation status:
  ```bash
  aws secretsmanager list-secrets --query 'SecretList[].[Name,RotationEnabled,LastRotatedDate]' --output table
  ```
  This gives the full inventory without side effects. For accounts with
  more than 100 secrets, paginate with `--starting-token` (the
  `list-secrets` API returns at most 100 results per call). Use the
  `--filter` flag to scope by tag or owning service to reduce noise:
  ```bash
  aws secretsmanager list-secrets --filters Key=tag-key,Values=rotated --max-results 100
  ```

- **Check for multi-Region replica secrets.** Before auditing, determine
  whether each secret is a primary or replica:
  ```bash
  aws secretsmanager describe-secret --secret-id <name> --query '[Name,PrimaryRegion]'
  ```
  If `PrimaryRegion` is set and the secret is in a different region, it is
  a replica — audit rotation only on the primary.

- **Capture the secret's current state for rollback:**
  ```bash
  aws secretsmanager describe-secret --secret-id <name> > /tmp/<name>-describe-$(date +%s).json
  aws secretsmanager list-secret-version-ids --secret-id <name> > /tmp/<name>-versions-$(date +%s).json
  ```
  These captures are critical for incident response — if a manual
  rotation fails and creates a credential mismatch, you need the
  pre-change version IDs to restore `AWSCURRENT`.

- **Verify Lambda state before enabling rotation:**
  ```bash
  aws lambda get-function --function-name <rotation-lambda>
  aws lambda get-policy --function-name <rotation-lambda>
  ```
  Confirm `State: Active` and the resource-based policy allows
  `secretsmanager.amazonaws.com` to invoke.

- **Prefer additive changes over destructive ones.** Enabling rotation,
  fixing the execution role, and increasing the Lambda timeout are
  reversible. Deleting a stuck `AWSPENDING` version is irreversible — do
  it only after confirming the credential is not live on the target.

- **For ROTATION_BROKEN with target deleted:** if the RDS/Redshift
  instance was deleted but the secret remains, the secret is orphaned.
  Do NOT force a rotation — there is no target to rotate against.
  Either delete the secret (if it is truly orphaned) or update it to
  point to the replacement resource first.

## Remediation guidance

### For UNROTATED secrets

1. **Determine the secret type** and whether a managed rotation template
   exists (see Step 2 sub-check).
2. **For RDS/Aurora/Redshift/DocDB secrets:** use the AWS managed rotation
   template via Serverless Application Repository or CloudFormation:
   ```bash
   aws secretsmanager rotate-secret \
     --secret-id <name> \
     --rotation-lambda-arn arn:aws:lambda:<region>:<account>:function:<rotation-lambda> \
     --rotation-rules AutomaticallyAfterDays=30
   ```
3. **For API tokens / custom secrets (type `Other`):** author a custom
   rotation Lambda implementing the four-step contract
   (createSecret/setSecret/testSecret/finishSecret). See the AWS
   [Rotation function templates](https://docs.aws.amazon.com/secretsmanager/latest/userguide/reference_available-rotation-templates.html)
   reference for starter code.
4. **Set a rotation interval appropriate to the secret type:**
   - Database credentials: 30 days (industry standard; CIS benchmark)
   - API tokens: 7-90 days (depends on provider policy)
   - SSH keys: 90 days
5. **Trigger the first rotation manually** to verify the Lambda works
   before relying on the automatic schedule:
   ```bash
   aws secretsmanager rotate-secret --secret-id <name>
   ```

### For ROTATION_BROKEN secrets

1. **Lambda deleted (Step 3b):** recreate the Lambda from the rotation
   template, then update the secret's rotation config:
   ```bash
   aws secretsmanager update-secret --secret-id <name> \
     --rotation-lambda-arn arn:aws:lambda:<region>:<account>:function:<new-lambda>
   ```
2. **Lambda invocation erroring (Step 4a):** diagnose by reading the
   Lambda CloudWatch logs:
   ```bash
   aws logs filter-log-events \
     --log-group-name /aws/lambda/<rotation-lambda> \
     --filter-pattern ERROR \
     --limit 20
   ```
   Apply the fix based on the error code table in Step 4a.
3. **Execution-role permission missing (Step 5):** attach the
   `SecretsManagerRotation` managed policy or a scoped custom policy
   with the four required actions. For customer-managed KMS keys, add
   `kms:Decrypt` to the role's policy.
4. **VPC connectivity broken (Step 5, Link 3):** verify the Lambda's
   subnet route table has a path to the DB subnet, and the Lambda's
   security group allows egress to the DB security group on the DB port.
5. **AWSPENDING stuck version (Step 6):** first determine which
   credential is live on the target (test a connection with both
   `AWSCURRENT` and `AWSPENDING` values). Then either:
   - If `AWSPENDING` is the live credential: promote it to `AWSCURRENT`
     manually:
     ```bash
     aws secretsmanager update-secret-version-stage \
       --secret-id <name> \
       --version-stage AWSCURRENT \
       --move-to-version-id <pending-version-id> \
       --remove-from-version-id <current-version-id>
     ```
   - If `AWSCURRENT` is still the live credential: cancel the pending
     version:
     ```bash
     aws secretsmanager update-secret-version-stage \
       --secret-id <name> \
       --version-stage AWSPENDING \
       --remove-from-version-id <pending-version-id>
     ```
6. **After fixing the root cause:** trigger a manual rotation to verify:
   ```bash
   aws secretsmanager rotate-secret --secret-id <name>
   ```
   Check that `LastRotatedDate` advances and no new `AWSPENDING` is left
   behind.

### For STALE secrets

1. **Check CloudWatch Logs** for intermittent Lambda errors:
   ```bash
   aws logs filter-log-events \
     --log-group-name /aws/lambda/<rotation-lambda> \
     --start-time <last-rotation-epoch> \
     --limit 50
   ```
2. **Increase the Lambda timeout** if timeouts are the cause (common for
   large databases).
3. **Trigger a manual rotation** to bring the credential current:
   ```bash
   aws secretsmanager rotate-secret --secret-id <name>
   ```
4. **Monitor the next scheduled rotation** to verify it succeeds
   automatically. If the next rotation also fails, escalate to
   ROTATION_BROKEN diagnosis.

### For OK secrets

1. No remediation required.
2. Optionally set up a CloudWatch alarm on rotation failure:
   ```bash
   aws cloudwatch put-metric-alarm \
     --alarm-name "<name>-rotation-failed" \
     --metric-name RotationFailed \
     --namespace AWS/SecretsManager \
     --dimensions Name=SecretId,Value=<name> \
     --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold \
     --period 300 --evaluation-periods 1
   ```

### For secrets in the recovery window (DELETION_FLAG)

1. **Verify no workload references the secret** — search application
   configurations, environment variables, and infrastructure code for
   the secret ARN or name.
2. **If still needed, restore:**
   ```bash
   aws secretsmanager restore-secret --secret-id <name>
   ```
3. **If deletion is intentional and no workload references it:**
   allow the purge to proceed. Document the deletion in the change
   management record.

## Recent AWS features (2024-2026)

- **Cross-account secret access (2024):** Secrets Manager now supports cross-account secret access via resource policies. Auditors should verify that cross-account access policies include `aws:SourceAccount` conditions and that only intended accounts can read secrets.
- **Rotation strategy templates (2024-2025):** New rotation Lambda templates for additional database engines and third-party services. Auditors should verify that the rotation Lambda uses the latest template version and that custom rotation functions follow AWS best practices.
- **Amazon Q integration (2024):** Secrets Manager integrates with Amazon Q Developers for secret detection in code. No direct audit-surface change, but auditors should verify that Q's scanning does not inadvertently expose secret values in logs.
- **Secret replication across regions (2024):** Secrets can now be replicated across regions for DR. Auditors should verify that replicated secrets have equivalent KMS encryption in the destination region and that rotation status is consistent across replicas.

## Domain

AWS CloudOps / Secrets Manager Security & Compliance.

## AWS documentation

- **AWS Secrets Manager User Guide** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html
- **Secrets Manager Security** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/security.html
- **Secrets Manager API Reference** — https://docs.aws.amazon.com/secretsmanager/latest/apireference/
- **Secrets Manager CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/
- **Rotating secrets** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html
