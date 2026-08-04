---
description: Audit an EFS filesystem for encryption-at-rest, public filesystem policy, encryption-in-transit enforcement, lifecycle management, and access point governance.
nl_triggers:
  - "audit this EFS filesystem"
  - "check EFS encryption"
  - "EFS filesystem policy too permissive"
  - "is my EFS filesystem public"
  - "EFS lifecycle policy"
  - "EFS access points"
  - "Principal star EFS"
  - "elasticfilesystem ClientRootAccess"
  - "EFS filesystem unencrypted"
  - "harden EFS filesystem"
  - "EFS TLS enforcement"
  - "elasticfilesystem AccessPointArn"
  - "review EFS configuration"
  - "EFS storage security audit"
routes_to: efs-filesystem-auditor
---

# /aws:audit-efs-filesystem

Activate the `efs-filesystem-auditor` skill and audit one or more EFS
filesystems for security exposure and configuration gaps.

## What it does

Reads an EFS filesystem configuration (metadata + filesystem policy +
access point summary) and applies the ordered classification logic:

1. Encryption-at-rest — Encrypted: false is UNENCRYPTED (immutable, worst
   verdict; requires migration to a new encrypted filesystem).
2. Filesystem policy public principal — Principal: "*" with Client* actions
   and no STRONG condition is PUBLIC_POLICY.
3. Configuration gaps — no lifecycle policy, no TLS enforcement
   (aws:SecureTransport), no access points, or cross-account Client* grants
   without strong conditions.
4. Aggregation — worst finding wins (UNENCRYPTED > PUBLIC_POLICY >
   CONFIG_GAP > OK).

Emits a deterministic VERDICT per filesystem:

```text
FILESYSTEM: <fs-id>
VERDICT: UNENCRYPTED | PUBLIC_POLICY | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step/rule number>
FINDINGS:
  - [PUBLIC_POLICY] <finding description (Rule Na)>
  - [CONFIG_GAP] <finding description (Rule Nb)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an EFS filesystem configuration and ask any of:

- "audit this EFS filesystem"
- "is this EFS filesystem public?"
- "check EFS encryption"
- "is the filesystem policy too permissive?"
- "does this EFS have a lifecycle policy?"
- "are access points configured?"

A bare filesystem ID or ARN + any audit verb ("audit this filesystem",
"check EFS config") also routes here via the orchestrator.

## Inputs

- EFS filesystem metadata: Encrypted, KmsKeyId, PerformanceMode,
  ThroughputMode, LifecyclePolicies, NumberOfMountTargets.
- Filesystem policy JSON (if attached). If no policy is attached, the
  filesystem is IAM-governed (default-secure — not a gap for the
  public-principal dimension).
- Access point summary: count and root directories. Zero access points
  is a governance gap (Rule 3c).
- For live-account audits: the skill references describe-file-systems,
  describe-file-system-policy, describe-access-points, and
  describe-lifecycle-policies.

## Outputs

- One VERDICT block per filesystem (multiple findings aggregate to the
  worst severity).
- Enumerated FINDINGS list with per-finding verdict tag and rule citation.
- Specific remediation: restrict principals, add conditions, add lifecycle
  policies, enforce TLS, create access points, migrate unencrypted data.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for EFS storage security).
- `/aws:audit-kms-key-policy` for auditing the KMS key policy when the
  filesystem uses a customer-managed KMS key for encryption-at-rest.
