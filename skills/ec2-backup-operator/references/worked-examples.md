# Worked Examples (load on demand) — EC2 Backup Operator

Secondary worked examples and CLI/code patterns, moved verbatim from SKILL.md.


---

## Worked examples — cross-account share BLOCKED, AWS Backup restore job, DLM policy creation (moved from SKILL.md)

### Worked example — cross-account encrypted snapshot share BLOCKED

```text
OPERATION: copy-snapshot (cross-account, encrypted)
VERDICT: BLOCKED
TARGET: snap-0enc1234567890abc -> recipient account 222222222222
PRE_CHECKS:
  - [PASS] Snapshot State completed
  - [PASS] Snapshot Encrypted with KMS key arn:aws:kms:us-east-1:111111111111:key/abc
  - [PASS] Snapshot attribute createVolumePermission includes
    222222222222 (shared with recipient)
  - [FAIL] KMS key policy for arn:aws:kms:us-east-1:111111111111:key/abc
    does NOT grant 222222222222 kms:Decrypt or kms:CreateGrant.
    Recipient can describe-snapshots but cannot create-volume or
    copy-snapshot — the data is unreadable.
  - [PASS] Destination region us-west-2 opted-in
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
NEW_RESOURCE: (none)
REBOOT: n/a
NOTES:
  - Update the source account's KMS key policy to grant the recipient:
      {
        "Sid": "Allow recipient account to use the snapshot",
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
        "Action": ["kms:Decrypt", "kms:CreateGrant", "kms:DescribeKey"],
        "Resource": "*"
      }
    Then re-fetch: aws kms get-key-policy --key-id <key-id>
    --policy-name default.
  - OR re-issue the snapshot unencrypted via copy-snapshot --encrypted
    is NOT possible (encryption is immutable per resource); instead
    create a new unencrypted snapshot from the volume directly.
  - For cross-region: the recipient will additionally need to re-encrypt
    with their own KMS key in the destination region during copy-snapshot.
```

### Worked example — AWS Backup restore job

```text
OPERATION: start-restore-job (AWS Backup, EC2)
VERDICT: READY
TARGET: arn:aws:backup:us-east-1:111111111111:recovery-point:1a2b3c-4d5e-6f7g
PRE_CHECKS:
  - [PASS] Recovery point Status COMPLETED
  - [PASS] Recovery point ResourceArn is the source EC2 instance
  - [PASS] Restore IAM role arn:aws:iam::111111111111:role/service-role/AWSBackupRestoreRole
    trusts backup.amazonaws.com
  - [PASS] Metadata includes InstanceType, SubnetId, SecurityGroupIds,
    IamInstanceProfile (recovery-point defaults are valid)
  - [PASS] Target subnet has capacity for the instance type
STEPS:
  1. CONFIRM: About to start-restore-job from recovery-point
     1a2b3c-4d5e-6f7g in account 111111111111 region us-east-1. This
     will create a NEW EC2 instance with NEW volume-ids and a NEW ENI
     (original instance unchanged). Estimated duration: 15-30 minutes.
     Proceed? (yes/no)
  2. aws backup start-restore-job \
       --recovery-point-arn arn:aws:backup:us-east-1:111111111111:recovery-point:1a2b3c-4d5e-6f7g \
       --iam-role-arn arn:aws:iam::111111111111:role/service-role/AWSBackupRestoreRole \
       --metadata '{"InstanceType":"t3.large","SubnetId":"subnet-0prod","SecurityGroupIds":["sg-0prod"],"IamInstanceProfile":"arn:aws:iam::111111111111:instance-profile/prod-webapp","DeleteOnTermination":"false"}' \
       --resource-type EC2
  3. aws backup wait restore-job-completed --restore-job-id <RestoreJobId from step 2>
POST_VERIFY:
  - (pending execution)
  - aws backup describe-restore-job --restore-job-id <RestoreJobId>
    → Status: COMPLETED, CreatedResourceArn: arn:aws:ec2:...
  - aws ec2 describe-instances --instance-ids <instance-id from CreatedResourceArn>
    → State: running
  - Verify application on the new instance (HTTP 200, DB connectivity)
  - Plan connection-string cutover: original instance continues to bill
NEW_RESOURCE: (pending — will be a new EC2 instance-id and restore-job-id)
REBOOT: n/a (new instance)
NOTES:
  - The new instance has a NEW private IP (unless explicitly assigned).
    Update DNS, secrets manager, and connection strings atomically.
  - DeleteOnTermination=false on the root volume preserves data on
    instance termination.
  - Tag the restored instance with restored-from=<recovery-point-arn>
    and delete-after for cleanup.
  - Original instance unchanged — plan decommission separately.
```

### Worked example — DLM policy creation

```text
OPERATION: create-lifecycle-policy (DLM)
VERDICT: READY
TARGET: tag:BackupSchedule=daily (10 volumes match)
PRE_CHECKS:
  - [PASS] PolicyType EBS_SNAPSHOT_MANAGEMENT
  - [PASS] Schedule cron rate(1 day) valid; create-interval 24h
  - [PASS] Target tags Key=BackupSchedule,Values=daily → 10 volumes match
    (verified via ec2 describe-volumes --filters)
  - [PASS] IAM role AWS-DLM-LifeCycleRole exists, trusts dlm.amazonaws.com,
    has ec2:CreateSnapshot/CreateTags/DeleteSnapshot on the volume ARNs
  - [PASS] Retention count 7 (7 daily snapshots), reasonable
  - [PASS] Copy-tags-from-source=true (lineage preserved)
  - [PASS] Cross-region copy NOT configured (single-region policy)
STEPS:
  1. CONFIRM: About to create-lifecycle-policy in account 111111111111
     region us-east-1. This will take a daily snapshot of 10 volumes
     tagged BackupSchedule=daily, retain 7 snapshots per volume (~70 GB-
     month added storage initially). Proceed? (yes/no)
  2. aws dlm create-lifecycle-policy \
       --description "Daily snapshots of volumes tagged BackupSchedule=daily" \
       --state ENABLED \
       --execution-role-arn arn:aws:iam::111111111111:role/service-role/AWS-DLM-LifeCycleRole \
       --policy-details '{
         "PolicyType": "EBS_SNAPSHOT_MANAGEMENT",
         "ResourceTypes": ["VOLUME"],
         "TargetTags": [{"Key": "BackupSchedule", "Value": "daily"}],
         "Schedules": [{
           "Name": "Daily",
           "CreateRule": {"Interval": 24, "IntervalUnit": "HOURS", "Times": ["03:00"]},
           "RetainRule": {"Count": 7},
           "CopyTags": true,
           "FastRestoreRule": {"Interval": 0, "IntervalUnit": "HOURS"}
         }]
       }'
  3. aws dlm get-lifecycle-policy --policy-id <PolicyId from step 2>
POST_VERIFY:
  - (pending first execution at 03:00 UTC)
  - aws dlm get-lifecycle-policy --policy-id <PolicyId>
    → State: ENABLED, no recent failures
  - After 03:00 UTC: aws ec2 describe-snapshots --owner-ids self
    --filters Name=tag:dlm:policy,Values=<PolicyId> → 10 snapshots State completed
NEW_RESOURCE: (pending — will be a DLM policy-id)
REBOOT: n/a
NOTES:
  - DLM does NOT capture instance metadata (AMI is the right tool for
    that). Use PolicyType=IMAGE_MANAGEMENT for instance-level DLM.
  - Retain count 7 keeps 7 daily snapshots; older snapshots auto-deleted.
  - Review the policy weekly for `State: ERROR` (often IAM role drift).
  - For cross-region DR via DLM, add a `CrossRegionCopyRule` (separate
    region, separate KMS key).
```
