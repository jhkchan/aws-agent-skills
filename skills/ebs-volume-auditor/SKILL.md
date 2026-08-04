---
name: ebs-volume-auditor
description: >-
  Audits AWS EBS volumes and EBS snapshots for unencrypted volumes, unattached
  cost-drift volumes, legacy gp2 volume types (gp3 upgrade path), stale
  snapshots accumulating storage cost, and public snapshots exposing block
  data to every AWS account. Emits a deterministic verdict
  (UNENCRYPTED | UNATTACHED | LEGACY_TYPE | STALE_SNAPSHOT | PUBLIC_SNAPSHOT | OK)
  per resource with enumerated findings and specific CLI remediation. Use
  when reviewing EBS volume posture, checking for unencrypted volumes,
  hunting unattached cost-waste volumes, validating gp2->gp3 upgrade
  candidates, pruning stale snapshots, or detecting public-snapshot data
  exposure.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline configuration classification.
  Live-account audits use aws ec2 describe-volumes, aws ec2
  describe-snapshots, aws ec2 describe-snapshot-tier-status, and aws ec2
  describe-fast-snapshot-restores (AWS CLI v2, SSO or key-based credentials).
keywords:
  - EBS
  - Elastic Block Store
  - EBS volume
  - EBS snapshot
  - unencrypted volume
  - encryption-by-default
  - unattached volume
  - gp2
  - gp3
  - io1
  - io2
  - provisioned IOPS
  - stale snapshot
  - public snapshot
  - CreateVolumePermission
  - fast snapshot restore
  - FSR
  - cross-region snapshot copy
  - KMS encryption
  - volume type upgrade
  - storage cost optimization
  - block storage audit
tags: [ebs, storage, security, encryption, cost-optimization, snapshot, volume-type, public-snapshot, audit]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Storage
  verdict_shape: "UNENCRYPTED | UNATTACHED | LEGACY_TYPE | STALE_SNAPSHOT | PUBLIC_SNAPSHOT | OK"
  when_to_use: >-
    Reviewing an EBS volume or snapshot before production deployment, hunting
    unencrypted volumes under compliance mandates (PCI/SOC2/HIPAA), pruning
    unattached cost-waste volumes, validating gp2->gp3 upgrade candidates,
    detecting public-snapshot block-data exposure, or hardening EBS posture
    across an account.
  activation_triggers:
    - "audit this EBS volume"
    - "is my EBS volume encrypted"
    - "unattached EBS volumes"
    - "gp2 to gp3 upgrade"
    - "stale EBS snapshots"
    - "public snapshot exposure"
    - "EBS cost optimization"
    - "CreateVolumePermission public"
    - "hardening EBS storage"
  invocation_schema: >-
    Input: either (a) an EBS volume or snapshot configuration (describe-volumes
    or describe-snapshots JSON, optionally paired with CreateVolumePermissions),
    OR (b) a volume-id / snapshot-id for live-account audit. Output:
    deterministic RESOURCE/VERDICT/REASON/FINDINGS/REMEDIATION block per
    resource, where VERDICT ∈ {UNENCRYPTED, UNATTACHED, LEGACY_TYPE,
    STALE_SNAPSHOT, PUBLIC_SNAPSHOT, OK, ERROR}.
---

# EBS Volume Auditor

## Mindset

**One-line takeaway:** the verdict is the **worst** finding across all
dimensions, applied in strict priority order — PUBLIC_SNAPSHOT beats
UNENCRYPTED beats UNATTACHED beats STALE_SNAPSHOT beats LEGACY_TYPE beats
OK — and three EBS realities drive the ordering:

- **Public snapshots expose block-level data.** A public EBS snapshot can
  be `CreateVolume`-d by **any AWS account in any region** — the requester
  reads every block, including OS files, secrets in user-data residue, and
  the on-disk remnants of deleted files (snapshots are point-in-time block
  copies, not application-level exports).
- **EBS encryption is immutable per resource.** A volume's `Encrypted` flag
  and KMS key are fixed at creation. Retrofitting requires a snapshot-copy
  + new-volume flow; an unencrypted snapshot can be re-issued from the
  volume at any time, so the unencrypted volume is the leak source.
- **Unattached volumes still bill.** An `available` volume accrues the full
  GB-month charge the moment it is detached — there is no "parked" rate.
  The single largest source of EBS overspend is detached volumes kept
  "just in case" across regions and accounts.

## Quick reference — verdict thresholds

| Condition | Verdict | Severity |
|---|---|---|
| Snapshot `CreateVolumePermissions` includes `Group: all` | **PUBLIC_SNAPSHOT** | CRITICAL |
| Volume `Encrypted: false` (or absent) | **UNENCRYPTED** | HIGH |
| Snapshot `Encrypted: false` | **UNENCRYPTED** | HIGH |
| Volume `State: available` for >= 30 days with no Attachments | **UNATTACHED** | MEDIUM |
| Volume `State: available` for >= 90 days (escalation) | **UNATTACHED** | MEDIUM |
| Snapshot `StartTime` >= 90 days old, no AMI / FSR / restore reference | **STALE_SNAPSHOT** | MEDIUM |
| Snapshot in Archive tier, >= 180 days old, no consumer | **STALE_SNAPSHOT** | MEDIUM |
| Volume `VolumeType: gp2` (upgrade path: gp3) | **LEGACY_TYPE** | LOW |
| Volume `VolumeType: io1` (upgrade path: io2) or `standard` (magnetic) | **LEGACY_TYPE** | LOW |
| Encrypted gp3 attached volume, no public/stale snapshots | **OK** | OK |

**Severity tags — MANDATORY in output.** Every FINDINGS line MUST begin
with a severity tag in square brackets: `[CRITICAL]` | `[HIGH]` |
`[MEDIUM]` | `[LOW]` | `[OK]`. The severity tag maps 1:1 to the verdict's
severity row above (PUBLIC_SNAPSHOT→CRITICAL, UNENCRYPTED→HIGH,
UNATTACHED/STALE_SNAPSHOT→MEDIUM, LEGACY_TYPE→LOW, OK→OK). A FINDINGS
list without bracketed severity tags is malformed output.

**Cheat sheet — CLI commands by verdict (MUST appear verbatim in
REMEDIATION):**

| Verdict | Primary CLI (lowercase, exact) |
|---|---|
| PUBLIC_SNAPSHOT | `aws ec2 reset-snapshot-attribute` |
| UNENCRYPTED | `aws ec2 copy-snapshot --encrypted` + `aws ec2 create-volume --encrypted` |
| UNATTACHED | `aws ec2 create-snapshot` then `aws ec2 delete-volume` |
| STALE_SNAPSHOT | `aws ec2 delete-snapshot` (drain FSR via `disable-fast-snapshot-restores` first) |
| LEGACY_TYPE | `aws ec2 modify-volume --volume-type gp3` (or `--volume-type io2`) |
| OK | None required |

**Top rules at a glance (NEVER-list essentials, expanded in Anti-Patterns):**

1. Unencrypted → always UNENCRYPTED (HIGH). Network position is not a mitigation.
2. EBS encryption is immutable — never say "enable encryption on a volume."
3. `Group: all` → always PUBLIC_SNAPSHOT (CRITICAL). Shared-private ≠ public.
4. `gp2`/`io1`/`standard` → always LEGACY_TYPE. `gp3`/`io2`/`st1`/`sc1` are MODERN.
5. Never auto-delete. Always emit `CONFIRM:` gate before destructive CLI.
6. FSR ($0.06/hr per AZ) dominates stale-snapshot cost — always enumerate it.
7. Never `delete-snapshot` without checking AMI references (`describe-images`).
8. Cross-region snapshot copy does not preserve public/private state — sweep every region.

**Concrete cost baseline (us-east-1, 2026):** gp2 $0.10/GB-mo, gp3
$0.08/GB-mo (20% cheaper), io1/io2 $0.125/GB-mo + $0.065/provisioned-IOPS-mo,
standard $0.05/GB-mo + $0.05/million-I/O, snapshot standard $0.05/GB-mo,
snapshot archive $0.012/GB-mo, FSR $0.06/hr per AZ ($43.20/AZ-mo). A 1 TB
gp2→gp3 upgrade saves ~$20/mo; a 100 GB stale snapshot with FSR in 3 AZs
costs $129.60/mo FSR + $5/mo storage = $134.60/mo of waste.

EBS internals (FSR cost, cross-region copy, tiering) are in the
[Deep reference](#deep-reference-ebs-internals) section.

## Pre-flight: resource metadata gate (run before classification)

Identify the resource type and short-circuit unsupported cases.
Misclassifying these produces false positives.

**Multi-resource sweep note (pagination):** `describe-volumes` and
`describe-snapshots` paginate at 500 per page — drain `--next-token` to
completion. For snapshots ALWAYS pass `--owner-ids self` (or the explicit
account id); without `--owner-ids`, the call returns every public
snapshot in the world and is rate-limited.

**Live-account pre-flight checks (skip if offline audit):**
1. Verify encryption-by-default at account+region level:
   `aws ec2 get-ebs-encryption-by-default --profile <p> --region <r>`.
   If `false`, an unencrypted volume is expected state — surface the
   account-level gap alongside the resource verdict.
2. Verify the caller can run `ec2:ModifyVolume` /
   `ec2:ModifySnapshotAttribute` if remediation is intended — read-only
   auditor roles CANNOT and the remediation CLI will fail with
   `UnauthorizedOperation`.
3. Snapshot ownership: only snapshots where `OwnerId` matches the caller
   are mutable. Shared snapshots can be `CopySnapshot`'d but never
   `ModifySnapshotAttribute`'d.

| Attribute | Value | Effect on audit |
|---|---|---|
| Resource type | `volume` | Run Steps 1, 3, 5, 7 (skip snapshot steps). |
| Resource type | `snapshot` | Run Steps 2, 4, 6, 7 (skip volume steps). |
| Volume `Encrypted` | `false` | Jump to Step 1 — UNENCRYPTED regardless of other dimensions. |
| Volume `KmsKeyId` | `aws/ebs` alias / AWS-managed ARN | AWS-managed key — rotation automatic. Do NOT audit the key policy. |
| Volume `KmsKeyId` | customer-managed ARN | Cross-reference kms-key-policy-auditor on the key; the volume itself is encrypted. |
| Volume `MultiAttachEnabled` | `true` | io1/io2 only. Verify ALL `Attachments` are healthy — single-attach multi-attach is wasted IOPS budget. |
| Snapshot `OwnerId` | caller account | Owned — full audit + remediation scope. |
| Snapshot `OwnerId` | other account | Shared with caller. Cannot remediate. Skip PUBLIC check (shared-private ≠ public). |
| Volume `State` | `error` / `creating` / `deleting` | Transient or failed state. Output VERDICT: ERROR, do not force-fit the verdict enum. |

**If the input JSON is malformed** (invalid JSON, missing required fields),
output:

```text
RESOURCE: <volume-id or snapshot-id>
VERDICT: ERROR
REASON: Resource configuration is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Re-fetch with `aws ec2 describe-volumes --volume-ids <id> --output json` (or describe-snapshots) and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious EBS behaviours that change classification

- **`gp3` is the AWS-recommended general-purpose baseline since 2020.** A
  `gp2` volume at the same size pays ~20% more and delivers a less
  flexible performance curve (gp2 IOPS scale with size; gp3 IOPS/throughput
  are independent). `ModifyVolume` upgrade to `gp3` is **online, no detach,
  no data loss**. Never report gp2 as "fine" when gp3 is cheaper and tunable.

- **io1 vs io2: same price, different durability.** `io2` replaced `io1`
  at the same per-GB and per-IOPS price but raises durability from
  99.8%-99.9% (io1) to 99.999% (io2). An io1 volume on a production or
  finance-tagged workload is a silent reliability gap. Always escalate
  io1 findings on critical workloads.

- **Fast Snapshot Restore (FSR) is the silent budget killer.** Enabling
  FSR in N AZs bills `N x $0.06/hour` per snapshot — $43.20/AZ/month. A
  100 GB snapshot is $4.50/month in storage but $129.60/month in FSR for
  3 AZs. ALWAYS enumerate FSR via `describe-fast-snapshot-restores` for
  STALE_SNAPSHOT candidates — disabling FSR is the largest single saving
  in this audit.

- **Cross-region snapshot copy does not preserve public/private state.**
  Each region is an independent snapshot registry. Account-wide public-
  snapshot sweeps MUST iterate `describe-snapshots --owner-ids self` per
  region — "clean" in one region does not imply clean in others.

- **Cross-account snapshot sharing does NOT share the KMS key.** Sharing
  an encrypted snapshot grants the recipient a reference; they cannot
  decrypt without the KMS key policy allowing `kms:CreateGrant` /
  `kms:Decrypt` from their account. Encrypted cross-account sharing
  requires BOTH the snapshot share AND the KMS key policy update.

- **Snapshot tiering (Archive) changes staleness math.** Archive-tier
  snapshots cost ~$0.012/GB-month (vs $0.05 standard) but take 24-72
  hours to restore. An "old" archive snapshot is NOT stale by age —
  check `describe-snapshot-tier-status` and apply the 180-day threshold
  for archive-tier snapshots.

- **Snapshot chains are incremental but billed independently.** Each
  snapshot in a chain stores only its delta, but each snapshot-id is its
  own billing line. Deleting an intermediate snapshot in a chain does NOT
  free its referenced blocks — they migrate to later snapshots. Storage
  is freed only when an snapshot-id's unique blocks are unreferenced.

- **`DeleteOnTermination` is the silent data-loss vector for attached
  volumes.** An EC2-attached data volume with `DeleteOnTermination: true`
  is destroyed when its instance terminates — catastrophic for data
  volumes. Surface as a finding inside an OK or LEGACY_TYPE verdict; do
  NOT change the verdict (it is not in the enum).

- **Public snapshot ≠ public volume.** Volumes cannot be public. Only
  snapshots carry `CreateVolumePermissions`. A volume is "exposed" only
  via its snapshot lineage — flag the snapshot, not the volume.

### Step 1: Volume encryption (UNENCRYPTED — HIGH)

If resource is a volume and `Encrypted` is `false` (or absent):

- **Verdict: UNENCRYPTED (HIGH).** Volume blocks are readable by anyone
  with physical/insider access to the storage infrastructure, and any
  snapshot re-issued inherits the unencrypted state. Under PCI-DSS,
  HIPAA, SOC2, and most enterprise policies, unencrypted EBS is a
  compliance violation regardless of workload sensitivity.

- **Compound check:** `KmsKeyId` set with `Encrypted: false` is
  impossible in valid `describe-volumes` output (KmsKeyId appears only
  when Encrypted is true) — treat as input corruption (VERDICT: ERROR).

- **Account-level escalation:** if `get-ebs-encryption-by-default` is
  `false` for the region, surface: "Region does not enforce encryption-
  by-default; future volumes will also be unencrypted."

### Step 2: Snapshot encryption (UNENCRYPTED — HIGH on snapshots)

If resource is a snapshot and `Encrypted` is `false`:

- **Verdict: UNENCRYPTED (HIGH).** Unencrypted snapshots inherit the
  parent volume's exposure and are restorable by anyone with snapshot
  access. Same compliance violation as an unencrypted volume.

- **Source-region signal:** if encryption-by-default is `true` in the
  snapshot's region but the snapshot is unencrypted, the snapshot
  predates the setting or was copied from a non-encrypting region —
  surface as a "stale-source" finding.

### Step 3: Volume attachment state (UNATTACHED — MEDIUM)

If resource is a volume, `State: available`, and `Attachments` empty or
all entries `detached`:

- **Derive duration of detachment.** `describe-volumes` does not report
  when the last attachment ended. Derive from CloudTrail `DetachVolume`
  events OR from resource tags (`lastAttached`, `detachedDate`). Without
  a duration signal, fall back to `CreateTime`: a volume older than 30
  days that is currently available is treated as UNATTACHED.

- **>= 30 days: MEDIUM.** Volume accrues full GB-month cost with no
  workload benefit. Surface the monthly cost estimate
  (`Size * regional $/GB-month`).
- **>= 90 days: MEDIUM with escalation.** Likely forgotten. Recommend
  snapshot-and-delete (snapshot preserves data at ~5x cheaper).
- **>= 365 days: surface for snapshot+delete.** Year-old detached
  volumes are organisational debt; the data is unlikely to be needed
  but cannot be silently deleted without owner confirmation.

**Never auto-delete.** The audit EMITS verdict + remediation CLI;
deletion requires explicit operator approval (Pre-flight safety).

### Step 4: Snapshot staleness (STALE_SNAPSHOT — MEDIUM)

If resource is a snapshot, derive staleness from `StartTime`:

- **< 90 days: NOT stale.** No finding.
- **>= 90 days: STALE_SNAPSHOT candidate.** Verify the snapshot is NOT:
  (a) referenced by a registered AMI (`describe-images --filters
  BlockDeviceMapping.SnapshotId=<id>`); (b) enabled for Fast Snapshot
  Restore (`describe-fast-snapshot-restores`); (c) tagged with a
  retention override (`retainUntil`, `backup:policy`); (d) in the
  Archive tier (`describe-snapshot-tier-status` — archive snapshots use
  the 180-day threshold instead).
- **>= 90 days AND none of the above: STALE_SNAPSHOT (MEDIUM).**
- **>= 365 days with no consumer: STALE_SNAPSHOT with escalation.**
  Year-old snapshots are prime deletion candidates.

**FSR cost dominance.** If a snapshot has FSR enabled in any AZ, surface
the FSR monthly cost (AZ count × $0.06 × 720 hours) BEFORE the storage
cost — FSR routinely exceeds storage 10-30x and is the larger lever.

### Step 5: Volume type modernity (LEGACY_TYPE — LOW)

If resource is a volume, classify `VolumeType`:

| VolumeType | Classification | Upgrade path | Notes |
|---|---|---|---|
| `gp3` | MODERN | — | Current general-purpose baseline. No finding. |
| `gp2` | LEGACY_TYPE | `ModifyVolume --volume-type gp3` | ~20% cost reduction; IOPS/throughput tunable. |
| `io2` / `io2-block-express` | MODERN | — | Current provisioned-IOPS baseline. No finding. |
| `io1` | LEGACY_TYPE | `ModifyVolume --volume-type io2` | Same price, lower durability. Always upgrade. |
| `st1` (throughput HDD) / `sc1` (cold HDD) | MODERN | — | Correct for sequential or cold workloads. |
| `standard` (magnetic) | LEGACY_TYPE | `ModifyVolume --volume-type gp3` | Legacy; expensive, poor latency. |

LEGACY_TYPE is the **lowest-severity verdict**. A gp2 volume that is
encrypted and attached is still LEGACY_TYPE — gp2 is worse than OK even
though it is not a security issue.

**IOPS overspend note.** For `gp3` and `io1`/`io2`, compare provisioned
`Iops` against typical workload. A `gp3` volume at 16,000 IOPS for an idle
web-server is a 5x overspend. Surface as a finding; the verdict stays
MODERN (gp3) but the finding is actionable.

### Step 6: Public snapshot detection (PUBLIC_SNAPSHOT — CRITICAL)

If resource is a snapshot and owned by the caller (`OwnerId` matches):

- **Retrieve `CreateVolumePermissions`:** `aws ec2
  describe-snapshot-attribute --snapshot-id <id> --attribute
  createVolumePermission`. If `Group: all` is present OR entries include
  accounts the operator cannot identify, classify as
  **PUBLIC_SNAPSHOT (CRITICAL)**.

- **PUBLIC_SNAPSHOT means any AWS account, in any region, can
  `ec2:CreateVolume` from the snapshot.** This is block-level read access
  to every block of the original volume, including OS files, application
  configuration, environment variables in user-data residue, and the
  on-disk remnants of deleted files. Treat as data-breach-likely.

- **Account-wide sweep.** Iterate every owned snapshot in every region
  with `describe-snapshot-attribute createVolumePermission` to enumerate
  all public exposures. One public snapshot is a finding; many is a
  systemic misconfiguration.

- **Shared-private ≠ public.** A snapshot with explicit non-owner account
  IDs (not `all`) is shared-private. Surface as a finding if the accounts
  are unexpected, but do NOT classify as PUBLIC_SNAPSHOT.

### Step 7: Aggregation — worst finding wins

Final verdict is the **maximum severity** across all dimensions
(CRITICAL > HIGH > MEDIUM > LOW > OK):

```
severity_rank = {
  PUBLIC_SNAPSHOT: CRITICAL, UNENCRYPTED: HIGH,
  UNATTACHED: MEDIUM, STALE_SNAPSHOT: MEDIUM, LEGACY_TYPE: LOW, OK: OK,
}
verdict = max(all_step_findings, key=severity_rank)
```

If no findings across all applicable steps, the verdict is **OK**.

## Output format (per resource)

```text
RESOURCE: <volume-id or snapshot-id>
VERDICT: UNENCRYPTED | UNATTACHED | LEGACY_TYPE | STALE_SNAPSHOT | PUBLIC_SNAPSHOT | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [HIGH] <finding description (Step N)>
  - [LOW] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, with CLI, or "None required" if OK>
```

### Worked example — unencrypted gp2 detached volume

```text
RESOURCE: vol-0abc123def4567890
VERDICT: UNENCRYPTED
REASON: Volume is unencrypted (Step 1, HIGH). Also gp2 (legacy type) and
unattached for > 90 days — verdict is the worst finding (UNENCRYPTED).
FINDINGS:
  - [HIGH] Encrypted is false — data at rest is unencrypted (Step 1)
  - [MEDIUM] State available for > 90 days — unattached cost waste (Step 3)
  - [LOW] VolumeType gp2 — upgrade path gp3, ~20% cheaper and tunable (Step 5)
REMEDIATION:
  1. HIGH — Snapshot and re-create encrypted. Encryption is immutable:
     aws ec2 create-snapshot --volume-id vol-0abc... --description "pre-encrypt"
     aws ec2 copy-snapshot --source-snapshot-id snap-... --encrypted --kms-key-id <kms>
     aws ec2 create-volume --snapshot-id snap-... --volume-type gp3 --encrypted --kms-key-id <kms>
     Swap the attachment and delete the old volume.
  2. MEDIUM — Confirm volume is unneeded, then snapshot + delete:
     aws ec2 delete-volume --volume-id vol-0abc...
  3. LOW — Moot; the new volume will be gp3.
```

## Edge-case handling

- **Encrypted volume with public snapshot lineage.** The snapshot is the
  exposure vector. If the volume is encrypted but a snapshot of it is
  public, the snapshot is PUBLIC_SNAPSHOT; the volume is OK. Two separate
  resources, two separate verdicts.

- **Shared-private snapshot from another account.** `OwnerId` differs
  from caller — cannot be modified. Surface as a dependency finding;
  route remediation to the owning account. NOT PUBLIC_SNAPSHOT.

- **Volume/snapshot in `creating` / `deleting` / `error` / `pending`.**
  Transient or failed states are NOT classified. VERDICT: ERROR with
  operational note ("re-fetch describe-volumes in 5 minutes").

- **Volume with `MultiAttachEnabled` but VolumeType not io1/io2.**
  Impossible in valid `describe-volumes` output (Multi-Attach requires
  io1/io2). Treat as input corruption (VERDICT: ERROR).

- **Tag override for retention.** A snapshot tagged
  `retainUntil:2099-01-01` is exempt from STALE_SNAPSHOT regardless of
  age — surface as a finding but the verdict is OK for this dimension.

- **`standard` (magnetic) volume with attached state.** Magnetic volumes
  are always LEGACY_TYPE regardless of attachment state — the upgrade to
  gp3 is non-negotiable. Verdict is LEGACY_TYPE even on a healthy
  production workload.

## Anti-Patterns — NEVER

- NEVER classify an unencrypted volume as anything other than UNENCRYPTED
  (HIGH). "It's a dev volume" / "It's behind a VPC" / "It has no public
  IP" are NOT mitigations — encryption-at-rest protects against
  insider/snapshot/physical-disk access, none of which are network-gated.

- NEVER recommend enabling encryption on an existing volume. EBS
  encryption is immutable per resource. The only valid remediation is
  snapshot → copy-snapshot --encrypted → create-volume --encrypted,
  then swap attachments. Saying "enable encryption" is a non-action.

- NEVER flag a gp3 / io2 / st1 / sc1 volume as LEGACY_TYPE. Only gp2,
  io1, and standard are legacy. Misclassifying modern types produces
  noise that buries real findings.

- NEVER classify a shared-private snapshot (explicit non-owner account
  IDs, no `Group: all`) as PUBLIC_SNAPSHOT. Shared-private is targeted
  sharing; public is world-readable. Conflating them produces false
  CRITICAL alerts.

- NEVER auto-delete an unattached or stale resource. The audit EMITS the
  verdict and the recommended `delete-volume` / `delete-snapshot` CLI.
  Execution requires explicit operator confirmation. Auto-deleting a
  snapshot referenced by an AMI bricks launches; auto-deleting a volume
  destroys the data irrecoverably.

- NEVER skip FSR enumeration for STALE_SNAPSHOT candidates. FSR costs
  $0.06/hr per AZ — a stale snapshot with FSR in 3 AZs is $129.60/month
  of waste vs $4.50/month of storage. Reporting storage cost without FSR
  hides the real saving lever.

- NEVER report `gp2` as "fine" because it is "still supported." gp3 is
  cheaper at baseline, IOPS/throughput are independently tunable, and
  AWS recommends gp3 for new volumes. A skill that does not surface gp2
  is missing the highest-value EBS optimisation in most accounts.

- NEVER treat a snapshot in the Archive tier as stale by the 90-day
  threshold. Archive snapshots cost $0.012/GB-month — apply the 180-day
  threshold and surface the archive status in FINDINGS.

- NEVER recommend deleting a snapshot without checking AMI references.
  `describe-images --filters BlockDeviceMapping.SnapshotId=<id>` — if
  any AMI references it, deleting bricks launches. Deregister the AMI
  first (separate operator approval).

- NEVER assume cross-region snapshot copy preserves public/private state.
  Each region's snapshot registry is independent. A sweep that checks
  one region misses exposures in every other region.

- NEVER recommend `ModifyVolume` on a multi-attached io1 volume without
  verifying all attachments support io2 concurrency. io2 Multi-Attach
  supports up to 16 Nitro instances; io1 varies. A blind modify changes
  concurrency semantics.

- NEVER treat `DeleteOnTermination: true` on an attached data volume as
  OK. This is a data-loss vector: terminating the instance destroys the
  data volume. Surface as a finding (does not change verdict).

- NEVER classify a volume with `State: error` into the verdict enum.
  Force-fitting an errored volume as UNENCRYPTED or UNATTACHED hides the
  operational issue. VERDICT: ERROR, re-fetch.

- NEVER assume `delete-snapshot` on an intermediate snapshot frees its
  storage immediately. EBS snapshots are incremental — deleting an
  intermediate snapshot migrates its unique blocks to later snapshots
  that reference them; storage is freed only when a snapshot-id's blocks
  are unreferenced by any remaining snapshot in the chain. The delete is
  safe (no data loss) but the expected cost saving may lag by weeks.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any destructive or state-changing
  operation (DeleteVolume, DeleteSnapshot, ModifyVolume,
  ModifySnapshotAttribute, ResetSnapshotAttribute), emit:
  `CONFIRM: About to <action> on <resource-id> in account <account>
  region <region>. This affects <consequence>. Proceed? (yes/no)`. Do
  NOT execute the CLI until the operator confirms.

- **Snapshot-then-delete ordering.** Safe sequence for DeleteVolume:
  (1) `create-snapshot` (preserve data), (2) wait `completed`,
  (3) `delete-volume`. Reverse order destroys data irrecoverably. For
  DeleteSnapshot, ALWAYS check AMI references and FSR first.

- **ModifyVolume side-effects.** Type/IOPS changes are online and non-
  destructive, but performance changes can take up to 6 hours to take
  full effect and the volume enters `modifying` state during which
  further modifications are limited.

- **Public-snapshot remediation is reversible.** `aws ec2
  reset-snapshot-attribute --snapshot-id <id> --attribute
  createVolumePermission` removes all public sharing. Prefer reset over
  ModifySnapshotAttribute — reset is idempotent, Modify can leave
  residual shared accounts.

- **Capture state for rollback.** Before modification:
  `aws ec2 describe-volumes --volume-ids <id> --output json >
  /tmp/<id>-backup-$(date +%s).json`. Volume and snapshot metadata are
  not versioned.

- **Encryption-by-default account-level gate.** Before recommending
  volume-level encryption re-creation, surface the account-level fix:
  `aws ec2 enable-ebs-encryption-by-default` — this prevents future
  unencrypted volumes and is the higher-leverage remediation.

- **Cross-account snapshot sharing requires KMS coordination.** If
  recommending encrypted cross-account sharing, the snapshot share is
  necessary but NOT sufficient — the KMS key policy must also permit
  the recipient account, or `CreateVolume` returns `InvalidParameter`.

- **Prefer reversible changes.** Tag (`audit:review-required`,
  `retainUntil`) before deleting — a tagged resource is recoverable; a
  deleted one is not.

## Remediation guidance

**Ordering principle:** prefer the cheapest reversible action that
removes the exposure. Reset attribute for PUBLIC_SNAPSHOT (instant).
Enable encryption-by-default first for UNENCRYPTED (stops bleeding),
then triage existing volumes. Snapshot-then-delete for UNATTACHED/
STALE_SNAPSHOT (cheaper than retention). ModifyVolume for LEGACY_TYPE
(online, low-risk).

### For CRITICAL — PUBLIC_SNAPSHOT (Step 6)

1. **Immediately** reset the attribute:
   `aws ec2 reset-snapshot-attribute --snapshot-id <id> --attribute createVolumePermission --profile <p> --region <r>`.
   Removes `Group: all` and explicit shared-account entries in one call.
2. **Assume breach.** Audit CloudTrail for `CreateVolume` events
   referencing this snapshot-id from unexpected accounts during the
   exposure window. Any volume created from the public snapshot is
   compromised.
3. **Verify content sensitivity.** If the snapshot contains secrets (AWS
   keys in user-data residue, application credentials, database dumps),
   rotate them — block-level access exposes deleted files and disk
   residue, not just current state.
4. **Account-wide sweep.** Iterate `describe-snapshots --owner-ids self`
   per region and check each `createVolumePermission`.

### For HIGH — UNENCRYPTED volume (Step 1)

1. **Account-level fix first:**
   `aws ec2 enable-ebs-encryption-by-default --profile <p> --region <r>`.
2. **Resource-level re-creation (encryption is immutable in place):**
   ```bash
   SNAP=$(aws ec2 create-snapshot --volume-id <id> --description "encrypt-migration" --query SnapshotId --output text)
   aws ec2 wait snapshot-completed --snapshot-ids $SNAP
   ENC=$(aws ec2 copy-snapshot --source-snapshot-id $SNAP --source-region <r> --encrypted --kms-key-id <kms> --query SnapshotId --output text)
   aws ec2 wait snapshot-completed --snapshot-ids $ENC
   NEW=$(aws ec2 create-volume --snapshot-id $ENC --availability-zone <az> --volume-type gp3 --encrypted --kms-key-id <kms> --query VolumeId --output text)
   aws ec2 wait volume-available --volume-ids $NEW
   aws ec2 attach-volume --volume-id $NEW --instance-id <i> --device <dev>
   aws ec2 detach-volume --volume-id <old-id>
   aws ec2 delete-volume --volume-id <old-id>
   ```
3. **Confirm** with the app owner before the swap — the new volume has a
   different volume-id and may need to be re-tagged.

### For HIGH — UNENCRYPTED snapshot (Step 2)

1. If referenced by an AMI, the AMI must be re-registered from an
   encrypted copy — multi-step remediation.
2. Otherwise:
   ```bash
   ENC=$(aws ec2 copy-snapshot --source-snapshot-id <id> --source-region <r> --encrypted --kms-key-id <kms> --query SnapshotId --output text)
   aws ec2 wait snapshot-completed --snapshot-ids $ENC
   aws ec2 delete-snapshot --snapshot-id <old-id>
   ```

### For MEDIUM — UNATTACHED (Step 3)

1. Verify no operator has a pending re-attach plan (tags, recent
   `DetachVolume` events, ticketing system).
2. Snapshot (preserve data at ~5x cheaper):
   `aws ec2 create-snapshot --volume-id <id> --description "pre-delete $(date +%F)"`.
3. After snapshot completes, delete:
   `aws ec2 delete-volume --volume-id <id>`.
4. Tag the snapshot `audit:detached-volume-backup` with the original
   volume-id for traceability.

### For MEDIUM — STALE_SNAPSHOT (Step 4)

1. **Drain FSR first** if enabled:
   `aws ec2 disable-fast-snapshot-restores --availability-zones <az1> <az2> ...`.
2. Verify no AMI references it:
   `aws ec2 describe-images --owners self --filters Name=block-device-mapping.snapshot-id,Values=<id>`.
3. Verify no recent `CreateVolume` events in CloudTrail.
4. `aws ec2 delete-snapshot --snapshot-id <id>`.

### For LOW — LEGACY_TYPE (Step 5)

1. **gp2 -> gp3 (online, seconds to minutes):**
   `aws ec2 modify-volume --volume-id <id> --volume-type gp3`.
   Optionally `--iops 3000 --throughput 125` (defaults).
2. **io1 -> io2 (online):**
   `aws ec2 modify-volume --volume-id <id> --volume-type io2`. Confirm
   Multi-Attach concurrency limits after the modify.
3. **standard -> gp3:** same `modify-volume` command.
4. Monitor CloudWatch `VolumeStalled` / `VolumeConsumedReadWriteOps` for
   24 hours post-modify.

### For OK

1. No remediation required for current posture.
2. Recommend enabling account-level encryption-by-default if not already.
3. Recommend a 30/60/90-day snapshot retention schedule via DLM or AWS
   Backup to prevent future staleness drift.

## Severity matrix

| Verdict | Severity | Reason |
|---|---|---|
| `PUBLIC_SNAPSHOT` | CRITICAL | Block-level data readable by every AWS account; assume breach |
| `UNENCRYPTED` | HIGH | Compliance violation; data at rest exposed to insider/snapshot/physical-disk vectors |
| `UNATTACHED` | MEDIUM | Cost waste; no workload benefit |
| `STALE_SNAPSHOT` | MEDIUM | Cost waste + stale restore point; check FSR cost dominance |
| `LEGACY_TYPE` | LOW | Cost optimisation + (io1/standard) reliability gap |
| `OK` | OK | All dimensions clean |

## Deep reference: EBS internals

**Encryption immutability:** Volume/snapshot `Encrypted` flag is fixed at
creation. `ModifyVolume` cannot toggle it. `enable-ebs-encryption-by-default`
applies to NEW volumes only — existing unencrypted volumes remain until
individually migrated.

**gp3 vs gp2 performance model:** `gp2` IOPS scale at 3 IOPS/GB (max 16,000
at 5,334 GB). Below 1 TB, gp2 is IOPS-constrained relative to gp3. `gp3`
delivers 3,000 IOPS and 125 MB/s baseline at lower per-GB price, with
independent provisioning up to 16,000 IOPS / 1,000 MB/s. For most
general-purpose workloads, gp3 is strictly better.

**io2 vs io1:** `io1` 99.8%-99.9% durability, Multi-Attach up to 1 Nitro
instance. `io2` 99.999% durability, Multi-Attach up to 16 Nitro instances,
same per-GB and per-IOPS price. `io2-block-express` extends io2 to 64,000
IOPS / 4 GB/s per volume. No scenario prefers a new io1 over io2.

**Fast Snapshot Restore (FSR):** Pre-warms a snapshot in a specific AZ so
the first `CreateVolume` reaches full performance immediately. Cost:
$0.06/hour per AZ per snapshot — $43.20/AZ/month. Independent of
`createVolumePermission`; a private snapshot can carry FSR.

**Snapshot tiering (Archive):** $0.012/GB-month, 24-72 hour restore, via
`modify-snapshot-tier` or DLM. Apply the 180-day staleness threshold (vs
90-day for standard tier).

**Snapshot chain semantics:** EBS snapshots are incremental. Deleting an
intermediate snapshot does NOT free its blocks — they migrate to later
snapshots that reference them. `delete-snapshot` is safe regardless of
chain position; the backend handles reference counting.

**Cross-region snapshot copy:** `copy-snapshot` replicates to a destination
region with a different snapshot-id. Public/private state does NOT
propagate — each region's registry is independent. Encrypted cross-region
copy requires the destination region's KMS key.

**Cross-account snapshot sharing:** Unencrypted snapshot sharing grants
the recipient `CreateVolume` access. For encrypted snapshots, the KMS key
policy must ALSO permit the recipient (`kms:CreateGrant` / `kms:Decrypt`).
Without the KMS side, the recipient gets the snapshot reference but cannot
create a volume — a common deadlock.

## Domain

AWS CloudOps / EBS Storage Security & Cost Optimisation.
