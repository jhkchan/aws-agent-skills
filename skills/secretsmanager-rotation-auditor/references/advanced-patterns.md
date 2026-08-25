# Advanced Patterns — Secrets Manager Rotation Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

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

## Step 0 — input schema (describe-secret fields)

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

### Step 1 — recovery window facts

The default recovery window is 30 days (minimum 7, maximum 30), set at
deletion time via `RecoveryWindowInDays`. A secret in the recovery window
still appears in `list-secrets` and can be read until the purge date. After
purge, the secret value is irrecoverable.

### Step 3 — sub-state explanations (3a–3d)

"enabled" in the config but has no Lambda to execute. This is an
inconsistent state — the `RotationEnabled` flag was set but
`RotationLambdaARN` was never populated, or was cleared after the Lambda
was deleted.

points to a Lambda that no longer exists. Secrets Manager cannot invoke a
deleted function; every scheduled rotation silently fails. The
`LastRotatedDate` will not advance.

invocations. `Inactive` Lambda functions (created from a container image
with a deleted base, or whose deployment package was removed from S3)
cannot be invoked.

functions in the same account and region as the secret. A cross-account or
cross-region ARN will produce an `AccessDeniedException` on every rotation
attempt.

### Step 4 — invocation-health context

The Lambda's CloudWatch Logs and `LastInvocationStatus` reveal whether the
rotation is actually succeeding.

fails before completing the rotation. Note the specific error code in the
REASON field.

  `aws lambda get-function-concurrency --function-name <name>`. This is
  a stealth failure: the Lambda has no error logs (the invocation never
  runs), so it looks healthy in every status check.

## Step 5 — execution-role permission chain (link detail)

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

### Step 6 — AWSPENDING failure mechanics

Lambda contract" below). A version in `AWSPENDING` means the rotation
failed between `setSecret` (step 2) and `finishSecret` (step 4) — the
new credential was generated and possibly applied to the target, but
never promoted to `AWSCURRENT`.

credential (from `setSecret`) but the secret's `AWSCURRENT` stage still
points to the old version. Applications reading the secret get the old
password; the database has the new password — a credential mismatch that
causes authentication failures across the workload.

### Step 7a — never-rotated explanation

  multiple intervals means every rotation attempt has silently failed.
  The Lambda may show `State: Active` (it exists) but the invocations
  are erroring (Step 4a). This is the most commonly missed finding —
  the posture appears "managed" but no rotation has ever succeeded.

## Step 7 — interval edge cases

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

## Recent AWS features (2024-2026)

- **Cross-account secret access (2024):** Secrets Manager now supports cross-account secret access via resource policies. Auditors should verify that cross-account access policies include `aws:SourceAccount` conditions and that only intended accounts can read secrets.
- **Rotation strategy templates (2024-2025):** New rotation Lambda templates for additional database engines and third-party services. Auditors should verify that the rotation Lambda uses the latest template version and that custom rotation functions follow AWS best practices.
- **Amazon Q integration (2024):** Secrets Manager integrates with Amazon Q Developers for secret detection in code. No direct audit-surface change, but auditors should verify that Q's scanning does not inadvertently expose secret values in logs.
- **Secret replication across regions (2024):** Secrets can now be replicated across regions for DR. Auditors should verify that replicated secrets have equivalent KMS encryption in the destination region and that rotation status is consistent across replicas.

