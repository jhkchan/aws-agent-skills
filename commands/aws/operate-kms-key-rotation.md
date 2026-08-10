---
description: Operate AWS KMS key rotation operations — enable automatic backing-key rotation on symmetric CMKs, verify rotation status, disable rotation (rare), plan manual rotation for asymmetric/HMAC/external-material keys, diagnose why EnableKeyRotation fails — with deterministic pre-checks, CONFIRM gate, and post-verification via get-key-rotation-status and CloudTrail.
nl_triggers:
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
  - "rotate-key-on-demand"
routes_to: kms-key-rotation-operator
---

# /aws:operate-kms-key-rotation

Activate the `kms-key-rotation-operator` skill and plan/execute a KMS
key rotation operation with deterministic pre-checks, CONFIRM gate,
and post-verification.

## What it does

Reads a KMS key configuration (`describe-key`) plus the intended
operation and applies the priority-ordered pre-check sequence:

1. Pre-flight key metadata gate — short-circuit PendingDeletion keys,
   Disabled keys, and custom-key-store cluster state.
2. Pre-check gate — BLOCKED if any check fails (asymmetric/HMAC/external
   usage with auto-rotation requested, Multi-Region replica key with
   auto-rotation requested, missing `kms:EnableKeyRotation` permission,
   custom key store with cluster not ACTIVE).
3. READY — emit the exact CLI sequence (`enable-key-rotation` with
   `--rotation-period-in-days` if applicable), the expected
   cryptographic-material lifecycle, and the CONFIRM gate prompt.
4. Execute behind CONFIRM gate — capture pre-state, execute the CLI,
   verify CloudTrail logs the event.
5. Post-verification — `get-key-rotation-status` matches intent,
   CloudTrail `EnableKeyRotation` event present, key policy and grants
   unchanged. COMPLETED only if ALL post-verification checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <enable-rotation | verify-rotation | disable-rotation | plan-manual-rotation | diagnose-rotation>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <key-id> (alias: <alias-or-"none">, account <account>, region <region>)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <verification command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <rotation period, material lifecycle, monitoring, caveats>
```

## When to invoke

Paste a KMS key configuration plus the intended operation, or just
describe the scenario and ask any of:

- "enable rotation on this customer-managed key"
- "verify key rotation is enabled and NextRotationDate is set"
- "the key is asymmetric — how do I rotate it?"
- "EnableKeyRotation returns InvalidOperationException"
- "EnableKeyRotation returns AccessDeniedException"
- "is this Multi-Region replica inheriting rotation from the primary?"
- "rotate this HMAC key"
- "plan a manual rotation for my RSA signing key"
- "diagnose why KMS rotation is not running"
- "what's the difference between enable-key-rotation and rotate-key-on-demand?"

A bare key-id or alias + any rotation verb also routes here via the
orchestrator.

## Inputs

- Key configuration (`describe-key` JSON): `KeyState`, `Enabled`,
  `KeyUsage`, `KeySpec`, `Origin`, `MultiRegionConfiguration`,
  `Description`, `DeletionDate`.
- Rotation status (`get-key-rotation-status` JSON): `Enabled`,
  `RotationPeriodInSeconds`, `NextRotationDate`.
- Key policy (`get-key-policy` JSON) — verify
  `kms:EnableKeyRotation` for the caller's role.
- Grants (`list-grants` JSON) — verify grant count and that none are
  retiring.
- Aliases (`list-aliases` JSON) — capture which aliases point to the
  key (for manual-rotation cutover planning).
- CloudTrail `EnableKeyRotation` / `DisableKeyRotation` events
  (`lookup-events` on `kms.amazonaws.com`).
- For custom key stores: `describe-custom-key-stores` cluster state.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact `enable-key-rotation` CLI command with
  `--rotation-period-in-days` if specified, the expected material
  lifecycle behavior (old material retained for decrypt, new
  encrypts), and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, including
  `get-key-rotation-status.Enabled` matching intent, CloudTrail event
  present, key policy and grants unchanged.
- For BLOCKED: the specific failure reason and the remediation step
  (e.g., enable the key first, call enable-key-rotation on the
  Multi-Region primary, plan a manual rotation for asymmetric keys,
  add `kms:EnableKeyRotation` to the key policy).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for KMS key rotation).
- `/aws:audit-kms-key-policy` for the audit-side counterpart —
  auditing key policy posture across many keys without changing
  state.
- `/aws:deploy-iam-role` for IAM role deployment (rotation
  permissions are typically granted via IAM policies).
