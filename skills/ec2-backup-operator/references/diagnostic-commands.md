# Diagnostic Commands (load on demand) — EC2 Backup Operator

Pre-flight and diagnostic command listings, moved verbatim from SKILL.md.


---

## Pre-flight: Pagination rules and live-account pre-flight command list (moved from SKILL.md)

**Pagination:** `describe-snapshots` paginates at 500/page — ALWAYS pass
`--owner-ids self` (without it, the call returns every public snapshot in
the world and is rate-limited). `describe-images` paginates at 200/page
when filtering by owner. AWS Backup jobs paginate at 100/page.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws ec2 describe-instances --instance-ids <id>` — confirm `State` is
   `running` or `stopped` for AMI create; capture `BlockDeviceMappings`
   (volume-ids), `IamInstanceProfile`, `RootDeviceName`, VPC/subnet/SG
   context (needed for launch-from-AMI restore).
2. `aws ec2 describe-volumes --volume-ids <id>` — confirm `State: in-use`
   for attached volumes, capture `Encrypted`, `KmsKeyId`, `Size`,
   `VolumeType`, `Iops`, `Throughput`, `Attachments` (AttachTime, DeleteOnTermination).
3. `aws ec2 describe-snapshots --snapshot-ids <id> --owner-ids self` —
   confirm `State: completed`; capture `StartTime` (age), `VolumeId`,
   `Encrypted`, `KmsKeyId`, `Description`, `Tags`, `StorageTier` (standard
   vs archive).
4. `aws ec2 describe-images --image-ids <id> --owners self` — confirm
   `State: available`; capture `BlockDeviceMappings` (the snapshot-ids
   backing the AMI), `RootDeviceType`, `DeprecationTime`, `Tags`.
5. `aws ec2 describe-snapshot-attribute --snapshot-id <id> --attribute
   createVolumePermission` — for cross-account share, verify whether
   `Group: all` (public) or specific account IDs are present.
6. `aws kms describe-key --key-id <kms-key-id>` — for encrypted snapshots,
   confirm `KeyState: Enabled` and the key policy grants the caller
   `kms:Decrypt` and `kms:CreateGrant`. For cross-account copy, the source
   account's KMS key policy MUST grant the recipient.
7. `aws ec2 describe-fast-snapshot-restores` — for any snapshot targeted
   for delete, verify it is NOT FSR-enabled (deleting an FSR snapshot
   fails; FSR must be disabled first via `disable-fast-snapshot-restores`).
8. `aws backup describe-backup-vault --backup-vault-name <name>` — for
   vault operations, capture `VaultType`, `LockState` (`Unlocked` /
   `Locked` / `Compliance`), `MinRetentionDays`, `MaxRetentionDays`.
9. `aws backup get-backup-plan --backup-plan-id <id>` — for plan
   operations, capture rules, target vault, schedule, lifecycle.
10. `aws dlm get-lifecycle-policy --policy-id <id>` — for DLM, capture
    `PolicyType` (`EBS_SNAPSHOT_MANAGEMENT` / `IMAGE_MANAGEMENT`), schedule,
    target tags, `PolicyDetails`.

---

## Step 4: Post-verification — COMPLETED (moved from SKILL.md)

### Step 4: Post-verification — COMPLETED

After the operation finishes, run post-verification. ALL checks must pass
for `COMPLETED`.

1. `describe-snapshots --snapshot-ids <id>` — confirm `State: completed`.
2. `describe-images --image-ids <id>` — confirm `State: available`.
3. `describe-volumes --volume-ids <id>` — confirm `State: available` (pre-
   attach) or `in-use` (post-attach).
4. `describe-instances --instance-ids <id>` — confirm `State: running`.
5. For AWS Backup restore: `describe-restore-job --restore-job-id <id>` —
   confirm `Status: COMPLETED` and the created resource ARN.
6. For cross-account/cross-region: verify the recipient can `describe` and
   `create-volume`/`run-instances` from the new resource.
7. For application-consistent restore: fsck the volume, mount, and run a
   sentinel query (database checksum, file count).
8. Clean up temporary resources (verification volumes, restored instances).
9. Plan follow-up: tag the new resource, schedule lifecycle transition
   (archive tier, DLM policy attachment, AWS Backup plan attachment).

If ANY verification fails, emit `VERDICT: ERROR` with the failure details
— do not claim COMPLETED.
