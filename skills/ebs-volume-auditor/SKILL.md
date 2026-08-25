---
name: ebs-volume-auditor
description: Audits AWS EBS volumes and EBS snapshots for unencrypted volumes, unattached cost-drift volumes, legacy gp2 volume types (gp3 upgrade path), stale snapshots accumulating storage cost, and public snapshots exposing block data to every AWS account. Emits a deterministic verdict (UNENCRYPTED | UNATTACHED | LEGACY_TYPE | STALE_SNAPSHOT | PUBLIC_SNAPSHOT | OK) per resource with enumerated findings and specific CLI remediation. Use when reviewing EBS volume posture, checking for unencrypted volumes, hunting unattached cost-waste volumes, validating gp2->gp3 upgrade candidates, pruning stale snapshots, or detecting public-snapshot data exposure.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline configuration classification. Live-account audits use aws ec2 describe-volumes, aws ec2 describe-snapshots, aws ec2 describe-snapshot-tier-status, and aws ec2 describe-fast-snapshot-restores (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  verdict_shape: UNENCRYPTED | UNATTACHED | LEGACY_TYPE | STALE_SNAPSHOT | PUBLIC_SNAPSHOT | OK
  when_to_use: Reviewing an EBS volume or snapshot before production deployment, hunting unencrypted volumes under compliance mandates (PCI/SOC2/HIPAA), pruning unattached cost-waste volumes, validating gp2->gp3 upgrade candidates, detecting public-snapshot block-data exposure, or auditing EBS encryption and volume-type posture across an account.
  activation_triggers: audit this EBS volume, is my EBS volume encrypted, unattached EBS volumes, gp2 to gp3 upgrade, stale EBS snapshots, public snapshot exposure, EBS cost optimization, CreateVolumePermission public, EBS encryption and volume-type audit, EBS snapshot public access check
  invocation_schema: 'Input: either (a) an EBS volume or snapshot configuration (describe-volumes or describe-snapshots JSON, optionally paired with CreateVolumePermissions), OR (b) a volume-id / snapshot-id for live-account audit. Output: deterministic RESOURCE/VERDICT/REASON/FINDINGS/REMEDIATION block per resource, where VERDICT ∈ {UNENCRYPTED, UNATTACHED, LEGACY_TYPE, STALE_SNAPSHOT, PUBLIC_SNAPSHOT, OK, ERROR}.'
  version: 0.1.1
  author: Jacky Chan — AWS Community Builder
  keywords: EBS, Elastic Block Store, EBS volume, EBS snapshot, unencrypted volume, encryption-by-default, unattached volume, gp2, gp3, io1, io2, provisioned IOPS, stale snapshot, public snapshot, CreateVolumePermission, fast snapshot restore, FSR, cross-region snapshot copy, KMS encryption, volume type upgrade, storage cost optimization, block storage audit
  tags: ebs, storage, security, encryption, cost-optimization, snapshot, volume-type, public-snapshot, audit
---

# EBS Volume Auditor

## Quick start

**Decision tree — worst finding wins in strict priority order:**

`PUBLIC_SNAPSHOT` (CRITICAL) > `UNENCRYPTED` (HIGH) > `UNATTACHED` (MEDIUM) ≡ `STALE_SNAPSHOT` (MEDIUM) > `LEGACY_TYPE` (LOW) > `OK`

| Verdict | Trigger condition | Sev | Primary CLI (lowercase, exact) |
|---|---|---|---|
| `PUBLIC_SNAPSHOT` | snapshot `createVolumePermission` includes `Group: all` | CRITICAL | `aws ec2 reset-snapshot-attribute` |
| `UNENCRYPTED` | volume or snapshot `Encrypted: false` (or absent) | HIGH | `aws ec2 copy-snapshot --encrypted` + `aws ec2 create-volume --encrypted` |
| `UNATTACHED` | volume `State: available`, no attachments, >= 30 days detached | MEDIUM | `aws ec2 create-snapshot` then `aws ec2 delete-volume` |
| `STALE_SNAPSHOT` | snapshot >= 90 days (standard) / 180 days (archive), no AMI/FSR/retention consumer | MEDIUM | `aws ec2 delete-snapshot` (drain FSR via `disable-fast-snapshot-restores` first) |
| `LEGACY_TYPE` | `VolumeType` in {`gp2`, `io1`, `standard`} | LOW | `aws ec2 modify-volume --volume-type gp3` (or `--volume-type io2`) |
| `OK` | encrypted modern-type attached volume, no public/stale snapshots | OK | None required |

**Critical rules (always apply — expanded in Anti-Patterns):**

1. **CONFIRM gate before any destructive or state-changing CLI.** Emit `CONFIRM: About to <action> on <resource-id> in account <acct> region <region>...` and wait for explicit operator "yes". Never auto-delete.
2. **EBS encryption is immutable per resource.** Never say "enable encryption on a volume" — the only path is snapshot → `copy-snapshot --encrypted` → `create-volume --encrypted`.
3. **FSR dominates stale-snapshot cost** — $0.06/hr per AZ ($43.20/AZ-month). A 100 GB snapshot with FSR in 3 AZs costs $129.60/mo FSR + $4.50/mo storage. Always enumerate via `describe-fast-snapshot-restores`.
4. **`Group: all` = any AWS account, in any region, can `CreateVolume` and read every block.** Treat as data-breach-likely. Shared-private (explicit account IDs) ≠ public.
5. **Cross-region snapshot copy is billable** (per-GB transfer + destination-region storage). Never bulk-copy without surfacing the cost estimate; each region's public/private registry is independent — sweep every region.

**Cost baseline (us-east-1, 2026):** gp2 $0.10/GB-mo, gp3 $0.08/GB-mo, io1/io2 $0.125/GB-mo + $0.065/provisioned-IOPS-mo, standard $0.05/GB-mo, snapshot standard $0.05/GB-mo, snapshot archive $0.012/GB-mo, FSR $0.06/hr per AZ.

## Mindset

**One-line takeaway:** the verdict is the **worst** finding across all dimensions, applied in strict priority order, driven by three EBS realities:

- **Public snapshots expose block-level data.** A public EBS snapshot can be `CreateVolume`-d by **any AWS account in any region** — the requester reads every block, including OS files, secrets in user-data residue, and on-disk remnants of deleted files (snapshots are point-in-time block copies, not application-level exports).
- **EBS encryption is immutable per resource.** A volume's `Encrypted` flag and KMS key are fixed at creation. Retrofitting requires a snapshot-copy + new-volume flow; an unencrypted snapshot can be re-issued from the volume at any time, so the unencrypted volume is the leak source.
- **Unattached volumes still bill.** An `available` volume accrues the full GB-month charge the moment it is detached — there is no "parked" rate. The single largest source of EBS overspend is detached volumes kept "just in case" across regions and accounts.

## Pre-flight: resource metadata gate

Run before classification. Misclassifying these produces false positives.

**Pagination:** `describe-volumes` and `describe-snapshots` paginate at 500/page — drain `--next-token` to completion. For snapshots ALWAYS pass `--owner-ids self`; without it, the call returns every public snapshot in the world and is rate-limited/throttled.

**Malformed input:** if the input JSON is invalid or missing required fields, output `VERDICT: ERROR` with `REASON: Resource configuration is not valid JSON or is missing required fields — cannot classify.` and `REMEDIATION: Re-fetch with aws ec2 describe-volumes --volume-ids <id> --output json (or describe-snapshots) and re-audit.`

**Malformed timestamps:** timestamps MUST be ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`). If `StartTime` / `CreateTime` / `AttachTime` is missing, non-ISO, or unparseable, surface `[MEDIUM] Timestamp missing or unparseable — age-based thresholds skipped` in FINDINGS and fall back to the worst-case assumption for that step (treat as stale/unattached if other signals support it, else skip the age-gated check).

**Live-account pre-flight (skip if offline audit):**
1. `aws ec2 get-ebs-encryption-by-default` — if `false`, surface the account-level gap alongside any resource verdict.
2. Verify the caller holds `ec2:ModifyVolume` / `ec2:ModifySnapshotAttribute` if remediation is intended — read-only roles return `UnauthorizedOperation`.
3. Snapshot ownership: only snapshots where `OwnerId` matches the caller are mutable. Shared snapshots can be `CopySnapshot`'d but never `ModifySnapshotAttribute`'d.

| Attribute | Effect on audit |
|---|---|
| Resource type `volume` | Run Steps 1, 3, 5, 7 (skip snapshot steps). |
| Resource type `snapshot` | Run Steps 2, 4, 6, 7 (skip volume steps). |
| `Encrypted: false` | Jump to Step 1 — UNENCRYPTED regardless of other dimensions. |
| `KmsKeyId` = `aws/ebs` alias / AWS-managed ARN | AWS-managed key — rotation automatic. Do NOT audit the key policy. |
| `KmsKeyId` = customer-managed ARN | Cross-reference kms-key-policy-auditor; the volume itself is encrypted. |
| `MultiAttachEnabled: true` | io1/io2 only. Verify ALL `Attachments` are healthy and on Nitro instances (io2 Multi-Attach is Nitro-only). |
| Snapshot `OwnerId` ≠ caller | Shared-private — cannot remediate. Skip PUBLIC check (shared ≠ public). |
| `State: error` / `creating` / `deleting` | Transient/failed. VERDICT: ERROR — do not force-fit the enum. |

## Process — classification logic (apply in order, aggregate worst)

### Step 1: Volume encryption (UNENCRYPTED — HIGH)

If resource is a volume and `Encrypted` is `false` (or absent):

- **Verdict: UNENCRYPTED (HIGH).** Volume blocks are readable by anyone with physical/insider access to the storage infrastructure, and any snapshot re-issued inherits the unencrypted state. Under PCI-DSS, HIPAA, SOC2, and most enterprise policies, unencrypted EBS is a compliance violation regardless of workload sensitivity. Network position is not a mitigation.
- **Compound check:** `KmsKeyId` set with `Encrypted: false` is impossible in valid `describe-volumes` output (KmsKeyId appears only when Encrypted is true) — treat as input corruption (VERDICT: ERROR).
- **Account-level escalation:** if `get-ebs-encryption-by-default` is `false` for the region, surface: "Region does not enforce encryption-by-default; future volumes will also be unencrypted."

### Step 2: Snapshot encryption (UNENCRYPTED — HIGH on snapshots)

If resource is a snapshot and `Encrypted` is `false`: **Verdict: UNENCRYPTED (HIGH).** Unencrypted snapshots inherit the parent volume's exposure and are restorable by anyone with snapshot access. If encryption-by-default is `true` in the snapshot's region but the snapshot is unencrypted, the snapshot predates the setting or was copied from a non-encrypting region — surface as a "stale-source" finding.

### Step 3: Volume attachment state (UNATTACHED — MEDIUM)

If resource is a volume, `State: available`, and `Attachments` empty or all entries `detached`:

- **Derive duration of detachment.** `describe-volumes` does not report when the last attachment ended. Derive from CloudTrail `DetachVolume` events OR resource tags (`lastAttached`, `detachedDate`). Without a duration signal, fall back to `CreateTime`: a volume older than 30 days that is currently available is treated as UNATTACHED.
- **>= 30 days: MEDIUM.** Volume accrues full GB-month cost with no workload benefit. Surface the monthly cost estimate (`Size * regional $/GB-month`).
- **>= 90 days: MEDIUM with escalation.** Likely forgotten. Recommend snapshot-and-delete (snapshot preserves data at ~5x cheaper).
- **>= 365 days: surface for snapshot+delete.** Year-old detached volumes are organisational debt; the data is unlikely to be needed but cannot be silently deleted without owner confirmation.

### Step 4: Snapshot staleness (STALE_SNAPSHOT — MEDIUM)

If resource is a snapshot, derive staleness from `StartTime`:

- **< 90 days: NOT stale.** No finding.
- **>= 90 days: STALE_SNAPSHOT candidate.** Verify the snapshot is NOT: (a) referenced by a registered AMI (`describe-images --filters BlockDeviceMapping.SnapshotId=<id>`); (b) enabled for Fast Snapshot Restore (`describe-fast-snapshot-restores`); (c) tagged with a retention override (`retainUntil`, `backup:policy`); (d) in the Archive tier (`describe-snapshot-tier-status` — archive snapshots use the 180-day threshold instead).
- **>= 90 days AND none of the above: STALE_SNAPSHOT (MEDIUM).** >= 365 days with no consumer: escalate.
- **FSR cost dominance.** If a snapshot has FSR enabled in any AZ, surface the FSR monthly cost (AZ count × $0.06 × 720 hours) BEFORE the storage cost — FSR routinely exceeds storage 10-30x and is the larger lever.

### Step 5: Volume type modernity (LEGACY_TYPE — LOW)

| VolumeType | Classification | Upgrade path | Notes |
|---|---|---|---|
| `gp3` | MODERN | — | Current general-purpose baseline. No finding. |
| `gp2` | LEGACY_TYPE | `ModifyVolume --volume-type gp3` | ~20% cost reduction; IOPS/throughput tunable independently of size. |
| `io2` / `io2-block-express` | MODERN | — | Current provisioned-IOPS baseline. No finding. |
| `io1` | LEGACY_TYPE | `ModifyVolume --volume-type io2` | Same price, lower durability (99.8-99.9% vs 99.999%). Always upgrade. |
| `st1` (throughput HDD) / `sc1` (cold HDD) | MODERN | — | Correct for sequential or cold workloads. Min size 500 GB. |
| `standard` (magnetic) | LEGACY_TYPE | `ModifyVolume --volume-type gp3` | Legacy; expensive, poor latency. |

LEGACY_TYPE is the **lowest-severity verdict**. A gp2 volume that is encrypted and attached is still LEGACY_TYPE. For `gp3` and `io1`/`io2`, compare provisioned `Iops` against typical workload — a gp3 volume at 16,000 IOPS for an idle web-server is a 5x overspend (surface as a finding; verdict stays MODERN).

### Step 6: Public snapshot detection (PUBLIC_SNAPSHOT — CRITICAL)

If resource is a snapshot owned by the caller (`OwnerId` matches):

- **Retrieve `CreateVolumePermissions`:** `aws ec2 describe-snapshot-attribute --snapshot-id <id> --attribute createVolumePermission`. If `Group: all` is present OR entries include accounts the operator cannot identify, classify as **PUBLIC_SNAPSHOT (CRITICAL)**.
- **PUBLIC_SNAPSHOT means any AWS account, in any region, can `ec2:CreateVolume` from the snapshot** — block-level read access to every block of the original volume, including OS files, application configuration, environment variables in user-data residue, and on-disk remnants of deleted files. Treat as data-breach-likely.
- **Account-wide sweep:** iterate every owned snapshot in every region with `describe-snapshot-attribute createVolumePermission`. One public snapshot is a finding; many is systemic misconfiguration.
- **Shared-private ≠ public.** A snapshot with explicit non-owner account IDs (not `all`) is shared-private. Surface as a finding if the accounts are unexpected, but do NOT classify as PUBLIC_SNAPSHOT.

### Step 7: Aggregation — worst finding wins

Final verdict is the **maximum severity** across all dimensions (CRITICAL > HIGH > MEDIUM > LOW > OK). If no findings across all applicable steps, the verdict is **OK**.

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

**Severity tags are MANDATORY in every FINDINGS line:** `[CRITICAL]` | `[HIGH]` | `[MEDIUM]` | `[LOW]` | `[OK]`. The tag maps 1:1 to the verdict's severity row (PUBLIC_SNAPSHOT→CRITICAL, UNENCRYPTED→HIGH, UNATTACHED/STALE_SNAPSHOT→MEDIUM, LEGACY_TYPE→LOW, OK→OK).

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
  1. HIGH — Account-level: aws ec2 enable-ebs-encryption-by-default
  2. HIGH — Resource-level: encryption is immutable, snapshot + re-create:
     aws ec2 create-snapshot --volume-id vol-0abc... --description "pre-encrypt"
     aws ec2 copy-snapshot --source-snapshot-id snap-... --encrypted --kms-key-id <kms>
     aws ec2 create-volume --snapshot-id snap-... --volume-type gp3 --encrypted --kms-key-id <kms>
     Swap the attachment and delete the old volume.
  3. MEDIUM — Confirm volume is unneeded, then snapshot + delete:
     CONFIRM: About to delete-volume vol-0abc... in account <acct> region <r>. This destroys the volume (snapshot preserved). Proceed? (yes/no)
     aws ec2 delete-volume --volume-id vol-0abc...
  4. LOW — Moot; the new volume will be gp3.
```

### Worked example — clean encrypted gp3 volume

```text
RESOURCE: vol-0fff666encrypted-gp3-ok
VERDICT: OK
REASON: All dimensions clean (encrypted, gp3, attached, no public/stale exposure).
FINDINGS:
  - [OK] Encrypted with customer-managed KMS key (Step 1)
  - [OK] State in-use, attached, no detachment drift (Step 3)
  - [OK] VolumeType gp3 — modern baseline (Step 5)
REMEDIATION: None required. Recommend enabling account-level encryption-by-default if not already, and a 30/60/90-day DLM retention schedule to prevent future staleness drift.
```

## Anti-Patterns — NEVER

- NEVER classify an unencrypted volume as anything other than UNENCRYPTED (HIGH). "It's a dev volume" / "It's behind a VPC" / "It has no public IP" are NOT mitigations — encryption-at-rest protects against insider/snapshot/physical-disk access, none of which are network-gated.
- NEVER recommend enabling encryption on an existing volume. EBS encryption is immutable per resource. The only valid remediation is snapshot → `copy-snapshot --encrypted` → `create-volume --encrypted`, then swap attachments. Saying "enable encryption" is a non-action.
- NEVER flag a gp3 / io2 / st1 / sc1 volume as LEGACY_TYPE. Only gp2, io1, and standard are legacy.
- NEVER classify a shared-private snapshot (explicit non-owner account IDs, no `Group: all`) as PUBLIC_SNAPSHOT. Shared-private is targeted sharing; public is world-readable. Conflating them produces false CRITICAL alerts.
- NEVER auto-delete an unattached or stale resource. The audit EMITS the verdict and the recommended CLI. Execution requires explicit `CONFIRM:` gate approval. Auto-deleting a snapshot referenced by an AMI bricks launches; auto-deleting a volume destroys data irrecoverably.
- NEVER skip FSR enumeration for STALE_SNAPSHOT candidates. FSR costs $0.06/hr per AZ — a stale snapshot with FSR in 3 AZs is $129.60/month of waste vs $4.50/month of storage. Reporting storage cost without FSR hides the real saving lever.
- NEVER report `gp2` as "fine" because it is "still supported." gp3 is cheaper at baseline, IOPS/throughput are independently tunable, and AWS recommends gp3 for new volumes.
- NEVER treat a snapshot in the Archive tier as stale by the 90-day threshold. Archive snapshots cost $0.012/GB-month — apply the 180-day threshold and surface the archive status in FINDINGS.
- NEVER recommend deleting a snapshot without checking AMI references. `describe-images --filters BlockDeviceMapping.SnapshotId=<id>` — if any AMI references it, deleting bricks launches. Deregister the AMI first (separate operator approval).
- NEVER assume cross-region snapshot copy preserves public/private state. Each region's snapshot registry is independent. A sweep that checks one region misses exposures in every other region.
- NEVER assume `delete-snapshot` immediately reduces billing. EBS snapshots are incremental — deleting an intermediate snapshot migrates its unique blocks to later snapshots that reference them; storage is freed only when a snapshot-id's blocks are unreferenced by any remaining snapshot. The delete is safe (no data loss) but the expected cost saving may lag by weeks.
- NEVER recommend `modify-volume --volume-type io2` on a multi-attached io1 volume without verifying (a) ALL attached instances are Nitro-based — io2 Multi-Attach is Nitro-only and non-Nitro instances lose block access silently post-modify, and (b) the io2 Multi-Attach concurrency ceiling (16 Nitro instances) covers the current attachment count. A blind modify changes concurrency semantics and can silently detach non-Nitro consumers.
- NEVER treat `DeleteOnTermination: true` on an attached data volume as OK. This is a data-loss vector: terminating the instance destroys the data volume. Surface as a finding (does not change verdict).
- NEVER classify a volume with `State: error` into the verdict enum. VERDICT: ERROR, re-fetch.
- NEVER trust `describe-volumes` `KmsKeyId` for alias-based key matching — it always returns the full key ARN even when the volume was created with an alias like `alias/aws/ebs`. Resolve via `aws kms describe-key --key-id <arn>` if alias identity matters.
- NEVER bulk-issue cross-region `copy-snapshot` without surfacing the cost. Cross-region copy bills per-GB data transfer plus destination-region storage — a 1 TB snapshot copied to 3 regions is 3 TB of transfer + 3 TB-month of storage, ongoing.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any destructive or state-changing operation (DeleteVolume, DeleteSnapshot, ModifyVolume, ModifySnapshotAttribute, ResetSnapshotAttribute), emit: `CONFIRM: About to <action> on <resource-id> in account <account> region <region>. This affects <consequence>. Proceed? (yes/no)`. Do NOT execute the CLI until the operator confirms.
- **Snapshot-then-delete ordering.** Safe sequence for DeleteVolume: (1) `create-snapshot` (preserve data), (2) wait `completed`, (3) `delete-volume`. Reverse order destroys data irrecoverably. For DeleteSnapshot, ALWAYS check AMI references and FSR first.
- **ModifyVolume side-effects.** Type/IOPS changes are online and non-destructive, but: (a) performance changes can take up to 6 hours to reach full effect — CloudWatch may show stale metrics in the interim; (b) a volume can only be modified once every 6 hours — serialise back-to-back size+type+IOPS changes with waits; (c) the volume enters `modifying` state during which further modifications are limited.
- **Public-snapshot remediation is reversible.** `reset-snapshot-attribute` removes all public sharing in one idempotent call. Prefer it over ModifySnapshotAttribute, which can leave residual shared accounts.
- **Capture state for rollback.** Before modification: `aws ec2 describe-volumes --volume-ids <id> --output json > /tmp/<id>-backup-$(date +%s).json`. Volume/snapshot metadata is not versioned.
- **Encryption-by-default account-level gate.** Before recommending volume-level encryption re-creation, surface the account-level fix: `enable-ebs-encryption-by-default` — this prevents future unencrypted volumes and is the higher-leverage remediation.
- **Cross-account encrypted sharing requires KMS coordination.** The snapshot share is necessary but NOT sufficient — the KMS key policy must also permit the recipient account (`kms:CreateGrant` / `kms:Decrypt`), or `CreateVolume` returns `InvalidParameter`. This is a common deadlock.
- **Prefer reversible changes.** Tag (`audit:review-required`, `retainUntil`) before deleting — a tagged resource is recoverable; a deleted one is not.

## Reference — EBS internals (deep material)

**Non-obvious operational behaviours (affect classification and remediation):**

- **gp2 burst credits vs gp3 provisioned model.** gp2 accumulates IOPS burst credits (5.4M-credit bucket, refill at 3 IOPS/GB-second) and can burst above its baseline briefly. gp3 has NO burst bucket — above 3,000 IOPS / 125 MB/s baseline is purely provisioned and billed. Treating gp3 like gp2 (expecting free burst) is a capacity-planning trap.
- **ModifyVolume rate limit.** A volume accepts one `ModifyVolume` call every 6 hours; performance changes take up to 6 hours for full effect. Bulk automation (e.g., fleet-wide gp2→gp3) must serialise per-volume with waits, not fan out concurrently.
- **`describe-snapshot-tier-status` is eventually consistent** (~1 hour lag). A snapshot just archived may still show STANDARD. Do not re-issue `modify-snapshot-tier` — wait and re-check.
- **`describe-volumes` always returns `KmsKeyId` as the full key ARN**, even when the volume was created with an alias like `alias/aws/ebs`. Automation that string-matches on the alias will miss encrypted volumes silently. Use `aws kms describe-key --key-id <arn>` to resolve the alias if needed.
- **st1 / sc1 minimum size is 500 GB.** `create-volume --size 100 --volume-type st1` fails with `ValidationError`. A right-sizing workflow that suggests downscaling an st1 volume below 500 GB is broken.
- **FSR per-region quota.** Default quota is 50 FSR-enabled snapshots per region. Bulk enabling FSR fails on the 51st with a quota error — request a quota increase before fleet-wide FSR rollout.
- **`DeleteVolume` on a volume with a pending snapshot fails** with a misleading "volume is in use" error. Drain pending snapshots to `completed` before delete.

**Encryption immutability:** Volume/snapshot `Encrypted` flag is fixed at creation. `ModifyVolume` cannot toggle it. `enable-ebs-encryption-by-default` applies to NEW volumes only — existing unencrypted volumes remain until individually migrated. Cross-account encrypted snapshot sharing requires BOTH the snapshot share AND the KMS key policy update (`kms:CreateGrant` / `kms:Decrypt`); without the KMS side, the recipient gets a snapshot reference but cannot create a volume — a common deadlock.

**gp3 vs gp2 performance model:** gp2 IOPS scale at 3 IOPS/GB (max 16,000 at 5,334 GB). Below 1 TB, gp2 is IOPS-constrained relative to gp3. gp3 delivers 3,000 IOPS and 125 MB/s baseline at lower per-GB price, with independent provisioning up to 16,000 IOPS / 1,000 MB/s. For most general-purpose workloads, gp3 is strictly better. `ModifyVolume` upgrade to gp3 is online, no detach, no data loss.

**io2 vs io1:** io1 99.8-99.9% durability, Multi-Attach up to 1 Nitro instance. io2 99.999% durability, Multi-Attach up to 16 Nitro instances, same per-GB and per-IOPS price. io2-block-express extends io2 to 64,000 IOPS / 4 GB/s per volume (not available in all AZs — verify before recommending). No scenario prefers a new io1 over io2.

**Fast Snapshot Restore (FSR):** Pre-warms a snapshot in a specific AZ so the first `CreateVolume` reaches full performance immediately. Cost: $0.06/hour per AZ per snapshot — $43.20/AZ/month. Independent of `createVolumePermission`; a private snapshot can carry FSR.

**Snapshot tiering (Archive):** $0.012/GB-month, 24-72 hour restore, via `modify-snapshot-tier` or DLM. Apply the 180-day staleness threshold (vs 90-day for standard tier).

**Snapshot chain semantics:** EBS snapshots are incremental. Deleting an intermediate snapshot does NOT free its blocks — they migrate to later snapshots that reference them. `delete-snapshot` is safe regardless of chain position; the backend handles reference counting. Storage is freed only when a snapshot-id's unique blocks are unreferenced by any remaining snapshot in the chain.

**Cross-region snapshot copy:** `copy-snapshot` replicates to a destination region with a different snapshot-id. Public/private state does NOT propagate — each region's registry is independent. Encrypted cross-region copy requires a destination-region KMS key. Cross-region copy is billable (per-GB transfer + destination storage) — surface the cost before bulk operations.

## Recent AWS features (2024-2026)

- **Snapshots Archive and Recycling Bin (2024):** EBS Snapshots Archive enables tiering snapshots to a lower-cost archive tier, and the Recycling Bin retains deleted snapshots for recovery. Auditors should verify that the recycling bin retention period is appropriate (too short = permanent data loss on accidental delete; too long = cost accumulation) and that archived snapshots are tracked.
- **Fast Snapshot Restore (FSR) GA:** FSR eliminates initialization latency on restored volumes. Auditors should verify that FSR is enabled only where needed (it has a significant per-zone cost) and that FSR zones match the application's deployment zones.
- **io2 Block Express GA (2024):** io2 Block Express volumes support up to 256,000 IOPS and 4,000 MB/s throughput. Auditors should verify that high-performance workloads use io2 Block Express rather than over-provisioning gp3.
- **EBS default encryption at account level:** Auditors should verify that account-level default encryption is enabled — this prevents creation of unencrypted volumes even when the caller forgets the encryption flag.

## Domain

AWS CloudOps / EBS Storage Security & Cost Optimisation.

## AWS documentation

- **Amazon EBS User Guide** — https://docs.aws.amazon.com/ebs/latest/userguide/what-is-ebs.html
- **Security in Amazon EBS** — https://docs.aws.amazon.com/ebs/latest/userguide/security.html
- **Amazon EC2 API Reference** (covers EBS API) — https://docs.aws.amazon.com/AWSEC2/latest/APIReference/
- **AWS CLI Command Reference: ec2** (covers EBS CLI) — https://docs.aws.amazon.com/cli/latest/reference/ec2/
- **Archive Amazon EBS snapshots** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/snapshot-archive.html
