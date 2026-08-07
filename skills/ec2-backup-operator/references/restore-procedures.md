# EC2 / EBS / AMI Restore Procedures Reference

Load this reference when planning or executing any EC2 restore operation.
The procedures below are the canonical sequences for each restore
archetype, with pre-checks, command sequence, post-verification, and
rollback notes.

## Decision tree — which restore archetype

| Scenario | Use | Why |
|---|---|---|
| Volume-level data rollback (file-level) | **create-volume from snapshot** + swap attach | Volume-level granularity; preserves the instance |
| Whole-instance rollback / migration | **launch from AMI** | Captures all volumes + metadata in one artifact |
| Compliance / WORM backup | **AWS Backup vault lock (compliance mode)** | Only native WORM for EC2/EBS |
| Cross-service DR (EC2 + RDS + EFS) | **AWS Backup plan** | Single plan, cross-region/cross-account copy |
| 1-second-granularity PITR for EC2 | **AWS Backup continuous backup** | Only native PITR; 35-day window |
| Automated daily snapshots with retention | **DLM lifecycle policy** | Simplest, schedule-based |
| Cross-region DR snapshot | **copy-snapshot cross-region** | Re-encrypts with destination-region KMS |
| Cross-account data sharing | **modify-snapshot-attribute + KMS grant** | Recipient creates volume or AMI in their account |
| Long-term cold retention (3+ months) | **Snapshot Archive tier** | $0.0125/GB-mo, 24-72 hr restore |
| Latency-sensitive snapshot restore | **Fast Snapshot Restore (FSR)** | Pre-warms volume to full IOPS on first read |

## Create-volume-from-snapshot procedure

**When to use:** volume-level data rollback without recreating the instance.

**Pre-checks:**
1. Source snapshot `State: completed`.
2. Destination AZ matches the target instance's AZ (for attach).
3. (For encrypted source) KMS key accessible to the caller.
4. (For resize) New `--size` >= snapshot size.

**Command sequence:**
```bash
# 1. Capture pre-state
aws ec2 describe-volumes --volume-ids <old-volume-id> \
  --output json > /tmp/<old-volume-id>-pre-$(date +%s).json

# 2. Create the new volume from the snapshot
aws ec2 create-volume \
  --snapshot-id <snap-id> \
  --availability-zone <target-az> \
  --volume-type gp3 \
  --iops 3000 --throughput 125 \
  --encrypted \
  --kms-key-id <kms-key-id> \
  --tag-specifications "ResourceType=volume,Tags=[{Key=restored-from,Value=<snap-id>},{Key=created-by,Value=ec2-backup-operator}]"

# 3. Wait for the volume to be available
aws ec2 wait volume-available --volume-ids <new-volume-id>

# 4. Detach the old volume (CONFIRM gate first)
aws ec2 detach-volume --volume-id <old-volume-id> --instance-id <instance-id> --device <device>

aws ec2 wait volume-in-use --volume-ids <old-volume-id> --filters Name=attachment.status,Values=detached
# OR poll until State: available

# 5. Attach the new volume
aws ec2 attach-volume \
  --volume-id <new-volume-id> \
  --instance-id <instance-id> \
  --device <device>

aws ec2 wait volume-in-use --volume-ids <new-volume-id>
```

**Post-verification:**
1. `describe-volumes --volume-ids <new-id>` → State: in-use, Attachments populated.
2. SSH/SSM into the instance, mount the volume, fsck if needed.
3. Run a sentinel check (file count, database checksum).
4. Tag the old volume with `delete-after` once the swap is verified.

## Launch-instances-from-AMI procedure

**When to use:** whole-instance restore or migration to new instance type.

**Pre-checks:**
1. AMI `State: available`, architecture matches the target instance type.
2. Subnet, security group, key pair, IAM instance profile all exist.
3. EBS-optimized instance type recommended for production.
4. `BlockDeviceMappings[].Ebs.DeleteOnTermination` set explicitly.

**Command sequence:**
```bash
# 1. Identify the AMI and its block device mappings
aws ec2 describe-images \
  --image-ids <ami-id> --owners self \
  --query 'Images[0].[BlockDeviceMappings,RootDeviceType,Architecture]'

# 2. Launch a replacement instance from the AMI
aws ec2 run-instances \
  --image-id <ami-id> \
  --instance-type t3.large \
  --subnet-id <subnet-id> \
  --security-group-ids <sg-id> \
  --key-name <key-name> \
  --iam-instance-profile Name=<profile-name> \
  --block-device-mappings '[
    {"DeviceName":"/dev/sda1","Ebs":{"VolumeType":"gp3","Iops":3000,"Throughput":125,"DeleteOnTermination":false}},
    {"DeviceName":"/dev/sdb","Ebs":{"VolumeType":"gp3","DeleteOnTermination":false}}
  ]' \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=restored-webapp},{Key=restored-from-ami,Value=<ami-id>},{Key=temp,Value=true}]"

# 3. Wait for the instance to be running
aws ec2 wait instance-running --instance-ids <new-instance-id>

# 4. Wait for status checks to pass
aws ec2 wait instance-status-ok --instance-ids <new-instance-id>
```

**Post-verification:**
1. `describe-instances --instance-ids <new-id>` → State: running.
2. Application health check (HTTP 200, DB connectivity).
3. Log streaming (CloudWatch agent / SSM agent) active.
4. Plan connection-string cutover: new private IP, new ENI id.

## AWS Backup restore job procedure

**When to use:** cross-service restore, PITR for EC2, vault-locked backups.

**Pre-checks:**
1. Recovery point ARN valid and `Status: COMPLETED`.
2. Restore IAM role trusts `backup.amazonaws.com`.
3. Metadata (InstanceType, SubnetId, SecurityGroupIds) populated.
4. Target subnet has capacity for the instance type.

**Command sequence:**
```bash
# 1. Identify the recovery point
aws backup describe-recovery-point \
  --backup-vault-name <vault-name> \
  --recovery-point-arn <recovery-point-arn>

# 2. Start the restore job
aws backup start-restore-job \
  --recovery-point-arn <recovery-point-arn> \
  --iam-role-arn arn:aws:iam::<acct>:role/service-role/AWSBackupRestoreRole \
  --metadata '{
    "InstanceType":"t3.large",
    "SubnetId":"subnet-0prod",
    "SecurityGroupIds":["sg-0prod"],
    "IamInstanceProfile":"arn:aws:iam::<acct>:instance-profile/prod-webapp",
    "DeleteOnTermination":"false"
  }' \
  --resource-type EC2

# 3. Wait for the restore to complete
aws backup wait restore-job-completed --restore-job-id <RestoreJobId>

# 4. Identify the restored resource
aws backup describe-restore-job --restore-job-id <RestoreJobId> \
  --query 'CreatedResourceArn'
```

**Post-verification:**
1. `describe-restore-job` → Status: COMPLETED.
2. `describe-instances --instance-ids <new-id>` → State: running.
3. Application health check.
4. Connection-string cutover (new private IP).

## Cross-region snapshot copy procedure

**When to use:** DR-region seeding, multi-region AMI distribution.

**Pre-checks:**
1. Source snapshot `State: completed`.
2. Destination region opted-in.
3. Destination-region KMS key specified (encrypted source).
4. Cost surfaced: $0.02/GB transfer + destination-region storage.

**Command sequence:**
```bash
# 1. Initiate the cross-region copy
aws ec2 copy-snapshot \
  --source-region us-east-1 \
  --source-snapshot-id snap-0source123 \
  --destination-region us-west-2 \
  --description "DR copy of snap-0source123" \
  --encrypted \
  --kms-key-id arn:aws:kms:us-west-2:111111111111:key/dr-key \
  --tag-specifications "ResourceType=snapshot,Tags=[{Key=copied-from,Value=snap-0source123},{Key=source-region,Value=us-east-1},{Key=purpose,Value=dr-copy}]"

# 2. Wait for the destination snapshot to be completed
# (use the destination region in the client)
aws ec2 wait snapshot-completed --snapshot-ids <destination-snap-id> --region us-west-2
```

**Post-verification:**
1. `describe-snapshots --snapshot-ids <dest-id> --region us-west-2` → State: completed.
2. Recipient account can `create-volume` from the snapshot (test-restore).
3. Tag the destination snapshot with `delete-after` once the DR plan is validated.

## AMI cleanup procedure (deregister + delete-snapshot)

**When to use:** cleaning up old or deprecated AMIs to recover storage cost.

**Pre-checks:**
1. AMI not referenced by any ASG launch template, EC2 Image Builder pipeline,
   or recent launch (`describe-instances --filters Name=image-id,Values=<ami-id>`).
2. Snapshots backing the AMI are NOT shared with another account.
3. Snapshots are NOT FSR-enabled.

**Command sequence:**
```bash
# 1. Identify the snapshots backing the AMI
aws ec2 describe-images --image-ids <ami-id> --owners self \
  --query 'Images[0].BlockDeviceMappings[*].Ebs.SnapshotId' \
  --output text

# 2. Deregister the AMI (metadata only; snapshots preserved)
aws ec2 deregister-image --image-id <ami-id>

# 3. Verify no remaining AMI references each snapshot
for snap_id in snap-0aaa snap-0bbb snap-0ccc; do
  aws ec2 describe-images --owners self \
    --filters Name=BlockDeviceMapping.SnapshotId,Values=$snap_id \
    --query 'Images[*].ImageId' --output text
  # MUST return empty before delete
done

# 4. Verify FSR status (must be empty before delete)
for snap_id in snap-0aaa snap-0bbb snap-0ccc; do
  aws ec2 describe-fast-snapshot-restores \
    --filters Name=snapshot-id,Values=$snap_id
done

# 5. Delete each snapshot
for snap_id in snap-0aaa snap-0bbb snap-0ccc; do
  aws ec2 delete-snapshot --snapshot-id $snap_id
done
```

**Post-verification:**
1. `describe-images --image-ids <ami-id>` → InvalidAMIID.NotFound (expected).
2. `describe-snapshots --snapshot-ids <snap-id>` → InvalidSnapshot.NotFound.
3. Billing: storage cost will drop only after the blocks are unreferenced
   by any other snapshot (may lag by weeks).

## Common failure modes (root-cause cheat sheet)

| Symptom | Likely root cause | Diagnostic |
|---|---|---|
| Snapshot `State: pending` for > 30 min | S3 eventual consistency on first full snapshot of a large volume | Wait; check `Progress` field |
| `create-image` fails with `InvalidParameterValue` | Instance in `shutting-down`, `pending`, or `terminated` state | `describe-instances --instance-ids <id>` |
| `copy-snapshot` cross-account fails with `AccessDenied` | Source KMS key policy missing recipient grant | `get-key-policy` |
| `delete-snapshot` returns `InvalidSnapshot.InUse` | Snapshot referenced by a registered AMI OR FSR-enabled | `describe-images` + `describe-fast-snapshot-restores` |
| Vault lock delete returns `InvalidParameter` | Compliance mode + cool-down passed | `describe-backup-vault` LockState |
| AWS Backup restore job `FAILED` | Subnet IP exhaustion, KMS inaccessible, IAM role revoked | `describe-restore-job` StatusMessage |
| DLM policy `State: ERROR` | IAM role drift (lost `ec2:CreateSnapshot`) | `get-lifecycle-policy` LastExecutionStatus |
| AMI launch fails with `Unsupported` | Architecture mismatch (x86_64 AMI on graviton) | `describe-images` Architecture |
| FSR cost > storage cost | FSR enabled in multiple AZs | `describe-fast-snapshot-restores` |
| Restored volume `State: error` | KMS key disabled mid-restore | `describe-keys` |
