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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#mindset).
> Audit question, the four-dependency chain, why ROTATION_BROKEN is the most dangerous posture, dependency-order classification.

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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-0--input-schema-describe-secret-fields).
> Ten-field describe-secret input schema table (Name, RotationEnabled, RotationLambdaARN, RotationRules, LastRotatedDate, DeletedDate, PrimaryRegion, VersionIdsToStages, KmsKeyId).

If the secret name is missing or `RotationEnabled` is not a boolean or
`RotationRules` is not a map, output:

> Moved to [references/error-handling.md](references/error-handling.md#malformed-input--error-emit-block).
> ERROR emit template for missing name / non-boolean RotationEnabled / non-map RotationRules.

Do not attempt classification on malformed input.

**Replica pre-flight (run BEFORE Step 1).** Check `PrimaryRegion`. If
`PrimaryRegion` is set and non-null, the secret is a **replica** in a
multi-Region setup. Replicas are read-only — rotation CANNOT be enabled
on them (only the primary can rotate, and Secrets Manager returns
`InvalidParameterException` if you try). A replica with
`RotationEnabled: false` is EXPECTED, not UNROTATED. Emit and stop:

> Moved to [references/worked-examples.md](references/worked-examples.md#replica-pre-flight-emit-block-ok--read-only-replica).
> OK emit block for a replica secret (PrimaryRegion set): rotation runs on the primary; audit it there instead.
Do NOT apply Steps 2–8 to a replica — doing so produces false-positive
UNROTATED or ROTATION_BROKEN classifications.

### Step 1: Recovery-window / deletion check (pre-flight flag)

If `DeletedDate` is present, the secret is in the **recovery window** —
scheduled for permanent deletion. Emit a `DELETION_FLAG` before the normal
classification block. The flag does NOT change the verdict; it adds context
that the secret will be purged and may need restoration.

> Moved to [references/worked-examples.md](references/worked-examples.md#deletion_flag-emit-block-recovery-window).
> DELETION_FLAG emit template when DeletedDate is present (restore-or-verify decision).


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

**Step 3b: Lambda function deleted (404).** If the Lambda's `State` is
`Deleted`, or the Lambda returns `ResourceNotFoundException` —
**VERDICT: ROTATION_BROKEN**, risk **CRITICAL**. The rotation config

**Step 3c: Lambda function inactive or failed.** If the Lambda `State` is
`Failed`, `Inactive`, or `Pending` (stuck in creation) —
**VERDICT: ROTATION_BROKEN**. The function exists but cannot accept

**Step 3d: Lambda cross-region or cross-account.** If the `RotationLambdaARN`
contains a different region or account ID than the secret —
**VERDICT: ROTATION_BROKEN**. Secrets Manager can only invoke Lambda

### Step 4: Lambda invocation health

If the Lambda exists and is `Active`, check its last invocation result.

**Step 4a: Last invocation errored.** If `LastInvocation.Status` is `ERROR`
or `TIMED_OUT`, examine the error code to determine root cause:

> Moved to [references/error-handling.md](references/error-handling.md#step-4a--invocation-error-code-table).
> Error code → root cause → classification note for six Lambda invocation error signatures.

In all error cases — **VERDICT: ROTATION_BROKEN**. The Lambda runs but

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

### Step 5: Execution-role permission chain

The rotation Lambda's execution role must have a complete permission chain
to perform the four-step rotation contract. Check each link:


> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-5--execution-role-permission-chain-link-detail).
> Four permission links: Secrets Manager API actions, kms:Decrypt, VPC ENI access, AWSCURRENT/target credential match — each with failure modes.

If any link is broken — **VERDICT: ROTATION_BROKEN** with the specific
broken link cited in the REASON.

### Step 6: AWSPENDING stuck version

Check `VersionIdsToStages` for any version stuck in the `AWSPENDING`
stage. The rotation Lambda follows a four-step contract (see "Rotation

If `AWSPENDING` is present — **VERDICT: ROTATION_BROKEN**, risk **HIGH**.
The secret is in an inconsistent state: the target may have the new

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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-7--interval-edge-cases).
> Null interval → ROTATION_BROKEN; >365 silently never schedules; LastChangedDate newer than LastRotatedDate → verify-credential note.

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


> Moved to [references/worked-examples.md](references/worked-examples.md#null-lastrotateddate-rotation-enabled-multiple-intervals-rotation_broken).
> Second worked example: RISK HIGH, ResourceNotFoundException on a deleted RDS target, orphaned-secret remediation.

## Rotation Lambda contract (expert reference)


> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#rotation-lambda-contract-expert-reference).
> Four-step Lambda contract (createSecret/setSecret/testSecret/finishSecret) with per-step failure modes and the stuck-AWSPENDING forensic signature.

## Expert knowledge — rotation scheduling and failure modes


> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-knowledge--rotation-scheduling-and-failure-modes).
> Scheduler internals (Duration window, jitter, NextRotationDate), concurrency limits, replica secrets, SecretsManagerRotation policy scope, HostedRotationLambda, CloudTrail events, rotation quotas.

## Risk / severity matrix (emit exactly one RISK per secret)


> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#risk--severity-matrix-emit-exactly-one-risk-per-secret).
> Verdict-condition → RISK table, UNROTATED risk-by-secret-type rationale, and the AWS-provided rotation template catalogue by secret type.

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


> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#pre-flight-safety-checks-run-before-any-remediation-cli).
> Read-only discovery commands, replica detection, rollback captures, Lambda state verification, additive-over-destructive rule, orphaned-secret rule.

## Remediation guidance


> Moved to [references/remediation-guidance.md](references/remediation-guidance.md#remediation-guidance).
> Per-verdict playbooks with CLI: UNROTATED (template selection, intervals), ROTATION_BROKEN (6 causes incl. AWSPENDING promote/cancel), STALE, OK (RotationFailed alarm), DELETION_FLAG (restore-or-verify).

## Recent AWS features (2024-2026)


> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#recent-aws-features-2024-2026).
> Cross-account access, new rotation templates, Amazon Q integration, cross-region replication.

## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — Mindset, input schema, trimmed step prose, Step 5 permission links, interval edge cases, rotation Lambda contract, scheduler/failure-mode expert knowledge, risk matrix, recent AWS features
- [diagnostic-commands](references/diagnostic-commands.md) — pre-flight safety checks and read-only discovery CLI
- [error-handling](references/error-handling.md) — malformed-input ERROR block and Step 4a invocation error table
- [remediation-guidance](references/remediation-guidance.md) — per-verdict remediation playbooks with CLI
- [worked-examples](references/worked-examples.md) — replica, DELETION_FLAG, and null-LastRotatedDate worked examples

## Domain

AWS CloudOps / Secrets Manager Security & Compliance.

## AWS documentation

- **AWS Secrets Manager User Guide** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html
- **Secrets Manager Security** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/security.html
- **Secrets Manager API Reference** — https://docs.aws.amazon.com/secretsmanager/latest/apireference/
- **Secrets Manager CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/
- **Rotating secrets** — https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html
