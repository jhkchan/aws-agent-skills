# Examples: backup-schedule-automator

This directory contains end-to-end usage scenarios for the Backup
Schedule Automator skill.

## Scenario: Production backup automation with compliance vault

A walkthrough showing the skill designing a backup plan for two
workload tiers: a standard production backup with lifecycle tiering and
cross-region copy, and a compliance backup with WORM vault lock.

### Input (user prompt)

> Design backup automation for our production workloads. We need daily
> backups of DynamoDB tables and EBS volumes (30d hot, 90d cold, DR copy
> to us-west-2). We also have RDS instances that need SOX-compliant
> 7-year WORM retention.

```
Design reference: prod-backup-rollout
Account: 111111111111
Region: us-east-1

Workload 1: Standard production
  Resources: DynamoDB + EBS tagged backup-plan=daily-prod, environment=prod
  Frequency: Daily at 05:00 UTC
  Retention: 30d hot, 90d cold
  Cross-region copy: us-west-2 (90d retention)
  Vault: prod-backup-vault (GOVERNANCE lock)
  Restore testing: monthly, RTO 4 hours

Workload 2: Compliance (SOX)
  Resources: RDS tagged backup-plan=compliance, environment=prod
  Frequency: Daily
  Retention: 365d hot, 2555d cold (7 years)
  Vault: prod-compliance-vault (COMPLIANCE lock, WORM)
  Cross-region copy: us-west-2 compliance-vault
  Restore testing: quarterly, RTO 24 hours
```

### Skill output

```text
BACKUP: prod-backup-rollout
PLAN: tiered-retention-plan (daily, 30d hot + 60d cold, cross-region copy to us-west-2)
VAULT: prod-backup-vault (GOVERNANCE lock, min 7d, max 365d)
LIFECYCLE: MoveToColdStorageAfterDays=30, DeleteAfterDays=90
TRIGGER: SCHEDULED (cron(0 5 ? * * *))
RESTORE_TEST: Monthly, RTO target 4 hours, Tier 2
TAG_SCOPE: backup-plan=daily-prod, environment=prod
CROSS_ACCOUNT: NONE
CROSS_REGION: us-west-2 (dr-vault, 90d retention)
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws backup create-backup-plan --backup-plan '{"BackupPlanName":"tiered-retention-plan","Rules":[{"RuleName":"daily-tiered","TargetBackupVaultName":"prod-backup-vault","ScheduleExpression":"cron(0 5 ? * * *)","Lifecycle":{"MoveToColdStorageAfterDays":30,"DeleteAfterDays":90},"CopyActions":[{"DestinationBackupVaultArn":"arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault","Lifecycle":{"DeleteAfterDays":90}}]}]}'

BACKUP: prod-backup-rollout
PLAN: compliance-strict-plan (daily, 365d hot + 2190d cold, cross-region copy)
VAULT: prod-compliance-vault (COMPLIANCE lock, min 365d, max 2555d — WORM)
LIFECYCLE: MoveToColdStorageAfterDays=365, DeleteAfterDays=2555
TRIGGER: SCHEDULED (cron(0 5 ? * * *))
RESTORE_TEST: Quarterly, RTO target 24 hours, Tier 3
TAG_SCOPE: backup-plan=compliance, environment=prod
CROSS_ACCOUNT: NONE
CROSS_REGION: us-west-2 (compliance-vault, 2555d retention)
VERDICT: AUTOMATION_DEPLOYED
GAP: None — test GOVERNANCE mode for 3 days before switching to COMPLIANCE
TEMPLATE:
  aws backup put-backup-vault-lock-configuration --backup-vault-name prod-compliance-vault --changeable-for-days 3 --min-retention-days 365 --max-retention-days 2555 --mode GOVERNANCE
```

**Account-level aggregate verdict: AUTOMATION_DEPLOYED for both
workloads.** Deploy the standard plan immediately; the compliance plan
should run in GOVERNANCE mode for 3 days before switching to COMPLIANCE.

## Slash-command invocation

```
/aws:automate-backup-schedule
```

Or via the orchestrator:

```
/aws:pipeline
You: "automate backup schedules for production with lifecycle tiering"
```

## Live-account invocation (requires AWS CLI)

```bash
# Check existing backup plans
aws backup list-backup-plans --region us-east-1 --profile default

# Check existing backup vaults and lock status
aws backup list-backup-vaults --region us-east-1 --profile default
aws backup describe-backup-vault --backup-vault-name prod-vault --region us-east-1 --profile default

# Verify tag coverage for backup selection
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=backup-plan,Values=daily-prod \
  --region us-east-1 --profile default

# Check backup job history
aws backup list-backup-jobs --by-state COMPLETED --max-results 5 \
  --region us-east-1 --profile default

# Check restore job history
aws backup list-restore-jobs --max-results 5 \
  --region us-east-1 --profile default

# Check Organizations backup policy
aws organizations list-policies --filter BACKUP_POLICY \
  --profile default
```
