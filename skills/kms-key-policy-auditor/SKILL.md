---
name: kms-key-policy-auditor
description: Audits AWS KMS key policies and key metadata for cross-account or external principals, wildcard kms:* grants, the kms:Decrypt blast-radius multiplier, automatic-key-rotation status, and key-deletion window exposure. Emits a deterministic severity verdict (CRITICAL | HIGH | MEDIUM | OK) per key with enumerated findings and specific remediation. Use when reviewing KMS key policies, checking for cross-account decrypt access, validating rotation enablement, auditing key deletion windows, or hardening encryption key posture before production deployment.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline policy-document classification. Live-account audits use aws kms describe-key, aws kms get-key-policy, and aws kms list-keys (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  verdict_shape: CRITICAL | HIGH | MEDIUM | OK
  when_to_use: Reviewing a KMS key policy before production deployment, checking for cross-account or external principal access, auditing wildcard kms:* grants, validating automatic key rotation, inspecting a key deletion window, or hardening encryption-key posture across an account.
  activation_triggers: audit this KMS key policy, is my KMS key exposed cross-account, check kms:Decrypt blast radius, review key deletion window, is key rotation enabled, harden KMS key policy, who can kms:Decrypt, kms key policy too permissive
  invocation_schema: 'Input: either (a) a KMS key policy JSON document, optionally paired with describe-key metadata, OR (b) a key-id/ARN for live-account audit. Output: deterministic KEY/VERDICT/REASON/FINDINGS/REMEDIATION block per key, where VERDICT ∈ {CRITICAL, HIGH, MEDIUM, OK, ERROR}.'
  version: 0.2.0
  author: Jacky Chan — AWS Community Builder
  keywords: KMS, key policy, cross-account, kms:Decrypt, kms:*, wildcard permissions, key rotation, key deletion, PendingDeletion, EnableKeyRotation, kms:CreateGrant, kms:ScheduleKeyDeletion, encryption key audit, data-at-rest, blast radius, kms:ViaService, Principal:"*", key policy remediation
  tags: kms, security, key-policy, cross-account, rotation, deletion-window, encryption, audit
---

# KMS Key Policy Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
all dimensions, and three KMS actions are in a class of their own —
`kms:Decrypt` (blast-radius multiplier), `kms:ScheduleKeyDeletion`
(one-way door), and `kms:CreateGrant` (silent delegation vector).

KMS is the root of trust for data-at-rest encryption. A KMS key policy is
the authorisation gate for every ciphertext ever produced under that key.
- `kms:Decrypt` is a **blast-radius multiplier**: one permission grants
  read access to *all* encrypted data, not one record.
- `kms:ScheduleKeyDeletion` is a **one-way door**: deleted key material is
  permanently unrecoverable after the window expires.
- `kms:CreateGrant` is a **delegation vector**: it can widen access beyond
  what the key policy text shows (grants are a separate auth layer).

## Quick reference — severity thresholds

| Condition | Verdict | Rule |
|---|---|---|
| `KeyState: PendingDeletion` + `PendingWindowInDays <= 7` | **CRITICAL** | Step 1 |
| `Principal: "*"` + `kms:Decrypt`/`kms:*`/`*` + no strong condition | **CRITICAL** | Rule 5a/5b |
| Cross-account + `kms:Decrypt`/`kms:*` + no strong condition | **CRITICAL** | Rule 5c/5d |
| Cross-account + `kms:PutKeyPolicy`/`kms:ScheduleKeyDeletion` | **CRITICAL** | Rule 5d |
| `Principal: "*"` + `kms:CreateGrant` + no strong condition | **CRITICAL** | Rule 5e |
| Cross-account + `kms:Encrypt`/`kms:CreateGrant` + no strong condition | **HIGH** | Rule 5g/5h |
| `Principal: "*"` + `kms:Encrypt` + no strong condition | **HIGH** | Rule 5f |
| `EnableKeyRotation: false` on customer-managed SYMMETRIC_DEFAULT key | **HIGH** | Step 6 |
| `KeyState: PendingDeletion` + `PendingWindowInDays 8-30` | **HIGH** | Step 1 |
| Cross-account + any action + STRONG condition | **MEDIUM** (downgrade) | Rule 5k |
| Cross-account + `kms:Describe*`/`kms:List*` only | **MEDIUM** | Rule 5j |
| Same-account only + named actions + rotation enabled + not pending deletion | **OK** | Step 7 |

See the ordered steps below for edge cases. Deep KMS authorization
internals (evaluation pipeline, grant chaining, policy versioning) are in
the [Deep reference](#deep-reference-kms-authorization-internals) section
at the end.

## Pre-flight: key metadata gate (run before policy classification)

Before evaluating the key policy, classify the key itself. Several key
attributes **short-circuit** the audit — misclassifying them produces false
positives that erode trust.

Pagination note + live-account pre-flight checks moved verbatim to
`references/diagnostic-commands.md` (load on demand).

| Attribute | Value | Effect on audit |
|---|---|---|
| `KeyManager` | `AWS` | **AWS-managed key** (`aws/s3`, `aws/ebs`, etc.). Policy is managed by AWS — skip policy audit. Rotation is automatic (annual). Verdict: **OK** unless pending deletion (rare for AWS-managed keys). |
| `KeyManager` | `CUSTOMER` | Proceed with full audit. |
| `KeySpec` | `RSA_*`, `ECC_*`, `SM2` | **Asymmetric key.** Automatic rotation is NOT supported. Do NOT flag `EnableKeyRotation: false` — it is a false positive. Still audit the policy. |
| `KeySpec` | `HMAC_*` | **HMAC key.** No rotation concept. Do NOT flag rotation. Still audit the policy. |
| `KeySpec` | `SYMMETRIC_DEFAULT` | **Symmetric key.** Rotation is supported — flag if disabled. |
| `Origin` | `EXTERNAL` | **Imported key material.** Automatic rotation is N/A (you manage rotation by re-importing). Do NOT flag `EnableKeyRotation: false`. Still audit the policy. |
| `Origin` | `AWS_CLOUDHSM` | Custom key store. Rotation is supported but managed via the HSM. Flag if `EnableKeyRotation: false` on a symmetric key. |
| `MultiRegion` | `true` | **Multi-Region key.** Each replica has an INDEPENDENT key policy and INDEPENDENT rotation setting. Audit each replica separately — a policy change on the primary does NOT propagate to replicas. |
| `KeyState` | `PendingDeletion` | **Key scheduled for deletion.** Jump to Step 1 (deletion window evaluation) — this is the highest-priority finding regardless of policy state. |
| `KeyState` | `Disabled` | Key is administratively disabled — `kms:Encrypt`/`Decrypt` fail. Note as operational risk but not a security verdict driver unless combined with other findings. |

**If the key policy JSON is malformed** (invalid JSON, missing `Statement`,
missing `Principal` or `Action`/`NotAction`), output:

```text
KEY: <key-id>
VERDICT: ERROR
REASON: Key policy document is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical policy with `aws kms get-key-policy --key-id <id> --policy-name default --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious KMS behaviors that change classification

Step-0 expert behaviors moved verbatim to `references/advanced-patterns.md`
(aliases, Resource semantics, Sign, ReEncrypt, grants, ViaService, more).

### Step 1: Key deletion window (highest priority — irrecoverable data loss)

If `KeyState` is `PendingDeletion`, extract `PendingWindowInDays`:

- **PendingWindowInDays <= 7** → **CRITICAL**. The key becomes permanently
  unrecoverable in 7 days or fewer. Any data encrypted under this key that
  has no re-encryption path is on a countdown to permanent loss. More
  importantly, `kms:Encrypt` and `kms:Decrypt` **fail immediately** when a
  key enters `PendingDeletion` — the blast radius starts NOW, not at
  expiry. Any live workload depending on this key is already experiencing
  an outage.

- **PendingWindowInDays 8-30** → **HIGH**. The key is recoverable
  (`kms:CancelKeyDeletion`) during the window, but the clock is ticking.
  Identify all data dependencies and either cancel deletion or initiate
  re-encryption to a replacement key.

The deletion window is evaluated first because it is the only finding that
produces **time-irreversible data loss**. A cross-account decrypt grant can
be revoked; a deleted key cannot be restored.

### Step 2: Principal scope classification

For each `Effect: Allow` statement in the key policy, classify the principal:

- **WILDCARD_PRINCIPAL** — Principal is `"*"`, `{"AWS": "*"}`, or any
  construct that resolves to all principals (including `"*"` nested under
  `Service` or `Federated`). Note: `Principal: {"AWS": "*"}` is
  functionally equivalent to `Principal: "*"` — both mean every AWS
  account holder.

- **CROSS_ACCOUNT** — Principal includes an ARN whose 12-digit account ID
  differs from the key's owning account (the account in the key ARN).
  Example: key ARN `arn:aws:kms:us-east-1:111111111111:key/abc` with
  principal `arn:aws:iam::222222222222:role/external-app` is cross-account.

- **SAME_ACCOUNT** — All principals share the key's owning account ID.
  This includes the account root (`arn:aws:iam::111111111111:root`),
  same-account roles, users, and services.

A statement with BOTH same-account and cross-account principals is
classified by the **widest** scope — CROSS_ACCOUNT.

### Step 3: Action danger classification

Classify the action set in each Allow statement by danger level. A single
statement may span multiple levels — classify by the **highest** danger
action present:

| Danger level | Actions | Why |
|---|---|---|
| **DATA_ACCESS** | `kms:Decrypt`, `kms:DecryptDataKey`, `kms:GenerateDataKey*`, `kms:*`, `*` | Can read **all** ciphertext encrypted under this key. `kms:Decrypt` is a blast-radius multiplier — one permission, full data exposure. `kms:GenerateDataKey*` returns plaintext key material to the caller. |
| **KEY_CONTROL** | `kms:PutKeyPolicy`, `kms:ScheduleKeyDeletion`, `kms:Delete*`, `kms:DisableKey`, `kms:Update*` | Can modify the key policy (lockout attack), schedule deletion (data-loss vector), or disable the key (availability attack). |
| **DELEGATION** | `kms:CreateGrant`, `kms:RetireGrant` (less dangerous) | `kms:CreateGrant` delegates subset permissions to other principals — a privilege-widening vector similar to `iam:PassRole`. Grants can chain if the grant itself includes `kms:CreateGrant`. |
| **DATA_WRITE** | `kms:Encrypt`, `kms:ReEncrypt*`, `kms:GenerateMac` | Can encrypt/inject data under the key. Less dangerous than Decrypt (no data exfiltration) but enables ciphertext injection and re-encryption abuse. |
| **METADATA** | `kms:Describe*`, `kms:List*`, `kms:Get*`, `kms:Sign`, `kms:Verify` | Information disclosure (key spec, policy, grants). `Sign`/`Verify` apply to asymmetric signing keys. Low severity but still sensitive in aggregate. |

`NotAction` in an Allow statement is an inverse wildcard — it grants every
KMS action EXCEPT the listed ones. Treat as DATA_ACCESS + KEY_CONTROL +
DELEGATION (worst case) because new KMS APIs are automatically included.

### Step 4: Condition strength evaluation

If an Allow statement includes a `Condition` block, evaluate whether the
condition genuinely restricts access or is bypassable:

**STRONG conditions (downgrade severity by one level):**
- `kms:ViaService` (e.g., `s3.us-east-1.amazonaws.com`) — the request must
  come through the named AWS service's infrastructure. The caller cannot
  forge this; it is set by the AWS service layer. This is the strongest
  KMS-specific condition because it couples key use to a known service
  integration.
- `aws:SourceAccount` with `StringEquals` — request must originate from
  the named account. Set by the AWS service when a resource in that account
  accesses the key.
- `aws:SourceArn` with `StringEquals`/`StringLike` — request must
  originate from the named resource ARN. Even tighter than SourceAccount.
- `kms:CallerAccount` — KMS-specific: restricts to the named account.
  Equivalent to `aws:SourceAccount` but set by KMS itself.
- `kms:EncryptionContext:*` with `StringEquals` — for Decrypt, requires
  the ciphertext to have been encrypted with a matching encryption context
  pair. STRONG when the context is service-controlled (e.g., S3 sets the
  bucket ARN as context); WEAK when the caller controls the context value
  (see below).

**WEAK conditions (do NOT downgrade — treat as no condition):**
- `aws:SourceIp` / `aws:SourceIp` containing `0.0.0.0/0` — IP-based
  restrictions are bypassable by callers who control their egress. A
  `0.0.0.0/0` CIDR is the entire internet. Do NOT treat as a restriction.
- `kms:EncryptionContext:*` when the caller controls the encryption
  context — if the encrypting service lets the caller set arbitrary
  context values, the caller can encrypt with a chosen context and then
  decrypt with the same context. Only treat as STRONG when the context is
  set by a service the caller does not control (e.g., S3, EBS).
- `aws:Referer`, `aws:UserAgent` — trivially forgeable by any HTTP client.
  Never treat as a restriction.
- Any condition wrapped in `IfExists` — weakens the assertion; evaluate
  the underlying key but flag the `IfExists` semantics.

### Step 5: Cross-reference — the severity matrix

Combine the principal scope (Step 2), action danger (Step 3), and condition
strength (Step 4) to determine the statement's severity. Apply this matrix
in order — the first matching row is the statement severity:

| # | Principal | Action danger | Condition | Severity | Rule citation |
|---|---|---|---|---|---|
| 5a | WILDCARD_PRINCIPAL | DATA_ACCESS | None/weak | **CRITICAL** | Rule 5a: wildcard decrypt — any AWS account holder can read all encrypted data |
| 5b | WILDCARD_PRINCIPAL | KEY_CONTROL | None/weak | **CRITICAL** | Rule 5b: wildcard key control — any account can replace the policy or schedule deletion |
| 5c | CROSS_ACCOUNT | DATA_ACCESS | None/weak | **CRITICAL** | Rule 5c: cross-account decrypt — external account can read all encrypted data |
| 5d | CROSS_ACCOUNT | KEY_CONTROL | None/weak | **CRITICAL** | Rule 5d: cross-account key control — external account can lock out the owner |
| 5e | WILDCARD_PRINCIPAL | DELEGATION | None/weak | **CRITICAL** | Rule 5e: wildcard CreateGrant — any account can delegate access to anyone |
| 5f | WILDCARD_PRINCIPAL | DATA_WRITE | None/weak | **HIGH** | Rule 5f: wildcard encrypt — any account can inject ciphertext under this key |
| 5g | CROSS_ACCOUNT | DELEGATION | None/weak | **HIGH** | Rule 5g: cross-account CreateGrant — external principal can widen access via grants |
| 5h | CROSS_ACCOUNT | DATA_WRITE | None/weak | **HIGH** | Rule 5h: cross-account encrypt — external principal can inject ciphertext |
| 5i | WILDCARD_PRINCIPAL | METADATA | None/weak | **MEDIUM** | Rule 5i: wildcard metadata — any account can enumerate key config |
| 5j | CROSS_ACCOUNT | METADATA | None/weak | **MEDIUM** | Rule 5j: cross-account metadata — external principal can enumerate key config |
| 5k | WILDCARD or CROSS | Any above | STRONG | **Downgrade one level** | Rule 5k: strong condition narrows exposure — fragile but currently restricted |
| 5l | SAME_ACCOUNT | Any | Any | **MEDIUM at worst** | Rule 5l: same-account — IAM policies still apply; not a cross-account exposure |

**Special case — the account-root statement:** The default KMS key policy
includes a statement allowing `Principal: {AWS: "arn:aws:iam::ACCOUNT:root"}`
with `Action: "kms:*"`. This is the **root-of-trust statement** — it delegates
key management to the account's IAM policies. Without it, the key is only
accessible via the key policy (not IAM), which can surprise operators. This
statement is **NORMAL and required** — do NOT flag it as WILDCARD or HIGH.
Classify as SAME_ACCOUNT / OK unless the action is `kms:*` on `Principal: "*"`
(which is different from root).

**The `kms:*` to root vs `kms:*` to `"*"` distinction:**
- `Principal: {"AWS": "arn:aws:iam::111111111111:root"}` + `kms:*` →
  **NORMAL** (delegates to IAM within the account). Not flagged.
- `Principal: "*"` + `kms:*` → **CRITICAL** (any AWS account has full key
  control). Flagged per Rule 5a/5b.

### Step 6: Rotation status evaluation

Evaluate `EnableKeyRotation` only for keys where rotation is applicable
(see Pre-flight gate):

- **Customer-managed symmetric key + `EnableKeyRotation: false`** →
  **HIGH** (additive finding). The key material never changes — if the
  key material is ever compromised, all past and future ciphertext is
  exposed indefinitely. Annual rotation limits the blast window.
- **Customer-managed symmetric key + `EnableKeyRotation: true`** →
  OK for this dimension (no finding).
- **Asymmetric / HMAC / EXTERNAL origin** → N/A. Do NOT flag. Emit a note:
  "Rotation N/A for KeySpec=<spec> / Origin=<origin> — automatic rotation
  not supported."
- **AWS-managed key** → Rotation is automatic (annual). OK.

**Multi-Region keys:** check `EnableKeyRotation` on EACH replica
independently. A primary with rotation enabled but a replica with rotation
disabled is HIGH for the replica.

Rotation timing expert note moved verbatim to
`references/advanced-patterns.md` (load on demand).

### Step 7: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all findings from all
steps, where CRITICAL > HIGH > MEDIUM > OK:

```text
verdict = max(all_statement_severities, rotation_severity, deletion_window_severity)
```

If no findings (all dimensions OK), the verdict is **OK**.

## Output format (per key)

```text
KEY: <key-id or alias>
VERDICT: CRITICAL | HIGH | MEDIUM | OK
REASON: <1-2 sentences citing the worst finding and its rule number>
FINDINGS:
  - [CRITICAL] <finding description (Rule Na)>
  - [HIGH] <finding description (Rule Nb)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — cross-account decrypt with rotation disabled

```text
KEY: arn:aws:kms:us-east-1:111111111111:key/abc-123
VERDICT: CRITICAL
REASON: Statement 1 grants kms:Decrypt to a cross-account principal
(222222222222) with no restrictive condition — external account can read all
ciphertext encrypted under this key (Rule 5c). Rotation is also disabled.
FINDINGS:
  - [CRITICAL] Cross-account kms:Decrypt to 222222222222 with no condition (Rule 5c)
  - [HIGH] EnableKeyRotation is false on a customer-managed symmetric key (Step 6)
REMEDIATION:
  1. Remove the cross-account principal from Statement 1, or add a strong
     condition (kms:ViaService, aws:SourceAccount) to scope the grant.
  2. Enable rotation: aws kms enable-key-rotation --key-id abc-123.
```

## Edge-case handling

Edge-case detail moved verbatim to `references/advanced-patterns.md`
(malformed statements, Deny conflicts, NotPrincipal, empty policy, more).

## Anti-Patterns — NEVER

- NEVER classify a `Principal: "*"` grant with `kms:Decrypt` as anything
  other than CRITICAL. `kms:Decrypt` is a blast-radius multiplier — one
  permission grants read access to every ciphertext encrypted under the
  key, across every service that uses it (S3, EBS, RDS, Secrets Manager).
  This is not "broad access" — it is total data exposure.

- NEVER treat `Principal: {"AWS": "arn:aws:iam::ACCOUNT:root"}` + `kms:*`
  as a vulnerability. This is the **default root-of-trust statement** that
  delegates key management to the account's IAM policies. Removing it makes
  the key accessible only via the key policy (IAM is bypassed), which
  breaks IAM-based access patterns. Flagging it as WILDCARD is a
  false positive that causes unnecessary policy churn.

- NEVER flag `EnableKeyRotation: false` on an **asymmetric key**
  (KeySpec `RSA_*`, `ECC_*`, `SM2`) or **HMAC key** (KeySpec `HMAC_*`).
  These key types do not support automatic rotation — the flag is always
  false and flagging it is a false positive. Check `KeySpec` before
  evaluating rotation.

- NEVER flag `EnableKeyRotation: false` on a key with `Origin: EXTERNAL`
  (imported key material). Rotation for imported keys is managed by
  re-importing new key material — the automatic-rotation flag is
  permanently false and irrelevant.

- NEVER skip auditing **multi-region replica keys**. Each replica has an
  independent key policy and independent rotation setting. A primary with
  a clean policy does NOT imply replicas are clean — a common mistake is
  auditing only the primary and missing a cross-account grant on a replica
  in another region.

- NEVER classify a `Principal: "*"` grant with a STRONG condition
  (`kms:ViaService`, `aws:SourceAccount`, `kms:CallerAccount`,
  `aws:SourceArn`) as CRITICAL. The condition narrows access to a known
  service or account. Downgrade one level per Rule 5k. Classifying it as
  CRITICAL conflates "currently restricted" with "unrestricted" and
  produces alert fatigue.

- NEVER treat `aws:SourceIp` with `0.0.0.0/0` as a real condition. This
  CIDR is the entire internet and provides zero restriction. Treat the
  statement as if the condition is absent.

- NEVER treat `kms:EncryptionContext` as unconditionally STRONG when the
  caller controls the encryption context. If the calling service lets the
  principal set arbitrary context values, the principal can encrypt with a
  chosen context and decrypt with the same context — the condition is
  self-satisfiable. Only treat as STRONG when the context is set by
  infrastructure the caller does not control (e.g., S3 bucket ARN, EBS
  volume ID).

- NEVER assume a key in `PendingDeletion` can still decrypt data. KMS
  rejects all `kms:Encrypt` and `kms:Decrypt` calls the moment a key
  enters `PendingDeletion` — the blast radius starts at scheduling, not
  at window expiry. A key in `PendingDeletion` with live data dependencies
  is an **active outage**, not a future risk.

- NEVER recommend deleting a KMS key as remediation without first
  verifying that no resources are encrypted under it. Key deletion is
  irreversible after the window expires. Run
  `aws kms list-resource-tags`, check CloudTrail for recent
  `kms:Encrypt`/`GenerateDataKey` calls, and confirm with application
  owners before scheduling deletion. This is a one-way door.

- NEVER recommend replacing a cross-account key policy grant with an
  AWS-managed key (`aws/s3`, `aws/ebs`) without explaining the trade-off.
  AWS-managed keys are shared across all accounts in the region — they
  cannot be restricted to specific principals. The remediation for
  cross-account exposure is to tighten the customer-managed key policy,
  not to downgrade to a shared AWS-managed key.

- NEVER ignore the `kms:CreateGrant` permission. It is a delegation vector
  — a principal with `kms:CreateGrant` can create grants that delegate
  Decrypt/Encrypt to other principals, widening access beyond what the key
  policy text shows. Treat as DELEGATION danger level and apply the
  severity matrix.

- NEVER classify a same-account-only policy with named actions as worse
  than MEDIUM. Same-account access is governed by IAM policies (identity-
  based + resource-based intersection for cross-principal), which provides
  a second layer of authorisation. The key policy is not the only gate.

- NEVER overlook `NotPrincipal` in an `Allow` statement. `NotPrincipal`
  grants to every principal EXCEPT the listed one — the inverse of the
  intended scope, and almost always a typo or copy-paste error. In a key
  policy, an Allow with `NotPrincipal: {AWS: "arn:aws:iam::111:root"}`
  grants KMS access to every AWS account EXCEPT 111. This is a
  CRITICAL-severity finding on any DATA_ACCESS action (treat as
  WILDCARD_PRINCIPAL), and the remediation is to replace `NotPrincipal`
  with an explicit `Principal` listing the intended grantees. The same
  logic applies to `NotAction` in an Allow (inverse wildcard — grants
  every action except the listed ones); classify as DATA_ACCESS +
  KEY_CONTROL + DELEGATION worst-case.

- NEVER assume the key policy is the complete access picture when
  `kms:CreateGrant` is present. Grants are a **separate authorisation
  layer** evaluated after the key policy and IAM. A principal with
  `kms:CreateGrant` can create a grant that delegates Decrypt to another
  principal — even if that delegatee has no IAM or key-policy grant.
  Grants can chain up to 2 levels deep (a grantee can create a sub-grant
  if CreateGrant is in their grant). Always enumerate live grants with
  `aws kms list-grants --key-id <id>` when CreateGrant appears in the
  policy — the key policy text alone does not show grant-based access.

- NEVER treat `aws:SourceIp` restrictions as equivalent to
  `kms:ViaService` or `aws:SourceAccount`. SourceIp is caller-controlled
  in practice: any principal with a VPC NAT gateway, a proxy, or a VPN
  can route through an allowed CIDR. ViaService and SourceAccount are set
  by the AWS service infrastructure — the caller cannot forge them.
  SourceIp downgrades cross-account severity by zero levels (treat as no
  condition); ViaService/SourceAccount downgrade by one level.

- NEVER assume the key policy alone reflects the complete access picture
  when `kms:CreateGrant` is in the policy. Grants are a separate
  authorisation layer — a grantee can access the key even with zero IAM
  or key-policy permissions. The only way to see grant-based access is
  `aws kms list-grants --key-id <id>`. An audit that checks only the key
  policy text misses every live grant. When `kms:CreateGrant` is present,
  always enumerate grants and flag any grantee not also named in the
  policy.

- NEVER attempt to modify the policy of an AWS-managed key
  (`KeyManager: AWS`, aliases like `aws/s3`, `aws/ebs`, `aws/rds`).
  AWS-managed key policies are not customer-editable — `kms:PutKeyPolicy`
  returns `AccessDeniedException`. If the input shows a custom policy on
  a key with `KeyManager: AWS`, the input is either stale (the policy was
  changed by AWS since the snapshot) or the KeyManager field is
  misidentified. Re-fetch with `aws kms describe-key` before acting.

## Pre-flight safety checks (run before any remediation CLI)

Pre-flight safety checks moved verbatim to
`references/diagnostic-commands.md` (load on demand).

## Remediation guidance

**Remediation ordering principle:** always prefer additive changes over
destructive changes. Add a Deny statement (blocks access immediately,
reversible by removing the Deny) BEFORE removing an Allow statement
(which may break a workload you did not anticipate). The safe sequence
for any CRITICAL policy finding is: (1) back up policy, (2) add a Deny
that blocks the exposed principal/action, (3) verify the Deny is effective
via `aws kms describe-key` + IAM policy simulator, (4) only then remove
the offending Allow statement. This ordering prevents a window where
neither the old nor new policy is in effect.

Per-severity remediation runbooks moved verbatim to
`references/error-handling.md` (load on demand).

## Condition strength reference (KMS-specific)

Condition strength table moved verbatim to
`references/advanced-patterns.md` (load on demand).

## Deep reference: KMS authorization internals

Authorization internals moved verbatim to
`references/advanced-patterns.md` (load on demand).

## Recent AWS features (2024-2026)

Recent-feature notes moved verbatim to
`references/advanced-patterns.md` (load on demand).


## References (load on demand)

- [`references/advanced-patterns.md`](references/advanced-patterns.md) — Step-0 expert KMS behaviors, rotation timing, edge-case handling, condition-strength table, authorization internals, recent AWS features.
- [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — account-wide sweep pagination, live-account pre-flight checks, pre-flight safety checks (confirmation gate, backups).
- [`references/error-handling.md`](references/error-handling.md) — remediation guidance by severity (CRITICAL/HIGH/MEDIUM/OK runbooks).

## Domain

AWS CloudOps / KMS Encryption Security & Compliance.

## AWS documentation

- **AWS KMS Developer Guide** — https://docs.aws.amazon.com/kms/latest/developerguide/overview.html
- **KMS API Reference** — https://docs.aws.amazon.com/kms/latest/APIReference/
- **AWS CLI Command Reference (KMS)** — https://docs.aws.amazon.com/cli/latest/reference/kms/
- **KMS Security** — https://docs.aws.amazon.com/kms/latest/developerguide/security.html
- **KMS key policies** — https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html
- **On-demand key rotation** — https://docs.aws.amazon.com/kms/latest/developerguide/rotate-keys.html
