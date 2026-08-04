# End-to-end usage scenario: backup-plan-auditor

A walkthrough showing the skill auditing a production backup plan that has
an impossible lifecycle (CONFIG_GAP) alongside a well-configured vault,
demonstrating ordered classification (CONFIG_GAP caught first), the
cold-storage-after-deletion concept, and the lifecycle-fix remediation
workflow.

## Input (user prompt)

> Review this AWS Backup plan before we deploy it to production. It backs
> up our EFS file systems to cold storage for cost optimization.

```yaml
Plan name: prod-efs-backup
Plan ARN: arn:aws:backup:us-east-1:111111111111:backup-plan:prod-efs-001

Backup vault: prod-secure-vault
Vault lock: COMPLIANCE (MinRetentionDays: 30)
Vault encryption key: arn:aws:kms:us-east-1:111111111111:key/cmk-backup (customer-managed CMK)

Backup plan rules:
  Rule 1 (daily-efs):
    ScheduleExpression: cron(0 2 * * ? *)  — daily at 02:00 UTC
    TargetBackupVault: prod-secure-vault
    Lifecycle:
      MoveToColdStorageAfterDays: 90
      DeleteAfterDays: 30
    CopyActions:
      - DestinationBackupVaultArn: arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault
        Lifecycle:
          DeleteAfterDays: 30

Backup selections:
  Selection 1 (efs-prod):
    IamRoleArn: arn:aws:iam::111111111111:role/service-role/AWSBackupDefaultServiceRole
    Resources:
      - arn:aws:elasticfilesystem:us-east-1:111111111111:file-system/fs-prod-data-01
      - arn:aws:elasticfilesystem:us-east-1:111111111111:file-system/fs-prod-data-02
    Conditions: (none)
```

## Skill output

```text
PLAN: prod-efs-backup
VERDICT: CONFIG_GAP
REASON: Rule "daily-efs" has MoveToColdStorageAfterDays (90) >=
DeleteAfterDays (30) — the cold-storage transition can never execute because
the recovery point is deleted first (Step 1a). The vault, schedule, and
coverage are all well-configured, but the lifecycle is impossible.
FINDINGS:
  - CONFIG_GAP: Impossible lifecycle in rule "daily-efs" —
    MoveToColdStorageAfterDays 90 >= DeleteAfterDays 30 (Step 1a). Both
    values count from creation date; the backup is deleted at day 30, before
    the cold transition at day 90.
  - [OK] Coverage: 2 EFS file systems assigned via explicit ARN (Step 2 —
    no coverage gap)
  - [OK] Vault "prod-secure-vault": compliance-mode lock (MinRetentionDays:
    30) + customer-managed CMK (Step 3 — vault dimension passes)
  - [OK] Schedule: daily cron — meets the daily-frequency baseline (Step 4a)
  - [WARNING] Cross-region copy retention (30 days) meets the 30-day minimum
    but is below the vault lock's MinRetentionDays (30) — borderline; consider
    aligning with the primary lifecycle after fix.
REMEDIATION:
  1. Fix the lifecycle so MoveToColdStorageAfterDays < DeleteAfterDays.
     For 90-day retention with cold tier: cold at 30, delete at 90.
     Update the plan:
     aws backup get-backup-plan --backup-plan-id prod-efs-001 --output json > /tmp/prod-efs-backup.json
     # Edit the JSON: set MoveToColdStorageAfterDays to 30, DeleteAfterDays to 90
     aws backup update-backup-plan --backup-plan-id prod-efs-001 --backup-plan file:///tmp/prod-efs-backup-fixed.json
  2. After fixing, verify the lifecycle is accepted:
     aws backup get-backup-plan --backup-plan-id prod-efs-001 --output json | jq '.BackupPlan.Rules[0].Lifecycle'
```

## What the skill caught that a generic assistant misses

1. **The impossible lifecycle is the root-cause finding.** A generic
   assistant might note the lifecycle "looks off" but then proceed to
   evaluate the vault, schedule, and coverage — producing a mixed review.
   The skill's ordered classification catches CONFIG_GAP at Step 1 and
   makes it the verdict. All other dimensions are reported as passing
   (OK), so the operator knows exactly what to fix.

2. **Both lifecycle values count from creation date.** A common
   misconception is that DeleteAfterDays counts from the cold-storage
   transition. The skill explains that both count from the recovery-point
   creation timestamp — so cold=90, delete=30 means deletion happens 60
   days before the cold transition.

3. **The cross-region copy retention is flagged as borderline.** The
   copy action's DeleteAfterDays (30) exactly meets the 30-day minimum
   but doesn't leave room for the vault lock's MinRetentionDays. The
   skill flags this as a WARNING, not a CONFIG_GAP — because the copy
   action targets a different vault (dr-vault) whose lock floor may
   differ.

4. **The vault is NOT flagged despite the lifecycle issue.** The vault
   has a compliance-mode lock and CMK — it passes Step 3 cleanly. A naive
   auditor might flag the vault because the overall plan is broken, but
   the skill isolates dimensions correctly.

## Slash-command invocation

```
/aws:audit-backup-plan
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this backup plan before we deploy to production"
```

The orchestrator emits
`[Phase: Audit | Skills routed: backup-plan-auditor]` and hands off
to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit this backup plan"
# [Phase: Audit | Skills routed: backup-plan-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the lifecycle, validate the backup plan:

```bash
# Verify the lifecycle is now valid
aws backup get-backup-plan --backup-plan-id prod-efs-001 \
  --profile default --output json | jq '.BackupPlan.Rules[0].Lifecycle'

# Confirm the next backup job succeeds with the fixed lifecycle
aws backup start-backup-job --backup-vault-name prod-secure-vault \
  --resource-arn arn:aws:elasticfilesystem:us-east-1:111111111111:file-system/fs-prod-data-01 \
  --iam-role-arn arn:aws:iam::111111111111:role/service-role/AWSBackupDefaultServiceRole \
  --profile default

# Check that recovery points are transitioning to cold storage correctly
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name prod-secure-vault --profile default
```
