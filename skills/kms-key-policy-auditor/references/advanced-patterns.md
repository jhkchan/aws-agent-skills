# Advanced Patterns — kms-key-policy-auditor

Expert deep-dives moved verbatim from SKILL.md. Load on demand.

## Step 0: Expert knowledge — non-obvious KMS behaviors that change classification

These behaviors are easy to misjudge without operational KMS experience.
Each changes a verdict if ignored:

- **Aliases are NOT access control.** `kms:Decrypt` does not honour the
  alias used at encryption time — a caller with `kms:Decrypt` on
  `arn:aws:kms:...:key/abc` can decrypt ciphertext regardless of which
  alias (`alias/prod`, `alias/dev`) was used to encrypt. A policy that
  scopes Decrypt to "alias/prod only" provides **zero** restriction. The
  alias is a pointer, not a boundary. Do NOT downgrade a wildcard Decrypt
  finding because the alias looks scoped.

- **`Resource` in a key policy is effectively always `"*"`.** The key
  policy IS attached to the key — there is no other resource it could
  refer to. A statement with `Resource: "<own-key-arn>"` and one with
  `Resource: "*"` are functionally identical. Do not treat a scoped
  `Resource` element as a restriction; evaluate `Principal` + `Action` +
  `Condition` only.

- **`kms:GenerateDataKey` returns plaintext key material;
  `kms:GenerateDataKeyWithoutPlaintext` returns ciphertext only.** Both
  are DATA_ACCESS for severity purposes, but the WithoutPlaintext variant
  is meaningfully lower risk on its own (the caller cannot decrypt
  without a separate Decrypt call). When a statement grants ONLY
  `GenerateDataKeyWithoutPlaintext`, downgrade one level vs. granting
  `GenerateDataKey`.

- **`kms:Sign` is irreversible and outlives key deletion.** A signature
  made today is valid forever; deleting the signing key does NOT
  invalidate signatures already produced. Treat `kms:Sign` on an
  asymmetric key to a wildcard/cross-account principal as HIGH (not
  MEDIUM) — the exposure window is permanent, unlike Decrypt which can be
  revoked. This is the same logic that elevates `kms:ScheduleKeyDeletion`
  to CRITICAL.

- **`kms:ReEncrypt*` is a two-key privilege.** `ReEncryptFrom` and
  `ReEncryptTo` operate across a source AND a destination key. A
  destination key with a wildcard `ReEncryptFrom` lets any account push
  ciphertext into your key — pair it with the SOURCE key's policy when
  auditing, not just the destination.

- **`kms:BypassPolicyLockoutSafetyCheck`** is a real PutKeyPolicy flag.
  When `true`, KMS skips the check that requires the calling account to
  remain in the new policy. It is REQUIRED when transferring a key to a
  different account (no principals from the calling account remain).
  Presence of this flag in CloudTrail logs on `PutKeyPolicy` is a strong
  signal of a key-ownership transfer or a lockout — investigate before
  treating the resulting policy as the steady state.

- **Grants are per-key, not per-principal.** `aws kms list-grants
  --key-id <id>` returns ALL grants on the key; there is no
  `--grantee-principal` filter at the API level. When auditing
  `kms:CreateGrant`, you must enumerate the full grant list and filter
  client-side — a grant created by principal A may delegate to principal
  B, and the key policy shows neither.

- **Grant constraint distinction:** `EncryptionContextEquals` requires
  EXACT context match (all pairs, no extras); `EncryptionContextSubset`
  allows the grantee to ADD extra context pairs. A grant constrained
  with `Subset` is weaker than one constrained with `Equals` — flag the
  difference when reviewing grant constraints.

- **AWS-managed keys are REGIONAL, not global.** `aws/s3` in us-east-1 is
  a different physical key from `aws/s3` in ap-southeast-1. A workload
  using S3 SSE-KMS in multiple regions transparently uses N different
  AWS-managed keys. This matters for CloudTrail forensics: a Decrypt
  event in region A does not match an Encrypt event in region B even
  though both reference "aws/s3".

- **Key policy size limit is 32 KiB.** A policy with many statements can
  hit this cap and silently reject `PutKeyPolicy` with
  `ValidationException`. When proposing additive Deny statements as
  remediation, estimate cumulative size — prefer fewer, broader Denies
  over many narrow ones if the policy is already near the cap.

- **Custom key store (CloudHSM) keys couple to HSM availability.** A key
  with `Origin: AWS_CLOUDHSM` becomes INACCESSIBLE (not Disabled —
  `kms:Decrypt` returns `KMSInternalException`) if the backing CloudHSM
  cluster is down or deleted. This is an availability risk that
  standard KMS keys do not have. Flag as an operational finding
  (MEDIUM) if the cluster has < 3 HSM nodes or is in a single AZ.

- **`kms:GenerateMac` / `kms:VerifyMac` are HMAC-key operations.** They
  are the MAC analogues of Sign/Verify. Treat as METADATA danger level
  (low), but flag HMAC keys separately — they have no rotation concept
  regardless of KeySpec.

- **HMAC `KeySpec` (`HMAC_*`) vs `Origin: EXTERNAL`**: both disable
  rotation, but for different reasons. HMAC keys genuinely have no
  rotation API; imported key material rotates by re-importing. The
  Pre-flight gate treats both as N/A, but the remediation note differs:
  for HMAC, "no action available"; for EXTERNAL, "re-import fresh key
  material per your rotation policy".

- **`kms:Decrypt` ignores the calling service when no
  `kms:ViaService` condition is present.** A principal with Decrypt can
  call from EC2, Lambda, or anywhere — KMS does not infer the caller's
  service. Only an explicit `kms:ViaService` condition couples the call
  to a named service. This is why ViaService is STRONG and the absence
  of any condition is treated as "anywhere".

- **The 7-30 day deletion window is a hard API bound.** AWS rejects
  `ScheduleKeyDeletion` with `ValidationException` if
  `PendingWindowInDays` is < 7 or > 30. A reported value outside this
  range indicates either a stale snapshot (re-fetch via `describe-key`)
  or a pre-2022 key scheduled under the older 7-30 default. The
  CRITICAL threshold at ≤ 7 days is the API minimum — anything at 7 is
  already at the floor and should be treated as imminent.

## Rotation timing (expert note) — Step 6 detail

**Rotation timing (expert note):** when you enable rotation on an existing
key, the first rotation does NOT happen immediately — it occurs within
365 days. After that, rotations repeat annually. The backing key material
changes, but the key ARN, key ID, and all policies remain unchanged.
Critically, old backing key material is **retained** so that prior
ciphertext can still be decrypted — rotation does NOT require re-encryption
of existing data. However, if the current backing key is compromised
BEFORE the next rotation window, the attacker retains access until KMS
rotates. This is why disabled rotation is HIGH, not MEDIUM — the exposure
window is unbounded.

## Edge-case handling — detail

- **Partially malformed policy.** If the policy JSON parses but individual
  statements are missing required fields (`Effect`, `Principal`, `Action`
  or `NotAction`), classify each valid statement normally and emit an
  ERROR note for each malformed statement: "Statement N is malformed
  (missing Effect/Principal/Action) — skipped." Do NOT silently classify
  the entire key as ERROR when only one statement is broken; the valid
  statements may still produce a CRITICAL finding.

- **Conflicting Allow and Deny.** If a Deny statement blocks the same
  principal/action/resource tuple as an Allow, the Deny wins (standard AWS
  evaluation). However, Deny statements in KMS key policies are rare and
  usually target specific conditions (e.g., `aws:SecureTransport: false`
  to enforce TLS). A Deny does NOT cancel a CRITICAL Allow unless it
  blocks the exact same principal + action + resource triple. A Deny on
  `aws:SecureTransport: false` with `Principal: "*"` blocks non-TLS
  access but does NOT restrict TLS access from a cross-account principal
  — the cross-account decrypt is still CRITICAL.

- **Statement with `Principal: "*"` AND same-account principals.** A
  single statement with `Principal: {"AWS": ["arn:aws:iam::111:role/app",
  "*"]}` is classified by the **widest** principal in the list —
  WILDCARD_PRINCIPAL. The same-account principal does not "dilute" the
  wildcard. Flag as CRITICAL if the action is DATA_ACCESS.

- **`NotPrincipal`.** `NotPrincipal` in an Allow statement grants access
  to every principal EXCEPT the listed ones — the inverse of the intended
  scope. Treat any `NotPrincipal` in an Allow as WILDCARD_PRINCIPAL
  (grants to everyone except the named principal, which is almost never
  the intent).

- **Empty policy (no statements).** A key policy with an empty `Statement`
  array means no principal — not even the account root — has explicit key
  policy access. If the root-of-trust statement is absent, IAM policies
  are bypassed and the key may be unmanageable. Output:
  `VERDICT: ERROR, REASON: Key policy has no statements — key may be
  unmanageable. Contact AWS support if root access is lost.`

- **AWS-managed key with custom policy.** AWS-managed keys
  (`KeyManager: AWS`) should have an AWS-default policy. If the input
  shows a custom policy on an AWS-managed key, flag as an anomaly —
  AWS-managed key policies are not customer-editable and a custom policy
  suggests either a misidentified key or stale documentation.

## Condition strength reference (KMS-specific) — table

| Condition key | Strength | Reason |
|---|---|---|
| `kms:ViaService` | STRONG | Set by AWS service infrastructure; caller cannot forge. Couples key use to a named service (e.g., `s3.us-east-1.amazonaws.com`). |
| `kms:CallerAccount` | STRONG | Set by KMS itself; restricts to a specific account. Equivalent to `aws:SourceAccount`. |
| `aws:SourceAccount` | STRONG | Set by the calling AWS service; identifies the owning account of the calling resource. |
| `aws:SourceArn` | STRONG | Set by the calling AWS service; identifies the specific calling resource. Tighter than SourceAccount. |
| `kms:EncryptionContext:*` | CONDITIONAL | STRONG when context is service-controlled (S3, EBS); WEAK when caller controls the context value (self-satisfiable). |
| `kms:GrantConstraintType` | MODERATE | Limits which grant constraint types a principal can create. Reduces delegation abuse surface. |
| `aws:SourceIp` (non-public CIDR) | WEAK | Network-scoped but bypassable by callers who control egress. Treat cross-account IP-restricted grants as one level less severe than unrestricted. |
| `aws:SourceIp` (`0.0.0.0/0`) | NONE | The entire internet. Do NOT treat as a restriction. |
| `aws:Referer` | NONE | Forgeable by any HTTP client. Never a real restriction. |
| `aws:UserAgent` | NONE | Forgeable by any HTTP client. Never a real restriction. |

## Deep reference: KMS authorization internals — detail

### Authorization evaluation pipeline

KMS evaluates an access request in a fixed order that differs from the IAM
pipeline — it has a **grant layer** that does not exist for other AWS
resources:

1. **Organizations SCP** — sets the maximum permissions. An SCP Deny blocks
   the request.
2. **Key policy** — the resource-based policy. For cross-account access,
   BOTH the key policy AND the caller's identity-based policy must allow
   the action (intersection). For same-account access, EITHER suffices
   (union) — but only if the key policy includes the root-of-trust
   statement.
3. **IAM identity-based policy** — evaluated only if the key policy
   delegates to IAM via the root-of-trust statement. If the key policy
   does NOT include `Principal: {AWS: "arn:aws:iam::ACCOUNT:root"}`, IAM
   policies are **bypassed entirely**. This is the most misunderstood KMS
   behavior.
4. **Grants** — evaluated last. A grant can delegate permissions NOT in
   either the key policy or the IAM policy. This is why `kms:CreateGrant`
   is a delegation vector.

### Grant chaining and enumeration

A grant can include `kms:CreateGrant` as an allowed operation, allowing the
grantee to create a sub-grant. KMS limits grant depth to **2 levels**
(original grant + one sub-grant). When auditing `kms:CreateGrant`, enumerate
all live grants: `aws kms list-grants --key-id <id>`. Check for: (1) grants
to principals not in the key policy, (2) grants with no constraints, (3)
grants that include `CreateGrant` in Operations (chain-capable). Retire
suspicious grants with `aws kms retire-grant --key-id <id> --grant-id <gid>`.

### Key policy versioning

Unlike IAM managed policies (which support up to 5 versions with rollback),
KMS key policies have **no version history**. `kms:PutKeyPolicy` replaces
the entire policy atomically — no diff, no staged rollout, no automatic
rollback. The only recovery path is a manual backup file.

### Rotation timing internals

When you enable rotation on an existing key, the first rotation occurs
within 365 days (not immediately), then annually. The backing key material
changes, but the key ARN, key ID, and policies remain unchanged. Old
backing key material is **retained** so prior ciphertext can still be
decrypted — rotation does NOT require re-encryption. If the current backing
key is compromised before the next rotation window, the attacker retains
access until KMS rotates. This is why disabled rotation is HIGH, not MEDIUM.

### Multi-region replica independence

Each replica has an independent key policy and independent rotation
setting. Policy fixes must be applied to each replica via
`aws kms describe-key` → `MultiRegionConfiguration` → replicate ARNs →
apply per-replica. KMS does NOT sync key policies across replicas.

## Recent AWS features (2024-2026) — detail

- **On-demand key rotation (2024):** KMS now supports on-demand key rotation for customer-managed keys in addition to the annual automatic rotation. Auditors should verify that critical keys have rotation enabled (either automatic or on-demand) — the `RotationEnabled` field in `describe-key` now reflects both automatic and on-demand rotations.
- **HMAC key support GA (2024):** KMS now supports HMAC (Hash-based Message Authentication Code) keys (`KeySpec: HMAC_*`). Auditors should verify that HMAC key policies follow the same cross-account restrictions as encryption keys — an HMAC key with `Principal: "*"` is equally dangerous.
- **External Key Store (XKS) updates (2024-2025):** XKS allows using external (on-premises) key material with KMS. Auditors should verify that XKS connectivity is healthy (the XKS proxy endpoint is reachable and authenticated) — an unreachable XKS means encryption/decryption operations silently fail.
- **Multi-Region keys enhancements (2024):** Improved multi-region key replica management. Auditors should verify that multi-region primary keys have appropriate policy guards and that replica keys in other regions do not have broader policies than the primary.
- **Key spec expansion (2024-2025):** New key specs including `RSA_4096`, `ML_*` (post-quantum hybrid key exchange for TLS). Auditors should verify that key specs match the encryption requirements — using RSA_2048 for workloads that require RSA_4096 is a compliance gap.
