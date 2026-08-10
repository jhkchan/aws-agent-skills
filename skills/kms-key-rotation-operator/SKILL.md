---
name: kms-key-rotation-operator
description: >-
  Operates AWS KMS key rotation workflows end-to-end — key type
  classification (AWS-managed, customer-managed symmetric,
  asymmetric RSA/ECDSA, HMAC, Multi-Region primary/replica, custom key
  store / CloudHSM), automatic annual backing-key rotation enablement
  and verification, manual key rotation (create new CMK + re-encrypt),
  cryptographic material lifecycle (old material retained for decrypt,
  new encrypts transparently), and diagnostic loops (describe-key,
  get-key-rotation-status, CloudTrail EnableKeyRotation events,
  list-grants, key-policy diff). Runs deterministic pre-checks
  (key Enabled, key state not PendingDeletion, symmetric
  SYMMETRIC_DEFAULT usage, multi-Region primary not replica,
  EnableKeyRotation permission in key policy) behind a CONFIRM gate
  and emits a READY, BLOCKED, or COMPLETED verdict per rotation. Use
  when enabling automatic rotation, verifying rotation ran, planning a
  manual rotation, or diagnosing why rotation cannot be enabled.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline plan classification.
  Live-account operations use aws kms describe-key, get-key-rotation-
  status, enable-key-rotation, disable-key-rotation, list-grants,
  get-key-policy, list-resource-tags, aws cloudtrail lookup-events
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - KMS
  - key rotation
  - backing key
  - cryptographic material
  - customer managed key
  - CMK
  - AWS managed key
  - Multi-Region key
  - replica key
  - asymmetric key
  - RSA_2048
  - ECC_NIST_P256
  - HMAC_256
  - SYMMETRIC_DEFAULT
  - EnableKeyRotation
  - GetKeyRotationStatus
  - CloudHSM custom key store
  - key policy
  - re-encrypt
  - cryptographic agility
tags: [aws, kms, security, encryption, key-management, rotation, compliance, operate]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Security
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY | BLOCKED | COMPLETED"
  when_to_use: >-
    Enabling automatic backing-key rotation on a customer-managed KMS
    key, verifying a key's rotation status and last rotation date,
    planning a manual rotation for asymmetric/HMAC keys that do not
    support automatic rotation, diagnosing why EnableKeyRotation fails
    (Disabled/PendingDeletion key, asymmetric usage, replica key,
    missing key-policy permission), confirming CloudTrail
    EnableKeyRotation events, or validating cryptographic-agility
    posture across a fleet of CMKs.
  activation_triggers:
    - "enable KMS key rotation"
    - "rotate KMS key"
    - "verify key rotation"
    - "GetKeyRotationStatus"
    - "EnableKeyRotation"
    - "automatic key rotation"
    - "manual key rotation"
    - "backing key"
    - "Multi-Region key rotation"
    - "replica key rotation"
    - "asymmetric key rotation"
    - "HMAC key rotation"
    - "re-encrypt with new key"
    - "cryptographic agility"
    - "KMS rotation failed"
  invocation_schema: >-
    Input: either (a) a KMS key configuration (describe-key output)
    plus the intended operation (enable-rotation, verify-rotation,
    disable-rotation, plan-manual-rotation, diagnose-rotation), OR
    (b) a key-id + operation for live-account execution. Output:
    deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS /
    POST_VERIFY / NOTES block per rotation, where VERDICT is one of
    READY, BLOCKED, COMPLETED.
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

**Pagination:** `list-keys` paginates at 100/page — drain
`--marker`/`--next-marker` to completion. `list-grants` paginates at
50/page. `list-aliases` paginates at 100/page.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws kms describe-key --key-id <id>` — capture `KeyState`,
   `Enabled`, `KeyUsage`, `KeySpec`, `Origin`,
   `MultiRegionConfiguration`, `CreationDate`, `Description`,
   `DeletionDate` (if pending).
2. `aws kms get-key-rotation-status --key-id <id>` — capture
   `Enabled` (rotation status), `RotationPeriodInSeconds`,
   `NextRotationDate` (if enabled).
3. `aws kms get-key-policy --key-id <id> --policy-name default` —
   capture the policy; verify the caller's role has
   `kms:EnableKeyRotation` or that the caller is the root admin.
4. `aws kms list-grants --key-id <id>` — capture all grants.
   Rotation does not invalidate grants, but verify there are no
   ` retiring` grants that could affect behavior.
5. `aws kms list-aliases --key-id <id>` — capture aliases pointing
   to this key. Aliases are the application-facing name; rotation
   does not affect aliases.
6. `aws cloudtrail lookup-events --lookup-attributes
   AttributeKey=ResourceName,AttributeValue=<key-arn>
   --attribute-key EventSource --attribute-value kms.amazonaws.com
   --max-results 20` — capture recent `EnableKeyRotation`,
   `DisableKeyRotation`, `RotateKey` (manual) events.
7. For custom key stores: `aws kms describe-custom-key-stores` —
   verify the CloudHSM cluster state is `ACTIVE` and the key store
   `ConnectionState: CONNECTED`.

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

These behaviors are easy to misjudge without operational rotation
experience. Each changes a plan if ignored:

- **The key ID and ARN do NOT change after rotation.** A KMS key is
  a logical construct. Automatic rotation swaps the backing
  cryptographic material under the same key ID. Applications that
  reference the key by ID, ARN, or alias see no change. This is the
  single most important fact — rotation is invisible to callers.

- **Old backing material is retained for decrypt.** KMS tracks which
  backing material produced each ciphertext (via an internal
  material-id embedded in the ciphertext blob). When you decrypt, KMS
  selects the correct material automatically. You NEVER need to
  "re-encrypt after rotation" — existing ciphertext remains
  decryptable forever (or until the key is deleted).

- **New `Encrypt` calls always use the newest material.** After a
  rotation, every new `Encrypt` operation uses the new backing key
  material. Old ciphertext is unaffected. There is no gradual
  rollout — the switch is immediate for new operations.

- **Rotation does NOT modify the key policy.** The key's resource-
  based policy is independent of the backing material. Grants,
  aliases, and IAM permissions all survive rotation unchanged. Do not
  expect a policy diff after `EnableKeyRotation`.

- **`RotationPeriodInSeconds` is configurable (2024+).** The default
  is 365 days (annual). You can set 7-365 days via
  `enable-key-rotation --rotation-period-in-days N`. Shorter periods
  increase cryptographic agility but do not change cost.

- **`NextRotationDate` is computed by KMS.** After enabling,
  `get-key-rotation-status` returns `NextRotationDate`. KMS performs
  the actual material swap within 24 hours of this date (typically
  within minutes). The exact rotation moment is not user-controlled.

- **Asymmetric keys (RSA/ECDSA) do NOT support automatic rotation.**
  This is a hard limitation. The plan for an asymmetric key MUST be a
  manual rotation: (1) create a new key with the same
  `KeySpec`/`KeyUsage`, (2) update all callers (aliases are easiest
  — `update-alias` to point to the new key), (3) optionally
  re-encrypt old data with the new key.

- **HMAC keys do NOT support automatic rotation.** Same as
  asymmetric. HMAC keys (`KeyUsage: GENERATE_VERIFY_MAC`) require
  manual rotation. Update all MAC verifiers to use the new key.

- **Multi-Region replica keys inherit rotation from the primary.**
  Calling `EnableKeyRotation` on a replica returns
  `InvalidOperationException: You cannot manage key rotation on a
  replica key. Manage key rotation on the primary key instead.` The
  primary's rotation status propagates to all replicas via the
  Multi-Region key infrastructure.

- **Custom key store (CloudHSM) keys support automatic rotation.**
  For `Origin: AWS_CLOUDHSM`, `enable-key-rotation` rotates the
  backing key in the CloudHSM cluster. The cluster must be `ACTIVE`
  and `ConnectionState: CONNECTED`. If the cluster is disconnected,
  rotation is deferred.

- **External key material (`Origin: EXTERNAL`) does NOT support
  automatic rotation.** You imported the material; you must re-import
  new material to rotate. Use `import-key-material` with a new public
  key from `get-parameters-for-import`.

- **Grants survive rotation.** A grant is per-key-ID, not per-
  backing-material. After rotation, all existing grants continue to
  work on both old (decrypt) and new (encrypt) operations. Do NOT
  re-create grants after rotation.

- **CloudTrail logs `EnableKeyRotation` and `DisableKeyRotation` as
  management events.** The actual material rotation is logged as an
  internal KMS event — NOT a separate CloudTrail event. The proof
  that rotation occurred is `NextRotationDate` advancing and
  `LastRotationDate` (if exposed) updating in `get-key-rotation-
  status`.

- **Aliases are the rotation-friendly reference.** If applications
  reference the key by alias (`alias/my-app-key`), manual rotation is
  a one-line `update-alias` — callers see no change. If applications
  hard-code the key ARN, manual rotation requires updating every
  caller. Always prefer aliases for application-facing key references.

- **`schedule-key-deletion` cancels rotation implicitly.** When a key
  enters `PendingDeletion`, its rotation schedule is cancelled. If
  you later `cancel-key-deletion`, you must re-enable rotation
  explicitly — it does not resume automatically.

- **`kms:EnableKeyRotation` requires the key policy to allow the
  caller.** The root account always has access. For non-root callers,
  the key policy must include `kms:EnableKeyRotation` (and
  `kms:GetKeyRotationStatus` for verification) on the key ARN. The
  default managed policy `AWSKeyManagementServicePowerUser` does NOT
  include rotation actions.

- **AWS-managed keys (`aws/s3`, `aws/rds`, etc.) rotate automatically
  every 3 years (not annually).** You CANNOT enable, disable, or
  configure rotation on AWS-managed keys. The rotation cadence is
  fixed by AWS. Customer-managed keys support the configurable
  annual cadence.

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

| Symptom | Root cause | Fix |
|---|---|---|
| `enable-key-rotation` returns `InvalidOperationException: ... cannot be performed on a key with KeyUsage SIGN_VERIFY` | Asymmetric key — automatic rotation not supported | Plan manual rotation (create new key + update aliases + re-sign) |
| `enable-key-rotation` returns `InvalidOperationException: ... cannot be performed on a key with Origin EXTERNAL` | Imported key material — KMS cannot rotate | Re-import new material via `get-parameters-for-import` + `import-key-material` |
| `enable-key-rotation` returns `AccessDeniedException` | Key policy denies caller `kms:EnableKeyRotation`, or caller's identity-based policy lacks it | Add `kms:EnableKeyRotation` to the key policy for the caller's role, or call from an authorized role |
| `enable-key-rotation` returns `KMSInvalidStateException: Key is in Disabled state` | Key is `Disabled` | `aws kms enable-key --key-id <id>` first, then enable rotation |
| `enable-key-rotation` returns `KMSInvalidStateException: Key is in PendingDeletion state` | Key scheduled for deletion | `cancel-key-deletion --key-id <id>`, then `enable-key`, then `enable-key-rotation` |
| `enable-key-rotation` returns `InvalidOperationException: ... replica key` | Multi-Region replica — rotation controlled by primary | Call `enable-key-rotation` on the primary key ARN (cross-region if needed) |
| `enable-key-rotation` returns `CloudHsmClusterNotActiveException` | Custom key store's CloudHSM cluster is not `ACTIVE` | Restore the CloudHSM cluster to `ACTIVE`; reconnect the key store |
| `get-key-rotation-status.Enabled: true` but `NextRotationDate` is in the past | Rotation deferred due to KMS internal scheduling or a transient issue | Wait 24 hours; if still overdue, open AWS support |
| `get-key-rotation-status` returns `AccessDeniedException` | Key policy denies caller `kms:GetKeyRotationStatus` | Add `kms:GetKeyRotationStatus` to the key policy for the caller's role |
| CloudTrail shows no `EnableKeyRotation` event but status shows enabled | Rotation was enabled via the console (still logs as `EnableKeyRotation`) or before the trail was created | Verify via `get-key-rotation-status` directly; CloudTrail history is bounded by the trail's retention |
| Applications break after manual rotation (alias updated) | The old key was disabled or deleted before ciphertext was re-encrypted | Re-enable the old key; applications decrypting old ciphertext need the old key `Enabled` |

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

```text
OPERATION: plan-manual-rotation
VERDICT: READY
TARGET: arn:aws:kms:us-east-1:111111111111:key/rsa12345-... (alias:
        alias/prod-signing-key, account 111111111111, region
        us-east-1)
PRE_CHECKS:
  - [PASS] Key exists, KeyState: Enabled
  - [PASS] Not PendingDeletion
  - [INFO] KeySpec: RSA_2048, KeyUsage: SIGN_VERIFY — automatic
    rotation NOT supported (hard KMS limitation)
  - [PASS] Operator has kms:CreateKey permission
  - [PASS] Alias alias/prod-signing-key points to this key — callers
    using the alias will follow the update-alias cutover transparently
  - [INFO] 3 CloudTrail-observed callers in the last 30 days:
    prod-orders-service (uses alias), prod-payments-service (uses
    alias), prod-web-app (uses key ARN — MUST be updated manually)
STEPS:
  1. CONFIRM: About to perform a MANUAL rotation on RSA signing key
     alias/prod-signing-key. This involves: (a) creating a new RSA_2048
     key, (b) updating alias/prod-signing-key to point to the new key,
     (c) updating prod-web-app to use the new key ARN. Old signatures
     remain verifiable against the old key (which stays Enabled).
     Proceed? (yes/no)
  2. Create the new key:
     aws kms create-key \
       --description "prod-signing-key rotation 2026-08" \
       --key-usage SIGN_VERIFY \
       --key-spec RSA_2048 \
       --policy file://new-key-policy.json
     # Capture the new KeyId from the response.
  3. Update the alias (atomic cutover for alias-referencing callers):
     aws kms update-alias \
       --alias-name alias/prod-signing-key \
       --target-key-id <new-key-id>
  4. Update prod-web-app (hard-coded ARN caller):
     # Update the application configuration / environment variable to
     # the new key ARN. Deploy. Verify signatures validate with the
     # new key.
  5. (Optional) Re-sign critical artifacts with the new key. Old
     signatures remain valid as long as the old key is Enabled.
POST_VERIFY:
  - (pending execution)
NOTES:
  - The old key (rsa12345-...) MUST remain Enabled for as long as any
    signature produced with it needs to be verified. Disabling or
    deleting the old key breaks signature verification for all
    artifacts signed by it.
  - Schedule a review in 90 days: if all observed verifications use
    the new key, consider scheduling the old key for deletion (after
    compliance approval).
  - For compliance evidence, document the manual rotation with a
    ticket reference and the CloudTrail CreateKey + UpdateAlias
    events.
```

### Worked example — diagnose-rotation (BLOCKED with remediation)

```text
OPERATION: diagnose-rotation
VERDICT: BLOCKED
TARGET: arn:aws:kms:us-east-1:111111111111:key/multi-replica-... (alias:
        alias/prod-dr-key, account 111111111111, region us-east-1)
PRE_CHECKS:
  - [PASS] Key exists
  - [INFO] KeyState: Enabled
  - [FAIL] MultiRegionConfiguration.MultiRegionKeyType: REPLICA
    (primary: arn:aws:kms:eu-west-1:111111111111:key/multi-primary-...)
    — EnableKeyRotation cannot be called on a replica key. Rotation
    must be enabled on the primary in eu-west-1.
STEPS: (none — wrong key target)
POST_VERIFY: (none)
NOTES:
  - Root cause: the operator is trying to enable rotation on a Multi-
    Region REPLICA key. KMS returns InvalidOperationException for
    this case. Rotation is controlled by the primary key.
  - Fix: call enable-key-rotation on the PRIMARY key in eu-west-1:
    aws kms enable-key-rotation \
      --key-id arn:aws:kms:eu-west-1:111111111111:key/multi-primary-... \
      --region eu-west-1
    The primary's rotation status propagates to all replicas
    automatically. Verify on the replica after the primary's
    NextRotationDate:
    aws kms get-key-rotation-status \
      --key-id arn:aws:kms:us-east-1:111111111111:key/multi-replica-...
```

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

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`enable-key-rotation`, `disable-key-rotation`, `enable-key`,
  `disable-key`, `schedule-key-deletion`, `cancel-key-deletion`,
  `create-key`, `update-alias`, `rotate-key-on-demand`), emit:
  `CONFIRM: About to <operation> on KMS key <key-id> in account
  <account> region <region>. This will <consequence>. Proceed?
  (yes/no)`. Do NOT execute until the operator confirms.

- **Capture pre-state for audit.** Before any rotation operation:
  `aws kms describe-key --key-id <id> --output json > /tmp/<id>-
  describe-pre-$(date +%s).json` AND `aws kms get-key-rotation-status
  --key-id <id> --output json > /tmp/<id>-rotation-pre-$(date
  +%s).json`. These captures are critical for compliance evidence and
  for diagnosing any post-change anomaly.

- **Verify the key policy is unchanged after rotation.** `get-key-
  policy --key-id <id> --policy-name default` — diff against pre-state.
  Rotation must not modify the policy. A policy change indicates a
  concurrent modification by another process.

- **Verify grants are unchanged.** `list-grants --key-id <id>` — diff
  against pre-state. Rotation does not affect grants.

- **Verify CloudTrail is logging the event.** If the account's
  CloudTrail trail is paused or misconfigured, the `EnableKeyRotation`
  event will not be captured. Compliance evidence depends on the
  trail being active.

- **Prefer additive changes over destructive ones.** Enabling
  rotation is safe and reversible. Disabling rotation, disabling a
  key, or scheduling deletion is consequential — confirm intent
  explicitly.

## Recent AWS features (2024-2026)

- **`rotate-key-on-demand` (2024):** Immediate backing-key material
  rotation on symmetric CMKs, separate from the scheduled rotation.
  Useful for incident response (suspected compromise). The on-demand
  rotation does not affect the scheduled `NextRotationDate`. Costs
  nothing extra.

- **Configurable `RotationPeriodInSeconds` (2024):** The rotation
  period is now 7-365 days, set via `enable-key-rotation --rotation-
  period-in-days N` (or `--rotation-period-in-seconds`). Previously
  fixed at 365 days.

- **HMAC keys (`GENERATE_VERIFY_MAC`, 2022 GA, 2024 hardening):** Do
  NOT support automatic rotation. Manual rotation required. Plan a
  new HMAC key + update callers + retire old key.

- **Multi-Region keys GA (2023-2024):** Primary key controls rotation.
  Replicas inherit. A replica's `get-key-rotation-status` reflects the
  primary's setting. `EnableKeyRotation` on a replica fails.

- **Custom key store (CloudHSM) rotation (2024):** Symmetric keys in
  a custom key store support automatic rotation. KMS rotates the
  backing key material within the CloudHSM cluster. The cluster must
  be `ACTIVE` and `CONNECTED`.

- **Asymmetric RSA and ECDSA keys (no auto-rotation, 2024-2026):**
  Still no automatic rotation support. Manual rotation is the only
  option. AWS roadmap items have been discussed but no GA feature as
  of 2026.

- **`XksProxyUriEndpoint` for external key stores (2024-2025):**
  External key stores (XKS) allow BYOK with an external HSM via the
  KMS XKS proxy. Keys in an XKS do NOT support automatic rotation;
  rotation is managed by the external HSM.

- **CloudTrail data event logging for KMS (2025):** CloudTrail now
  supports data-event logging for `Decrypt`, `Encrypt`, and
  `GenerateDataKey`. Useful for auditing which ciphertext was
  decrypted by whom — but management events (`EnableKeyRotation`)
  are always logged without data-event configuration.

- **KMS key aliases as CloudFormation resources (2024):**
  `AWS::KMS::Alias` is now fully supported in CloudFormation, making
  alias-based manual rotation automation-friendly.

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
