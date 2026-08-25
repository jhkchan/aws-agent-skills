# DLM Lifecycle Policy Auditor — advanced patterns (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Step 0: Expert knowledge — non-obvious DLM behaviors (moved from SKILL.md)


These behaviors are easy to misjudge without operational DLM experience.
Each changes a verdict if ignored:

- **DLM has no native "last run" indicator in the policy object.** The
  policy object exposes `DateCreated`, `DateModified`, and `LastModifiedBy`
  — none of which tell you whether the policy executed. A policy can be
  `ENABLED` and silently failing for months (broken service role, missing
  KMS decrypt, invalid Cron) with no signal in `get-lifecycle-policy`. The
  ONLY ground-truth execution signal is the `aws:dlm:lifecycle-policy-id`
  tag on the snapshots themselves. Always cross-check with
  `describe-snapshots` before declaring a policy OK.

- **`CronExpression` must be 6-field (with year), not 5-field.** Standard
  Unix cron is `min hour day month weekday` (5 fields). DLM REQUIRES
  `min hour day month weekday year` (6 fields) — a 5-field cron like
  `0 5 * * ?` is rejected at `CreateLifecyclePolicy` with
  `ValidationException`. The year field is required and commonly missed by
  teams migrating from cron tooling. Valid alternative: use
  `CreateRule.Interval` + `CreateRule.IntervalUnit`
  (e.g., `Interval: 24, IntervalUnit: HOURS`). A policy created via console
  that "lost" its Cron field on update is a silent no-op.

- **`CrossRegionCopyTargets` re-encrypts with the DESTINATION region's
  default EBS encryption key, NOT the source key.** KMS keys are regional —
  DLM cannot copy the source CMK ARN across regions. If you want a specific
  CMK in the DR region, you must set
  `CrossRegionCopyTargets[].EncryptionConfiguration.EncryptedKeyId`. Without
  it, the DR snapshot uses the destination's default EBS encryption setting —
  which is `false` (unencrypted) in many DR regions that were never
  production-hardened. This is a silent data-at-rest gap that the policy
  object does not surface.

- **`CopyTags: false` (the default) drops ALL source volume tags from the
  snapshot EXCEPT `Name` and `aws:dlm:*` tags.** This breaks downstream
  automation that filters snapshots by tag (cost allocation, cleanup
  scripts, restore scripts). `CopyTags: true` is almost always correct for
  production policies. A policy with `CopyTags: false` or no CopyTags field
  is silently losing attribution metadata on every snapshot.

- **The per-volume snapshot quota is 1,000 snapshots.** A policy with
  `RetainRule.Count: 1000` on a volume that other policies or manual
  snapshots also target will hit the per-volume cap. DLM does NOT delete
  the oldest snapshot to make room — it silently stops creating new ones.
  The error surfaces only in CloudTrail (`SnapshotCreationPerVolumeRateExceeded`).
  Treat `Count >= 1000` as a CONFIG_GAP quota risk.

- **DLM service role breakage is invisible in the policy object.** DLM
  assumes `AWSDataLifecycleManagerServiceRole` (with attached
  `AWSDataLifecycleManagerServiceRole` policy and `dlm-service-role` trust)
  to call `ec2:CreateSnapshot` and `kms:Decrypt`. If the role is deleted,
  its trust policy is revoked, or its inline/managed policy loses the
  `ec2:CreateSnapshot` action, the policy remains `State: ENABLED` but
  every scheduled run fails. The error appears ONLY in CloudTrail
  (`AccessDenied` on `ec2:CreateSnapshot`). This is the #1 silent-failure
  mode for DLM and the reason Step 1 (existence + execution) outranks
  every other check.

- **`TargetTags` matching is case-SENSITIVE and exact.** A policy targeting
  `Environment: production` will NOT match a volume tagged
  `Environment: Production` (capital P). Teams migrating from shell scripts
  that did case-insensitive matching routinely miss volumes. A policy with
  valid-looking `TargetTags` and zero matching volumes is functionally
  identical to empty `TargetTags` — both are MISCONFIGURED.

- **`ResourceTypes: INSTANCE` snapshots ALL attached volumes as a set.** An
  `EBS_SNAPSHOT_POLICY` with `ResourceTypes: ["VOLUME", "INSTANCE"]` will
  double-snapshot any instance volume (once as a volume target, once as an
  instance target), doubling cost and hitting the per-volume quota faster.
  Mixing the two is allowed but almost always unintended.

- **`CreateRule.Interval` minimum is 12 HOURS.** Sub-12-hour intervals are
  rejected by the API. For more frequent backups, use a CronExpression,
  but DLM still enforces a minimum 1-hour gap between snapshots of the same
  volume. A policy requesting `Interval: 1, IntervalUnit: HOURS` is invalid
  and will not create.

- **`FastRestoreRule` is expensive: ~$0.75 per AZ-hour per snapshot.** A
  single snapshot with FastRestore enabled in 3 AZs costs ~$54/day.
  FastRestore should be enabled ONLY for snapshots that will be rapidly
  attached (boot volumes for autoscaling, hot DB restores). Enabling
  FastRestore on every snapshot is a common cost-overrun pattern — flag as
  CONFIG_GAP if the policy has FastRestoreRule on a non-boot-volume policy.

- **`ShareRules[].TargetAccounts[]` is cross-account SHARING, not DR.**
  Shared snapshots remain in the SOURCE region; the recipient account must
  explicitly copy them to another region if DR is the goal. A team that
  configures ShareRules expecting DR behavior has a false sense of safety.
  Only `CrossRegionCopyTargets` provides cross-region DR.

- **`ExecutionHandler` / `ExecutionHandlerRole` are legacy fields, NOT in
  the modern DLM API.** Older documentation references these, but the
  current API uses implicit service-role assumption. Do NOT classify a
  modern policy as MISCONFIGURED for lacking `ExecutionHandler` — it is not
  a valid field. This is a false-positive trap for auditors migrating from
  2018-era DLM tooling.

- **`update-lifecycle-policy` does NOT validate `--execution-role-arn`.**
  The API accepts any ARN and returns success, even if the role doesn't
  exist, lacks trust policy, or has no `ec2:CreateSnapshot` permission.
  Validation happens only at the next scheduled execution — a typo in the
  ARN produces a "successfully updated" policy that silently fails on the
  next run. Always verify the role via `aws iam get-role` after any
  `update-lifecycle-policy` call, not just at creation.

- **Customer-managed IAM policy versioning can silently change DLM
  behavior.** In regulated environments, teams often replace the
  AWS-managed `AWSDataLifecycleManagerServiceRole` policy with a
  customer-managed policy for tighter control. Customer-managed policies
  keep up to 5 versions; a least-privilege sweep that creates a v2
  (stripping `kms:Decrypt` as "overly broad") without promoting it to
  default leaves v1 active — DLM keeps working. Weeks later someone sets v2
  as default, and encrypted-volume snapshots start failing with
  `AccessDenied` in CloudTrail despite zero DLM configuration changes.
  `get-lifecycle-policy` shows nothing; the policy is ENABLED and
  unchanged. Detect via `aws iam get-policy-version --policy-arn <arn>
  --version-id v2`.

- **DLM publishes NO CloudWatch metrics.** There is no `AWS/DLM` namespace
  — no `ExecutionCount`, no `ErrorRate`, no `SnapshotCreated` metric.
  CloudWatch alarms and dashboards built on DLM metrics are structurally
  impossible. The only two observability signals are: (a) CloudTrail error
  events (`AccessDenied` on `ec2:CreateSnapshot`) and (b) the
  presence/absence of `aws:dlm:lifecycle-policy-id`-tagged snapshots. Any
  "health dashboard" claiming to monitor DLM via CloudWatch metrics is
  showing empty data — verify the signal source.


## Edge-case handling (moved from SKILL.md)


- **Partially malformed policy.** If the policy JSON parses but individual
  fields are malformed (e.g., `Schedules` is not an array, `CreateRule` is
  a string instead of an object), classify the valid dimensions normally and
  emit an ERROR note for each malformed field. Do NOT classify the entire
  policy as ERROR when only one schedule is broken — the valid schedules
  may still produce findings.

- **Multi-schedule policy.** A policy may have multiple schedules (e.g.,
  daily + weekly + monthly with different retention). Evaluate EACH schedule
  independently against Steps 4-9. The verdict aggregates the worst finding
  across all schedules — one broken schedule MISCONFIGURES the whole policy.

- **Account with policies but none ENABLED.** If `get-lifecycle-policies`
  returns policies but ALL are `State: DISABLED`, the workload verdict is
  NO_POLICY (Step 1) — a disabled policy does not cover the workload. The
  per-policy verdict for each disabled policy is MISCONFIGURED (Step 2).

- **INSTANCE policy vs VOLUME policy.** An `EBS_SNAPSHOT_POLICY` with
  `ResourceTypes: ["INSTANCE"]` snapshots all volumes attached to matching
  instances as a consistent set. This is valid. Flag only if BOTH `VOLUME`
  and `INSTANCE` are present (double-snapshot risk — Step 9 cost note).

- **Cross-account share as DR substitute.** `ShareRules` without
  `CrossRegionCopyTargets` is NOT DR — shared snapshots remain in the source
  region. If a team claims the share is for DR, flag Step 7 (CONFIG_GAP)
  and explain the distinction.

- **Policy with valid structure but zero execution history.** If
  `describe-snapshots` returns zero snapshots with the policy's tag, the
  policy has never run OR has been silently failing. Output OK only if
  execution is verified; otherwise flag as a verification item (the policy
  is structurally clean but unproven).


## Deep reference: DLM internals (moved from SKILL.md)


### Silent-failure modes (why State: ENABLED proves nothing)

DLM's policy object (`get-lifecycle-policy` response) contains `State`,
`DateCreated`, `DateModified`, `LastModifiedBy`, and `PolicyDetails`. It does
NOT contain any execution metadata — no "last run time", no "last success",
no "error count". A policy can be ENABLED and failing for the entire account
lifetime with zero signal in the policy object. The three silent-failure
modes:

1. **Service role deleted/modified.** DLM assumes
   `AWSDataLifecycleManagerServiceRole` to call `ec2:CreateSnapshot`. If the
   role is gone, every scheduled run fails with `AccessDenied` in CloudTrail.
   The policy stays ENABLED.
2. **KMS decrypt missing.** If the source volume is encrypted with a CMK and
   the service role lacks `kms:Decrypt` on that key, snapshot creation fails.
   The policy stays ENABLED.
3. **Target tag drift.** If volumes are retagged (case change, key rename)
   such that none match `TargetTags`, the policy runs on schedule and
   snapshots nothing. The policy stays ENABLED.

The ONLY ground-truth signal is the `aws:dlm:lifecycle-policy-id` tag on
snapshots. Always verify via `describe-snapshots`.

### CronExpression syntax (6-field requirement)

DLM CronExpression requires exactly 6 fields: `Minutes Hours Day-of-month
Month Day-of-week Year`. The Year field is mandatory and commonly missed.
Valid wildcards: `*` (any), `?` (no specific value, for Day-of-month or
Day-of-week when the other is specified), `L` (last), `#` (nth weekday). A
5-field cron is rejected at `CreateLifecyclePolicy` but may persist in
policies edited via tooling that does not validate. Example valid cron for
daily 05:00 UTC: `0 5 * * ? *` (note the trailing year field).

### Cross-region copy encryption flow

When DLM copies a snapshot cross-region, it CANNOT use the source KMS key
(keys are regional). The copy flow:
1. DLM reads the source snapshot (requires `kms:Decrypt` on the source key
   via the service role).
2. DLM creates a new snapshot in the destination region.
3. The destination snapshot is encrypted with EITHER the
   `EncryptionConfiguration.CmkArn` (if specified) OR the destination
   region's default EBS encryption key (if default encryption is enabled) OR
   left UNENCRYPTED (if neither is set).

Step 3 is the silent gap: if `CmkArn` is absent and the destination region's
default EBS encryption is `false`, the DR snapshot is unencrypted. Always
specify `CmkArn` explicitly.

### Per-volume snapshot quota

AWS enforces a per-volume limit of 1,000 snapshots (soft quota, raisable via
`service-quotas`). This quota counts ALL snapshots of the volume, regardless
of which policy or manual process created them. When the quota is hit, DLM
does NOT delete the oldest snapshot to make room — it stops creating new
ones, and the error surfaces only in CloudTrail
(`SnapshotCreationPerVolumeRateExceeded`). A policy with `RetainRule.Count: 1000`
is one manual snapshot away from the cliff.

### Service-role trust policy

The `AWSDataLifecycleManagerServiceRole` trust policy must allow
`ec2:CreateSnapshot`, `ec2:CreateTags`, `ec2:DeleteSnapshot`, `ec2:Describe*`,
and (for encrypted volumes) `kms:Decrypt`/`kms:DescribeKey` on the source
key. If the role's inline policy is narrowed (e.g., by a least-privilege
sweep that removed `kms:Decrypt`), DLM silently fails on encrypted volumes.
This is a common side-effect of IAM hygiene campaigns.


## Recent AWS features 2024-2026 (moved from SKILL.md)


- **DLM policy type expansion (2024-2025):** DLM now supports additional policy types beyond EBS snapshots, including policies for EBS-backed AMIs. Auditors should verify that all policy types are accounted for — an AMI lifecycle policy may run alongside snapshot policies and create redundant or conflicting schedules.
- **Cross-region copy improvements (2024):** Enhanced cross-region copy with tag preservation and encryption key mapping. Auditors should verify that cross-region copy policies correctly map KMS keys (source-region key ARNs will not work in the destination region).
- **Policy schedule improvements:** DLM now supports more flexible schedule configurations including variable retention tiers. Auditors should verify that retention tiers are compliant with backup policies.

