# Backup Vault Lock and Lifecycle Reference

Supplementary reference for the Backup Schedule Automator skill. Use
when configuring vault lock (WORM compliance), designing lifecycle
transitions (hot to cold storage), or debugging cross-account backup
failures.

## Vault lock modes

| Mode | Reversible | Override | Use case |
|---|---|---|---|
| `GOVERNANCE` | Yes (admin can modify/remove during `ChangeableForDays`) | Root/admin | Testing, pre-production, non-regulated |
| `COMPLIANCE` | NO (irreversible until retention expires) | NO ONE | SOX, HIPAA, PCI DSS production compliance |

### GOVERNANCE mode setup (test first)

```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name "prod-vault" \
  --changeable-for-days 3 \
  --min-retention-days 7 \
  --max-retention-days 365 \
  --mode GOVERNANCE
```

After `ChangeableForDays` expires, the lock becomes immutable. During
the window, an admin with `backup:DeleteBackupVaultLockConfiguration`
can remove it.

### COMPLIANCE mode setup (irreversible)

```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name "prod-vault" \
  --min-retention-days 365 \
  --max-retention-days 2555 \
  --mode COMPLIANCE
```

**WARNING:** COMPLIANCE mode cannot be removed. Every recovery point in
this vault is retained for at least `min-retention-days`. Verify
retention values twice before executing.

## Lifecycle transition design

| Workload tier | Hot retention | Cold transition | Total retention | RTO impact |
|---|---|---|---|---|
| Dev/test | 7d | None | 7d | Minutes (hot only) |
| Production standard | 30d | 60d cold | 90d | Minutes (hot) then hours (cold thaw) |
| Production critical | 7d | 23d cold | 30d | Minutes for recent, hours for older |
| Compliance (SOX) | 365d | 2190d cold | 2555d (7yr) | Hours (cold thaw) |

### Cold storage thaw times (approximate)

| Data size | Thaw time |
|---|---|
| < 1 GB | 5-15 minutes |
| 1-10 GB | 15-30 minutes |
| 10-100 GB | 30 minutes - 2 hours |
| 100 GB - 1 TB | 2-12 hours |
| > 1 TB | 12+ hours |

**Design rule:** if the application RTO is less than the thaw time for
the recovery point size, do NOT transition to cold storage within the
RTO window. Keep hot for the entire RTO-relevant period.

## Lifecycle configuration

```bash
aws backup create-backup-plan --backup-plan '{
  "BackupPlanName": "tiered-plan",
  "Rules": [{
    "RuleName": "daily-tiered",
    "TargetBackupVaultName": "prod-vault",
    "ScheduleExpression": "cron(0 5 ? * * *)",
    "Lifecycle": {
      "MoveToColdStorageAfterDays": 30,
      "DeleteAfterDays": 365
    }
  }]
}'
```

Key constraints:
- `MoveToColdStorageAfterDays` must be less than `DeleteAfterDays`.
- If vault lock is active, `DeleteAfterDays` must be >=
  `min-retention-days` and <= `max-retention-days`.
- `CopyActions` can have different lifecycle values than the primary
  rule.

## Cross-account backup requirements

For source account A to back up to destination account B's vault:

1. **Destination vault access policy** must grant source account's
   backup role:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Principal": {"AWS": "arn:aws:iam::SOURCE_ACCOUNT:role/service-role/AWSBackupServiceRole"},
       "Action": ["backup:CopyIntoBackupVault"],
       "Resource": "*"
     }]
   }
   ```

2. **Destination KMS key policy** must grant source account:
   - `kms:Decrypt`
   - `kms:GenerateDataKey`

3. **Source account backup role** must have permissions to write to the
   destination vault and use the destination KMS key.

Common failure: backup job succeeds in source but recovery point never
appears in destination. Root cause: missing `backup:CopyIntoBackupVault`
in the destination vault policy.

## Restore testing automation

Scheduled Lambda that starts a restore job and verifies the result:

| Tier | Frequency | Verification | RTO target |
|---|---|---|---|
| Tier 1 (prod critical) | Weekly | App health check endpoint | < 1 hour |
| Tier 2 (prod standard) | Monthly | Data integrity query | < 4 hours |
| Tier 3 (internal/dev) | Quarterly | Restore job status only | < 24 hours |

Always use a separate test VPC/subnet for restore testing to avoid
conflicts with production resources.

## Backup report plans

| Report template | Content | Use case |
|---|---|---|
| `BACKUP_JOB_REPORT` | Job status, duration, size | Operational monitoring |
| `BACKUP_PLAN_TEMPLATE_COMPLIANCE` | Plan adherence summary | Compliance evidence |
| `RESTORE_JOB_REPORT` | Restore test history | RTO/RPO validation |

Reports are delivered to S3 with a 24-hour delay. For real-time job
status, use CloudWatch Events on `Backup Job State Change`.
