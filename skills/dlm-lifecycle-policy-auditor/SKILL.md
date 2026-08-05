---
name: dlm-lifecycle-policy-auditor
description: >-
  Audits AWS Data Lifecycle Manager (DLM) EBS snapshot lifecycle policies for
  coverage gaps and silent-failure modes: disabled policies, empty tag/resource
  targets, invalid Cron schedules, weak or missing retention rules, absent
  cross-region copy (DR gap), CopyTags metadata loss, per-volume snapshot
  quota risk, and the DLM service-role breakage that silently halts backups.
  Emits a deterministic verdict (NO_POLICY | MISCONFIGURED | CONFIG_GAP | OK)
  per policy or workload with enumerated findings and specific CLI remediation.
  Use when reviewing DLM EBS snapshot policies, checking backup coverage,
  validating retention/DR posture, or diagnosing why snapshots stopped
  appearing.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline policy-document classification.
  Live-account audits use aws dlm get-lifecycle-policies,
  aws dlm get-lifecycle-policy, aws ec2 describe-snapshots, and
  aws ec2 describe-volumes (AWS CLI v2, SSO or key-based credentials).
keywords:
  - DLM
  - Data Lifecycle Manager
  - EBS snapshot
  - lifecycle policy
  - backup
  - retention
  - cross-region copy
  - disaster recovery
  - snapshot policy
  - CronExpression
  - RetainRule
  - CreateRule
  - TargetTags
  - CopyTags
  - FastRestoreRule
  - CrossRegionCopyTargets
  - AWSDataLifecycleManagerServiceRole
  - snapshot quota
  - backup audit
  - DR gap
tags: [dlm, storage, ebs, snapshots, backup, retention, disaster-recovery, lifecycle, audit]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Storage
  verdict_shape: "NO_POLICY | MISCONFIGURED | CONFIG_GAP | OK"
  when_to_use: >-
    Auditing DLM EBS snapshot lifecycle policies for coverage and correctness,
    diagnosing why snapshots stopped appearing, validating retention/DR posture,
    checking cross-region copy configuration, or confirming a workload has
    automated EBS backup coverage before production deployment.
  activation_triggers:
    - "audit this DLM lifecycle policy"
    - "why did my EBS snapshots stop"
    - "is my backup policy enabled"
    - "check DLM retention"
    - "DLM cross-region copy gap"
    - "is DLM working"
    - "EBS snapshot coverage"
    - "lifecycle policy disabled"
    - "DLM silent failure"
    - "audit EBS backup posture"
  invocation_schema: >-
    Input: either (a) a DLM lifecycle policy JSON document (from
    get-lifecycle-policy), optionally paired with account-level context
    (list of volumes, list of all policies), OR (b) a workload/account
    identifier for live-account coverage audit. Output: deterministic
    POLICY/VERDICT/REASON/FINDINGS/REMEDIATION block per policy or workload,
    where VERDICT ∈ {NO_POLICY, MISCONFIGURED, CONFIG_GAP, OK}.
---

# DLM Lifecycle Policy Auditor

## Mindset

**One-line takeaway:** a DLM policy with `State: ENABLED` proves nothing
about whether backups are actually running — three layers can fail silently
beneath it (empty tag targets, broken service role, invalid Cron), and the
policy object surfaces none of them.

DLM automates EBS snapshot creation, retention, and cross-region copy on a
schedule. It looks deceptively simple in the console. The danger is that
**DLM has no native health indicator in the policy object**: `State: ENABLED`
means "the policy is registered", not "it has ever executed successfully."
The three silent-failure modes that every auditor must check:

- **Disabled policy.** `State: DISABLED` — the policy is registered but
  creates zero snapshots. Operators disable a policy to "pause for
  maintenance" and forget to re-enable. No alert fires.
- **Empty/broken target set.** `TargetTags: []` or `ResourceTypes: []` means
  zero volumes match. The policy runs on schedule and snapshots nothing.
- **Service-role breakage.** DLM assumes `AWSDataLifecycleManagerServiceRole`
  to call `ec2:CreateSnapshot`. If that role is deleted, its trust policy is
  revoked, or it lacks `kms:Decrypt` on the source key, the policy stays
  `ENABLED` but CloudTrail logs `AccessDenied` on every scheduled run. The
  policy object never reflects this.

The only ground-truth signal that a policy actually created snapshots is
`aws ec2 describe-snapshots --filters "Name=tag:aws:dlm:lifecycle-policy-id,Values=<id>"`
— the `aws:dlm:lifecycle-policy-id` tag is auto-applied by DLM to every
snapshot it creates. A policy that has never produced a tagged snapshot has
either never run or has been silently failing since creation.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| Account has zero enabled DLM policies covering the workload's volumes | **NO_POLICY** | Step 1 |
| `State: DISABLED` (policy registered but not running) | **MISCONFIGURED** | Step 2 |
| `TargetTags: []` or `ResourceTypes: []` (zero targets) | **MISCONFIGURED** | Step 3 |
| Any `Schedule.CreateRule` missing or invalid (no Cron, no Interval, 5-field cron) | **MISCONFIGURED** | Step 4 |
| Any `Schedule.RetainRule` entirely absent (unbounded retention) | **MISCONFIGURED** | Step 5 |
| `RetainRule.Count: 1` or `RetainRule.Interval < 7 days` (no recovery history) | **CONFIG_GAP** | Step 6 |
| No `CrossRegionCopyTargets` for any schedule (no DR) | **CONFIG_GAP** | Step 7 |
| `CopyTags: false` or absent (metadata/automation loss) | **CONFIG_GAP** | Step 8 |
| `RetainRule.Count >= 1000` (per-volume snapshot quota risk) | **CONFIG_GAP** | Step 9 |
| Enabled + valid schedule + sensible retention + DR + CopyTags | **OK** | Step 10 |

See the ordered steps below for edge cases. Deep DLM internals (service-role
flow, snapshot-tag conventions, Cron syntax quirks) are in the
[Deep reference](#deep-reference-dlm-internals) section at the end.

## Pre-flight: data collection gate (run before classification)

DLM's silent-failure modes mean the policy object alone is insufficient for a
trustworthy audit. Before classifying, gather ground truth:

**Account-wide coverage audit (Step 1 scope):**
1. `aws dlm get-lifecycle-policies` — list every policy. Note the count and
   each `State`. An account with `[]` (zero policies) hosting production EBS
   volumes is the clearest NO_POLICY finding possible.
2. `aws ec2 describe-volumes --filters "Name=tag-key,Values=<workload-tag>"` —
   enumerate the volumes the workload depends on. If the count is zero, the
   workload has no volumes to protect (skip DLM audit) OR the tag filter is
   wrong (a different NO_POLICY-shaped finding).

**Per-policy execution verification (most-skipped check):**
3. `aws ec2 describe-snapshots --filters "Name=tag:aws:dlm:lifecycle-policy-id,Values=<id>" --query 'Snapshots[*].{Id:SnapshotId,Start:StartTime}' --output table` —
   the canonical "did this policy ever actually run?" signal. A policy with
   `State: ENABLED` and zero tagged snapshots has either never executed or
   has been silently failing since creation. **Do NOT trust `State: ENABLED`
   alone** — it proves registration, not execution.
4. `aws iam get-role --role-name AWSDataLifecycleManagerServiceRole` — confirm
   the service role exists. A missing or renamed role is the #1 silent-failure
   mode; the policy stays ENABLED but every scheduled run fails with
   `AccessDenied` in CloudTrail.

**Live-account pre-flight checks (skip if doing offline policy-doc audit):**
5. Verify CloudTrail is logging `ec2:CreateSnapshot` events. DLM failures
   surface there, not in the DLM API. Without CloudTrail signal, a silently
   failing policy is invisible.
6. For cross-region copy schedules, verify the destination region's default
   EBS encryption setting: `aws ec2 get-ebs-encryption-by-default --region <dr-region>`.
   If `false` and the schedule has no explicit `EncryptionConfiguration`,
   DR snapshots land unencrypted.

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious DLM behaviors that change classification

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

### Step 1: Workload coverage — does ANY enabled policy protect these volumes?

**Scope:** apply this step when the input is an account or workload (not a
single policy document). When auditing a single policy object, skip to Step 2.

- If `get-lifecycle-policies` returns `[]` (zero policies in the account) AND
  the account hosts EBS volumes tagged for production → **NO_POLICY**. This is
  the most severe finding: zero automated backup exists. The verdict is
  NO_POLICY regardless of any other consideration.
- If policies exist but NONE is `State: ENABLED` AND targets tags that
  intersect the workload's volume tags → **NO_POLICY** for that workload. A
  disabled policy targeting the workload's tags does not cover it; an enabled
  policy targeting unrelated tags does not cover it.
- Verify intersection: list the workload's volumes
  (`describe-volumes --filters "Name=tag-key,Values=<tag>"`), collect their
  tag sets, and confirm at least one ENABLED policy's `TargetTags` is a
  subset of (or matches) those tag sets. Case-sensitive exact match.

NO_POLICY is the highest-severity verdict — it means a workload has no
automated EBS backup at all, and every volume is one misconfiguration away
from permanent data loss on deletion.

### Step 2: State check — is the policy actually running?

- `State: DISABLED` → **MISCONFIGURED**. The policy is registered but creates
  zero snapshots. Operators disable policies for maintenance and forget to
  re-enable; console-driven workflows sometimes leave a policy DISABLED after
  a tag edit. No CloudWatch alarm fires on this transition.
- `State: ENABLED` → proceed. Note: ENABLED proves registration only — it
  does NOT prove execution. Continue to Step 3.

### Step 3: Target coverage — can the policy match any volume?

- `PolicyDetails.TargetTags: []` (empty array) → **MISCONFIGURED**. With no
  tag filters, no volumes match (DLM does NOT default to "all volumes"). The
  policy runs on schedule and snapshots nothing.
- `PolicyDetails.ResourceTypes: []` (empty) → **MISCONFIGURED**. For an
  EBS_SNAPSHOT_POLICY, ResourceTypes must include `VOLUME` and/or `INSTANCE`.
- `TargetTags` present but matches zero volumes in the account (verify via
  `describe-volumes --filters`) → **MISCONFIGURED** with a note that the tags
  may be case-mismatched. A valid-looking tag set that matches nothing is
  functionally identical to empty TargetTags.

### Step 4: Schedule validity — can the policy create snapshots on schedule?

For each entry in `PolicyDetails.Schedules[]`:

- `CreateRule` entirely absent → **MISCONFIGURED**. No creation trigger.
- `CreateRule.CronExpression` is 5-field (e.g., `0 5 * * ?`) →
  **MISCONFIGURED**. DLM requires 6-field cron (with year). A 5-field cron
  is rejected at creation but may persist if the policy was edited via an
  older tool that did not validate.
- `CreateRule` has neither `CronExpression` nor `Interval` + `IntervalUnit`
  → **MISCONFIGURED**. At least one creation trigger is required.
- `CreateRule.Interval < 12` with `IntervalUnit: HOURS` → MISCONFIGURED
  (minimum 12-hour interval enforced by API).

### Step 5: Retention validity — is retention bounded?

For each `Schedule`:

- `RetainRule` entirely absent → **MISCONFIGURED**. Without a RetainRule,
  DLM never deletes snapshots — retention is unbounded. This is not "keep
  forever" (a deliberate choice); it is a missing field that will hit the
  per-volume snapshot quota (1,000) and then silently stop creating new
  snapshots. The oldest is NOT deleted to make room.
- `RetainRule` present but both `Count` and `Interval`/`IntervalUnit` are
  null/absent → **MISCONFIGURED**. The rule exists but specifies no bound.

### Step 6: Retention strength — is recovery history adequate?

- `RetainRule.Count: 1` → **CONFIG_GAP**. A single snapshot means zero
  recovery history — any corruption in the most recent snapshot is
  unrecoverable. Minimum recommended Count is 7 (one week of daily snapshots)
  for production volumes.
- `RetainRule.Interval < 7` with `IntervalUnit: DAYS` → **CONFIG_GAP**. Less
  than 7 days of retention is inadequate for most RPO/RTO targets. Note the
  workload's actual RPO requirement before flagging — a test environment may
  legitimately retain 3 days.

### Step 7: DR coverage — is there a cross-region copy?

- No `CrossRegionCopyTargets` on any schedule (or the array is empty) →
  **CONFIG_GAP**. Single-region snapshots mean a regional outage or the
  loss of the primary region destroys all backups along with the primary.
  Cross-region copy is the minimum DR posture for any production volume.
- `CrossRegionCopyTargets` present but `EncryptionConfiguration` absent AND
  the destination region's default EBS encryption is `false` → CONFIG_GAP
  (unencrypted DR snapshots). This requires knowing the destination region's
  encryption default — if unknown, flag as a verification item.

### Step 8: Metadata preservation — are tags copied?

- `CopyTags: false` OR `CopyTags` absent (the default) → **CONFIG_GAP**.
  Source volume tags are dropped from the snapshot except `Name` and
  `aws:dlm:*`. This breaks cost-allocation, cleanup, and restore automation
  that filters snapshots by tag. `CopyTags: true` is the correct default for
  production.

### Step 9: Quota and cost risks

- `RetainRule.Count >= 1000` → **CONFIG_GAP**. Approaching the per-volume
  snapshot quota (1,000). When the quota is hit, DLM stops creating new
  snapshots silently — the oldest is NOT deleted. This is a recovery-coverage
  cliff.
- `FastRestoreRule` present on a policy whose TargetTags suggest non-boot
  volumes (e.g., data volumes, not OS volumes) → **CONFIG_GAP** (cost risk).
  FastRestore is ~$0.75/AZ-hour/snapshot and should be reserved for
  rapidly-attached snapshots.

### Step 10: Aggregation — worst finding wins

The final verdict is the **worst** finding across all steps, where
NO_POLICY > MISCONFIGURED > CONFIG_GAP > OK:

```text
verdict = max(step1_finding, step2_finding, ..., step9_finding)
```

If no findings (all dimensions pass), the verdict is **OK**. Note that OK
requires verification that the policy has actually produced snapshots
(Step 1 execution check) — a policy that is structurally clean but has never
executed should be flagged as a verification item, not a clean OK.

## Output format (per policy)

```text
POLICY: <policy-id, or "ACCOUNT/<workload>" for coverage audits>
VERDICT: NO_POLICY | MISCONFIGURED | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [MISCONFIGURED] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — disabled policy with no cross-region copy

```text
POLICY: policy-0abc123456 (production-ebs-daily)
VERDICT: MISCONFIGURED
REASON: Policy State is DISABLED — zero snapshots are being created
regardless of how well-formed the schedules are (Step 2). Additionally, no
cross-region copy is configured (Step 7).
FINDINGS:
  - [MISCONFIGURED] State: DISABLED — policy registered but not running (Step 2)
  - [CONFIG_GAP] No CrossRegionCopyTargets on schedule daily-6am — no DR (Step 7)
  - [CONFIG_GAP] CopyTags absent — source volume tags dropped from snapshots (Step 8)
REMEDIATION:
  1. Re-enable: aws dlm update-lifecycle-policy --policy-id policy-0abc123456 --state ENABLED.
  2. Add a cross-region copy target to the schedule (see Deep reference for
     EncryptionConfiguration syntax).
  3. Set CopyTags: true on the schedule to preserve volume attribution.
  4. Verify execution after re-enabling:
     aws ec2 describe-snapshots --filters "Name=tag:aws:dlm:lifecycle-policy-id,Values=policy-0abc123456".
```

## Edge-case handling

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

## Anti-Patterns — NEVER

- NEVER classify a `State: DISABLED` policy as anything other than
  MISCONFIGURED (or NO_POLICY for the workload it was supposed to cover).
  A disabled policy creates zero snapshots — "the policy exists" is not
  coverage. This is the most common false-OK in DLM audits.

- NEVER declare a policy OK based on `State: ENABLED` alone. ENABLED proves
  registration, not execution. The policy object has no "last run" field.
  Always cross-check with `describe-snapshots --filters "Name=tag:aws:dlm:lifecycle-policy-id,Values=<id>"`
  before OK. A policy that has never produced a tagged snapshot is either
  brand-new or silently failing — neither is OK.

- NEVER treat empty `TargetTags` as "all volumes". DLM does NOT default to
  all volumes when TargetTags is empty — it matches ZERO volumes. A policy
  with `TargetTags: []` is a no-op, not a catch-all. Classify as
  MISCONFIGURED (Step 3).

- NEVER accept a 5-field `CronExpression`. DLM requires 6-field cron
  (min hour day month weekday YEAR). A 5-field cron is rejected at creation
  but may persist from older tooling. Treat any 5-field cron as
  MISCONFIGURED (Step 4). The year field is mandatory.

- NEVER treat `ShareRules` as a substitute for `CrossRegionCopyTargets`.
  Shared snapshots stay in the source region. Only cross-region copy
  provides DR. A policy with ShareRules but no CrossRegionCopyTargets still
  has the Step 7 CONFIG_GAP finding.

- NEVER assume `CrossRegionCopyTargets` encrypts with the source KMS key.
  KMS keys are regional — DLM cannot copy the source CMK. Without an
  explicit `EncryptionConfiguration.EncryptedKeyId`, the DR snapshot uses
  the destination region's default EBS encryption setting (often `false`).
  Verify the destination region's encryption default before declaring DR
  snapshots encrypted.

- NEVER flag `RetainRule` absence as "intentional keep-forever policy."
  Missing RetainRule is a field omission, not a deliberate retention
  strategy. DLM will hit the per-volume snapshot quota (1,000) and then
  silently stop creating new snapshots — the oldest is NOT deleted. This is
  MISCONFIGURED, not OK.

- NEVER recommend deleting a DLM policy as remediation without first
  confirming what snapshots it manages. Deleting a policy does NOT delete
  its existing snapshots — they become orphaned (still billed, no longer
  rotated). Use `aws dlm delete-lifecycle-policy --policy-id <id>` only
  after confirming no workload depends on the policy's snapshot stream.

- NEVER conflate `ResourceTypes: ["VOLUME", "INSTANCE"]` with comprehensive
  coverage. Mixing both double-snapshots instance-attached volumes (once
  as a VOLUME target, once as an INSTANCE target), doubling cost and
  accelerating quota exhaustion. This is a CONFIG_GAP cost finding.

- NEVER treat the absence of `ExecutionHandler` / `ExecutionHandlerRole`
  as a misconfiguration. These are legacy fields from 2018-era DLM and are
  NOT in the modern API. The modern API uses implicit service-role
  assumption. Flagging their absence is a false positive.

- NEVER assume the service role's permissions are stable across audits. IAM
  policy drift — from least-privilege sweeps, CloudFormation drift
  detection, or Terraform applies that narrow `ec2:*`/`kms:*` scopes — can
  silently strip `kms:Decrypt` or `ec2:CreateSnapshot` from the role's
  policy without any change to the DLM policy itself. DLM continues to show
  `State: ENABLED` but every encrypted-volume snapshot fails with
  `AccessDenied` in CloudTrail. Check role permissions
  (`aws iam get-role-policy`, `aws iam list-attached-role-policies`) as part
  of every audit — not just role existence.

- NEVER assume `TargetTags` matching is case-insensitive. DLM tag matching
  is EXACT and case-SENSITIVE. `Environment: production` does not match
  `Environment: Production`. A policy with valid-looking tags that match
  zero volumes (case mismatch) is functionally identical to empty TargetTags.

- NEVER enable `FastRestoreRule` on every snapshot as a "just in case."
  FastRestore costs ~$0.75 per AZ-hour per snapshot. A policy with
  FastRestore on a 3-AZ deployment retaining 30 snapshots costs
  ~$1,600/month. Reserve FastRestore for boot volumes that must attach in
  seconds (autoscaling, rapid DB restore).

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (update-lifecycle-policy, delete-lifecycle-policy), the auditor MUST emit:
  `CONFIRM: About to <action> on policy <id> in account <account>. This
  affects <consequence>. Proceed? (yes/no)` Do NOT execute the CLI command
  until the operator confirms.
- Capture the current policy for rollback:
  `aws dlm get-lifecycle-policy --policy-id <id> --output json > /tmp/<id>-backup-$(date +%s).json`
  BEFORE any modification. DLM policies are not versioned — there is no
  undo without a backup.
- Before re-enabling a DISABLED policy, confirm the service role still
  exists: `aws iam get-role --role-name AWSDataLifecycleManagerServiceRole`.
  Re-enabling a policy whose role was deleted produces a silently-failing
  ENABLED policy — worse than the original DISABLED state because it looks
  healthy.
- Before adding a `CrossRegionCopyTarget`, confirm the destination region
  has default EBS encryption enabled
  (`aws ec2 get-ebs-encryption-by-default --region <dr-region>`) OR specify
  an explicit `EncryptionConfiguration.EncryptedKeyId`. Unencrypted DR
  snapshots are a data-at-rest gap.
- Before tightening `RetainRule.Count` downward, confirm no downstream
  automation depends on the older snapshots being present (restore scripts,
  compliance archives). Reducing Count triggers immediate deletion of
  snapshots beyond the new bound — this is irreversible.
- Prefer additive changes (add a schedule, add a CrossRegionCopyTarget,
  enable CopyTags) over destructive changes (remove a schedule, lower
  retention). Additive changes are reversible and do not risk breaking
  existing snapshot streams.

## Remediation guidance

**Remediation ordering principle:** always prefer additive changes over
destructive changes. Add a CrossRegionCopyTarget (reversible by removing it)
BEFORE reducing retention (which deletes snapshots irreversibly). The safe
sequence for any finding is: (1) back up the policy, (2) apply the additive
fix, (3) verify execution via `describe-snapshots`, (4) only then apply any
destructive change.

### For NO_POLICY — workload has no enabled DLM coverage

1. Identify the workload's volume tag set
   (`describe-volumes --filters "Name=tag-key,Values=<tag>"`).
2. Create a policy targeting those tags:
   `aws dlm create-lifecycle-policy --description "<workload>-ebs-backup" --state ENABLED --execution-role-arn arn:aws:iam::<acct>:role/AWSDataLifecycleManagerServiceRole --policy-details file://policy.json`.
   The `policy.json` must include `PolicyType: EBS_SNAPSHOT_POLICY`,
   `ResourceTypes: ["VOLUME"]`, `TargetTags: [...]`, and at least one
   `Schedule` with `CreateRule` + `RetainRule`.
3. Verify the service role exists before creating the policy (see Pre-flight).
4. After creation, verify execution within the first schedule window via
   `describe-snapshots --filters "Name=tag:aws:dlm:lifecycle-policy-id,Values=<new-id>"`.

### For MISCONFIGURED — State: DISABLED (Step 2)

1. Confirm the service role exists (see Pre-flight).
2. Re-enable:
   `aws dlm update-lifecycle-policy --policy-id <id> --state ENABLED`.
3. Verify execution after the next schedule window via `describe-snapshots`.

### For MISCONFIGURED — empty TargetTags / ResourceTypes (Step 3)

1. Identify the correct tag set from the workload's volumes.
2. Update the policy details:
   `aws dlm update-lifecycle-policy --policy-id <id> --policy-details file://updated-details.json`.
3. Verify volume matching:
   `aws ec2 describe-volumes --filters "Name=tag:<key>,Values=<value>"` —
   the count must be > 0.

### For MISCONFIGURED — invalid Cron / CreateRule (Step 4)

1. Replace the 5-field cron with a 6-field cron (append the year field), OR
   switch to `Interval` + `IntervalUnit`
   (e.g., `Interval: 24, IntervalUnit: HOURS`).
2. Update via `update-lifecycle-policy --policy-details`.

### For MISCONFIGURED — missing RetainRule (Step 5)

1. Add a `RetainRule` with a sensible `Count` (7-30 for daily snapshots) or
   `Interval` + `IntervalUnit` (e.g., `Interval: 30, IntervalUnit: DAYS`).
2. Update via `update-lifecycle-policy --policy-details`.

### For CONFIG_GAP — short retention (Step 6)

1. Increase `RetainRule.Count` to at least 7 (daily) or match the workload's
   RPO/RTO requirement. For compliance-driven workloads, 30-90 days is common.
2. Update via `update-lifecycle-policy --policy-details`.

### For CONFIG_GAP — no cross-region copy (Step 7)

1. Add a `CrossRegionCopyTarget` to each schedule:
   ```json
   "CrossRegionCopyTargets": [{
     "TargetRegion": "us-west-2",
     "EncryptionConfiguration": {"Encrypted": true, "CmkArn": "arn:aws:kms:us-west-2:<acct>:key/<dr-cmk-id>"}
   }]
   ```
2. Specify an explicit `CmkArn` — do NOT rely on the destination region's
   default encryption.
3. Verify DR snapshots after the next copy window:
   `aws ec2 describe-snapshots --region us-west-2 --filters "Name=tag:aws:dlm:lifecycle-policy-id,Values=<id>"`.

### For CONFIG_GAP — CopyTags false/absent (Step 8)

1. Set `CopyTags: true` on each schedule.
2. Update via `update-lifecycle-policy --policy-details`.

### For CONFIG_GAP — quota risk (Count >= 1000) (Step 9)

1. Reduce `RetainRule.Count` below 1000 (e.g., 90-365 depending on RPO).
2. Confirm no other policies or manual snapshots are targeting the same
   volumes (cumulative snapshot count per volume across all sources).

### For OK

1. No remediation required for the current posture.
2. Recommend verifying execution quarterly via `describe-snapshots` (DLM
   silent-failure modes can appear at any time if the service role is edited).
3. For compliance-driven workloads, recommend a periodic CloudTrail alarm on
   `ec2:CreateSnapshot` `AccessDenied` events sourced from the DLM service
   role — this is the earliest signal of service-role breakage.

## Deep reference: DLM internals

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

## Recent AWS features (2024-2026)

- **DLM policy type expansion (2024-2025):** DLM now supports additional policy types beyond EBS snapshots, including policies for EBS-backed AMIs. Auditors should verify that all policy types are accounted for — an AMI lifecycle policy may run alongside snapshot policies and create redundant or conflicting schedules.
- **Cross-region copy improvements (2024):** Enhanced cross-region copy with tag preservation and encryption key mapping. Auditors should verify that cross-region copy policies correctly map KMS keys (source-region key ARNs will not work in the destination region).
- **Policy schedule improvements:** DLM now supports more flexible schedule configurations including variable retention tiers. Auditors should verify that retention tiers are compliant with backup policies.

## Domain

AWS CloudOps / Storage & Backup Resilience (DLM EBS Snapshot Lifecycle).
