# Advanced Patterns (load on demand) — EFS Filesystem Auditor

Step 0 expert-knowledge catalogue, edge-case handling, the EFS authorization internals deep reference, and 2024-2026 feature notes, moved verbatim from SKILL.md.

---

## Step 0: Expert knowledge — non-obvious EFS behaviours that change classification (moved from SKILL.md)

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

## Edge-case handling (moved from SKILL.md)

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

## Deep reference: EFS authorization internals (moved from SKILL.md)

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

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **EFS Intelligent Tiering GA (2024):** EFS Intelligent-Tiering automatically moves infrequently accessed files to the Infrequent Access (IA) storage class. Auditors should verify that lifecycle policies are configured — without Intelligent Tiering, all files remain in Standard class at full cost.
- **EFS automatic backups via AWS Backup (2024):** EFS now supports continuous backups via AWS Backup. Auditors should verify that EFS filesystems are enrolled in AWS Backup plans with continuous backup enabled (PITR).
- **EFS access points enhancements (2024):** Access points now support more granular POSIX identity enforcement. Auditors should verify that access points are used for application access (rather than root-level mount targets) and that the access point root directory is scoped appropriately.
- **EFS file system policy improvements:** Enhanced file system policy evaluation. Auditors should verify that file system policies do not grant `Principal: "*"` without restrictive conditions.

