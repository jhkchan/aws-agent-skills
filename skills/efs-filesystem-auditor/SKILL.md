---
name: efs-filesystem-auditor
description: >-
  Audits AWS EFS filesystems for encryption-at-rest, filesystem policy public
  principal exposure, encryption-in-transit enforcement, lifecycle management
  policies, and access point governance. Emits a deterministic verdict
  (UNENCRYPTED | PUBLIC_POLICY | CONFIG_GAP | OK) per filesystem with
  enumerated findings and specific remediation. Use when reviewing EFS
  filesystem configurations, checking for public filesystem policies,
  validating encryption posture, auditing lifecycle policies, or hardening
  EFS access before production deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline configuration classification.
  Live-account audits use aws efs describe-file-systems, aws efs
  describe-file-system-policy, aws efs describe-access-points, and aws efs
  describe-lifecycle-policies (AWS CLI v2, SSO or key-based credentials).
keywords:
  - EFS
  - Elastic File System
  - filesystem policy
  - encryption-at-rest
  - encryption-in-transit
  - aws:SecureTransport
  - elasticfilesystem:ClientMount
  - elasticfilesystem:ClientRootAccess
  - elasticfilesystem:ClientWrite
  - elasticfilesystem:AccessPointArn
  - Principal:"*"
  - lifecycle policy
  - TransitionToIA
  - Infrequent Access
  - access points
  - EFS audit
  - KmsKeyId
  - public filesystem
  - NFS encryption
  - storage security
tags: [efs, storage, security, filesystem-policy, encryption, lifecycle, access-points, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Storage
  verdict_shape: "UNENCRYPTED | PUBLIC_POLICY | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing an EFS filesystem configuration before production deployment,
    checking for public filesystem policy exposure, validating encryption-at-rest
    and encryption-in-transit enforcement, auditing lifecycle management
    policies, or hardening EFS access governance across an account.
  activation_triggers:
    - "audit this EFS filesystem"
    - "is my EFS filesystem public"
    - "check EFS encryption"
    - "EFS filesystem policy too permissive"
    - "review EFS lifecycle policy"
    - "EFS access points configured"
    - "harden EFS filesystem"
    - "Principal star EFS"
  invocation_schema: >-
    Input: either (a) an EFS filesystem configuration (metadata + optional
    filesystem policy JSON + optional access point summary), OR (b) a
    filesystem-id/ARN for live-account audit. Output: deterministic
    FILESYSTEM/VERDICT/REASON/FINDINGS/REMEDIATION block per filesystem,
    where VERDICT ∈ {UNENCRYPTED, PUBLIC_POLICY, CONFIG_GAP, OK, ERROR}.
---

# EFS Filesystem Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
all dimensions, applied in strict priority order — UNENCRYPTED beats
PUBLIC_POLICY beats CONFIG_GAP beats OK — and EFS encryption-at-rest is an
**immutable, creation-time-only** property that cannot be retroactively
enabled.

EFS is a shared NFS filesystem. The filesystem policy is the IAM-level
authorisation gate for mount operations, but three EFS-specific behaviours
make it unlike S3 or KMS policies:
- **Encryption-at-rest is permanent.** An unencrypted filesystem cannot be
  encrypted in place — data must be migrated to a new encrypted filesystem.
- **No filesystem policy is the secure default.** Without a policy, only
  IAM principals in the owning account can mount. A missing policy is NOT a
  gap — it means IAM governs access.
- **`elasticfilesystem:AccessPointArn` is the strongest condition.** It
  forces all clients through a named access point with a fixed POSIX identity
  and root directory. A policy with `Principal: "*"` scoped by this condition
  is NOT public.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| `Encrypted: false` (or absent) | **UNENCRYPTED** | Step 1 |
| Filesystem policy with `Principal: "*"` + Client* actions + no STRONG condition | **PUBLIC_POLICY** | Rule 2a |
| Filesystem policy with `NotPrincipal` in Allow | **PUBLIC_POLICY** | Rule 2b |
| `Principal: "*"` + STRONG condition (AccessPointArn, SourceAccount, SourceArn) | NOT public — proceed | Rule 2c |
| No lifecycle policy (empty/absent LifecyclePolicies) | **CONFIG_GAP** | Rule 3a |
| Filesystem policy with Client* actions but no `aws:SecureTransport: true` | **CONFIG_GAP** | Rule 3b |
| No access points configured | **CONFIG_GAP** | Rule 3c |
| Cross-account principal (specific external account) with Client* actions | **CONFIG_GAP** | Rule 3d |
| Encrypted + no public + lifecycle + TLS enforced + access points | **OK** | Step 4 |

See the ordered steps below for edge cases. EFS authorization internals
(filesystem policy + IAM + security-group interaction, access point
architecture, lifecycle storage classes) are in the [Deep reference](#deep-reference-efs-authorization-internals)
section at the end.

## Pre-flight: filesystem metadata gate (run before classification)

Before evaluating the filesystem policy, classify the filesystem itself.

**Live-account pre-flight checks (skip if doing offline config audit):**
1. Confirm the filesystem exists:
   `aws efs describe-file-systems --file-system-id <id> --profile <p>`.
   Fail closed if inaccessible.
2. Retrieve the filesystem policy:
   `aws efs describe-file-system-policy --file-system-id <id>`. Returns
   `Policy` as a JSON string (may be empty if no policy is attached).
3. Retrieve access points:
   `aws efs describe-access-points --file-system-id <id>`. Returns an
   `AccessPoints` array (may be empty).
4. Retrieve lifecycle policies:
   `aws efs describe-lifecycle-policies --file-system-id <id>` (or read from
   `LifecyclePolicies` in describe-file-systems output).
5. Verify CloudTrail is logging EFS API events for forensic audit trails.

| Attribute | Value | Effect on audit |
|---|---|---|
| `Encrypted` | `false` | **Unencrypted at rest.** Jump to Step 1 — UNENCRYPTED is the verdict regardless of other dimensions. |
| `Encrypted` | `true` | Proceed with full audit. |
| `Encrypted` | absent | Treat as **false** (fail closed — unknown encryption state is unencrypted). |
| Filesystem policy | empty / not attached | **IAM-governed state.** No public-policy finding. Still evaluate lifecycle and TLS (no policy = no TLS enforcement → CONFIG_GAP). |
| `KmsKeyId` | AWS-managed (`aws/elasticfilesystem`) | AWS-managed KMS key — rotation is automatic. Do NOT audit the key policy (not customer-editable). |
| `KmsKeyId` | customer-managed ARN | The KMS key policy also gates decryption — cross-reference with the kms-key-policy-auditor skill for defence-in-depth. |
| `PerformanceMode` | `maxIO` | Higher latency, parallel mode. Not a security finding. Note for operational context. |

**If the filesystem policy JSON is malformed** (invalid JSON, missing
`Statement`, missing `Principal` or `Action`), output:

```text
FILESYSTEM: <fs-id>
VERDICT: ERROR
REASON: Filesystem policy document is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical policy with `aws efs describe-file-system-policy --file-system-id <id> --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious EFS behaviours that change classification

These behaviours are easy to misjudge without operational EFS experience.
Each changes a verdict if ignored:

- **Encryption-at-rest is immutable after creation.** Unlike EBS volumes
  (which cannot be retroactively encrypted either, but can be snapshot-
  copied), EFS has no snapshot or copy mechanism that toggles encryption. An
  unencrypted filesystem MUST be migrated to a new encrypted filesystem via
  `aws efs create-file-system --encrypted` + data copy. This is why
  UNENCRYPTED is the worst verdict — the remediation is a migration project,
  not a config change.

- **A missing filesystem policy is NOT a vulnerability.** By default, when
  no resource policy is attached, EFS access is governed entirely by IAM
  identity-based policies. Only the owning account's IAM principals can mount.
  Do NOT flag a missing policy as "no access control" — IAM is the gate.

- **`elasticfilesystem:AccessPointArn` is the strongest EFS condition.** An
  access point enforces a fixed `PosixUser` (Uid/Gid) and `RootDirectory` on
  every client that mounts through it. A filesystem policy with
  `Principal: "*"` scoped by `AccessPointArn` is NOT public — only clients
  connecting through the named access point can access the filesystem, and
  they inherit the access point's POSIX identity. This is tighter than
  `aws:SourceAccount` or `aws:SourceArn`.

- **`aws:SecureTransport` is the only policy-level TLS enforcement.** EFS
  in-transit encryption is opt-in via the mount helper (`mount -t efs -o tls`).
  Without a `Bool: { aws:SecureTransport: "true" }` condition in the
  filesystem policy, clients can mount without TLS. Security groups control
  network access (port 2049) but do NOT enforce encryption. A filesystem
  policy without this condition on Client* actions has an encryption-in-transit
  gap.

- **`ClientRootAccess` is more dangerous than `ClientMount`/`ClientWrite`.**
  Root access bypasses file-level POSIX permissions (no root squashing). A
  policy granting `ClientRootAccess` to `Principal: "*"` is more severe than
  one granting `ClientMount` only — root can read/modify every file regardless
  of file ownership. Always note `ClientRootAccess` in the FINDINGS when
  present.

- **`Resource` in a filesystem policy is effectively always `"*"`.** The
  policy is attached to the filesystem — there is no other resource. A
  statement with `Resource: "<own-arn>"` and one with `Resource: "*"` are
  functionally identical. Do not treat a scoped `Resource` as a restriction;
  evaluate `Principal` + `Action` + `Condition`.

- **Cross-account EFS access is gated by networking.** EFS mount targets
  exist in VPC subnets. Even if a filesystem policy grants `Principal: "*"`
  with no condition, only clients that can reach a mount target (via VPC
  peering, Transit Gateway, VPN, or Direct Connect) can actually mount. This
  means PUBLIC_POLICY is gated by network topology — but the policy is still
  a finding because network topology changes, and a security-group
  misconfiguration can expose the mount target to 0.0.0.0/0 on port 2049.

- **EFS filesystem policy size limit is 20 KiB** (~20,000 characters). When
  proposing additive Deny statements as remediation, estimate cumulative
  size. Prefer fewer, broader Denies if the policy is already near the cap.

- **Lifecycle policies are cost/operational, not security — but a missing
  one is a CONFIG_GAP.** Without a lifecycle policy, all files remain in
  Standard (premium) storage indefinitely. For compliance and FinOps
  governance, this is unbounded cost growth. The valid `TransitionToIA`
  values are: `AFTER_7_DAYS`, `AFTER_14_DAYS`, `AFTER_30_DAYS`,
  `AFTER_60_DAYS`, `AFTER_90_DAYS`.

- **Access points enforce application-level isolation.** Each access point
  binds a `PosixUser` identity and a `RootDirectory`. Without access points,
  any IAM principal with mount access sees the entire filesystem namespace.
  For shared or multi-tenant filesystems, access points are a governance
  requirement. A filesystem with zero access points has a governance gap.

- **`elasticfilesystem:ClientRootAccess` + `Principal: "*"` + no condition
  + open security group = total data compromise.** The combination of a
  public filesystem policy granting root access and a permissive security
  group on the mount target means any network-reachable client can mount,
  read, modify, and delete every file with root privileges. This is the EFS
  equivalent of an open S3 bucket with write access.

### Step 1: Encryption-at-rest (UNENCRYPTED — worst verdict)

If `Encrypted` is `false` or absent → **UNENCRYPTED**. Stop. This is the
worst verdict because:
1. Data at rest is plaintext — no KMS protection.
2. EFS encryption is immutable — cannot be enabled after creation.
3. The only remediation is a full data migration to a new encrypted filesystem.

Even if all other dimensions (policy, lifecycle, access points) are
perfectly configured, the verdict is UNENCRYPTED. Encryption is the
foundational security control — without it, filesystem policy and access
points are irrelevant.

If `Encrypted: true`, proceed to Step 2.

### Step 2: Filesystem policy public principal (PUBLIC_POLICY)

Evaluate the filesystem policy for public principal exposure. This step
only applies if a filesystem policy is attached (non-empty).

For each `Effect: Allow` statement in the filesystem policy, classify the
principal:

- **WILDCARD_PRINCIPAL** — `Principal: "*"`, `Principal: {"AWS": "*"}`, or
  any construct that resolves to all AWS principals.

- **CROSS_ACCOUNT** — Principal includes a specific ARN whose 12-digit
  account ID differs from the filesystem's owning account (extract from
  the filesystem ARN).

- **SAME_ACCOUNT** — All principals share the owning account ID.

Apply the severity rules in order (first match wins):

| # | Principal | Actions | Condition | Verdict | Rule |
|---|---|---|---|---|---|
| 2a | WILDCARD | Client* (any) | None or WEAK | **PUBLIC_POLICY** | Rule 2a: public mount access — any network-reachable client can mount |
| 2b | `NotPrincipal` in Allow | Any | Any | **PUBLIC_POLICY** | Rule 2b: NotPrincipal grants to everyone EXCEPT listed — inverse wildcard |
| 2c | WILDCARD | Client* (any) | STRONG | NOT public — proceed | Rule 2c: strong condition (AccessPointArn, SourceAccount, SourceArn) scopes access |
| 2d | CROSS_ACCOUNT | Client* (any) | None or WEAK | **CONFIG_GAP** (Rule 3d) | Cross-account to specific external account — reviewed as config gap |
| 2e | SAME_ACCOUNT | Client* (any) | Any | NOT public — proceed | Same-account access governed by IAM policies |

**STRONG conditions (downgrade WILDCARD from PUBLIC_POLICY):**
- `elasticfilesystem:AccessPointArn` with `StringEquals` — forces access
  through a named access point with fixed POSIX identity. The strongest
  EFS-specific condition.
- `aws:SourceAccount` with `StringEquals` — request must originate from the
  named account.
- `aws:SourceArn` with `StringEquals`/`StringLike` — request must originate
  from the named resource ARN.

**WEAK conditions (do NOT downgrade — treat as no condition):**
- `aws:SourceIp` / `aws:SourceIp` containing `0.0.0.0/0` — IP-based, bypassable
  by callers who control their egress.
- `aws:Referer`, `aws:UserAgent` — trivially forgeable by any NFS/HTTP client.
- Any condition wrapped in `IfExists` — weakens the assertion.

**No filesystem policy attached:** skip this step entirely. The filesystem
is IAM-governed — not public. Proceed to Step 3.

### Step 3: Configuration gaps (CONFIG_GAP)

After confirming encryption-at-rest is enabled (Step 1) and no public
policy (Step 2), evaluate configuration gaps. ANY one gap triggers
CONFIG_GAP:

**Rule 3a — No lifecycle policy.** If `LifecyclePolicies` is empty or
absent, the filesystem has no storage-class transition. All files remain in
Standard storage indefinitely — unbounded cost growth and no automatic
tiering to Infrequent Access.

**Rule 3b — No TLS enforcement.** If a filesystem policy exists and grants
`elasticfilesystem:Client*` actions (ClientMount, ClientWrite,
ClientRootAccess) but does NOT include a condition requiring
`aws:SecureTransport: "true"`, clients can mount without TLS. This is an
encryption-in-transit gap. Note: if NO filesystem policy is attached, TLS
is also not policy-enforced — this also triggers Rule 3b.

**Rule 3c — No access points.** If zero access points are configured on the
filesystem, any IAM principal with mount access sees the full filesystem
namespace. For shared or multi-tenant filesystems, this is a governance
gap. Access points enforce per-application POSIX identity and root-directory
containment.

**Rule 3d — Cross-account principal with Client* actions.** If the
filesystem policy grants `elasticfilesystem:Client*` actions to a specific
cross-account principal (not `"*"`, but a named external account) with no
STRONG condition, this is a CONFIG_GAP. Cross-account mount access should be
reviewed and scoped with conditions.

If ANY of Rules 3a-3d apply → **CONFIG_GAP**. Enumerate all triggered gaps
in the FINDINGS list.

If NONE apply → proceed to Step 4.

### Step 4: OK — all dimensions pass

The filesystem is **OK** if ALL of:
1. `Encrypted: true` (Step 1 passed).
2. No public principal in filesystem policy, or no filesystem policy (Step 2
   passed).
3. Lifecycle policy present (Rule 3a not triggered).
4. TLS enforced via `aws:SecureTransport: true` condition on Client*
   actions in the filesystem policy (Rule 3b not triggered).
5. At least one access point configured (Rule 3c not triggered).
6. No cross-account Client* grants without strong conditions (Rule 3d not
   triggered).

### Step 5: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all findings, where
UNENCRYPTED > PUBLIC_POLICY > CONFIG_GAP > OK:

```text
verdict = max(encryption_finding, policy_finding, config_gap_findings)
```

## Output format (per filesystem)

```text
FILESYSTEM: <fs-id or name>
VERDICT: UNENCRYPTED | PUBLIC_POLICY | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step/rule number>
FINDINGS:
  - [UNENCRYPTED] <finding description (Step 1)>
  - [CONFIG_GAP] <finding description (Rule 3a)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — encrypted with public policy and no lifecycle

```text
FILESYSTEM: fs-abc1234567 (shared-data-fs)
VERDICT: PUBLIC_POLICY
REASON: Filesystem policy Statement "OpenMount" grants Principal "*" with
ClientMount + ClientWrite + ClientRootAccess and no restrictive condition —
any network-reachable client can mount with root privileges (Rule 2a).
Lifecycle policy is also missing.
FINDINGS:
  - [PUBLIC_POLICY] Principal "*" with ClientRootAccess and no condition
    (Rule 2a) — root-level mount access to any reachable client
  - [CONFIG_GAP] No lifecycle policy configured (Rule 3a) — all files in
    Standard storage indefinitely
  - [CONFIG_GAP] No TLS enforcement: policy grants Client* without
    aws:SecureTransport condition (Rule 3b)
  - [OK] Encrypted at rest with KMS key arn:aws:kms:us-east-1:111111111111:key/abc
REMEDIATION:
  1. PUBLIC_POLICY — Replace Principal "*" with specific IAM role ARNs, or
     add elasticfilesystem:AccessPointArn condition to force access-point
     routing. Back up policy first.
  2. CONFIG_GAP — Add lifecycle policy:
     aws efs put-lifecycle-configuration --file-system-id fs-abc1234567
     --lifecycle-policies TransitionToIA=AFTER_30_DAYS
  3. CONFIG_GAP — Add aws:SecureTransport condition to the filesystem policy.
```

## Edge-case handling

- **No filesystem policy attached.** This is the default IAM-governed state.
  Do NOT flag as a gap for the public-principal dimension. However, without
  a policy there is no TLS enforcement → CONFIG_GAP (Rule 3b).

- **`Principal: "*"` with `elasticfilesystem:AccessPointArn` condition.**
  NOT public. The access point enforces POSIX identity and root directory.
  Proceed to config-gap checks. If TLS, lifecycle, and access points are
  present → OK.

- **Conflicting Allow and Deny.** If a Deny statement blocks
  `aws:SecureTransport: false` with `Principal: "*"`, it enforces TLS for
  all clients. This satisfies Rule 3b even without an explicit
  `aws:SecureTransport: true` in the Allow statement — the Deny-on-non-TLS
  achieves the same enforcement.

- **Filesystem with zero mount targets.** The filesystem is unreachable
  (no mount targets in any subnet). Note as an operational observation but
  do NOT change the verdict — the filesystem may have mount targets added
  later. The policy audit is about the configuration, not current reachability.

- **Empty policy (no statements).** A filesystem policy with an empty
  `Statement` array means no principal has policy-level access. If the
  filesystem has no other access path (no IAM permissions granting mount),
  it may be orphaned. Output `VERDICT: ERROR, REASON: Filesystem policy has
  no statements — filesystem may be inaccessible. Verify IAM mount
  permissions.`

- **Partially malformed policy.** If the policy JSON parses but individual
  statements are missing required fields, classify each valid statement
  normally and emit an ERROR note for each malformed statement.

## Anti-Patterns — NEVER

- NEVER flag a missing filesystem policy as a vulnerability. By default, EFS
  access is IAM-governed — only the owning account's IAM principals can
  mount. A missing policy is a valid posture, not "no access control."

- NEVER classify `Principal: "*"` with `elasticfilesystem:AccessPointArn`
  condition as PUBLIC_POLICY. The access point enforces a fixed POSIX
  identity and root directory — clients cannot bypass it. This is the
  strongest EFS-specific access-scoping mechanism.

- NEVER recommend enabling encryption on an existing unencrypted filesystem.
  EFS encryption-at-rest is immutable — set only at creation via
  `aws efs create-file-system --encrypted`. The only remediation for
  UNENCRYPTED is to create a new encrypted filesystem and migrate data.
  Suggesting a config change produces a false expectation.

- NEVER treat `aws:SourceIp` with `0.0.0.0/0` as a real condition. This CIDR
  is the entire internet and provides zero restriction. Treat the statement
  as if the condition is absent.

- NEVER treat `Resource: "*"` in a filesystem policy as broader than
  `Resource: "<own-arn>"`. The policy is attached to the filesystem — there
  is no other resource. Evaluate Principal + Action + Condition only.

- NEVER conflate `ClientRootAccess` with `ClientMount`. Root access bypasses
  file-level POSIX permissions (no root squashing). A public policy granting
  `ClientRootAccess` is total filesystem compromise, not just read access.

- NEVER classify an encrypted filesystem with config gaps (missing lifecycle,
  no TLS, no access points) as OK. CONFIG_GAP means the filesystem is not
  fully hardened — the verdict is CONFIG_GAP, not OK.

- NEVER assume a public filesystem policy has no real-world impact because
  "the mount target is in a private subnet." Security groups are a separate
  layer that can change independently. A filesystem policy with
  `Principal: "*"` and no condition is PUBLIC_POLICY regardless of current
  network topology.

- NEVER overlook `NotPrincipal` in an `Allow` statement. `NotPrincipal`
  grants to every principal EXCEPT the listed one — the inverse of the
  intended scope. Treat any `NotPrincipal` in an Allow as WILDCARD_PRINCIPAL.

- NEVER modify an EFS filesystem policy without first backing it up.
  `PutFileSystemPolicy` replaces the entire policy atomically — there is no
  version history and no automatic rollback. Capture the current policy with
  `aws efs describe-file-system-policy --file-system-id <id> --output json`
  before any modification.

- NEVER treat `aws:SecureTransport` enforcement as optional for production.
  Without TLS, NFS traffic (including file contents) travels in plaintext
  over the network. A security group allowing port 2049 from broad CIDRs
  without TLS enforcement is a data-exposure vector.

- NEVER skip the lifecycle policy dimension. A missing lifecycle policy is
  not a security vulnerability, but it is a CONFIG_GAP — unbounded storage
  cost growth with no automatic tiering. For FinOps governance, this is a
  finding.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`PutFileSystemPolicy`, `PutLifecycleConfiguration`,
  `CreateAccessPoint`, `CreateMountTarget`), the auditor MUST emit:
  `CONFIRM: About to <action> on filesystem <id> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute until the operator confirms.

- **Back up the current filesystem policy** before modification:
  `aws efs describe-file-system-policy --file-system-id <id> --output json > /tmp/<id>-policy-backup-$(date +%s).json`.
  Filesystem policies are unversioned — no undo without a backup.

- Confirm the filesystem exists and is accessible:
  `aws efs describe-file-systems --file-system-id <id> --profile <p>`.

- For UNENCRYPTED remediation (migration): verify the new encrypted
  filesystem is in the same VPC/subnet configuration, create mount targets,
  and test application access BEFORE decommissioning the old filesystem.
  Data migration must be verified with checksums — EFS does not provide a
  native copy API.

- Prefer additive changes (add a Deny statement blocking
  `aws:SecureTransport: false`, add a lifecycle policy, add access points)
  over destructive changes (removing an Allow statement) — additive changes
  are reversible and do not risk breaking existing mount patterns.

- For PUBLIC_POLICY findings (wildcard Client* access), treat as incident
  response: (1) back up policy, (2) add a Deny blocking the wildcard
  principal, (3) verify the Deny is effective, (4) only then remove the
  offending Allow. Audit CloudTrail for `elasticfilesystem:ClientMount`
  events from unexpected principals during the exposure window.

## Remediation guidance

### For UNENCRYPTED — encryption-at-rest disabled

1. **Create a new encrypted filesystem:**
   `aws efs create-file-system --encrypted --kms-key-id <kms-arn> --profile <p>`.
2. Create mount targets in the same subnets as the original.
3. Migrate data using `efsbackup` / AWS Backup restore, or a parallel-copy
   tool (rclone, aws s3 sync via EFS-to-S3 copy). Verify with checksums.
4. Update DNS/mount configurations to point to the new filesystem.
5. Decommission the old filesystem only after verification:
   `aws efs delete-file-system --file-system-id <old-id>`.

### For PUBLIC_POLICY — public principal with Client* access

1. **Immediately** remove `Principal: "*"` from the policy, or add a STRONG
   condition (`elasticfilesystem:AccessPointArn`, `aws:SourceAccount`).
2. **Assume breach.** Audit CloudTrail for `ClientMount` / `ClientWrite` /
   `ClientRootAccess` events from unexpected principals during the exposure
   window. Review security groups on mount targets for broad port-2049 rules.
3. Replace `Principal: "*"` with specific IAM role ARNs.
4. If broad access is intentional (e.g., multi-tenant shared filesystem),
   enforce access-point routing with `elasticfilesystem:AccessPointArn`.

### For CONFIG_GAP — no lifecycle policy (Rule 3a)

```bash
aws efs put-lifecycle-configuration \
  --file-system-id <id> \
  --lifecycle-policies '[{"TransitionToIA":"AFTER_30_DAYS"}]' \
  --profile <p>
```

### For CONFIG_GAP — no TLS enforcement (Rule 3b)

Add `aws:SecureTransport: true` condition to all Client* Allow statements,
OR add an explicit Deny:

```json
{
  "Sid": "DenyInsecureTransport",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "elasticfilesystem:Client*",
  "Resource": "*",
  "Condition": { "Bool": { "aws:SecureTransport": "false" } }
}
```

### For CONFIG_GAP — no access points (Rule 3c)

```bash
aws efs create-access-point \
  --file-system-id <id> \
  --name app-prod \
  --posix-user Uid=1000,Gid=1000 \
  --root-directory Path=/prod/app \
  --profile <p>
```

Then update the filesystem policy to require access-point routing via
`elasticfilesystem:AccessPointArn` condition.

### For CONFIG_GAP — cross-account principal (Rule 3d)

1. Verify the cross-account access is intentional and required.
2. Add `aws:SourceAccount` or `elasticfilesystem:AccessPointArn` condition.
3. If unintentional, remove the cross-account principal from the policy.

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit when mount targets or security groups change.
3. For customer-managed KMS keys, cross-reference with the
   `kms-key-policy-auditor` skill for key-policy defence-in-depth.

## Condition strength reference (EFS-specific)

| Condition key | Strength | Reason |
|---|---|---|
| `elasticfilesystem:AccessPointArn` | STRONG | Forces access through a named access point with fixed POSIX identity and root directory. Caller cannot forge this — set by the EFS service. |
| `aws:SourceAccount` | STRONG | Set by the calling AWS service; identifies the owning account of the calling resource. |
| `aws:SourceArn` | STRONG | Set by the calling AWS service; identifies the specific calling resource. |
| `aws:SecureTransport` | ENFORCEMENT | Not a scoping condition but a TLS enforcement mechanism. Use `Bool: true` in Allow or `Bool: false` in Deny. |
| `aws:SourceIp` (non-public CIDR) | WEAK | Network-scoped but bypassable by callers who control egress. |
| `aws:SourceIp` (`0.0.0.0/0`) | NONE | The entire internet. Do NOT treat as a restriction. |
| `aws:Referer` | NONE | Forgeable by any HTTP/NFS client. |
| `aws:UserAgent` | NONE | Forgeable by any HTTP/NFS client. |

## Deep reference: EFS authorization internals

### Authorization evaluation pipeline

EFS evaluates a mount/access request through multiple layers:

1. **Security group on the mount target** — network-level gate. Controls
   which IPs/CIDRs can reach NFS port 2049. This is independent of the
   filesystem policy.
2. **Filesystem policy** — resource-based IAM policy attached to the
   filesystem. If present, it is evaluated alongside the caller's
   identity-based policy. An explicit Deny in either blocks the request.
3. **IAM identity-based policy** — if NO filesystem policy is attached, IAM
   policies alone govern access. If a filesystem policy IS attached, both
   must allow the action (for same-account: union semantics; the filesystem
   policy can grant access even without an IAM Allow, and vice versa).
4. **Access point enforcement** — if the filesystem policy requires
   `elasticfilesystem:AccessPointArn`, clients MUST connect through the named
   access point. The access point applies its `PosixUser` and `RootDirectory`
   regardless of the client's actual identity.

### Encryption immutability

EFS encryption-at-rest is a **creation-time-only** property:
- `aws efs create-file-system --encrypted` sets it.
- There is no `update-file-system` flag to toggle encryption.
- There is no snapshot-and-copy mechanism (unlike EBS).
- The ONLY path is: create new encrypted filesystem → copy data → update
  mount configs → delete old filesystem.

This is why UNENCRYPTED is the worst verdict — remediation is a migration
project, not a configuration change.

### Lifecycle storage classes

EFS has two storage classes:
- **Standard** — default, premium pricing, low latency.
- **Infrequent Access (IA)** — lower cost, higher per-operation charge, for
  files accessed rarely.

Lifecycle policies automatically transition files between classes:
- `TransitionToIA`: `AFTER_7_DAYS | AFTER_14_DAYS | AFTER_30_DAYS | AFTER_60_DAYS | AFTER_90_DAYS`
- `TransitionToPrimaryStorageClass`: `AFTER_1_DAY` (moves back to Standard
  if accessed in IA)

Without a lifecycle policy, all files remain in Standard indefinitely.

### Access point architecture

An access point:
- Has a unique ID (`fsap-xxxxx`) and ARN.
- Enforces a `PosixUser` (Uid, Gid, secondary Gids) — the client's NFS
  operations execute as this identity, regardless of the client's actual
  system identity.
- Enforces a `RootDirectory` — the client sees this as `/`; they cannot
  navigate above it.
- Can be referenced in the filesystem policy via
  `elasticfilesystem:AccessPointArn` to require access-point routing.

### Filesystem policy vs. IAM interaction

| Filesystem policy present? | Same-account access | Cross-account access |
|---|---|---|
| No (empty) | IAM alone governs — only principals with an IAM `elasticfilesystem:Client*` Allow can mount | Not possible without IAM policy (no resource policy to grant) |
| Yes (attached) | Both filesystem policy and IAM evaluated — either can Allow, explicit Deny in either blocks | Both must Allow (intersection) — filesystem policy must explicitly grant the cross-account principal |

## Recent AWS features (2024-2026)

- **EFS Intelligent Tiering GA (2024):** EFS Intelligent-Tiering automatically moves infrequently accessed files to the Infrequent Access (IA) storage class. Auditors should verify that lifecycle policies are configured — without Intelligent Tiering, all files remain in Standard class at full cost.
- **EFS automatic backups via AWS Backup (2024):** EFS now supports continuous backups via AWS Backup. Auditors should verify that EFS filesystems are enrolled in AWS Backup plans with continuous backup enabled (PITR).
- **EFS access points enhancements (2024):** Access points now support more granular POSIX identity enforcement. Auditors should verify that access points are used for application access (rather than root-level mount targets) and that the access point root directory is scoped appropriately.
- **EFS file system policy improvements:** Enhanced file system policy evaluation. Auditors should verify that file system policies do not grant `Principal: "*"` without restrictive conditions.

## Domain

AWS CloudOps / EFS Storage Security & Compliance.
