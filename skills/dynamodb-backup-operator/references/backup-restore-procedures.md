# DynamoDB Backup and Restore Procedures Reference

Load this reference when planning or executing any DynamoDB backup or
restore operation. The procedures below are the canonical sequences for
each backup/restore archetype, with pre-checks, command sequence,
post-verification, and rollback notes.

## Decision tree — which backup/restore archetype

| Scenario | Use | Why |
|---|---|---|
| Recover from bad write, original table intact | **PITR restore** | Rewind to a specific second; new table, original preserved |
| Recover to a known snapshot instant | **On-demand backup restore** | Snapshot-style restore from a backup ARN |
| Long-term / cross-region retention | **AWS Backup vault plan** | Vault Lock + cross-region copy + scheduled snapshots |
| Cross-region disaster recovery (no AWS Backup) | **Export to S3 + import** | S3-based cross-region path when AWS Backup not in use |
| Partial recovery (specific partition / attributes) | **Selective restore (PITR + projection filter)** | Smaller restore, lower cost |
| Ransomware resilience | **AWS Backup Vault Lock COMPLIANCE** | Immutable backups even from root |
| Compliance / analytics data extraction | **S3 export (Parquet)** | Snapshot to S3 for Athena/Glue |
| Bulk load from external source | **S3 import** | Load CSV/Parquet data into a new table |

## Pre-checks (run before any operation)

**ALL operations:**
1. `TableStatus` is `ACTIVE` (or `UPDATING` for read-only ops).
2. `DeletionProtectionEnabled` flag captured (does not block restore,
   but must be re-applied on the new table).
3. IAM caller has the required DynamoDB permissions.

**For PITR restore:** `PointInTimeRecoveryStatus: ENABLED` AND
`LatestRestorableDateTime >= --restore-date-time >=
EarliestRestorableDateTime`.

**For snapshot restore:** backup ARN exists AND `BackupStatus: AVAILABLE`.

**For export to S3:** `PointInTimeRecoveryStatus: ENABLED` (export reads
from the continuous-backup store).

**For import from S3:** target table name free, S3 source in the same
region.

## On-demand backup procedure

**When to use:** pre-migration safety snapshot, scheduled snapshot
outside AWS Backup, known-good recovery point for a long-running
migration.

**Command sequence:**
```bash
# 1. Capture pre-state
aws dynamodb describe-table --table-name <name> --output json \
  > /tmp/<name>-pre-$(date +%s).json

# 2. Create the on-demand backup (stored in DynamoDB service, NOT S3)
aws dynamodb create-backup \
  --table-name <name> \
  --backup-name <name>-pre-migration-$(date -u +%Y%m%dT%H%M%S)

# 3. Poll for AVAILABLE
aws dynamodb describe-backup \
  --backup-arn <returned-arn> \
  --query 'BackupDescription.BackupDetails.BackupStatus'

# 4. Verify backup size matches source (approximately)
aws dynamodb describe-backup --backup-arn <arn> \
  --query 'BackupDescription.BackupDetails.{Size:BackupSizeBytes,Status:BackupStatus,Expiry:BackupExpiryDateTime}'
```

**Post-verification:**
- `BackupStatus: AVAILABLE`.
- `BackupSizeBytes` is within ~10% of the source `TableSizeBytes`
  (allow for backup metadata overhead).
- `BackupCreationDateTime` matches the create call.

**Rollback:** delete the backup:
```bash
aws dynamodb delete-backup --backup-arn <arn>
```

**Common failure modes:**
- `BackupAlreadyExists` — choose a unique `--backup-name`.
- `TableNotFoundException` — wrong region or wrong table name.

## Enable-PITR procedure

**When to use:** any production table that requires second-level RPO.
Should be the default for production.

**Command sequence:**
```bash
aws dynamodb update-continuous-backups \
  --table-name <name> \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

# Verify
aws dynamodb describe-continuous-backups --table-name <name> \
  --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription'
```

**Post-verification:**
- `PointInTimeRecoveryStatus: ENABLED`.
- `EarliestRestorableDateTime` is the moment of enablement (note: data
  from BEFORE enablement is not recoverable via PITR).
- `LatestRestorableDateTime` updates in near-real-time.

**Rollback:** disable PITR (`PointInTimeRecoveryEnabled=false`). NOT
recommended — disables the 35-day recovery window.

**Common failure modes:**
- `ContinuousBackupsUnavailableException` — table in CREATING state;
  wait for ACTIVE.

## PITR restore procedure

**When to use:** recover from bad DML/DDL on a live table where the
original is still active.

**Pre-checks:**
1. `PointInTimeRecoveryStatus: ENABLED`.
2. `LatestRestorableDateTime >= --restore-date-time >=
   EarliestRestorableDateTime`.
3. `TableStatus: ACTIVE`.
4. Target `--target-table-name` does NOT exist.
5. CMK accessible (if encrypted).

**Command sequence:**
```bash
# 1. Capture pre-state
aws dynamodb describe-table --table-name <name> --output json \
  > /tmp/<name>-pre-$(date +%s).json

# 2. Identify the latest restorable time (informational)
aws dynamodb describe-continuous-backups --table-name <name> \
  --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.LatestRestorableDateTime' \
  --output text

# 3. Execute (NEW table; original unchanged)
aws dynamodb restore-table-to-point-in-time \
  --source-table-name <name> \
  --target-table-name <name>-pitr-$(date -u +%Y%m%d) \
  --restore-date-time 2026-08-09T10:00:00Z \
  --billing-mode-override PAY_PER_REQUEST

# 4. Poll for ACTIVE
aws dynamodb describe-table --table-name <name>-pitr-... \
  --query 'Table.TableStatus'
# Status transitions RESTORING -> ACTIVE.

# 5. Get the new table ARN
aws dynamodb describe-table --table-name <name>-pitr-... \
  --query 'Table.TableArn' --output text
```

**Post-verification:**
- `describe-table` shows `TableStatus: ACTIVE`.
- `ItemCount` (approximate) matches the source at the restore point.
- A sentinel `get-item` query returns the expected value.
- GSI/LSI are `ACTIVE` (not `BUILDING`).

**Rollback:** Delete the restored table:
```bash
aws dynamodb delete-table --table-name <name>-pitr-...
```
The original source is untouched — there is no in-place rollback needed.

**Common failure modes:**
- `PointInTimeRecoveryUnavailableException` — PITR not enabled; run
  `update-continuous-backups` first.
- `ResourceInUseException` — target name already exists.
- `LimitExceededException` — too many concurrent restores in the
  account; wait and retry.

## Snapshot-style restore procedure

**When to use:** recover from a known-good backup ARN (on-demand
backup, AWS Backup recovery point, or a previously-created snapshot).

**Command sequence:**
```bash
# 1. Verify the backup is AVAILABLE
aws dynamodb describe-backup --backup-arn <arn> \
  --query 'BackupDescription.BackupDetails.BackupStatus'

# 2. Execute the restore
aws dynamodb restore-table-from-backup \
  --target-table-name <name>-restored-$(date -u +%Y%m%d) \
  --backup-arn <arn>

# 3. Poll for ACTIVE
aws dynamodb describe-table --table-name <name>-restored-... \
  --query 'Table.TableStatus'
```

**Post-verification:** same as PITR restore.

**Common failure modes:**
- `BackupNotFoundException` — wrong ARN or wrong region.
- `BackupInUseException` — concurrent restore from the same backup;
  wait and retry.

## Cross-region restore via S3 export + import

**When to use:** cross-region DR when AWS Backup is not in use, or when
you need an S3-resident copy for analytics/compliance.

**Export (source region):**
```bash
# 1. Confirm PITR is enabled (export reads from continuous-backup store)
aws dynamodb describe-continuous-backups --table-name <name> \
  --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus'

# 2. Execute the export (writes to your S3 bucket)
aws dynamodb export-table-to-point-in-time \
  --table-arn arn:aws:dynamodb:<src-region>:<acct>:table/<name> \
  --s3-bucket <export-bucket> \
  --s3-prefix <name>/export-$(date -u +%Y%m%d)/ \
  --export-format DYNAMODB_JSON \
  --export-time 2026-08-09T10:00:00Z

# 3. Poll for COMPLETED
aws dynamodb describe-export --export-arn <returned-arn> \
  --query 'ExportDescription.ExportStatus'
```

**Cross-region copy (if export bucket is in a different region):**
```bash
aws s3 sync s3://<src-bucket>/<prefix>/ s3://<dst-bucket>/<prefix>/ \
  --source-region <src-region> --region <dst-region>
```

**Import (target region):**
```bash
aws dynamodb import-table \
  --s3-bucket-source S3Bucket=<dst-bucket>,S3KeyPrefix=<prefix>/ \
  --input-format DYNAMODB_JSON \
  --table-creation-parameters \
    TableName=<name>-imported,AttributeDefinitions=[{AttributeName=id,AttributeType=S}],\
KeySchema=[{AttributeName=id,KeyType=HASH}],BillingMode=PAY_PER_REQUEST

# Poll
aws dynamodb describe-import --import-arn <returned-arn> \
  --query 'ImportTableDescription.ImportStatus'
```

**Common failure modes:**
- `ExportConflictException` — concurrent export to the same prefix.
- `ImportConflictException` — concurrent import on the same table.
- `S3AccessDenied` — export/import role missing `s3:PutObject` or
  `s3:GetObject`.

## AWS Backup procedure (scheduled snapshots + cross-region copy)

**When to use:** scheduled/automated snapshots, cross-region DR copies,
compliance retention with Vault Lock.

**Command sequence (create a backup plan):**
```bash
# 1. Create a vault (with Vault Lock for compliance)
aws backup create-backup-vault \
  --backup-vault-name <name>-vault \
  --encryption-key-arn <cmk-arn>

# 2. Create a backup plan (daily snapshot + cross-region copy)
aws backup create-backup-plan --backup-plan '{
  "BackupPlanName": "dynamodb-daily-dr",
  "Rules": [
    {
      "RuleName": "daily-snapshot",
      "TargetBackupVaultName": "<name>-vault",
      "ScheduleExpression": "cron(0 5 ? * * *)",
      "StartWindowMinutes": 60,
      "CompletionWindowMinutes": 1440,
      "Lifecycle": {"DeleteAfterDays": 30},
      "CopyActions": [
        {"DestinationBackupVaultArn": "arn:aws:backup:<dr-region>:<acct>:backup-vault:<name>-vault-dr",
         "Lifecycle": {"DeleteAfterDays": 90}}
      ]
    }
  ]
}'

# 3. Assign the DynamoDB table to the plan
aws backup create-backup-selection \
  --backup-plan-id <plan-id> \
  --backup-selection '{
    "SelectionName": "dynamodb-prod",
    "IamRoleArn": "arn:aws:iam::<acct>:role/service-role/AWSBackupServiceRole",
    "Resources": ["arn:aws:dynamodb:<region>:<acct>:table/<name>"]
  }'
```

**Restore via AWS Backup:**
```bash
aws backup start-restore-job \
  --recovery-point-arn <recovery-point-arn> \
  --iam-role-arn arn:aws:iam::<acct>:role/service-role/AWSBackupServiceRole \
  --metadata TargetTableName=<name>-restored
```

**Common failure modes:**
- Cross-region copy fails silently — verify in CloudWatch `AWS/Backup`.
- Vault Lock COMPLIANCE mode is irrevocable — verify retention before
  locking.
- Cross-account copy needs both source KMS key policy grant and
  destination vault policy.

## Post-restore side-config checklist

Restore does NOT copy these — reconfigure each one after restore:

- [ ] Auto-scaling policies (if PROVISIONED)
  - `register-scalable-target` for table + each GSI
  - `put-scaling-policy` for table + each GSI
- [ ] DynamoDB Streams
  - `update-table --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES`
- [ ] TTL
  - `update-time-to-live --time-to-live-specification Enabled=true,AttributeName=ttl`
- [ ] CloudWatch alarms
  - Re-create alarms referencing the new table name
- [ ] IAM resource policies
  - Update inline/managed policies referencing the source table ARN
- [ ] Tags
  - `tag-resource --resource <new-arn> --tags ...`
- [ ] Deletion protection
  - `update-table --deletion-protection-enabled`
- [ ] Table class (if source was Standard-IA)
  - `update-table --table-class STANDARD_INFREQUENT_ACCESS`
- [ ] Application connection strings
  - Env vars, config files, Secrets Manager, Parameter Store, DNS

## Cost comparison (2026 us-east-1)

| Mechanism | Storage cost | Restore cost | Retention |
|---|---|---|---|
| PITR (continuous) | ~$0.20/GB-month (change volume) | ~$0.10/GB read | 35 days rolling |
| On-demand backup | ~$0.10/GB-month | Free (creates new table) | Until `delete-backup` |
| AWS Backup snapshot | ~$0.10/GB-month | ~$0.10/GB restore | Per plan lifecycle |
| Export to S3 (Parquet) | S3 Standard ~$0.023/GB-month | ~$0.008/GB read | Per S3 lifecycle |
| Import from S3 | (target table write cost) | ~$0.008/GB write | N/A |

**Rule of thumb:** production tables should have BOTH PITR (for
second-level RPO) AND AWS Backup (for longer-term retention and
cross-region DR). Use S3 export for analytics/compliance archives.
