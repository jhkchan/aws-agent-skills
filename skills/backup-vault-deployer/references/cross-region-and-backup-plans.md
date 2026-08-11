# Cross-Region Copy and Backup Plans — Backup Vault Deployer

Deep reference on cross-region and cross-account copy configuration,
backup plan rule structure (schedule, lifecycle, copy actions),
continuous vs periodic backup mechanics (PITR), backup selection
methods (tag, resource-ARN, conditions), and resource-type coverage
matrices. Loaded on demand by the skill.

## Cross-region copy in detail

### Prerequisites checklist

```text
1. Destination vault exists in target Region
   aws backup create-backup-vault --backup-vault-name dr-vault --region us-west-2

2. Destination KMS key exists in target Region (customer-managed)
   aws kms create-key --region us-west-2
   Key policy MUST allow source account:
     {
       "Principal": { "AWS": "arn:aws:iam::<source-acct>:root" },
       "Action": ["kms:Encrypt","kms:Decrypt","kms:GenerateDataKey*","kms:DescribeKey"]
     }

3. (Cross-account) Destination vault access policy
   aws backup put-backup-vault-access-policy
     --backup-vault-name dr-vault --region us-west-2
     --policy '{
       "Statement": [{
         "Effect": "Allow",
         "Principal": { "AWS": "arn:aws:iam::<source-acct>:root" },
         "Action": "backup:CopyIntoBackupVault"
       }]
     }'

4. Backup plan rule has CopyActions block
   {
     "CopyActions": [{
       "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:...:vault:dr-vault",
       "Lifecycle": { "DeleteAfterDays": 180 }
     }]
   }
```

### Copy action in backup plan JSON

```json
{
  "BackupPlanName": "production-with-dr",
  "Rules": [{
    "RuleName": "daily-backup-with-copy",
    "TargetBackupVaultName": "production-backup-vault",
    "ScheduleExpression": "cron(0 5 ? * MON-SAT *)",
    "Lifecycle": {
      "DeleteAfterDays": 90,
      "MoveToColdStorageAfterDays": 30
    },
    "CopyActions": [
      {
        "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:123456789012:backup-vault:dr-backup-vault",
        "Lifecycle": {
          "DeleteAfterDays": 180,
          "MoveToColdStorageAfterDays": 90
        }
      }
    ]
  }]
}
```

### Concurrency limits

```text
Concurrent copy jobs per account+Region: 6 (soft limit)
  ├── Large backups (TB-scale) can take hours
  ├── Multiple copy rules share the concurrency pool
  ├── If limit exceeded, copy jobs QUEUE (not fail)
  └── Request limit increase: Support Center → Backup → Limit increase

Cross-region data transfer cost:
  ├── ~$0.02/GB (us-east-1 → us-west-2)
  ├── Cross-region copy is the primary cost driver
  └── Scope copy rules to high-value resources to control cost
```

## Backup plan structure

### Rule components

| Component | Description | Example |
|---|---|---|
| `RuleName` | Identifier for the rule | `daily-full-backup` |
| `TargetBackupVaultName` | Vault for recovery points | `production-vault` |
| `ScheduleExpression` | Cron schedule | `cron(0 5 ? * MON-SAT *)` |
| `StartWindowMinutes` | Window to start backup | `480` (8 hours) |
| `CompletionWindowMinutes` | Window to complete | `10080` (7 days) |
| `Lifecycle.DeleteAfterDays` | When to delete recovery point | `90` |
| `Lifecycle.MoveToColdStorageAfterDays` | When to move to cold | `30` |
| `RecoveryPointType` | SNAPSHOT or CONTINUOUS | `CONTINUOUS` |
| `CopyActions` | Cross-region/cross-account copies | (see above) |
| `EnableContinuousBackup` | Boolean for PITR | `true` |

### Multiple rules per plan

```json
{
  "BackupPlanName": "production-tiered-backup",
  "Rules": [
    {
      "RuleName": "critical-daily-full",
      "TargetBackupVaultName": "critical-vault",
      "ScheduleExpression": "cron(0 1 ? * * *)",
      "Lifecycle": { "DeleteAfterDays": 30 },
      "EnableContinuousBackup": true
    },
    {
      "RuleName": "standard-weekly",
      "TargetBackupVaultName": "standard-vault",
      "ScheduleExpression": "cron(0 5 ? * SUN *)",
      "Lifecycle": { "DeleteAfterDays": 90, "MoveToColdStorageAfterDays": 30 }
    }
  ]
}
```

## Continuous backup (PITR) mechanics

### How continuous backup works

```text
Periodic (SNAPSHOT):
  ├── Takes a snapshot at the scheduled time
  ├── Recovery point = point-in-time snapshot
  ├── RPO = schedule interval (e.g., 24h for daily)
  └── PITR: NO (cannot restore to arbitrary point in time)

Continuous (CONTINUOUS):
  ├── Journaling in addition to periodic snapshots
  ├── Recovery point = any point in time within retention window
  ├── RPO = near-zero (1 second for VSS, 5 min for non-VSS)
  └── PITR: YES (restore to any second within window)

Continuous backup requires:
  ├── EnableContinuousBackup: true in the rule
  ├── OR RecoveryPointType: CONTINUOUS (CLI JSON)
  ├── Resource type must support PITR (EC2, RDS, DynamoDB, EFS)
  └── Supported resource has VSS agent (for EC2)
```

### PITR resource support

| Resource | PITR support | Granularity | Notes |
|---|---|---|---|
| EC2 | Yes (VSS) | 1 second | Requires VSS agent on instance |
| EC2 | Yes (non-VSS) | 5 minutes | Application-consent not guaranteed |
| RDS | Yes | 5 minutes | Uses RDS automated backup journal |
| DynamoDB | Yes | 1 second | Uses DynamoDB point-in-time recovery |
| EFS | Yes | 15 minutes | Conditional backup |
| Aurora | Yes | 5 minutes | Cluster-level continuous backup |
| S3 | No | N/A | Use S3 versioning for object-level PITR |
| FSx | No | N/A | Periodic snapshots only |
| DocumentDB | Yes | 5 minutes | MongoDB-compatible |
| Neptune | No | N/A | Periodic snapshots only |

## Backup selection methods

### Tag-based selection

```json
{
  "SelectionName": "production-tagged",
  "IamRoleArn": "arn:aws:iam::123456789012:role/service-role/AWSBackupDefaultServiceRole",
  "Conditions": {
    "StringEquals": {
      "aws:ResourceTag/Backup": "daily"
    }
  }
}
```

**Audit tip:** verify tag coverage before relying on tag-based
selection:

```bash
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Backup,Values=daily \
  --query 'ResourceTagMappingList[*].ResourceARN' \
  --output table
```

### Resource-ARN selection

```json
{
  "SelectionName": "specific-resources",
  "IamRoleArn": "arn:aws:iam::123456789012:role/service-role/AWSBackupDefaultServiceRole",
  "Resources": [
    "arn:aws:ec2:us-east-1:123456789012:instance/i-aaa111222",
    "arn:aws:rds:us-east-1:123456789012:db:production-db"
  ]
}
```

### Conditions-based selection

```json
{
  "SelectionName": "production-ec2-only",
  "IamRoleArn": "arn:aws:iam::123456789012:role/service-role/AWSBackupDefaultServiceRole",
  "Conditions": {
    "StringEquals": {
      "aws:ResourceTag/Environment": "production"
    },
    "StringLike": {
      "aws:ResourceType": "EC2*"
    }
  }
}
```

## Resource-type coverage matrix

| Resource | Backup | PITR | Cross-region | Selection |
|---|---|---|---|---|
| EC2 | Snapshot | Yes | Yes | Tag, ARN |
| RDS | Snapshot | Yes | Yes | Tag, ARN |
| Aurora | Snapshot | Yes | Yes | Tag, ARN |
| DynamoDB | On-demand | Yes | Yes | Tag, ARN |
| EFS | Incremental | Yes | Yes | Tag, ARN |
| S3 | Versioning | No | Yes | Tag, ARN |
| FSx (Lustre) | Snapshot | No | Yes | Tag, ARN |
| FSx (Windows) | Snapshot | No | Yes | Tag, ARN |
| FSx (ONTAP) | Snapshot | No | Yes | Tag, ARN |
| FSx (OpenZFS) | Snapshot | No | Yes | Tag, ARN |
| Storage Gateway | Snapshot | No | Yes | Tag, ARN |
| DocumentDB | Snapshot | Yes | Yes | Tag, ARN |
| Neptune | Snapshot | No | Yes | Tag, ARN |

## Backup report plans

### Report types and templates

| Template | Content | Frequency |
|---|---|---|
| `BACKUP_JOB_REPORT` | Job status, duration, resource, vault | Daily |
| `BACKUP_PLAN_COMPLIANCE_REPORT` | On-time, missed backups | Daily |
| `COPY_JOB_REPORT` | Cross-region copy job status | Daily |
| `RESTORE_JOB_REPORT` | Restore job status | Daily |
| `RECOVERY_POINT_REPORT` | Recovery point inventory | Daily |

### Create report plan

```bash
aws backup create-report-plan \
  --report-plan-name "daily-compliance-report" \
  --report-setting '{"ReportTemplate":"BACKUP_JOB_REPORT"}' \
  --report-delivery-config '{
    "S3BucketName": "backup-compliance-reports",
    "S3KeyPrefix": "reports/",
    "Formats": ["CSV","JSON"]
  }' \
  --region us-east-1
```

## Terraform examples

```hcl
# Backup vault
resource "aws_backup_vault" "production" {
  name        = "production-backup-vault"
  kms_key_arn = aws_kms_key.backup.arn
  tags        = { Environment = "production" }
}

# Backup plan with cross-region copy
resource "aws_backup_plan" "production" {
  name = "production-daily-backup"

  rule {
    rule_name         = "daily-with-dr"
    target_vault_name = aws_backup_vault.production.name
    schedule          = "cron(0 5 ? * MON-SAT *)"

    lifecycle {
      cold_storage_after = 60
      delete_after       = 180
    }

    copy_action {
      destination_vault_arn = "arn:aws:backup:us-west-2:${data.aws_caller_identity.current.account_id}:backup-vault:dr-vault"
      lifecycle {
        cold_storage_after = 90
        delete_after       = 365
      }
    }

    enable_continuous_backup = true
  }
}

# Tag-based selection
resource "aws_backup_selection" "production" {
  plan_id      = aws_backup_plan.production.id
  name         = "production-tagged"
  iam_role_arn = aws_iam_role.backup.arn

  selection_tag {
    type  = "STRINGEQUALS"
    key   = "Backup"
    value = "daily"
  }
}

# Report plan
resource "aws_backup_report_plan" "compliance" {
  name        = "daily-compliance-report"
  description = "Daily backup compliance report"

  report_setting {
    report_template = "BACKUP_JOB_REPORT"
  }

  report_delivery_config {
    s3_bucket_name = aws_s3_bucket.reports.bucket
    formats        = ["CSV", "JSON"]
  }
}
```
