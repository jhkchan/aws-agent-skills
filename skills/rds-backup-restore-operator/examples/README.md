# End-to-end usage scenario: rds-backup-restore-operator

A walkthrough showing the skill planning a PITR restore for a production
MySQL instance where a bad migration was applied 30 minutes ago. The
pre-checks pass on retention, restore window, and all target resources,
producing a READY plan with the exact CLI sequence, the CONFIRM gate,
and the connection-string update step — and contrasted with the BLOCKED
case where the target subnet group is missing.

## Input (user prompt)

> We applied a bad migration to prod-orders-db at 10:05 UTC. We need to
> restore to 10:00 UTC. The instance is MySQL 8.0, 500 GB, encrypted,
> Multi-AZ.

```json
{
  "Operation": "pitr-restore",
  "Source": "prod-orders-db",
  "Target identifier": "prod-orders-db-pitr-2026-08-07",
  "Restore time": "2026-08-07T10:00:00Z",
  "Target DB subnet group": "prod-subnet-group",
  "Target security group": "sg-prod-rds",
  "Target option group": "default:mysql-8-0",
  "Target parameter group": "prod-mysql80",
  "KMS key": "arn:aws:kms:us-east-1:111111111111:key/prod-key",
  "SourceInstance": {
    "DBInstanceIdentifier": "prod-orders-db",
    "DBInstanceStatus": "available",
    "Engine": "mysql",
    "EngineVersion": "8.0.35",
    "AllocatedStorage": 500,
    "BackupRetentionPeriod": 7,
    "EarliestRestorableTime": "2026-07-31T00:00:00Z",
    "LatestRestorableTime": "2026-08-07T10:55:00Z",
    "StorageEncrypted": true,
    "MultiAZ": true,
    "KmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/prod-key"
  },
  "TargetResourceChecks": {
    "describe-db-subnet-groups.prod-subnet-group": "OK (subnets in 3 AZs)",
    "describe-security-groups.sg-prod-rds": "OK",
    "describe-option-groups.default:mysql-8-0": "OK",
    "describe-db-parameter-groups.prod-mysql80": "OK",
    "kms.describe-key.prod-key": "OK (key enabled, policy grants kms:Decrypt)"
  }
}
```

## Skill output

```text
OPERATION: pitr-restore
VERDICT: READY
TARGET: prod-orders-db -> prod-orders-db-pitr-2026-08-07
PRE_CHECKS:
  - [PASS] prod-orders-db DBInstanceStatus is available
  - [PASS] BackupRetentionPeriod is 7 (> 0, PITR enabled)
  - [PASS] RestoreTime 2026-08-07T10:00:00Z is within window
    [2026-07-31T00:00:00Z, 2026-08-07T10:55:00Z] (5 min before the bad
    migration at 10:05 UTC)
  - [PASS] Target identifier prod-orders-db-pitr-2026-08-07 does not exist
  - [PASS] DB subnet group prod-subnet-group has subnets in 3 AZs
    (Multi-AZ restore supported)
  - [PASS] Security group sg-prod-rds exists in vpc-vpc-12345
  - [PASS] Option group default:mysql-8-0 matches engine mysql 8.0.35
  - [PASS] Parameter group prod-mysql80 matches engine mysql 8.0.35
  - [PASS] KMS key arn:aws:kms:us-east-1:111111111111:key/prod-key accessible
    (kms:Decrypt, kms:CreateGrant granted)
STEPS:
  1. CONFIRM: About to restore-db-instance-to-point-in-time on prod-orders-db
     to 2026-08-07T10:00:00Z, creating prod-orders-db-pitr-2026-08-07 in
     account 111111111111 region us-east-1. This will create a NEW instance
     with a NEW endpoint (original prod-orders-db is unchanged and continues
     to bill). Estimated duration: 60-90 minutes for 500 GB. Proceed? (yes/no)
  2. aws rds restore-db-instance-to-point-in-time \
       --source-db-instance-identifier prod-orders-db \
       --target-db-instance-identifier prod-orders-db-pitr-2026-08-07 \
       --restore-time 2026-08-07T10:00:00Z \
       --db-subnet-group-name prod-subnet-group \
       --vpc-security-group-ids sg-prod-rds \
       --option-group-name default:mysql-8-0 \
       --db-parameter-group-name prod-mysql80 \
       --no-deletion-protection \
       --tags Key=restored-from,Value=prod-orders-db \
              Key=restore-reason,Value=bad-migration-2026-08-07 \
              Key=temp,Value=true \
              Key=delete-after,Value=2026-08-21
  3. aws rds wait db-instance-available \
       --db-instance-identifier prod-orders-db-pitr-2026-08-07
POST_VERIFY:
  - (pending execution)
  - aws rds describe-db-instances --db-instance-identifier \
      prod-orders-db-pitr-2026-08-07 → DBInstanceStatus: available
  - mysql -h <new-endpoint> -u admin -p → connect OK
  - SELECT COUNT(*) FROM orders.orders_by_date → row count matches
    pre-migration state
  - Verify the migration's sentinel row is ABSENT (rewound to 10:00 UTC)
  - aws rds modify-db-instance --db-instance-identifier \
      prod-orders-db-pitr-2026-08-07 --deletion-protection \
      --apply-immediately (set after verification)
ENDPOINT: (pending — will be prod-orders-db-pitr-2026-08-07.<random>.us-east-1.rds.amazonaws.com)
NOTES:
  - The new instance has a NEW endpoint. Update application connection
    strings atomically during cutover:
      * Application env vars / config files
      * Secrets Manager secret prod/orders-db
      * Parameter Store /rds/orders-db-endpoint
      * Route 53 CNAME orders-db.internal → new endpoint
  - The original prod-orders-db is UNCHANGED and continues to bill. Plan
    cleanup: snapshot + delete the original after cutover is verified.
  - The restored instance is created WITHOUT deletion protection initially;
    enable it via modify-db-instance after the post-verification passes.
  - The restored instance is tagged `temp: true, delete-after: 2026-08-21`
    for automated cleanup if cutover does not happen.
  - Multi-AZ is NOT enabled on the restored instance by default; enable
    after verification if the original was Multi-AZ.
```

## Contrast — BLOCKED case (target subnet group missing)

If the operator had specified `dr-subnet-group` (a non-existent subnet
group), the pre-check gate would fire and no CLI would execute:

```text
OPERATION: pitr-restore
VERDICT: BLOCKED
TARGET: prod-orders-db -> prod-orders-db-pitr-2026-08-07
PRE_CHECKS:
  - [PASS] prod-orders-db DBInstanceStatus is available
  - [PASS] BackupRetentionPeriod is 7 (> 0, PITR enabled)
  - [PASS] RestoreTime is within window
  - [PASS] Target identifier does not exist
  - [FAIL] DB subnet group dr-subnet-group does not exist
    (DBSubnetGroupNotFoundFault). The restore would download the 500 GB
    snapshot and then fail at the network configuration step, wasting
    30-45 minutes.
  - [PASS] Security group sg-prod-rds exists
  - [PASS] Option group default:mysql-8-0 matches
  - [PASS] Parameter group prod-mysql80 matches
  - [PASS] KMS key accessible
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
ENDPOINT: (none)
NOTES:
  - Create the target DB subnet group before retrying:
    aws rds create-db-subnet-group --db-subnet-group-name dr-subnet-group \
      --db-subnet-group-description "DR subnet group" \
      --subnet-ids subnet-aaa subnet-bbb subnet-ccc
  - Or restore into the existing prod-subnet-group (the source VPC) and
    migrate cross-VPC afterward.
```

## What the skill caught that a generic assistant misses

1. **Pre-check gate before any CLI executes.** A generic assistant emits
   the restore command directly. The skill runs 9 deterministic pre-checks
   and BLOCKS before downloading a 500 GB snapshot that would fail at the
   subnet configuration step, wasting 30-45 minutes.

2. **PITR window validation.** A generic assistant takes the operator's
   `--restore-time` at face value. The skill verifies the restore time is
   within `[EarliestRestorableTime, LatestRestorableTime]` and surfaces
   that `LatestRestorableTime` is 10:55 UTC (5 min lag) — restoring to
   10:00 UTC is valid; restoring to "right now" is not.

3. **`BackupRetentionPeriod: 0` detection.** A generic assistant emits the
   restore command and lets the API return
   `InvalidParameterValue: BackupRetentionPeriod is 0`. The skill catches
   this in pre-checks and surfaces the modify-db-instance remediation
   before any CLI runs.

4. **New endpoint + connection-string cutover plan.** A generic assistant
   mentions "the new endpoint" in passing. The skill enumerates every
   place the endpoint must be updated (env vars, Secrets Manager, Parameter
   Store, Route 53) and surfaces the cutover as an atomic step.

5. **Original instance unchanged + cleanup plan.** A generic assistant
   omits that the original `prod-orders-db` continues to bill. The skill
   surfaces the cleanup plan (snapshot + delete the original after
   cutover) and tags the restored instance with `delete-after: 2026-08-21`
   for automated cleanup.

6. **Deletion protection lifecycle.** A generic assistant omits that the
   restored instance is created without deletion protection (it would
   block the restore). The skill surfaces the post-verification step to
   re-enable deletion protection.

7. **Multi-AZ flag.** A generic assistant omits that the restored instance
   is single-AZ by default even if the source was Multi-AZ. The skill
   surfaces the modify step to re-enable Multi-AZ.

8. **CONFIRM gate.** A generic assistant auto-executes. The skill emits
   `CONFIRM:` and waits — restore creates a billable instance and a
   duplicate workload, the operator must explicitly approve.

## Slash-command invocation

```
/aws:operate-rds-backup-restore
```

Or via the orchestrator:

```
/aws:pipeline
You: "restore prod-orders-db to 10:00 UTC before the bad migration"
```

The orchestrator emits
`[Phase: Operate | Skills routed: rds-backup-restore-operator]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "restore RDS prod-orders-db to point in time"
# [Phase: Operate | Skills routed: rds-backup-restore-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the restore completes and application traffic is cut over:

```bash
# Verify the restored instance is available and serves traffic
aws rds describe-db-instances --db-instance-identifier prod-orders-db-pitr-2026-08-07 \
  --profile default --query 'DBInstances[0].{Status:DBInstanceStatus,Endpoint:Endpoint.Address,MultiAZ:MultiAZ}' \
  --output json

# Test connectivity from an application host
mysql -h prod-orders-db-pitr-2026-08-07.<random>.us-east-1.rds.amazonaws.com \
  -u admin -p"$(aws secretsmanager get-secret-value --secret-id prod/orders-db \
    --query SecretString --output text | jq -r .password)" \
  -e "SELECT COUNT(*) FROM orders.orders_by_date"

# Verify the bad migration is reversed
mysql -h ... -e "SHOW COLUMNS FROM orders.orders_by_date LIKE 'legacy_field'"
# legacy_field should be ABSENT (restored to before the migration that added it)

# Enable Multi-AZ + deletion protection on the restored instance
aws rds modify-db-instance \
  --db-instance-identifier prod-orders-db-pitr-2026-08-07 \
  --multi-az --deletion-protection --apply-immediately \
  --profile default

# After cutover is verified, snapshot and delete the original instance
aws rds create-db-snapshot --db-instance-identifier prod-orders-db \
  --db-snapshot-identifier prod-orders-db-pre-deletion-$(date +%Y%m%d) \
  --profile default
aws rds wait db-snapshot-available --db-snapshot-identifier prod-orders-db-pre-deletion-$(date +%Y%m%d)
aws rds delete-db-instance --db-instance-identifier prod-orders-db \
  --final-db-snapshot-identifier prod-orders-db-final \
  --profile default
```
