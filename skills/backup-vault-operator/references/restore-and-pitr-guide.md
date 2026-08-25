# Restore and Point-in-Time Recovery Reference

Load this reference when planning or executing any restore operation.
The procedures below cover snapshot restore, continuous backup (PITR)
restore, cross-region restore, and restore-to-new patterns.

## Decision tree — restore strategy

| Scenario | Use | Why |
|---|---|---|
| Restore to a known recovery point | **Snapshot restore** | Recovery point ARN is fixed; restore to new resource |
| Restore to a specific minute (EC2, RDS, Aurora, DynamoDB) | **Continuous backup (PITR)** | Allows 1-minute granularity within the continuous window |
| Restore in a different region for DR | **Cross-region restore** | Destination region recovery point + destination KMS key |
| Restore a single file / item without full restore | **Backup Search + item restore** | 2025 feature; avoids full-resource restore for EFS/S3/DynamoDB |
| Test restore for drill | **Restore to non-production vault** | Avoids contaminating production recovery points |

## Snapshot restore procedure

**When to use:** recovery point ARN is known, no PITR needed.

**Pre-checks:**
1. `describe-recovery-point --backup-vault-name <vault>
   --recovery-point-arn <arn>` returns `Status: COMPLETED`.
2. Recovery point `CalculatedLifecycle` shows not `DELETE_AFTER_DAYS`
   expired.
3. `get-recovery-point-restore-metadata --recovery-point-arn <arn>`
   returns the metadata template for the resource type.
4. Caller IAM role holds `backup:StartRestoreJob`.
5. For EC2 restore: destination `SubnetId`, `SecurityGroupIds`,
   `InstanceType` exist and are valid.
6. For RDS restore: `NewDBInstanceIdentifier` not already in use.

**Command sequence:**
```bash
# 1. Capture metadata template
aws backup get-recovery-point-restore-metadata \
  --backup-vault-name prod-daily-vault \
  --recovery-point-arn arn:aws:backup:us-east-1:111111111111:recovery-point:1-2-3-4

# 2. CONFIRM gate, then start-restore-job
aws backup start-restore-job \
  --recovery-point-arn arn:aws:backup:us-east-1:111111111111:recovery-point:1-2-3-4 \
  --metadata '{"InstanceId": "i-restored-001", "SubnetId": "subnet-abc123", "SecurityGroupIds": "sg-abc123", "InstanceType": "t3.medium"}' \
  --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
  --resource-type EC2 \
  --idempotency-token "$(date +%s)"
```

**Post-verification:**
```bash
aws backup describe-restore-job --restore-job-id <id>
# Expected: Status=COMPLETED, CreatedResourceArn=arn:aws:ec2:...
```

## Continuous backup (PITR) restore procedure

**When to use:** restore to a specific minute within the continuous
backup window.

**Pre-checks (additional):**
1. `describe-recovery-point --recovery-point-arn <arn>` shows
   `ContinuousBackup: true` (for the parent recovery point).
2. The requested `RecoveryPointCreationDate` is within the continuous
   window (typically 35 days for EC2, 35 days for RDS, 35 days for
   DynamoDB).
3. For EC2: source instance supports PITR (most recent instance
   families; verify via `describe-recovery-point`).

**Command sequence (EC2 PITR):**
```bash
aws backup start-restore-job \
  --recovery-point-arn arn:aws:backup:us-east-1:111111111111:recovery-point:continuous-parent \
  --metadata '{
    "InstanceId": "i-restored-pitr",
    "SubnetId": "subnet-abc123",
    "SecurityGroupIds": "sg-abc123",
    "InstanceType": "t3.medium",
    "RestoreTime": "2026-08-09T14:30:00Z"
  }' \
  --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
  --resource-type EC2
```

The `RestoreTime` field (ISO 8601 UTC) selects the moment within the
continuous window. If omitted, restore uses the latest available
recovery point.

**PITR window limits (2026):**

| Service | PITR window | Granularity |
|---|---|---|
| EC2 | 35 days | 1 minute |
| RDS (MySQL, PostgreSQL, etc.) | 35 days | 1 second |
| Aurora | 35 days | 1 second |
| DynamoDB | 35 days | 1 second |
| S3 (with versioning) | Indefinite (per version) | Per object version |

## Cross-region restore procedure

**When to use:** DR scenario; restore in a different region.

**Pre-checks (additional):**
1. Destination region has a backup vault.
2. Destination region KMS key policy grants
   `backup:Decrypt` to the AWS Backup service principal.
3. Destination region IAM role holds `backup:StartRestoreJob`.
4. Recovery point exists in the destination region (verify via
   `list-recovery-points-by-backup-vault` in the destination region).

**Command sequence (executed in destination region):**
```bash
aws backup start-restore-job \
  --backup-vault-name dr-vault \
  --recovery-point-arn arn:aws:backup:us-west-2:111111111111:recovery-point:1-2-3-4 \
  --metadata '{"InstanceId": "i-dr-restored-001", "SubnetId": "subnet-xyz789", "SecurityGroupIds": "sg-xyz789", "InstanceType": "t3.medium"}' \
  --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
  --resource-type EC2 \
  --region us-west-2
```

The recovery point ARN must reference the destination region (created
by the cross-region copy action in the backup plan).

## Resource-type restore metadata fields

Each `--resource-type` has a different `--metadata` schema. The
canonical template is available via `get-recovery-point-restore-metadata`.

| Resource type | Required metadata fields |
|---|---|
| `EC2` | `InstanceId`, `SubnetId`, `SecurityGroupIds`, `InstanceType`; optional: `UserData`, `KeyName`, `IamInstanceProfile` |
| `RDS` | `NewDBInstanceIdentifier`, `DBInstanceClass`, `SubnetGroupName`, `SecurityGroups`, `AvailabilityZone`, `VpcSecurityGroupIds` |
| `Aurora` | `NewDBClusterIdentifier`, `DBClusterInstanceClass`, `VpcSecurityGroupIds`, `DBSubnetGroupName`, `EngineMode` |
| `EBS` | `VolumeId`, `AvailabilityZone`, `VolumeType`, `Iops`, `Throughput` |
| `S3` | `BucketName`, `NewKeyPrefix` (optional), `Encryption` (optional) |
| `DynamoDB` | `TableName`, `NewTableName` (for restore-to-new) |
| `EFS` | `NewFileSystemId`, `PerformanceMode`, `ThroughputMode`, `ProvisionedThroughputInMibps` |
| `FSx` (Windows) | `FileSystemId`, `SubnetIds`, `SecurityGroupIds`, `ActiveDirectoryId`, `DeploymentType`, `ThroughputCapacity` |
| `FSx` (Lustre) | `FileSystemId`, `SubnetIds`, `SecurityGroupIds`, `DeploymentType`, `PerUnitStorageThroughput`, `StorageType` |

## Common restore failures and remediations

| Failure | Root cause | Remediation |
|---|---|---|
| `FAILED: IAM role not authorized` | AWSBackupDefaultServiceRole missing service-specific permission | Add `ec2:RunInstances`, `rds:CreateDBInstance`, etc. to the role policy |
| `FAILED: Invalid metadata` | Missing required `--metadata` field for resource type | Use `get-recovery-point-restore-metadata` to get the template |
| `FAILED: KMS key inaccessible` | Destination region KMS key policy blocks `backup:Decrypt` | Update key policy to grant `backup.<region>.amazonaws.com` |
| `FAILED: Insufficient capacity` | Destination AZ lacks instance capacity | Use a different AZ or `InstanceType` |
| `FAILED: Recovery point expired` | Restore attempted after retention window | Cannot restore; the point is gone — use PITR within the window |
| `FAILED: Subnet not found` | `--metadata SubnetId` references wrong region or deleted subnet | Verify subnet exists in the restore region |
| `FAILED: Name conflict` | `InstanceId` / `NewDBInstanceIdentifier` already in use | Use a unique restore name (e.g., `i-restored-001`) |

## Restore drill checklist

A quarterly restore drill is required by most compliance frameworks:

1. Select a non-critical resource (or a non-production vault).
2. Capture the most recent recovery point ARN.
3. Start restore to a non-production subnet/security group.
4. Verify the restored resource boots / accepts connections / has the
   expected data.
5. Tear down the restored resource after the drill.
6. Document the drill: recovery point ARN, restore duration,
   verification results.

ALWAYS pair the drill with a vault lock audit (verify compliance mode
is still active, retention window unchanged).
---

### Start a point-in-time restore (PITR) (moved verbatim from SKILL.md)

```bash
aws backup start-restore-job \
  --recovery-point-arn arn:aws:backup:us-east-1:111111111111:recovery-point:1-2-3-4 \
  --metadata '{"InstanceId": "i-0 restored", "SubnetId": "subnet-abc123", "SecurityGroupIds": "sg-abc123", "InstanceType": "t3.medium"}' \
  --iam-role-arn "arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole" \
  --resource-type EC2
```

The `--metadata` fields vary by `--resource-type`. For RDS, use
`{"NewDBInstanceIdentifier": "restored-db"}`. For EBS, use
`{"VolumeId": "vol-..."}`. Use
`aws backup get-recovery-point-restore-metadata --recovery-point-arn
<arn>` to get the template metadata for the recovery point.

---

### Enable continuous backup for EC2 PITR (moved verbatim from SKILL.md)

Continuous backup is set in the backup plan rule via
`advanced backup settings` and the rule's continuous flag:

```bash
aws backup create-backup-plan \
  --backup-plan '{
    "BackupPlanName": "prod-ec2-pitr",
    "Rules": [
      {
        "RuleName": "ContinuousBackup",
        "TargetBackupVaultName": "prod-daily-vault",
        "ScheduleExpression": "cron(0 5 ? * * *)",
        "StartWindowMinutes": 60,
        "CompletionWindowMinutes": 1440,
        "ContinuousBackup": true
      }
    ],
    "AdvancedBackupSettings": [
      {"ResourceType": "EC2", "BackupOptions": {"WindowsVSS": "enabled"}}
    ]
  }'
```

EC2 PITR allows restoring to any 1-minute point within the past 35
days. Verify via `describe-recovery-point` that `ContinuousBackup:
true`.

