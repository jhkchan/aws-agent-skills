# Error Handling (load on demand) — EBS Volume Optimizer

Error-handling deep dives and API failure tables, moved verbatim from SKILL.md.


---

## Error handling — CLI and data-source failures (moved from SKILL.md)

## Error handling — CLI and data-source failures

### CloudWatch metric failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-metric-statistics` returns empty `Datapoints` for VolumeQueueLength | `len(Datapoints) == 0` | Verdict: `NEED_MORE_INFO`. Reason: "Volume may be detached or recently created. No I/O signal." |
| `VolumeConsumedReadWriteOps` absent on io1/io2 | `list-metrics` returns no match | Fall back to `VolumeReadOps + VolumeWriteOps`; mark IOPS recommendation as MEDIUM confidence. |
| `BurstBalance` absent on gp2 | Metric not published for gp2 volumes < 1 TB in some cases | Cannot assess burst credit exhaustion. Proceed with type migration recommendation based on per-GB savings alone; note BurstBalance data unavailable. |
| CloudWatch API throttling | Exit code non-zero, stderr contains "Throttling" | Retry with exponential backoff (`--max-attempts 5`). |

### EC2 API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-volumes` returns `InvalidVolume.NotFound` | API error | Volume does not exist. Skip entirely. |
| `modify-volume` fails with `InvalidVolumeModification` | API error | Another modification is in progress. Wait for `ModificationState = completed`, retry. |
| `modify-volume` fails with `VolumeModificationRateExceeded` | API error | Too many modifications in a short window. Wait 5 minutes, retry. |
| `modify-volume` for size decrease fails | API error | Size decrease is NOT supported via standard API. Surface as a higher-effort remediation (create new smaller volume, copy data, swap). |
| `modify-snapshot-tier` fails with `InvalidSnapshot.NotFound` | API error | Snapshot does not exist or has been deleted. Skip; update snapshot inventory. |
| `describe-fast-snapshot-restores` returns empty | `len(FastSnapshotRestores) == 0` | No FSR configured — this is GOOD. No FSR dimension finding. |

### DLM / AWS Backup failures

| Failure mode | Detection | Handling |
|---|---|---|
| `dlm get-lifecycle-policies` returns empty | `len(Policies) == 0` | No DLM policies exist in the account. Surface snapshot governance as OPPORTUNITY_FOUND on any volume with snapshots. |
| `backup list-backup-plans` returns empty | `len(BackupPlansList) == 0` | No AWS Backup plans. Do NOT block — DLM may be the right tool for EBS-only governance. |
| DLM policy creation fails with `AccessDeniedException` | API error | The role lacks `dlm:CreateLifecyclePolicy`. Surface the IAM requirement in MIGRATION_STEPS. |

---

## Error handling — procedure-level optimization failures (moved from SKILL.md)

## Error handling — procedure-level optimization failures

These branches complement the CLI/data-source table above. Each entry
describes what to do when an optimisation step itself fails — not when
a CLI call errors, but when the migration *cannot proceed safely*.

- **If `modify-volume` fails with `VolumeModificationRateExceeded`:**
  The account has exceeded the volume-modification throughput quota
  (default 500 modifications per account per region rolling window, with
  additional caps per-volume-type). Detection:
  `aws ec2 describe-volumes-modifications --filters Name=volume-id,
  Values=<id>` shows the prior modification still `modifying`. Do NOT
  retry immediately — retries count against the same quota. Remediation:
  (a) queue the modification with exponential backoff (start 60s, max
  600s); (b) for fleet migrations, sequence modifications with at least
  60s spacing and batch by ≤50 volumes per window; (c) request a quota
  increase via `service-quotas request-service-quota-increase
  --service-code ebs --quota-code L-<ID>`. Surface as `VERDICT:
  RATE_LIMITED` with retry-after and queue depth.

- **If gp2→gp3 migration is blocked because the attached instance type
  does not support gp3 (older generation, e.g., t2.micro, m1.small):**
  Detection: `aws ec2 describe-volume-status --volume-ids <id>` returns
  no error but the `modify-volume` API call returns
  `UnsupportedVolumeType`. The instance itself does not gate gp3 — but
  Nitro-only instance types gate certain IOPS/throughput ceilings.
  Remediation: (a) check the instance family in
  `aws ec2 describe-instances`; (b) for non-Nitro instances, the gp3
  baseline (3000 IOPS / 125 MB/s) still works but gp3's higher tiers
  (up to 16000 IOPS) require a Nitro instance; (c) if the workload
  needs the higher tier, plan an instance family migration BEFORE the
  volume migration. Do NOT migrate to gp3 with IOPS > 3000 on a
  non-Nitro instance — the IOPS will silently cap.

- **If io1→gp3 migration changes IOPS characteristics in a way the
  workload cannot tolerate:** io1 provides dedicated IOPS with strict
  latency guarantees; gp3 uses a credit-bucket model where sustained
  burst IOPS can be throttled after the burst credit is exhausted.
  Detection: before migration, check CloudWatch `VolumeConsumedReadWriteOps` against the io1 provisioned IOPS — if the p99
  exceeds the gp3 baseline (3000) for > 5 minutes per day, gp3 may
  throttle. Remediation: provision gp3 with explicit IOPS >= io1
  provisioned IOPS (up to 16000), OR keep io1/io2 for that volume.
  Surface as `VERDICT: IOPS_DEGRADE_RISK` with the p99 vs gp3 baseline
  delta and the gp3 provisioned-IOPS cost differential.

- **If the volume is in `error` or `in-use` state that blocks
  modification:** A volume in `error` state cannot be modified — it
  must be snapshotted and recreated. Detection:
  `aws ec2 describe-volumes --volume-ids <id> --query
  'Volumes[].State'`. Remediation: (a) for `error` state, create a
  snapshot (`create-snapshot`), create a new gp3 volume from the
  snapshot, detach the old volume (`detach-volume`), attach the new
  one (`attach-volume`); this requires an instance stop for the
  detach/attach window. (b) For `in-use` blocking modifications, note
  that gp2→gp3 type changes are live (no stop required) but
  size+type+IOPS changes together may require stop on some instance
  families — check the modification matrix in AWS docs.

- **If the instance cannot be stopped (production-critical, no
  maintenance window, no ASG):** Some migrations require instance stop
  (e.g., certain instance-family-gated IOPS, or re-attaching a restored
  volume). Remediation: defer the migration until a maintenance window
  OR migrate via a blue/green pattern (snapshot → new volume → attach
  to a replacement instance behind an ALB → shift traffic). Surface as
  `VERDICT: STOP_BLOCKED — schedule maintenance window or use blue/
  green replacement`.
