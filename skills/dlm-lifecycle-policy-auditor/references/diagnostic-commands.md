# DLM Lifecycle Policy Auditor — diagnostic commands (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Pre-flight: data collection gate — command listings (moved from SKILL.md)


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

