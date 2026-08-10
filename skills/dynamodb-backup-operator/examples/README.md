# End-to-end usage scenario: dynamodb-backup-operator

A walkthrough showing the skill planning a PITR restore for a production
DynamoDB table where a bad migration was applied ~5 minutes ago. The
pre-checks pass on PITR enablement, restore window, target name, and
CMK access, producing a READY plan with the exact CLI sequence, the
CONFIRM gate, and the side-config re-apply checklist — and contrasted
with the BLOCKED case where PITR is disabled.

## Input (user prompt)

> We applied a bad migration to prod-orders-table at 10:05 UTC, writing
> ~50K bad rows. We need to restore to 10:00 UTC. The table is
> provisioned (5000 RCU / 2000 WCU), 80 GB, encrypted with a customer
> CMK.

```json
{
  "Operation": "pitr-restore",
  "Source": "prod-orders-table",
  "Target table name": "prod-orders-table-pitr-2026-08-09",
  "Restore time": "2026-08-09T10:00:00Z",
  "SourceTable": {
    "TableName": "prod-orders-table",
    "TableStatus": "ACTIVE",
    "BillingModeSummary": {"BillingMode": "PROVISIONED"},
    "ProvisionedThroughput": {"ReadCapacityUnits": 5000, "WriteCapacityUnits": 2000},
    "SSEDescription": {
      "SSEType": "KMS",
      "KMSMasterKeyArn": "arn:aws:kms:us-east-1:111111111111:key/prod-key"
    },
    "GlobalSecondaryIndexes": ["gsi-order-status", "gsi-customer-id"],
    "DeletionProtectionEnabled": true
  },
  "ContinuousBackups": {
    "ContinuousBackupsStatus": "ENABLED",
    "PointInTimeRecoveryDescription": {
      "PointInTimeRecoveryStatus": "ENABLED",
      "EarliestRestorableDateTime": "2026-07-05T00:00:00Z",
      "LatestRestorableDateTime": "2026-08-09T10:59:30Z"
    }
  },
  "TargetNameCheck": "prod-orders-table-pitr-2026-08-09 does not exist",
  "KmsAccess": "arn:aws:kms:us-east-1:111111111111:key/prod-key is accessible"
}
```

## Skill output

```text
OPERATION: pitr-restore
VERDICT: READY
TARGET: prod-orders-table -> prod-orders-table-pitr-2026-08-09
PRE_CHECKS:
  - [PASS] prod-orders-table TableStatus is ACTIVE
  - [PASS] PointInTimeRecoveryStatus is ENABLED
  - [PASS] RestoreDateTime 2026-08-09T10:00:00Z is within window
    [2026-07-05T00:00:00Z, 2026-08-09T10:59:30Z] (5 min before the bad
    migration at 10:05 UTC)
  - [PASS] Target table name prod-orders-table-pitr-2026-08-09 does not exist
  - [PASS] Caller IAM role has dynamodb:RestoreTableToPointInTime
  - [PASS] CMK arn:aws:kms:us-east-1:111111111111:key/prod-key accessible
STEPS:
  1. CONFIRM: About to restore-table-to-point-in-time on prod-orders-table
     to 2026-08-09T10:00:00Z, creating prod-orders-table-pitr-2026-08-09 in
     account 111111111111 region us-east-1. This will create a NEW table
     (original unchanged). Estimated duration: 20-40 minutes for ~80 GB.
     Proceed? (yes/no)
  2. aws dynamodb restore-table-to-point-in-time \
       --source-table-name prod-orders-table \
       --target-table-name prod-orders-table-pitr-2026-08-09 \
       --restore-date-time 2026-08-09T10:00:00Z \
       --billing-mode-override PAY_PER_REQUEST \
       --tags Key=restored-from,Value=prod-orders-table \
              Key=restore-reason,Value=bad-migration-2026-08-09 \
              Key=temp,Value=true \
              Key=delete-after,Value=2026-08-23
  3. Poll: aws dynamodb describe-table \
       --table-name prod-orders-table-pitr-2026-08-09 \
       --query 'Table.TableStatus'
     Wait for ACTIVE (RESTORING -> ACTIVE).
POST_VERIFY:
  - (pending execution)
  - aws dynamodb describe-table --table-name \
      prod-orders-table-pitr-2026-08-09 → TableStatus: ACTIVE
  - ItemCount matches prod-orders-table at 10:00 UTC (~4,827,193)
  - gsi-order-status and gsi-customer-id both ACTIVE
  - Sentinel get-item on id=sentinel-001 returns the expected value
TABLE_ARN: (pending — will be arn:aws:dynamodb:us-east-1:111111111111:table/prod-orders-table-pitr-2026-08-09)
NOTES:
  - The new table has a NEW name. Update application connection strings
    atomically during cutover:
      * Application env vars / config files
      * Secrets Manager secret prod/orders-table
      * Parameter Store /dynamodb/orders-table-name
      * IAM resource policies referencing the table ARN
  - Restore does NOT copy these — reconfigure each on the new table:
      * Auto-scaling policies (or use --billing-mode-override PAY_PER_REQUEST,
        as in this plan, to skip autoscaling re-registration)
      * DynamoDB Streams (re-enable if the source had streams)
      * TTL (re-apply update-time-to-live)
      * CloudWatch alarms (re-create referencing the new table name)
      * IAM resource policies (update ARN references)
      * Tags (re-apply via tag-resource)
      * DeletionProtectionEnabled (set via update-table post-verification)
  - The original prod-orders-table is UNCHANGED and continues to bill.
    Plan cleanup: snapshot the original (create-backup) and delete after
    cutover is verified.
  - The restored table is tagged `temp: true, delete-after: 2026-08-23`
    for automated cleanup if cutover does not happen.
```

## Contrast — BLOCKED case (PITR disabled)

If the table had `PointInTimeRecoveryStatus: DISABLED`, the pre-check
gate would fire and no CLI would execute:

```text
OPERATION: pitr-restore
VERDICT: BLOCKED
TARGET: prod-orders-table -> prod-orders-table-pitr-2026-08-09
PRE_CHECKS:
  - [PASS] prod-orders-table TableStatus is ACTIVE
  - [FAIL] PointInTimeRecoveryStatus is DISABLED — PITR restore not
    possible. The table has no 35-day continuous recovery window.
    Bad writes/deletes between snapshots are unrecoverable without PITR.
  - [SKIP] RestoreDateTime window check skipped (PITR disabled)
  - [PASS] Target table name does not exist (would be valid if PITR
    were enabled)
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
TABLE_ARN: (none)
NOTES:
  - To enable PITR going forward:
      aws dynamodb update-continuous-backups \
        --table-name prod-orders-table \
        --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
    PITR becomes available within seconds; EarliestRestorableDateTime is
    the moment of enablement.
  - For THIS incident, recover from the most recent on-demand backup:
      aws dynamodb list-backups --table-name prod-orders-table \
        --backup-type USER --time-range-lower-bound 2026-07-01T00:00:00Z
    Then restore-table-from-backup with the latest USER backup ARN
    (recovery point = backup creation instant, not any second).
```

## What the skill caught that a generic assistant misses

1. **Pre-check gate before any CLI executes.** A generic assistant
   emits the restore command directly, which fails with
   `PointInTimeRecoveryUnavailableException` at the API. The skill
   catches PITR state in pre-checks and BLOCKS before any CLI runs.

2. **PITR window validation.** A generic assistant takes the operator's
   `--restore-date-time` at face value. The skill verifies the restore
   time is within `[EarliestRestorableDateTime, LatestRestorableDateTime]`
   and surfaces that `LatestRestorableDateTime` is 10:59:30 UTC —
   restoring to 10:00 UTC is valid.

3. **`PointInTimeRecoveryStatus: DISABLED` detection.** A generic
   assistant emits the restore command and lets the API fail. The skill
   surfaces the `update-continuous-backups` remediation and the
   snapshot fallback path.

4. **New table name + connection-string cutover plan.** A generic
   assistant mentions "the new table" in passing. The skill enumerates
   every place the table name must be updated (env vars, Secrets
   Manager, Parameter Store, IAM resource policies) and surfaces the
   cutover as an atomic step.

5. **Side-config gap.** A generic assistant omits that the restored
   table is missing auto-scaling, alarms, IAM policies, streams, TTL,
   tags, deletion protection. The skill enumerates each
   reconfiguration step in NOTES.

6. **Original table unchanged + cleanup plan.** A generic assistant
   omits that the original `prod-orders-table` continues to bill. The
   skill surfaces the cleanup plan (snapshot + delete after cutover)
   and tags the restored table with `delete-after: 2026-08-23`.

7. **CONFIRM gate.** A generic assistant auto-executes. The skill
   emits `CONFIRM:` and waits — restore creates a billable table, the
   operator must explicitly approve.

8. **Billing-mode override.** A generic assistant omits that restore
   copies PROVISIONED throughput but not autoscaling policies. The
   skill surfaces `--billing-mode-override PAY_PER_REQUEST` as a
   shortcut to skip autoscaling re-registration, or the explicit
   re-registration checklist.

## Slash-command invocation

```
/aws:operate-dynamodb-backup
```

Or via the orchestrator:

```
/aws:pipeline
You: "restore prod-orders-table to 10:00 UTC before the bad migration"
```

The orchestrator emits
`[Phase: Operate | Skills routed: dynamodb-backup-operator]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "restore DynamoDB prod-orders-table to point in time"
# [Phase: Operate | Skills routed: dynamodb-backup-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the restore completes and application traffic is cut over:

```bash
# Verify the restored table is ACTIVE and item count matches
aws dynamodb describe-table --table-name prod-orders-table-pitr-2026-08-09 \
  --profile default \
  --query 'Table.{Status:TableStatus,ItemCount:ItemCount,Arn:TableArn}' \
  --output json

# Sentinel get-item to verify data integrity
aws dynamodb get-item --table-name prod-orders-table-pitr-2026-08-09 \
  --key '{"id": {"S": "sentinel-001"}}' \
  --profile default

# Re-apply TTL on the restored table
aws dynamodb update-time-to-live \
  --table-name prod-orders-table-pitr-2026-08-09 \
  --time-to-live-specification Enabled=true,AttributeName=ttl \
  --profile default

# Enable deletion protection on the restored table
aws dynamodb update-table --table-name prod-orders-table-pitr-2026-08-09 \
  --deletion-protection-enabled \
  --profile default

# Re-apply tags
aws dynamodb tag-resource \
  --resource-arn arn:aws:dynamodb:us-east-1:111111111111:table/prod-orders-table-pitr-2026-08-09 \
  --tags Key=env,Value=prod Key=owner,Value=orders-team \
  --profile default

# After cutover is verified, snapshot and delete the original table
aws dynamodb create-backup --table-name prod-orders-table \
  --backup-name prod-orders-table-pre-deletion-$(date -u +%Y%m%d) \
  --profile default
aws dynamodb update-table --table-name prod-orders-table \
  --no-deletion-protection-enabled \
  --profile default
aws dynamodb delete-table --table-name prod-orders-table \
  --profile default
```
