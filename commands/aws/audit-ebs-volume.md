---
description: Audit an EBS volume or snapshot for unencrypted state, unattached cost waste, legacy gp2/io1/standard volume types, stale snapshots, and public-snapshot block-data exposure.
nl_triggers:
  - "audit this EBS volume"
  - "audit EBS snapshot"
  - "is my EBS volume encrypted"
  - "unattached EBS volumes"
  - "EBS volume cost waste"
  - "gp2 to gp3 upgrade"
  - "io1 to io2 upgrade"
  - "stale EBS snapshots"
  - "public snapshot exposure"
  - "CreateVolumePermission public"
  - "EBS cost optimization"
  - "EBS encryption check"
  - "hardening EBS storage"
  - "block storage audit"
  - "EBS compliance violation"
routes_to: ebs-volume-auditor
---

# /aws:audit-ebs-volume

Activate the `ebs-volume-auditor` skill and audit one or more EBS volume or
snapshot configurations for security, cost, and modernity exposure.

## What it does

Reads an EBS volume (`describe-volumes`) or snapshot (`describe-snapshots`)
configuration plus optional metadata (CreateVolumePermissions, tier status,
FSR status) and applies the ordered classification logic:

1. Pre-flight resource metadata gate — short-circuit shared-private
   snapshots (cannot remediate), AWS-managed KMS keys (no key-policy
   audit), transient/errored states (VERDICT: ERROR).
2. Volume encryption — `Encrypted: false` is UNENCRYPTED (HIGH), the
   worst-possible volume verdict after PUBLIC_SNAPSHOT.
3. Snapshot encryption — unencrypted snapshot is UNENCRYPTED (HIGH).
4. Volume attachment state — `State: available` for >= 30/90/365 days is
   UNATTACHED (MEDIUM), with escalating remediation guidance.
5. Snapshot staleness — `StartTime` >= 90 days (standard) or 180 days
   (archive) with no AMI/FSR/restore reference is STALE_SNAPSHOT (MEDIUM);
   always enumerate FSR first because it dominates cost.
6. Volume type modernity — gp2 / io1 / standard are LEGACY_TYPE (LOW);
   gp3, io2, st1, sc1 are MODERN.
7. Public snapshot detection — `CreateVolumePermissions: Group: all` is
   PUBLIC_SNAPSHOT (CRITICAL); shared-private is NOT public.
8. Aggregation — worst finding wins (CRITICAL > HIGH > MEDIUM > LOW > OK).

Emits a deterministic VERDICT per resource:

```text
RESOURCE: <volume-id or snapshot-id>
VERDICT: UNENCRYPTED | UNATTACHED | LEGACY_TYPE | STALE_SNAPSHOT | PUBLIC_SNAPSHOT | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [HIGH] <finding description (Step N)>
  - [LOW] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an EBS volume or snapshot configuration and ask any of:

- "audit this EBS volume"
- "is this volume encrypted?"
- "is this snapshot public?"
- "should I upgrade gp2 to gp3?"
- "is this volume costing us money while detached?"
- "is this snapshot stale?"

A bare volume-id or snapshot-id + any audit verb ("audit this volume",
"check snapshot exposure") also routes here via the orchestrator.

## Inputs

- An EBS volume configuration (`describe-volumes` JSON), pasted inline or
  referenced by file path.
- An EBS snapshot configuration (`describe-snapshots` JSON).
- For public-snapshot detection: the snapshot's
  `describe-snapshot-attribute --attribute createVolumePermission` output.
- For staleness: AMI references (`describe-images --filters
  BlockDeviceMapping.SnapshotId=<id>`), FSR status
  (`describe-fast-snapshot-restores`), tier status
  (`describe-snapshot-tier-status`).
- For unattached duration: CloudTrail `DetachVolume` events OR resource
  tags (`lastAttached`, `detachedDate`).
- Account/region encryption-by-default state
  (`get-ebs-encryption-by-default`) — drives the account-level escalation
  on unencrypted findings.

## Outputs

- One VERDICT block per resource (multiple findings aggregate to the
  worst severity).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation CLI per finding: `reset-snapshot-attribute`,
  `copy-snapshot --encrypted`, `delete-volume`, `delete-snapshot`,
  `modify-volume --volume-type gp3`, plus account-level
  `enable-ebs-encryption-by-default`.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for EBS storage security and cost optimisation).
- `/aws:audit-kms-key-policy` for the KMS side of encrypted-volume audits
  — customer-managed keys protecting EBS volumes need both the volume
  (encrypted) AND the key policy (not cross-account-exposed) to be sound.
- `/aws:audit-dlm-lifecycle-policy` for the lifecycle-policy side of
  stale-snapshot prevention — DLM generates the snapshot chain; this
  audit consumes it.
