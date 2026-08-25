---
name: kms-key-rotation-operator
description: Operates AWS KMS key rotation workflows end-to-end — key type classification (AWS-managed, customer-managed symmetric, asymmetric RSA/ECDSA, HMAC, Multi-Region primary/replica, custom key store / CloudHSM), automatic annual backing-key rotation enablement and verification, manual key rotation (create new CMK + re-encrypt), cryptographic material lifecycle (old material retained for decrypt, new encrypts transparently), and diagnostic loops (describe-key, get-key-rotation-status, CloudTrail EnableKeyRotation events, list-grants, key-policy diff). Runs deterministic pre-checks (key Enabled, key state not PendingDeletion, symmetric SYMMETRIC_DEFAULT usage, multi-Region primary not replica, EnableKeyRotation permission in key policy) behind a CONFIRM gate and emits a READY, BLOCKED, or COMPLETED verdict per rotation. Use when enabling automatic rotation, verifying rotation ran, planning a manual rotation, or diagnosing why rotation cannot be enabled.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws kms describe-key, get-key-rotation- status, enable-key-rotation, disable-key-rotation, list-grants, get-key-policy, list-resource-tags, aws cloudtrail lookup-events (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Enabling automatic backing-key rotation on a customer-managed KMS key, verifying a key's rotation status and last rotation date, planning a manual rotation for asymmetric/HMAC keys that do not support automatic rotation, diagnosing why EnableKeyRotation fails (Disabled/PendingDeletion key, asymmetric usage, replica key, missing key-policy permission), confirming CloudTrail EnableKeyRotation events, or validating cryptographic-agility posture across a fleet of CMKs.
  activation_triggers: enable KMS key rotation, rotate KMS key, verify key rotation, GetKeyRotationStatus, EnableKeyRotation, automatic key rotation, manual key rotation, backing key, Multi-Region key rotation, replica key rotation, asymmetric key rotation, HMAC key rotation, re-encrypt with new key, cryptographic agility, KMS rotation failed
  invocation_schema: 'Input: either (a) a KMS key configuration (describe-key output) plus the intended operation (enable-rotation, verify-rotation, disable-rotation, plan-manual-rotation, diagnose-rotation), OR (b) a key-id + operation for live-account execution. Output: deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY / NOTES block per rotation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: KMS, key rotation, backing key, cryptographic material, customer managed key, CMK, AWS managed key, Multi-Region key, replica key, asymmetric key, RSA_2048, ECC_NIST_P256, HMAC_256, SYMMETRIC_DEFAULT, EnableKeyRotation, GetKeyRotationStatus, CloudHSM custom key store, key policy, re-encrypt, cryptographic agility
  tags: aws, kms, security, encryption, key-management, rotation, compliance, operate
---

# KMS Key Rotation Operator

## What this skill does

Executes KMS key rotation operations correctly and safely. Runs
deterministic pre-checks before any state-changing CLI (key Enabled,
not PendingDeletion, symmetric SYMMETRIC_DEFAULT usage, Multi-Region
primary not replica, EnableKeyRotation permission in the key policy,
not a custom key store with external rotation), executes the
`enable-key-rotation` / `disable-key-rotation` CLI behind a CONFIRM
gate, and verifies the result by confirming
`get-key-rotation-status` returns `Enabled: true` and CloudTrail shows
the `EnableKeyRotation` event. Every enable-rotation produces a
cryptographic-material lifecycle note (old backing material retained
for decrypt of existing ciphertext; new material encrypts all new
operations transparently). Every asymmetric/HMAC key plan routes to
manual rotation (create new key, update callers, re-encrypt) since
automatic rotation is not supported.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds (BLOCKED/READY/COMPLETED) + pre-check priority | Before any operation |
| **§ Mindset** | Why rotation is transparent, the asymmetric-gap, the confirm gate | Understanding the safety model |
| **§ Pre-flight** | Key metadata gate — Enabled state, PendingDeletion, Multi-Region, custom key store | Before executing any CLI |
| **§ Process** | Per-operation planning: enable, verify, disable, plan-manual, diagnose | When choosing which operation to run |
| **§ Output format** | Structured OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY template | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that break encryption or strand data | Review before risky operations |
| **§ Pre-flight safety** | Capture pre-state, CloudTrail trail verification, key policy check | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (key Disabled, key PendingDeletion, asymmetric/HMAC usage with auto-rotation requested, replica key with auto-rotation requested, missing EnableKeyRotation permission, custom key store with external rotation) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Rotation enable/disable finished and post-verification passed (`get-key-rotation-status` matches intent, CloudTrail event present, key policy unchanged, applications using key ARN still work) | Emit verification results, monitoring plan |

**Priority order for pre-checks (apply in this sequence, all must pass
for READY):**

1. **Key reachability** — key exists (`describe-key` does not return
   `NotFoundException`), `Enabled` true, `KeyState: Enabled`.
2. **No deletion pending** — `KeyState` is NOT `PendingDeletion` (no
   rotation during the deletion window).
3. **Key supports automatic rotation** — `KeySpec` is
   `SYMMETRIC_DEFAULT` (or `AES_256` for multi-Region primary) AND
   `KeyUsage: ENCRYPT_DECRYPT` AND `Origin: AWS_KMS`. Asymmetric,
   HMAC, and external-key-material keys do NOT support automatic
   rotation.
4. **Multi-Region primary** — for Multi-Region keys, rotation is
   controlled by the primary key. A replica key
   (`MultiRegionConfiguration.PrimaryArmy` != self) inherits the
   primary's rotation status; `EnableKeyRotation` on a replica fails.
5. **Key policy permission** — the calling identity must have
   `kms:EnableKeyRotation` (or `kms:DisableKeyRotation`) on the key
   ARN. The key's own resource-based policy must allow the caller, or
   the caller's identity-based policy must grant it. Cross-account
   callers need both sides.
6. **Custom key store check** — for `Origin: AWS_CLOUDHSM`, rotation
   is supported (KMS rotates the backing key in the CloudHSM cluster),
  but the cluster must be `ACTIVE`. For `Origin: EXTERNAL`, rotation
   is NOT supported (you manage the key material externally).
7. **Schedule intent clarity** — `enable-key-rotation` accepts an
   optional `--rotation-period-in-days` (7-365, default 365). Confirm
   the intended cadence before enabling.

**Cost/time baselines (2026):**

- Customer-managed CMK: $1.00/key/month (regardless of rotation).
- Automatic rotation: no additional per-rotation fee. The CMK keeps
  its key ID and ARN; KMS retains old backing material for decrypt.
- Asymmetric keys (RSA, ECC): $1.00/key/month; do NOT support
  automatic rotation. Manual rotation = create new key + update
  callers + optional re-encrypt.
- HMAC keys: $1.00/key/month; do NOT support automatic rotation.
- Multi-Region keys: $1.00 per primary + $1.00 per replica.
- CloudTrail `EnableKeyRotation` / `DisableKeyRotation` events: free
  (management events).
- Re-encryption cost (manual rotation): `$0.03` per 10,000
  `Encrypt`/`Decrypt` requests. Re-encrypting a large S3 bucket or
  DynamoDB table is the dominant cost, not KMS itself.

## Mindset

**One-line takeaway:** automatic KMS key rotation is transparent to
applications — the key ID and ARN do not change, and old backing
material is retained so existing ciphertext remains decryptable.
Driven by three KMS realities:

- **Rotation swaps backing material, not the key.** A KMS key is a
  logical construct (key ID + ARN + policy) backed by cryptographic
  material. Automatic rotation creates new backing material under the
  same key ID. All new `Encrypt` operations use the new material; all
  `Decrypt` operations on existing ciphertext use the material that
  originally encrypted it (KMS tracks which material produced each
  ciphertext via the encryption context). Applications see no change.

- **Asymmetric and HMAC keys are the rotation blind spot.** Automatic
  rotation is supported ONLY on symmetric ENCRYPT_DECRYPT keys with
  `Origin: AWS_KMS` (and CloudHSM-backed symmetric keys). RSA, ECDSA,
  HMAC, and external-material keys do NOT support automatic rotation.
  For these, you must rotate manually: create a new key, update all
  callers to use the new key ARN, and optionally re-encrypt old data.
  This is a significant operational gap — auditors asking "are all
  keys rotating annually?" need to be told that asymmetric keys are
  manually rotated.

- **A Multi-Region replica key's rotation is set on the primary.**
  Calling `EnableKeyRotation` on a replica returns
  `InvalidOperationException`. Multi-Region replica keys share the
  same cryptographic material as the primary — when the primary's
  backing material rotates, replicas receive the new material
  automatically. Verify rotation on the primary's
  `get-key-rotation-status`.

## Pre-flight: key metadata gate

Run before classification. Misclassifying these produces wrong plans.

Pagination + live-account pre-flight commands moved verbatim to
`references/diagnostic-commands.md` (load on demand).

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Key configuration is not
valid JSON or is missing required fields — cannot plan.` and
`REMEDIATION: Re-fetch with aws kms describe-key --key-id <id> --output
json and re-plan.`

| Key attribute | Effect on operation |
|---|---|
| `KeyState: PendingDeletion` + `DeletionDate` set | BLOCKED — key in deletion window (7-30 days). Cancel deletion (`schedule-key-deletion` with `--pending-window-in-days 0` is not supported; you must wait or use `cancel-key-deletion` to restore). |
| `KeyState: Disabled` | BLOCKED — key disabled. `EnableKeyRotation` requires `Enabled: true`. Call `enable-key` first. |
| `KeyUsage: SIGN_VERIFY` (asymmetric) | BLOCKED for automatic rotation. Manual rotation required. |
| `KeyUsage: GENERATE_VERIFY_MAC` (HMAC) | BLOCKED for automatic rotation. Manual rotation required. |
| `KeySpec: RSA_2048` / `ECC_NIST_P256` etc. | BLOCKED for automatic rotation. Manual rotation required. |
| `Origin: EXTERNAL` (BYOK / imported material) | BLOCKED for automatic rotation. Re-import new material to rotate. |
| `Origin: AWS_CLOUDHSM` | Supported if the cluster is `ACTIVE`. KMS rotates the backing key in the CloudHSM. |
| `MultiRegionConfiguration.MultiRegionKeyType: REPLICA` | BLOCKED for `EnableKeyRotation` on the replica. Enable on the primary; replica inherits. |
| `MultiRegionConfiguration.MultiRegionKeyType: PRIMARY` | OK — rotation propagates to all replicas automatically. |
| Key policy denies caller `kms:EnableKeyRotation` | BLOCKED — add the permission to the policy (or call from a role that already has it). |
| `Enabled: false` in `get-key-rotation-status` | Not an error — rotation is currently disabled. The operation `enable-rotation` will enable it. |
| `Enabled: true` in `get-key-rotation-status` | If the operation is `enable-rotation`, no-op or update `RotationPeriodInSeconds`. If `disable-rotation`, plan the disable. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious KMS behaviors

Step-0 expert behaviors moved verbatim to `references/advanced-patterns.md`
(backing material, rotation period, aliases, grants, AWS-managed keys, more).

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks for the chosen operation. If ANY fails, the verdict
is BLOCKED with the failed checks in PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. Key exists (`describe-key` does not return `NotFoundException`).
2. Key is NOT `PendingDeletion` (`DeletionDate` absent,
   `KeyState != PendingDeletion`).
3. Calling identity has `kms:GetKeyRotationStatus` on the key (for
   verify-rotation and diagnose-rotation).

**For enable-rotation (`enable-key-rotation --key-id`):**
4. `KeyState: Enabled` (not `Disabled`).
5. `KeySpec: SYMMETRIC_DEFAULT` (or AES variant).
6. `KeyUsage: ENCRYPT_DECRYPT`.
7. `Origin: AWS_KMS` OR `Origin: AWS_CLOUDHSM` (with cluster ACTIVE).
8. NOT a Multi-Region replica
   (`MultiRegionConfiguration.MultiRegionKeyType == PRIMARY` or key is
   single-region).
9. Calling identity has `kms:EnableKeyRotation` on the key ARN.
10. (Optional) `--rotation-period-in-days` is in [7, 365], if
    specified.

**For verify-rotation (read-only, no BLOCKED gate for state):**
4. `get-key-rotation-status` returns `Enabled` and `NextRotationDate`.
5. CloudTrail shows an `EnableKeyRotation` event matching the key ARN
   (within the last rotation period).
6. (Optional) `NextRotationDate` is within the expected window.

**For disable-rotation (`disable-key-rotation --key-id`):**
4. `KeyState: Enabled`.
5. Current `get-key-rotation-status.Enabled: true` (otherwise it is a
   no-op).
6. Calling identity has `kms:DisableKeyRotation` on the key ARN.
7. (Advisory) Disabling rotation is rare and usually a compliance
   violation. Confirm the operator has a documented reason.

**For plan-manual-rotation (asymmetric / HMAC / external-material):**
4. Key is asymmetric (`KeyUsage: SIGN_VERIFY`), HMAC
   (`GENERATE_VERIFY_MAC`), or `Origin: EXTERNAL`.
5. Operator has `kms:CreateKey` permission (to create the new key).
6. List of all callers / aliases that reference the key — needed to
   plan the cutover.
7. (Optional) The set of ciphertexts / signatures / MACs that need
   re-encryption or re-signing (for compliance).

**For diagnose-rotation (read-only):**
4. Read `get-key-rotation-status`, CloudTrail events, and the
   failure-mode table to identify why rotation cannot be enabled or
   why it did not run.

**Rotation failure-mode table (use during diagnose-rotation):**

Rotation failure-mode table (API errors -> fixes) moved verbatim to
`references/error-handling.md` (load on demand).

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI
sequence and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated from the key
  configuration.
- The expected `RotationPeriodInSeconds` (365 days default, or the
  specified value).
- The expected side-effects (rotation status flips to `Enabled`,
  `NextRotationDate` is set to ~365 days from now, key policy
  unchanged, applications unaffected).
- The CONFIRM gate prompt.
- The verification step (`get-key-rotation-status` + CloudTrail +
  application spot-check).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`enable-key-rotation`, `disable-key-rotation`, `enable-key`,
  `disable-key`, `schedule-key-deletion`, `cancel-key-deletion`,
  `create-key`, `update-alias`), emit:
  `CONFIRM: About to <operation> on KMS key <key-id> (account
  <account> region <region>). This will <consequence>. Proceed?
  (yes/no)`. Do NOT execute until the operator confirms.
- Capture pre-state for rollback: `aws kms describe-key --key-id <id>
  --output json > /tmp/<id>-describe-pre-$(date +%s).json` AND
  `aws kms get-key-rotation-status --key-id <id> --output json >
  /tmp/<id>-rotation-pre-$(date +%s).json`.
- Execute the CLI. `enable-key-rotation` is synchronous — it returns
  once the rotation schedule is set. The actual material rotation
  happens at `NextRotationDate`.
- For manual rotations: the cutover (alias update or caller update)
  is the state-changing step. Capture the alias pre-state.

### Step 4: Post-verification — COMPLETED

After the CLI completes, run post-verification. ALL checks must pass
for `COMPLETED`.

1. `get-key-rotation-status --key-id <id>` — confirm `Enabled: true`
   (or `false` for disable-rotation) and `NextRotationDate` is set
   (or absent for disable).
2. CloudTrail shows the `EnableKeyRotation` (or `DisableKeyRotation`)
   event with the key ARN and the caller's identity.
3. `describe-key --key-id <id>` — confirm `KeyState: Enabled` (the
   key itself is unaffected by the rotation-status change).
4. `get-key-policy --key-id <id> --policy-name default` — confirm
   the policy is unchanged (rotation does not modify policy).
5. `list-grants --key-id <id>` — confirm grants are unchanged.
6. Spot-check: an application using the key ARN performs a test
   `Encrypt` + `Decrypt` cycle successfully (or confirm via metrics
   that no `KMSKeyUnavailableException` or `AccessDeniedException`
   spike occurred).

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim COMPLETED. A failed verification typically
means the key policy was inadvertently modified or the key was
simultaneously disabled by another process.

## Output format (per operation)

```text
OPERATION: <enable-rotation | verify-rotation | disable-rotation | plan-manual-rotation | diagnose-rotation>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <key-id> (alias: <alias-or-"none">, account <account>, region <region>)
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
NOTES: <rotation period, material lifecycle, monitoring, caveats>
```

### Worked example — enable-rotation (symmetric CMK)

```text
OPERATION: enable-rotation
VERDICT: READY
TARGET: arn:aws:kms:us-east-1:111111111111:key/abcd1234-... (alias:
        alias/prod-app-encryption-key, account 111111111111, region
        us-east-1)
PRE_CHECKS:
  - [PASS] Key exists, KeyState: Enabled
  - [PASS] Not PendingDeletion (DeletionDate absent)
  - [PASS] KeySpec: SYMMETRIC_DEFAULT, KeyUsage: ENCRYPT_DECRYPT
  - [PASS] Origin: AWS_KMS (supports automatic rotation)
  - [PASS] Single-region key (not a Multi-Region replica)
  - [PASS] Calling role has kms:EnableKeyRotation via key policy
    statement allowing arn:aws:iam::111111111111:role/SecurityAdmin
  - [PASS] RotationPeriodInSeconds: 365 (default — annual)
STEPS:
  1. CONFIRM: About to enable automatic backing-key rotation on KMS
     key alias/prod-app-encryption-key
     (arn:aws:kms:us-east-1:111111111111:key/abcd1234-...) in account
     111111111111 region us-east-1. Rotation period: 365 days. The key
     ID, ARN, policy, grants, and aliases are unchanged. Existing
     ciphertext remains decryptable. New Encrypt operations use the
     new backing material after the first rotation. Proceed? (yes/no)
  2. aws kms enable-key-rotation \
       --key-id arn:aws:kms:us-east-1:111111111111:key/abcd1234-...
  3. (Optional) Verify immediately:
     aws kms get-key-rotation-status \
       --key-id arn:aws:kms:us-east-1:111111111111:key/abcd1234-...
POST_VERIFY:
  - (pending execution)
NOTES:
  - The first rotation will occur within 24 hours of NextRotationDate
    (approximately 365 days from enablement). KMS performs the
    material swap; no application action is needed.
  - Old backing material is retained indefinitely (until the key is
    deleted). Existing ciphertext encrypted with old material remains
    decryptable — no re-encryption required.
  - CloudTrail will log the EnableKeyRotation event immediately. The
    actual material rotation does NOT produce a separate CloudTrail
    event; verify via NextRotationDate advancing.
  - For compliance evidence, capture quarterly:
    aws kms get-key-rotation-status --key-id <id>
    and store the output with NextRotationDate.
```

### Worked example — plan-manual-rotation (asymmetric RSA key)

Full plan-manual-rotation worked example moved verbatim to
`references/worked-examples.md` (load on demand).

### Worked example — diagnose-rotation (BLOCKED with remediation)

Full diagnose-rotation worked example moved verbatim to
`references/worked-examples.md` (load on demand).

## Anti-Patterns — NEVER

- NEVER call `enable-key-rotation` on an asymmetric, HMAC, or
  external-material key without first confirming it is a symmetric
  AWS_KMS-origin key. The API returns `InvalidOperationException`;
  the operator should plan a manual rotation instead.

- NEVER call `enable-key-rotation` on a Multi-Region replica key. The
  API returns `InvalidOperationException`. Enable rotation on the
  primary; the replica inherits the status.

- NEVER disable or delete an old key immediately after a manual
  rotation. Existing ciphertext, signatures, or MACs produced with the
  old key require the old key to be `Enabled` for decrypt / verify.
  Disable only after confirming all artifacts have been re-encrypted /
  re-signed or are no longer needed (typically 90+ days).

- NEVER assume `get-key-rotation-status.Enabled: true` means a
  rotation has occurred. It means rotation is SCHEDULED. The actual
  material swap happens at `NextRotationDate`. For proof that a
  rotation ran, compare `NextRotationDate` advancing over time or
  inspect the key's internal material versions (KMS does not expose
  material IDs publicly — `NextRotationDate` advancing is the
  observable signal).

- NEVER assume AWS-managed keys (`aws/s3`, `aws/rds`, etc.) rotate
  annually. They rotate approximately every 3 years on an AWS-managed
  schedule. You CANNOT enable, disable, or configure rotation on
  AWS-managed keys. For annual rotation compliance, use customer-
  managed keys.

- NEVER modify the key policy as part of a rotation operation. The
  policy is independent of the backing material. A policy change
  during rotation creates confusion about which change caused any
  subsequent access issue.

- NEVER assume `RotationPeriodInSeconds` is fixed at 365 days. It is
  configurable (7-365 days, default 365). Always read the current
  value from `get-key-rotation-status` before planning.

- NEVER confuse `enable-key-rotation` with `rotate-key-on-demand`
  (2024+ feature for immediate material rotation on symmetric keys).
  `enable-key-rotation` schedules recurring rotation;
  `rotate-key-on-demand` performs an immediate material swap. Use
  on-demand for incident response (suspected key compromise); use
  scheduled for routine cryptographic agility.

- NEVER call `schedule-key-deletion` to "force a rotation." Deletion
  is irreversible within the 7-30 day window; `cancel-key-deletion`
  restores the key but cancels its rotation schedule. Use
  `rotate-key-on-demand` for an immediate rotation instead.

- NEVER hard-code a key ARN in application configuration if you can
  use an alias. Aliases make manual rotation a one-line `update-alias`
  cutover; ARNs require updating every caller.

- NEVER assume CloudTrail logs the actual material rotation. CloudTrail
  logs `EnableKeyRotation` and `DisableKeyRotation` (management
  events). The material swap itself is an internal KMS operation with
  no separate CloudTrail event. Use `NextRotationDate` advancing as
  the observable signal.

- NEVER enable rotation on a key whose CloudHSM cluster is
  `DEGRADED` or `DISCONNECTED`. The `enable-key-rotation` API may
  succeed but the actual rotation will fail until the cluster is
  `ACTIVE`. Verify cluster state first.

- NEVER re-create grants after an automatic rotation. Grants are per-
  key-ID and survive rotation. Re-creating grants can create
  conflicting permissions and is unnecessary.

- NEVER call `disable-key-rotation` without a documented compliance
  exception. Disabling rotation is almost always a policy violation.
  If the goal is to "pause" rotation temporarily, leave rotation
  enabled and address the underlying concern instead.

- NEVER auto-execute a state-changing KMS CLI without the CONFIRM
  gate. Rotation operations are reversible, but disabling a key or
  scheduling deletion during a "rotation" workflow can cause
  immediate application outages.

## Pre-flight safety checks (run before any remediation CLI)

Pre-flight safety checks moved verbatim to
`references/diagnostic-commands.md` (load on demand).

## Recent AWS features (2024-2026)

Recent-feature details moved verbatim to
`references/advanced-patterns.md` (load on demand).


## References (load on demand)

- [`references/worked-examples.md`](references/worked-examples.md) — secondary worked examples: plan-manual-rotation (asymmetric RSA), diagnose-rotation (BLOCKED replica key).
- [`references/advanced-patterns.md`](references/advanced-patterns.md) — Step-0 expert KMS rotation behaviors, recent AWS features 2024-2026.
- [`references/error-handling.md`](references/error-handling.md) — rotation failure-mode table (symptom / root cause / fix).
- [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — sweep pagination, live-account pre-flight command listing, pre-flight safety checks.
- [`references/key-type-and-rotation-matrix.md`](references/key-type-and-rotation-matrix.md) — key type rotation support matrix and procedures.
- [`references/manual-rotation-procedures.md`](references/manual-rotation-procedures.md) — manual rotation procedures (caller identification, cutover).

## Domain

AWS CloudOps / KMS Key Rotation, Cryptographic Agility & Compliance.

## AWS documentation

- **AWS KMS Developer Guide** — https://docs.aws.amazon.com/kms/latest/developerguide/
- **Rotating keys** — https://docs.aws.amazon.com/kms/latest/developerguide/rotate-keys.html
- **Automatic key rotation** — https://docs.aws.amazon.com/kms/latest/developerguide/rotate-keys.html#rotate-keys-how-it-works
- **Manual key rotation** — https://docs.aws.amazon.com/kms/latest/developerguide/rotate-keys.html#rotating-keys-manually
- **Multi-Region keys** — https://docs.aws.amazon.com/kms/latest/developerguide/multi-region-keys-manage.html
- **Custom key stores** — https://docs.aws.amazon.com/kms/latest/developerguide/custom-key-store-overview.html
- **KMS API Reference** — https://docs.aws.amazon.com/kms/latest/APIReference/
- **KMS CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/kms/
- **KMS key quotas** — https://docs.aws.amazon.com/kms/latest/developerguide/resource-limits.html
