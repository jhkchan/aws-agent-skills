# End-to-end usage scenario: rds-snapshot-operator

A walkthrough showing the skill planning a pre-upgrade manual snapshot
creation on an RDS MySQL instance, with all pre-checks passing and the
operator confirming at the CONFIRM gate. Contrasted with the
REVIEW_REQUIRED case where a PITR restore needs human attention for
option group and security group configuration.

## Input (user prompt)

> We need to create a manual snapshot of `prod-orders-db` before
> upgrading the MySQL engine from 8.0.35 to 8.0.36. Snapshot name:
> `prod-orders-db-pre-upgrade-20260805`. The instance is multi-AZ,
> encrypted, 500 GB.

```json
{
  "Operation": "create-snapshot",
  "Instance": "prod-orders-db",
  "SnapshotIdentifier": "prod-orders-db-pre-upgrade-20260805",
  "Reason": "pre-upgrade safety snapshot",
  "InstanceMetadata": {
    "DBInstanceStatus": "available",
    "Engine": "mysql",
    "EngineVersion": "8.0.35",
    "AllocatedStorage": 500,
    "Encrypted": true,
    "KmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/orders-cmk",
    "MultiAZ": true,
    "BackupRetentionPeriod": 7,
    "DeletionProtection": true,
    "OptionGroupMemberships": [{"OptionGroupName": "prod-orders-options"}]
  },
  "KmsKey": {"Enabled": true},
  "ExistingSnapshots": {"HasSnapshotWithIdentifier": false}
}
```

## Skill output

```text
OPERATION: create-snapshot
VERDICT: OPERATION_COMPLETED
TARGET: prod-orders-db (snapshot: prod-orders-db-pre-upgrade-20260805)
PRE_CHECKS:
  - [PASS] Instance prod-orders-db exists, Status: available
  - [PASS] No existing snapshot with identifier
    prod-orders-db-pre-upgrade-20260805
  - [PASS] AllocatedStorage: 500 GB (estimated snapshot time: 10-20 min)
  - [PASS] Encrypted: true, KMS key
    arn:aws:kms:us-east-1:111111111111:key/orders-cmk Enabled
STEPS:
  1. CONFIRM: About to create manual snapshot
     prod-orders-db-pre-upgrade-20260805 on instance prod-orders-db in
     account 111111111111 region us-east-1. This will take ~10-20 minutes.
     Proceed? (yes/no)
  2. aws rds create-db-snapshot \
       --db-instance-identifier prod-orders-db \
       --db-snapshot-identifier prod-orders-db-pre-upgrade-20260805
  3. aws rds describe-db-snapshots \
       --db-snapshot-identifier prod-orders-db-pre-upgrade-20260805 \
       --query 'DBSnapshots[0].Status'
POST_VERIFY:
  - [PASS] Snapshot Status: available
  - [PASS] Snapshot Encrypted: true (KMS key matches source)
  - [PASS] AllocatedStorage: 500 GB (matches source)
NOTES:
  - This snapshot is the pre-upgrade recovery point. If the upgrade
    fails, restore from this snapshot.
  - Manual snapshots persist beyond instance deletion. Tag this
    snapshot: Key=DoNotDelete,Value=true Key=Purpose,Value=pre-upgrade
```

## Contrast — REVIEW_REQUIRED case (PITR restore)

If the operator requested a point-in-time restore, the pre-check gate
would surface review items instead of proceeding directly:

```text
OPERATION: restore-pitr
VERDICT: REVIEW_REQUIRED
TARGET: prod-orders-db (restore-to: 2026-08-05T14:35:00Z)
PRE_CHECKS:
  - [PASS] BackupRetentionPeriod: 7 (>= 1, automated backups enabled)
  - [PASS] LatestRestorableTime: 2026-08-05T14:40:12Z
  - [PASS] Target time within restorable window
  - [REVIEW] Restore creates a NEW instance with a new endpoint.
    Connection strings must be updated post-restore.
  - [REVIEW] Option group prod-orders-options includes TDE. Must specify
    the SAME option group on restore or data will be unreadable.
  - [REVIEW] Security group sg-prod-rds must be specified explicitly.
    Restore defaults to DEFAULT security group.
  - [REVIEW] PITR granularity is 5 minutes for RDS. Actual restore time
    may be rounded to the nearest 5-minute boundary.
STEPS:
  1. CONFIRM: About to restore prod-orders-db to 2026-08-05T14:35:00Z
     as new instance prod-orders-db-pitr. Proceed? (yes/no)
  2. aws rds restore-db-instance-to-point-in-time \
       --source-db-instance-identifier prod-orders-db \
       --target-db-instance-identifier prod-orders-db-pitr \
       --restore-time 2026-08-05T14:35:00Z \
       --db-instance-class db.r6g.xlarge \
       --option-group-name prod-orders-options \
       --vpc-security-group-ids sg-prod-rds \
       --db-subnet-group-name prod-db-subnet-group
POST_VERIFY:
  - (pending execution)
NOTES:
  - After restore, update DNS/connection strings to the new endpoint.
  - The original instance is UNCHANGED. Delete manually after cutover.
```

## What the skill caught that a generic assistant misses

1. **Pre-check gate before any CLI executes.** A generic assistant
   emits the create-db-snapshot command directly. The skill runs
   deterministic pre-checks (instance state, KMS key, existing
   snapshot conflict, size/time estimate) before executing.

2. **Option group warning on restore.** A generic assistant omits that
   restore defaults to the DEFAULT option group. The skill surfaces
   the TDE issue (data unreadable without the correct option group).

3. **PITR granularity awareness.** A generic assistant does not mention
   the 5-minute rounding for RDS PITR. The skill surfaces this so the
   operator knows the actual restore point may differ slightly.

4. **Cross-region KMS re-encryption.** A generic assistant omits that
   encrypted snapshots require a target-region KMS key. The skill
   surfaces the re-encryption requirement and the key configuration.

5. **Aurora clone vs RDS restore.** A generic assistant does not
   distinguish between Aurora (instant copy-on-write clone) and RDS
   (proportional restore). The skill names the engine-specific behavior.

6. **Compliance-hold tag awareness.** A generic assistant would delete
   all old snapshots. The skill identifies snapshots tagged
   `DoNotDelete: true` and flags them for review.

7. **Manual snapshots persist beyond deletion.** A generic assistant
   does not emphasize this critical DR property. The skill surfaces it
   so the operator understands why manual snapshots are the compliance
   baseline.

## Slash-command invocation

```
/aws:operate-rds-snapshots
```

Or via the orchestrator:

```
/aws:pipeline
You: "create a pre-upgrade snapshot of prod-orders-db"
```

The orchestrator emits
`[Phase: Operate | Skills routed: rds-snapshot-operator]` and hands off
to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "create pre-upgrade snapshot of prod-orders-db"
# [Phase: Operate | Skills routed: rds-snapshot-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the snapshot is available:

```bash
# Verify snapshot properties
aws rds describe-db-snapshots \
  --db-snapshot-identifier prod-orders-db-pre-upgrade-20260805 \
  --profile default \
  --query 'DBSnapshots[0].{Status:Status,Encrypted:Encrypted,Storage:AllocatedStorage,Engine:Engine}'

# Tag the snapshot for compliance hold
aws rds add-tags-to-resource \
  --resource-name arn:aws:rds:us-east-1:111111111111:snapshot:prod-orders-db-pre-upgrade-20260805 \
  --tags Key=DoNotDelete,Value=true Key=Purpose,Value=pre-upgrade \
  --profile default

# Copy to DR region (encrypted, re-encrypt with DR key)
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:us-east-1:111111111111:snapshot:prod-orders-db-pre-upgrade-20260805 \
  --target-db-snapshot-identifier prod-orders-db-dr-20260805 \
  --kms-key-id arn:aws:kms:us-west-2:111111111111:key/dr-cmk \
  --region us-west-2 \
  --profile default
```
