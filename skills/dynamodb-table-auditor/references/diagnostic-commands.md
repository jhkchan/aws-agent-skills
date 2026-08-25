# Diagnostic Commands (load on demand) — DynamoDB Table Auditor

Pre-remediation safety checks and remediation CLI sequences moved verbatim from SKILL.md. Loaded on demand.

---

## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)

The MANDATORY CONFIRMATION GATE is defined at the top of this document and
applies to every action below. Beyond the gate, these DynamoDB-specific
preconditions must hold before invoking the CLI:

- **Capture current table config before enabling SSE-KMS.** Enabling SSE on a
  table that previously had AES256 re-encrypts all existing data — this is a
  background migration that takes time proportional to table size. For large
  tables, monitor the migration via `describe-table` (SSEDescription.Status
  transitions DISABLED → ENABLING → ENABLED).

- **Verify the CMK exists and is enabled** before referencing it in
  `update-table`. A disabled or pending-deletion key causes the update to fail
  or leaves the table in an inaccessible state. Check with:
  `aws kms describe-key --key-id <cmk-id> --output json`.

- **Before switching from PROVISIONED to PAY_PER_REQUEST**, warn the operator
  about cost implications. On-demand for a steady high-throughput workload
  costs 3-5x provisioned with autoscaling. Verify the traffic profile justifies
  the switch.

- **Before enabling PITR**, warn about storage cost. PITR consumes additional
  storage proportional to the change rate over 35 days. For write-heavy tables,
  this can be significant. The compliance/recovery benefit typically outweighs
  the cost, but the operator should be informed.

- Prefer additive/non-destructive changes (enable SSE, enable PITR, enable
  deletion protection) over destructive ones (delete GSI, switch billing mode).
  Additive changes are reversible; destructive ones may break workloads.

---

## Remediation guidance (moved from SKILL.md)

### For UNENCRYPTED — SSE disabled (Step 1)

1. Enable SSE-KMS with a customer-managed CMK:
   ```bash
   aws dynamodb update-table --table-name <table> \
     --sse-specification Enabled=true,SSEType=KMS,\
KMSMasterKeyId=arn:aws:kms:us-east-1:111111111111:key/<cmk-id> \
     --profile <p>
   ```
2. Monitor the encryption migration: SSEDescription.Status transitions
   DISABLED → ENABLING → ENABLED. The table remains available during migration.
3. Verify: `aws dynamodb describe-table --table-name <table> --output json |
   jq '.Table.SSEDescription'`.

### For NO_PITR — continuous backups disabled (Step 2)

1. Enable PITR:
   ```bash
   aws dynamodb update-continuous-backups --table-name <table> \
     --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
     --profile <p>
   ```
2. Verify:
   ```bash
   aws dynamodb describe-continuous-backups --table-name <table> --profile <p>
   ```
3. Document the 35-day recovery window for the operator. Note that PITR restore
   creates a NEW table — plan for application cutover.

### For CAPACITY_MISMATCH — provisioned without autoscaling (Step 3)

1. Register scalable targets for the table:
   ```bash
   aws application-autoscaling register-scalable-target \
     --service-namespace dynamodb \
     --resource-id table/<table> \
     --scalable-dimension dynamodb:table:ReadCapacityUnits \
     --min-capacity 5 --max-capacity 1000 \
     --profile <p>
   aws application-autoscaling register-scalable-target \
     --service-namespace dynamodb \
     --resource-id table/<table> \
     --scalable-dimension dynamodb:table:WriteCapacityUnits \
     --min-capacity 5 --max-capacity 1000 \
     --profile <p>
   ```
2. Attach target-tracking policies:
   ```bash
   aws application-autoscaling put-scaling-policy \
     --policy-name <table>-read-autoscaling \
     --service-namespace dynamodb \
     --resource-id table/<table> \
     --scalable-dimension dynamodb:table:ReadCapacityUnits \
     --policy-type TargetTrackingScaling \
     --target-tracking-scaling-policy-configuration \
       '{"TargetValue":70.0,"PredefinedMetricSpecification":\
{"PredefinedMetricType":"DynamoDBReadCapacityUtilization"}}' \
     --profile <p>
   ```
3. Repeat for EVERY GSI:
   `--resource-id table/<table>/index/<gsi-name>` with
   `--scalable-dimension dynamodb:index:ReadCapacityUnits` (and Write). A GSI
   without autoscaling is the most commonly missed cascade vector.
4. Alternatively, switch to on-demand if traffic is unpredictable:
   ```bash
   aws dynamodb update-table --table-name <table> \
     --billing-mode PAY_PER_REQUEST --profile <p>
   ```

### For CONFIG_GAP — AWS-managed KMS key

1. Switch to a customer-managed CMK:
   ```bash
   aws dynamodb update-table --table-name <table> \
     --sse-specification Enabled=true,SSEType=KMS,\
KMSMasterKeyArn=arn:aws:kms:us-east-1:111111111111:key/<cmk-id> \
     --profile <p>
   ```

### For CONFIG_GAP — TTL disabled

1. Enable TTL on an attribute:
   ```bash
   aws dynamodb update-time-to-live --table-name <table> \
     --time-to-live-specification Enabled=true,AttributeName=ttl \
     --profile <p>
   ```
2. Verify existing items have the TTL attribute set (epoch seconds). Items
   without the attribute are never expired.

### For CONFIG_GAP — deletion protection off

1. Enable deletion protection:
   ```bash
   aws dynamodb update-table --table-name <table> \
     --deletion-protection-enabled --profile <p>
   ```

### For CONFIG_GAP — no DynamoDB Streams

1. Enable streams:
   ```bash
   aws dynamodb update-table --table-name <table> \
     --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
     --profile <p>
   ```

### For OK

1. No remediation required for the current posture.
2. Recommend verifying Global Table replicas independently (each replica has
   independent capacity, PITR, and KMS settings).
3. Recommend adding AWS Backup as a complementary layer to PITR for long-term
   retention (PITR caps at 35 days; AWS Backup provides weekly/monthly archives).
