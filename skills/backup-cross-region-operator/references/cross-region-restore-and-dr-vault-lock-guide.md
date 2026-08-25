# Cross-region restore and DR vault lock guide

This reference covers the operational mechanics of restoring from
cross-region recovery points and applying vault locks to the DR
region's vault for immutability.

## Cross-region restore flow

1. **Verify the recovery point in the destination region:**

```bash
aws backup describe-recovery-point \
  --backup-vault-name dr-vault \
  --recovery-point-arn arn:aws:backup:us-west-2:111111111111:recovery-point:5-6-7-8 \
  --region us-west-2
```

The recovery point must show `Status: COMPLETED`. If it shows
`DELETED` or `EXPIRED`, restore is not possible.

2. **Invoke `start-restore-job` in the destination region:**

```bash
aws backup start-restore-job \
  --recovery-point-arn arn:aws:backup:us-west-2:111111111111:recovery-point:5-6-7-8 \
  --metadata '{"InstanceId":"i-restored-xregion","SubnetId":"subnet-xyz","SecurityGroupIds":"sg-xyz","InstanceType":"t3.medium"}' \
  --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
  --resource-type EC2 \
  --region us-west-2
```

The `--region` flag MUST be the destination region. The metadata
fields are destination-region-specific.

3. **Poll `describe-restore-job`:**

```bash
aws backup describe-restore-job --restore-job-id <id> --region us-west-2
```

Wait for `Status: COMPLETED` and `CreatedResourceArn` populated.

## Per-resource-type restore metadata

| ResourceType | Required metadata fields |
|---|---|
| `EC2` | InstanceId, SubnetId, SecurityGroupIds, InstanceType |
| `RDS` | NewDBInstanceIdentifier |
| `EBS` | VolumeId, AvailabilityZone |
| `S3` | BucketName (existing or new) |
| `DynamoDB` | TableName |
| `EFS` | NewFileSystemId, CreationToken |
| `Aurora` | DBClusterIdentifier |
| `FSx` | FileSystemType, SubnetIds |

Use `aws backup get-recovery-point-restore-metadata
--recovery-point-arn <arn> --backup-vault-name <vault> --region
<region>` to retrieve the template metadata for the recovery
point.

## DR vault lock (COMPLIANCE mode)

Apply to the destination region's vault for immutable DR:

```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name dr-vault \
  --changeable-for-days 3 \
  --min-retention-days 30 \
  --max-retention-days 3650 \
  --region us-west-2
```

The lock is **independent** of the source region's vault lock.
Each region's lock must be applied separately.

### Lock semantics

- **COMPLIANCE mode**: irreversible after the `ChangeableForDays`
  grace window (max 3 days). Even root cannot bypass.
- **GOVERNANCE mode**: soft-bypassable by privileged principal. Not
  suitable for regulatory compliance.
- `MinRetentionDays`: floor on recovery point deletion.
- `MaxRetentionDays`: ceiling on recovery point retention.
- The lock applies to ALL recovery points in the destination vault,
  including future cross-region copies.

### Lock and copy rule interaction

The copy rule's `CopyActions[].Lifecycle.DeleteAfterDays` must fit
within the destination vault's `MaxRetentionDays`. A copy rule
with `DeleteAfterDays: 365` writing to a locked destination vault
with `MaxRetentionDays: 90` will fail at delete time — recovery
points cannot be deleted and accumulate.

## Continuous backup cross-region

Source-region continuous backup (PITR) supports 1-second RPO within
the region. Cross-region copy of the continuous recovery point is
asynchronous — minutes to hours latency.

Cross-region **continuous** PITR is NOT supported. For
cross-region PITR:

- **Aurora**: use Aurora Global Database for cross-region read
  replica with promotion capability.
- **DynamoDB**: use global tables for multi-region active-active.
- **EC2**: no native cross-region PITR; application-level
  replication required.

## DR drill best practices

1. Quarterly DR drill: restore a sample recovery point from the DR
   region to a non-production VPC in the destination region.
2. Verify the restored resource boots and the application is
   functional.
3. Verify the IAM role and metadata template work end-to-end
   before an actual incident.
4. Document the recovery time objective (RTO) and recovery point
   objective (RPO) for each resource type.
5. Test the cross-account restore flow if applicable — verify KMS
   grants and IAM policies work in the destination region.

## Start a cross-region restore (boilerplate)

```bash
aws backup start-restore-job \
  --recovery-point-arn arn:aws:backup:us-west-2:111111111111:recovery-point:5-6-7-8 \
  --metadata '{"InstanceId":"i-restored-xregion","SubnetId":"subnet-xyz","SecurityGroupIds":"sg-xyz","InstanceType":"t3.medium"}' \
  --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
  --resource-type EC2 \
  --region us-west-2
```

Run the CLI in the destination region (`--region us-west-2`). The
`--metadata` fields are destination-region-specific.

## Apply vault lock on the DR vault — COMPLIANCE mode (boilerplate)

```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name dr-vault \
  --changeable-for-days 3 \
  --min-retention-days 30 \
  --max-retention-days 3650 \
  --region us-west-2
```

The lock is independent of the source region's vault lock. After
the 3-day grace, the lock is irreversible.
