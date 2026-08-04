# End-to-end scenario: DLM EBS snapshot lifecycle policy audit

This walkthrough exercises every verdict in the `dlm-lifecycle-policy-auditor`
skill: NO_POLICY, MISCONFIGURED (two variants), CONFIG_GAP (two variants),
and OK. Each scenario shows the input policy/account context, the
classification step that fires, and the resulting VERDICT block.

## Scenario 1 — NO_POLICY (account coverage audit)

**Input:** Account hosts 50 production EBS volumes tagged
`Environment:production`, but `aws dlm get-lifecycle-policies` returns `[]`.

**Classification:** Step 1 fires immediately — zero enabled DLM policies
covering the workload's volumes. This is the highest-severity verdict: no
automated EBS backup exists for any production volume.

**Output:**

```text
POLICY: ACCOUNT/production (50 volumes tagged Environment:production)
VERDICT: NO_POLICY
REASON: Account has zero DLM lifecycle policies (get-lifecycle-policies
returned []) despite hosting 50 production EBS volumes — no automated EBS
backup exists (Step 1).
FINDINGS:
  - [NO_POLICY] Zero DLM policies in account covering Environment:production volumes (Step 1)
REMEDIATION:
  1. Confirm the AWSDataLifecycleManagerServiceRole exists:
     aws iam get-role --role-name AWSDataLifecycleManagerServiceRole
  2. Create a policy targeting production volumes:
     aws dlm create-lifecycle-policy \
       --description "production-ebs-daily" \
       --state ENABLED \
       --execution-role-arn arn:aws:iam::<acct>:role/AWSDataLifecycleManagerServiceRole \
       --policy-details file://policy.json
  3. Verify execution after the first schedule window:
     aws ec2 describe-snapshots \
       --filters "Name=tag:aws:dlm:lifecycle-policy-id,Values=<new-policy-id>"
```

---

## Scenario 2 — MISCONFIGURED (disabled policy)

**Input:** Policy `policy-disabled-abcdef` is well-formed (valid TargetTags,
24-hour Interval schedule, 14-snapshot retention, CopyTags:true) but
`State: DISABLED`.

**Classification:** Step 2 fires — a DISABLED policy creates zero snapshots
regardless of how well-formed its schedules are. Step 7 also fires (no
CrossRegionCopyTargets), but Step 2 is the worst finding.

**Output:**

```text
POLICY: policy-disabled-abcdef (production-ebs-daily)
VERDICT: MISCONFIGURED
REASON: Policy State is DISABLED — zero snapshots are being created
regardless of how well-formed the schedules are (Step 2). Additionally, no
cross-region copy is configured (Step 7).
FINDINGS:
  - [MISCONFIGURED] State: DISABLED — policy registered but not running (Step 2)
  - [CONFIG_GAP] No CrossRegionCopyTargets on schedule daily-6am — no DR (Step 7)
REMEDIATION:
  1. Confirm the service role exists before re-enabling:
     aws iam get-role --role-name AWSDataLifecycleManagerServiceRole
  2. Re-enable:
     aws dlm update-lifecycle-policy --policy-id policy-disabled-abcdef --state ENABLED
  3. Add a cross-region copy target to the schedule for DR coverage.
  4. Verify execution after the next schedule window:
     aws ec2 describe-snapshots \
       --filters "Name=tag:aws:dlm:lifecycle-policy-id,Values=policy-disabled-abcdef"
```

---

## Scenario 3 — MISCONFIGURED (empty TargetTags)

**Input:** Policy `policy-empty-targets-123456` is ENABLED with a valid
schedule and 7-snapshot retention, but `PolicyDetails.TargetTags: []`.

**Classification:** Step 3 fires — empty TargetTags means zero volumes match.
DLM does NOT default to "all volumes" when TargetTags is empty; it matches
nothing. The policy runs on schedule and snapshots zero volumes. This is
functionally identical to a DISABLED policy but subtler because State is
ENABLED.

**Output:**

```text
POLICY: policy-empty-targets-123456 (stale-dev-backup)
VERDICT: MISCONFIGURED
REASON: PolicyDetails.TargetTags is empty — no volumes match, so the policy
snapshots nothing despite being ENABLED (Step 3). DLM does not default to
all volumes when TargetTags is empty.
FINDINGS:
  - [MISCONFIGURED] TargetTags: [] — zero volumes match (Step 3)
REMEDIATION:
  1. Identify the correct tag set from the workload's volumes:
     aws ec2 describe-volumes --filters "Name=tag-key,Values=Environment"
  2. Update the policy details with the tag targets:
     aws dlm update-lifecycle-policy \
       --policy-id policy-empty-targets-123456 \
       --policy-details file://updated-details.json
  3. Verify volume matching returns > 0 volumes.
```

---

## Scenario 4 — CONFIG_GAP (no cross-region copy)

**Input:** Policy `policy-no-drcopy-789012` is ENABLED, targets production
volumes, creates daily snapshots, retains 14, CopyTags:true. But
`CrossRegionCopyTargets: []` on the only schedule.

**Classification:** Steps 2-6 pass (enabled, valid targets, valid schedule,
sensible retention). Step 7 fires — single-region snapshots mean a regional
outage destroys all backups along with the primary.

**Output:**

```text
POLICY: policy-no-drcopy-789012 (prod-volumes-daily)
VERDICT: CONFIG_GAP
REASON: Policy is enabled with a valid schedule and 14-snapshot retention,
but no CrossRegionCopyTargets on any schedule — single-region backup
provides no DR posture (Step 7).
FINDINGS:
  - [CONFIG_GAP] No CrossRegionCopyTargets on schedule daily-6am — no DR (Step 7)
REMEDIATION:
  1. Add a CrossRegionCopyTarget to the schedule with an explicit CMK:
     "CrossRegionCopyTargets": [{
       "TargetRegion": "us-west-2",
       "EncryptionConfiguration": {
         "Encrypted": true,
         "CmkArn": "arn:aws:kms:us-west-2:<acct>:key/<dr-cmk-id>"
       }
     }]
  2. Specify an explicit CmkArn — do NOT rely on the destination region's
     default encryption (often false in DR regions).
  3. Verify DR snapshots after the next copy window:
     aws ec2 describe-snapshots --region us-west-2 \
       --filters "Name=tag:aws:dlm:lifecycle-policy-id,Values=policy-no-drcopy-789012"
```

---

## Scenario 5 — CONFIG_GAP (short retention + CopyTags false)

**Input:** Policy `policy-weak-retention-345678` is ENABLED with a valid
daily schedule, but `RetainRule.Count: 1`, `CopyTags: false`, and no
cross-region copy.

**Classification:** Steps 2-5 pass (enabled, valid targets, valid schedule,
retention present). Step 6 fires (Count:1 — no recovery history). Step 7
fires (no DR). Step 8 fires (CopyTags:false — metadata loss).

**Output:**

```text
POLICY: policy-weak-retention-345678 (minimal-backup)
VERDICT: CONFIG_GAP
REASON: RetainRule.Count is 1 — zero recovery history (Step 6). CopyTags is
false — source volume tags dropped from snapshots, breaking downstream
automation (Step 8). No cross-region copy (Step 7).
FINDINGS:
  - [CONFIG_GAP] RetainRule.Count: 1 — no recovery history (Step 6)
  - [CONFIG_GAP] CopyTags: false — source volume tags dropped from snapshots (Step 8)
  - [CONFIG_GAP] No CrossRegionCopyTargets on schedule daily-3am — no DR (Step 7)
REMEDIATION:
  1. Increase RetainRule.Count to at least 7 (daily) or match the workload's
     RPO/RTO requirement.
  2. Set CopyTags: true on the schedule to preserve volume attribution.
  3. Add a CrossRegionCopyTarget with an explicit CMK in the DR region.
  4. Update via:
     aws dlm update-lifecycle-policy \
       --policy-id policy-weak-retention-345678 \
       --policy-details file://updated-details.json
```

---

## Scenario 6 — OK (clean production policy)

**Input:** Policy `policy-clean-production-001122` is ENABLED, targets
production volumes, uses a 6-field CronExpression (`0 6 * * ? *`), retains
30 snapshots, CopyTags:true, and has a cross-region copy to us-west-2 with
an explicit KMS CMK.

**Classification:** All steps pass. The 6-field cron is valid (Step 4).
Retention is 30 (Steps 5-6 pass). Cross-region copy present with explicit
CMK (Step 7 passes). CopyTags:true (Step 8 passes). Count < 1000 (Step 9
passes).

**Output:**

```text
POLICY: policy-clean-production-001122 (production-ebs-full-backup)
VERDICT: OK
REASON: Policy is enabled with a valid 6-field CronExpression, 30-snapshot
retention, CopyTags enabled, and cross-region copy to us-west-2 with an
explicit KMS CMK. All classification steps pass.
FINDINGS:
  - [OK] State: ENABLED (Step 2)
  - [OK] TargetTags match production volumes (Step 3)
  - [OK] Valid 6-field CronExpression (Step 4)
  - [OK] RetainRule.Count: 30 — sensible recovery history (Steps 5-6)
  - [OK] CrossRegionCopyTargets present with explicit CmkArn (Step 7)
  - [OK] CopyTags: true (Step 8)
REMEDIATION:
  1. None required for the current posture.
  2. Recommend verifying execution quarterly:
     aws ec2 describe-snapshots \
       --filters "Name=tag:aws:dlm:lifecycle-policy-id,Values=policy-clean-production-001122"
  3. Recommend a CloudTrail alarm on ec2:CreateSnapshot AccessDenied events
     sourced from the DLM service role — the earliest signal of service-role
     breakage (the #1 DLM silent-failure mode).
```

---

## Key takeaways across all scenarios

1. **State: ENABLED proves nothing about execution.** The only ground-truth
   signal is the `aws:dlm:lifecycle-policy-id` tag on snapshots. Always
   cross-check with `describe-snapshots`.
2. **Disabled and empty-TargetTags policies are functionally identical**
   (zero snapshots) but DISABLED is obvious while empty TargetTags is subtle.
3. **Cross-region copy is the minimum DR posture.** Single-region snapshots
   fail with the primary. ShareRules are NOT a substitute — shared snapshots
   stay in the source region.
4. **CopyTags:true is almost always correct.** CopyTags:false drops source
   volume tags except `Name` and `aws:dlm:*`, breaking downstream automation.
5. **Retention of 1 is no recovery history.** A single corrupt snapshot is
   unrecoverable. Minimum 7 for daily production snapshots.
