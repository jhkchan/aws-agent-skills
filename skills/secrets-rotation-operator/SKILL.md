---
name: secrets-rotation-operator
description: Operates AWS Secrets Manager rotation workflows end-to-end — rotation Lambda setup (Python template + IAM), rotation configuration (Lambda ARN, cron schedule, automatic vs manual), the four-step rotation cycle (createSecret, setSecret, testSecret, finishSecret with AWSPENDING and AWSCURRENT stage transitions), cross-account Lambda resource-based policies, RDS managed templates vs custom, and full diagnostic loops (describe-secret, get-resource-policy, lambda get-function-configuration, CloudWatch Logs). Runs deterministic pre-checks (Lambda state, execution role, KMS decrypt, VPC ENI reachability, AWSPENDING stuck versions, reserved concurrency) behind a CONFIRM gate and emits a READY, BLOCKED, or COMPLETED verdict per rotation. Use when enabling rotation, debugging a failed rotation, recovering a stuck AWSPENDING version, rotating RDS credentials, or wiring a cross-account rotation Lambda.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws secretsmanager describe-secret, get-resource-policy, list-secret-version-ids, rotate-secret, update-secret-version-stage, aws lambda get-function-configuration, get-function-concurrency, get-policy, aws logs filter-log-events, and aws kms describe-key (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Enabling rotation on a Secrets Manager secret, wiring a rotation Lambda (custom or managed template), scheduling rotation via cron or AutomaticallyAfterDays, triggering a manual rotation, diagnosing a failed or stuck (AWSPENDING) rotation, recovering from a credential mismatch, configuring cross-account rotation Lambda access, or validating that RDS database credentials rotate end-to-end.
  activation_triggers: enable secret rotation, rotate this secret, trigger rotation now, configure rotation Lambda, rotation Lambda setup, rotation failed, AWSPENDING stuck, credential mismatch after rotation, RDS password rotation, rotation schedule cron, cross-account rotation Lambda, diagnose rotation failure, Secrets Manager rotation
  invocation_schema: 'Input: either (a) a secret configuration (describe-secret output) plus the intended operation (enable-rotation, trigger-rotation, diagnose- rotation, recover-pending, update-config), OR (b) a secret-id + operation for live-account execution. Output: deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY / NOTES block per rotation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Secrets Manager, secret rotation, rotation Lambda, createSecret, setSecret, testSecret, finishSecret, AWSPENDING, AWSCURRENT, AWSPREVIOUS, rotate-secret, rotation-rules, ScheduleExpression, AutomaticallyAfterDays, RDS credentials, rotation template, cross-account rotation, resource-based policy, Lambda timeout, VPC ENI, reserved concurrency, KMS decrypt, HostedRotationLambda
  tags: aws, secretsmanager, security, rotation, credentials, lambda, rds, compliance, operate
---

# Secrets Manager Rotation Operator

## What this skill does

Executes Secrets Manager rotation operations correctly and safely. Runs
deterministic pre-checks before any state-changing CLI (Lambda state,
execution-role permission chain, KMS decrypt path, VPC ENI reachability,
stuck AWSPENDING versions, reserved concurrency), executes the rotation
behind a CONFIRM gate, and verifies the result by confirming
`LastRotatedDate` advanced and no version is stuck in AWSPENDING. Every
enable-rotation produces a four-step Lambda contract expectation; every
manual trigger surfaces the failure-mode table so the operator knows what
to look for in CloudWatch Logs.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds (BLOCKED/READY/COMPLETED) + pre-check priority | Before any operation |
| **§ Mindset** | Why rotation is a four-link chain, the false-sense-of-security trap, the confirm gate | Understanding the safety model |
| **§ Pre-flight** | Secret metadata gate — replica, deletion window, KMS key, current version | Before executing any CLI |
| **§ Process** | Per-operation planning: enable, trigger, diagnose, recover-pending, update-config | When choosing which operation to run |
| **§ Output format** | Structured OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY template | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that strand credentials or break auth | Review before risky operations |
| **§ Pre-flight safety** | Capture pre-state, KMS key policy, Lambda resource-based policy | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (Lambda deleted/inactive, execution role missing permissions, KMS decrypt denied, VPC unreachable, AWSPENDING stuck with unknown live credential, reserved concurrency = 0, replica secret) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Rotation finished and post-verification passed (`LastRotatedDate` advanced, no new AWSPENDING, target credential matches) | Emit verification results, monitoring plan |

**Priority order for pre-checks (apply in this sequence, all must pass for
READY):**

1. **Secret reachability** — secret exists, NOT in recovery window unless
   restore is intentional, NOT a replica (only primary can rotate).
2. **Lambda state** — rotation Lambda exists, `State: Active`, same account
   and region as the secret, reserved concurrency >= 1.
3. **Execution-role permission chain** — `secretsmanager:GetSecretValue`,
   `PutSecretValue`, `UpdateSecretVersionStage`, `DescribeSecret` on the
   secret ARN; plus service-specific permissions (rds-db:connect for RDS,
   redshift:GetClusterCredentials for Redshift).
4. **KMS decrypt path** — for customer-managed keys, the Lambda role has
   `kms:Decrypt` on the key ARN; the key policy allows the Lambda role.
5. **VPC network path** — for database targets, Lambda has `VpcConfig`
   with subnets that route to the DB and a security group allowing egress
   on the DB port.
6. **Credential match** — `AWSCURRENT` value matches the live target
   credential (no out-of-band password change). For AWSPENDING recovery,
   identify which version is live before promoting or cancelling.
7. **Schedule validity** — `AutomaticallyAfterDays` 1-365 OR
   `ScheduleExpression` is a valid rate/cron expression.

**Cost/time baselines (2026):**

- Manual rotation: 1-30 seconds Lambda invocation (database rotation
  typically 5-15 seconds for connect + ALTER USER).
- Scheduled rotation: jittered within the 24-hour window starting at
  midnight UTC on the scheduled day.
- Rotation Lambda cost: Lambda invocation (free tier covers most rotation
  workloads) + CloudWatch Logs ingestion (~1-5 MB per rotation).
- Multi-Region replica sync after primary rotation: 1-5 seconds.

## Mindset

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#mindset).
> Why rotation is a four-link chain, the false-sense-of-security trap, cross-account policy pair.

## Pre-flight: secret metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `list-secrets` paginates at 100/page — drain
`--next-token` to completion. `list-secret-version-ids` paginates at 100
versions per page; most secrets have <10 versions, but long-lived secrets
with many failed rotations can accumulate hundreds of AWSPENDING versions.

**Live-account pre-flight (skip if offline plan audit):**

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#live-account-pre-flight-secret-metadata-gate).
> Eight pre-flight CLI probes: describe-secret, resource policy, Lambda state/policy/concurrency, IAM role, KMS, CloudWatch errors.

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Secret/operation configuration
is not valid JSON or is missing required fields — cannot plan.` and
`REMEDIATION: Re-fetch with aws secretsmanager describe-secret --secret-id
<id> --output json and re-plan.`

| Secret attribute | Effect on operation |
|---|---|
| `DeletedDate` present | Secret in recovery window. Trigger-rotation BLOCKED unless restored. Diagnose / audit are still allowed. |
| `PrimaryRegion` set and non-null | Secret is a replica. Rotation CANNOT be enabled; only the primary rotates. Emit OK-for-replica advisory. |
| `RotationEnabled: false` | Trigger-rotation BLOCKED — enable first. Diagnose-rotation returns the unrotated finding. |
| `RotationEnabled: true` + `RotationLambdaARN: null` | ROTATION_BROKEN. Enable-rotation needed to populate the Lambda ARN. |
| `RotationRules.AutomaticallyAfterDays` outside 1-365 | Invalid; scheduler silently skips. Update-config needed. |
| `VersionIdsToStages` has version stuck in `AWSPENDING` | Recover-pending operation; identify the live credential first. |
| `KmsKeyId` absent | Default `aws/secretsmanager` managed key (account-scoped, no policy edits needed). |
| `KmsKeyId` set to a customer-managed CMK | Lambda role needs `kms:Decrypt` on the key; key policy must grant the role. |
| `LastRotatedDate` null with rotation enabled > 1 interval | Every rotation silently failed. Diagnose-rotation priority. |
| `OwningService: rds` (RDS managed secret) | Use the managed rotation template; do NOT override with a custom Lambda. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious Secrets Manager behaviors

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-0-expert-knowledge--non-obvious-secrets-manager-behaviors).
> Sixteen non-obvious behaviors: four-step cycle, AWSCURRENT atomicity, ScheduleExpression override, timeout, VPC routing, cross-account pair, RDS templates, hosted Lambda, reserved concurrency, KMS, manual ALTER, replicas, cron syntax, DR overwrite, managed-policy scope.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks for the chosen operation. If ANY fails, the verdict is
BLOCKED with the failed checks in PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. Secret exists (`describe-secret` does not return
   `ResourceNotFoundException`).
2. Secret is NOT in the recovery window (`DeletedDate` absent), unless the
   operation is explicitly `restore-then-rotate`.
3. Secret is NOT a replica (`PrimaryRegion` null), unless auditing.
4. KMS key (if customer-managed) is `Enabled`.

**For enable-rotation (`rotate-secret --rotation-lambda-arn`):**
5. `RotationLambdaARN` points to a Lambda in the same account and region
   as the secret (cross-account requires the resource-based policy pair).
6. Lambda `State: Active` (not `Failed`, `Inactive`, `Pending`).
7. Lambda's resource-based policy allows `lambda:InvokeFunction` from
   `secretsmanager.amazonaws.com` (same-account) or the secret's account
   (cross-account).
8. `ReservedConcurrentExecutions` is not 0.
9. Lambda execution role has `secretsmanager:GetSecretValue`,
   `PutSecretValue`, `UpdateSecretVersionStage`, `DescribeSecret` on the
   secret ARN.
10. Lambda execution role has `kms:Decrypt` on the KMS key (customer-
    managed keys only).
11. For database targets: Lambda has `VpcConfig` with subnets routing to
    the DB; DB SG allows ingress from the Lambda SG on the DB port.
12. For database targets: Lambda execution role has
    `ec2:CreateNetworkInterface`, `ec2:DescribeNetworkInterfaces`,
    `ec2:DeleteNetworkInterface` (granted by
    `AWSLambdaVPCAccessExecutionRole`).
13. For RDS targets: Lambda role has `rds-db:connect` on the DB cluster/
    instance ARN for the master user.
14. `RotationRules.AutomaticallyAfterDays` (if used) is in [1, 365].
15. `RotationRules.ScheduleExpression` (if used) is a valid rate/cron.

**For trigger-rotation (`rotate-secret --secret-id` no other flags):**
5. `RotationEnabled: true`.
6. `RotationLambdaARN` is non-null.
7. No version stuck in `AWSPENDING` (if there is, route to recover-pending
   first — triggering another rotation on top of a stuck one creates
   another pending version).
8. Lambda `State: Active`, reserved concurrency >= 1.
9. (Optional) `LastRotatedDate` is not within the last few minutes (avoid
   double-rotation).

**For diagnose-rotation (read-only, no BLOCKED gate):**
5. Read CloudWatch Logs and the failure-mode table to identify the root
   cause.

**For recover-pending (stuck AWSPENDING version):**
5. Exactly one version is in `AWSPENDING` (multiple = repeated failures;
   clean up chronologically).
6. Determine which credential is live on the target:
   - Test connection with `AWSPENDING` value → if succeeds, `AWSPENDING`
     is live → promote it to `AWSCURRENT`.
   - Test connection with `AWSCURRENT` value → if succeeds, `AWSCURRENT`
     is still live → cancel the pending version.
   - If NEITHER connects → out-of-band password change; manually set the
     secret value to the live credential, then trigger rotation.
7. The operator has access to the target resource to test connections.

**For update-config (change schedule, Lambda ARN, interval):**
5. New `RotationLambdaARN` (if changing) passes the enable-rotation pre-
   checks.
6. New `ScheduleExpression` (if changing) is valid rate/cron.
7. New `AutomaticallyAfterDays` (if changing) is in [1, 365].

**Rotation failure-mode table (use during diagnose-rotation):**

> Moved to [references/error-handling.md](references/error-handling.md#rotation-failure-mode-table-use-during-diagnose-rotation).
> Symptom → root cause → fix for 10 CloudWatch error signatures (AccessDenied, KMS, timeouts, VPC, throttles, replica errors).

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI sequence
and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated from the secret +
  Lambda configuration.
- The expected duration (manual rotation 5-30 seconds; scheduled rotation
  jittered within the 24-hour window).
- The expected side-effects (new `AWSCURRENT` version ID, old version
  moves to `AWSPREVIOUS`, `LastRotatedDate` advances).
- The CONFIRM gate prompt.
- The monitoring step (CloudWatch Logs tail to watch the four steps
  complete).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`rotate-secret`, `update-secret-version-stage`, `cancel-rotate-secret`,
  `delete-secret`, `restore-secret`), emit:
  `CONFIRM: About to <operation> on <secret-id> in account <account>
  region <region>. This will <consequence>. Proceed? (yes/no)`.
  Do NOT execute until the operator confirms.
- Capture pre-state for rollback: `aws secretsmanager describe-secret
  --secret-id <id> --output json > /tmp/<id>-pre-$(date +%s).json` AND
  `aws secretsmanager list-secret-version-ids --secret-id <id> --output
  json > /tmp/<id>-versions-$(date +%s).json`.
- Execute the CLI. For `rotate-secret`, the API returns immediately; the
  actual rotation runs asynchronously via Lambda invocation.
- Tail the Lambda CloudWatch Logs to watch the four steps:
  `aws logs tail /aws/lambda/<lambda> --follow --since 2m`.

### Step 4: Post-verification — COMPLETED

After the rotation finishes, run post-verification. ALL checks must pass
for `COMPLETED`.

1. `describe-secret --secret-id <id>` — confirm `LastRotatedDate` advanced
   to within the last few minutes (manual) or to the scheduled time.
2. `list-secret-version-ids --secret-id <id>` — confirm NO version is in
   `AWSPENDING`; the new version ID is in `AWSCURRENT`; the previous
   version is in `AWSPREVIOUS`.
3. For database targets: test login with the new `AWSCURRENT` credential
   via the application's normal connection path.
4. Confirm application metric dashboards show no authentication-error
   spike (sample 5-15 minutes of post-rotation traffic).
5. For multi-Region secrets: confirm replica secrets in all regions
   received the new value (`describe-secret` in each replica region; the
   version ID should match).
6. For the next scheduled rotation: confirm `NextRotationDate` advanced.

If ANY verification fails, emit `VERDICT: ERROR` with the failure details
— do not claim COMPLETED. A failed verification typically means the
rotation partially completed (stuck AWSPENDING); route to recover-pending.

## Output format (per operation)

```text
OPERATION: <enable-rotation | trigger-rotation | diagnose-rotation | recover-pending | update-config>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <secret-id> (rotation Lambda: <arn-or-"none">)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait / monitoring command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <schedule, monitoring, caveats>
```

### Worked example — enable-rotation (RDS PostgreSQL)

```text
OPERATION: enable-rotation
VERDICT: READY
TARGET: prod/payments-db-credentials (rotation Lambda:
        arn:aws:lambda:us-east-1:111111111111:function:SecretsManagerRDSPostgreSQLRotation)
PRE_CHECKS:
  - [PASS] Secret exists, not in recovery window, not a replica
  - [PASS] Rotation Lambda State: Active
  - [PASS] Lambda resource-based policy allows lambda:InvokeFunction
    from secretsmanager.amazonaws.com
  - [PASS] Reserved concurrency: 5 (>= 1)
  - [PASS] Execution role has SecretsManagerRotation policy attached
  - [PASS] Execution role has rds-db:connect on
    arn:aws:rds-db:us-east-1:111111111111:dbuser:db-ABCDEFGHIJ/postgres
  - [PASS] KMS key arn:aws:kms:us-east-1:111111111111:key/payments-cmk
    Enabled; key policy grants Lambda role kms:Decrypt
  - [PASS] Lambda VpcConfig subnets route to DB subnet group
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
NOTES:
  - Secrets Manager triggers the FIRST rotation immediately when you call
    rotate-secret with --rotation-lambda-arn. Watch the four steps
    complete in CloudWatch before relying on the schedule.
  - The Lambda uses the PostgreSQL single-user template (rotates the
    master credential). For multi-user, deploy the multi-user template
    and add the new username to the secret.
  - Set up a CloudWatch alarm on the RotationFailed metric:
    aws cloudwatch put-metric-alarm --alarm-name payments-rotation-failed
      --metric-name RotationFailed --namespace AWS/SecretsManager
      --dimensions Name=SecretId,Value=prod/payments-db-credentials
      --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold
      --period 300 --evaluation-periods 1
```

### Worked example — recover-pending (stuck AWSPENDING)

> Moved to [references/worked-examples.md](references/worked-examples.md#worked-example--recover-pending-stuck-awspending).
> Full COMPLETED block: promote a live AWSPENDING version to AWSCURRENT with CONFIRM gate and post-verify.

### Worked example — diagnose-rotation (BLOCKED with remediation)

> Moved to [references/worked-examples.md](references/worked-examples.md#worked-example--diagnose-rotation-blocked-with-remediation).
> BLOCKED block for a Lambda-timeout root cause with the update-function-configuration fix.

## Anti-Patterns — NEVER

- NEVER trigger `rotate-secret` as the FIRST remediation step for a broken
  rotation without first diagnosing and fixing the root cause (deleted
  Lambda, missing permissions, unreachable target, reserved-concurrency=0).
  Forcing an immediate rotation on a broken chain produces another failed
  rotation, potentially another stuck AWSPENDING version, and does not
  advance LastRotatedDate.

- NEVER execute `rotate-secret` on a secret with an existing AWSPENDING
  version without first resolving the pending version. Triggering another
  rotation on top of a stuck one creates a second pending version and
  complicates the recovery path. Run recover-pending first.

- NEVER delete a stuck AWSPENDING version without first testing which
  credential is live on the target. If `setSecret` completed before the
  failure, the AWSPENDING credential is the actual password on the
  database — deleting the version loses the only record of what that
  password is. Test a connection with both values first.

- NEVER assume `RotationEnabled: true` means the secret is rotating.
  Rotation is a four-link chain. Always verify `LastRotatedDate` advanced
  within the configured interval — that is the only proof a rotation
  succeeded.

- NEVER enable rotation on a replica secret. Replicas are read-only;
  Secrets Manager returns `InvalidParameterException`. Enable rotation on
  the primary in `PrimaryRegion`.

- NEVER set Lambda timeout below 30 seconds for database rotation targets.
  The `setSecret` step must connect, authenticate, and execute `ALTER
  USER` — on large or busy databases this can take 10-20 seconds. The
  default 3 seconds is insufficient.

- NEVER ignore `ReservedConcurrentExecutions: 0` on a rotation Lambda. It
  is a stealth kill switch — the Lambda appears `Active` but every
  invocation is throttled. CloudWatch shows a `Throttles` spike, not an
  error log.

- NEVER confuse `LastChangedDate` with `LastRotatedDate`. `LastChangedDate`
  tracks ANY metadata or value modification; `LastRotatedDate` tracks ONLY
  the rotation event (the `finishSecret` step moving `AWSCURRENT`). A
  recent `LastChangedDate` with an old `LastRotatedDate` means manual
  editing, not rotation.

- NEVER assume the default KMS key (`aws/secretsmanager`) is in use.
  Customer-managed keys require the Lambda role to have `kms:Decrypt` on
  the key ARN, AND the key policy must grant the role. A missing grant
  surfaces as `DecryptionFailureException` in Lambda logs, not in the
  Secrets Manager API response.

- NEVER attach the `SecretsManagerRotation` managed policy without
  scoping it. It grants `secretsmanager:*` on `*` — the rotation Lambda
  can read or modify every secret in the account. Use a custom policy
  scoped to the specific secret ARN with the `-??????` suffix.

- NEVER attempt cross-account rotation Lambda invocation with only one
  side of the resource-based policy pair. Both the Lambda's resource
  policy (allowing `secretsmanager.amazonaws.com` or the secret's account
  to invoke) AND the secret's resource policy (allowing the Lambda's role
  to GetSecretValue/PutSecretValue/UpdateSecretVersionStage) are required.

- NEVER enable rotation without specifying the Lambda ARN and the rotation
  interval. `RotationEnabled: true` without `RotationLambdaARN` is an
  inconsistent state where the dashboard says "rotating" but there is no
  function to invoke.

- NEVER trigger a rotation when the application is in the middle of a
  credential-sensitive operation. Although Secrets Manager rotations are
  designed for zero-downtime (apps reading the secret get the new value
  on their next read), the brief window during `setSecret` -> `finishSecret`
  can cause auth failures if the app holds the old credential in a
  long-lived cache.

- NEVER use `ForceOverwriteReplicaSecret` outside of a regional-failover
  DR procedure. It breaks the primary/replica sync and requires manual
  reconciliation when the primary returns.

- NEVER rely on `AutomaticallyAfterDays` for the schedule when
  `ScheduleExpression` is set. The cron expression overrides
  `AutomaticallyAfterDays`. Computing the interval off the wrong field
  produces false STALE classifications and wrong next-rotation estimates.

- NEVER auto-execute a state-changing Secrets Manager CLI without the
  CONFIRM gate. Rotation, AWSPENDING recovery, and secret deletion all
  have credential-mismatch side effects that can storm the workload with
  auth failures.

- NEVER use `AWSCURRENT` value to test the live DB connection if
  AWSPENDING exists and `setSecret` is suspected to have completed. The
  AWSPENDING value may be the live credential; the AWSCURRENT value may
  be stale. Test BOTH before deciding which to promote.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`rotate-secret`, `update-secret`, `update-secret-version-stage`,
  `cancel-rotate-secret`, `delete-secret`, `restore-secret`,
  `lambda update-function-configuration`, `iam attach-role-policy`),
  emit: `CONFIRM: About to <operation> on <target> in account <account>
  region <region>. This will <consequence>. Proceed? (yes/no)`. Do NOT
  execute until the operator confirms.

- **Capture pre-state for rollback.** Before any rotation or stage change:
  `aws secretsmanager describe-secret --secret-id <id> --output json >
  /tmp/<id>-describe-$(date +%s).json` AND
  `aws secretsmanager list-secret-version-ids --secret-id <id> --output
  json > /tmp/<id>-versions-$(date +%s).json`. These captures are
  critical for incident response — if a rotation fails and creates a
  credential mismatch, you need the pre-change version IDs to restore
  `AWSCURRENT`.

- **Verify Lambda state before enabling rotation.** `aws lambda
  get-function-configuration --function-name <lambda>` — confirm `State:
  Active` and `Timeout >= 30` for database targets.

- **Verify the Lambda resource-based policy.** `aws lambda get-policy
  --function-name <lambda>` — confirm
  `Principal: { Service: secretsmanager.amazonaws.com }` and `Action:
  lambda:InvokeFunction`. For cross-account, also confirm the secret's
  account ID is in the policy principal or Condition.

- **Verify KMS key access for customer-managed keys.** `aws kms
  describe-key --key-id <kms-id>` — confirm `Enabled`. Read the key
  policy and verify the Lambda role ARN has `kms:Decrypt`.

- **Verify VPC reachability for database targets.** Confirm the Lambda's
  subnets have a route to the DB subnet, and the DB SG allows ingress
  from the Lambda SG on the DB port. Use VPC Reachability Analyzer for
  complex topologies.

- **Verify the live credential before AWSPENDING recovery.** Test a
  connection with both `AWSCURRENT` and `AWSPENDING` values. The live
  credential wins — promote (if AWSPENDING is live) or cancel (if
  AWSCURRENT is still live).

- **Prefer additive changes over destructive ones.** Enabling rotation,
  fixing the execution role, and increasing the timeout are reversible.
  Deleting a stuck AWSPENDING version is irreversible — do it only after
  confirming the credential is not live on the target.

## Recent AWS features (2024-2026)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#recent-aws-features-2024-2026).
> HostedRotationLambda, cross-region replication GA, partial wildcards, ScheduleExpression GA, new engine templates, multi-user strategy, VPC endpoint, CloudTrail data events.

## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — Mindset principles, Step 0 expert behaviors, recent AWS features
- [diagnostic-commands](references/diagnostic-commands.md) — live-account pre-flight probe listing
- [error-handling](references/error-handling.md) — rotation failure-mode error table
- [worked-examples](references/worked-examples.md) — recover-pending and diagnose-rotation worked examples

## Domain

AWS CloudOps / Secrets Manager Rotation, Credential Hygiene & Compliance.

## AWS documentation

- **AWS Secrets Manager User Guide** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html
- **Rotating secrets** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html
- **Rotation function templates** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/reference_available-rotation-templates.html
- **Rotation Lambda contract** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets_lambda-app.html
- **Secrets Manager API Reference** — https://docs.aws.amazon.com/secretsmanager/latest/apireference/
- **Secrets Manager CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/
- **Cross-account rotation** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets_audit.html
- **ScheduleExpression syntax** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotate-secrets_schedule.html
