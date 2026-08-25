# Advanced Patterns — kms-key-rotation-operator

Expert deep-dives moved verbatim from SKILL.md. Load on demand.

## Step 0: Expert knowledge — non-obvious KMS behaviors

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

## Recent AWS features (2024-2026) — detail

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
