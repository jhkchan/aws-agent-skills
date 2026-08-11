# End-to-end usage scenario: dynamodb-global-tables-operator

A walkthrough showing the skill planning an add-replica operation on a
DynamoDB Global Table. This exercises Step 0 (expert knowledge), Step 1
(pre-check gate), Step 2 (READY plan), and the post-verification
workflow including per-region PITR and autoscaling.

## Input (user prompt)

> We want to add `eu-west-1` as a third replica to our `orders-prod`
> global table. Currently we have replicas in `us-east-1` and
> `us-west-2`, both ACTIVE. PAY_PER_REQUEST billing. PITR is enabled in
> both existing regions. The table is about 50 GB. Our IAM role has
> UpdateGlobalTable and CreateTable in eu-west-1.

## Skill output

```text
OPERATION: add-replica
VERDICT: READY
TARGET: orders-prod global table, adding replica in eu-west-1
  Current replicas: us-east-1, us-west-2
  Target replicas: us-east-1, us-west-2, eu-west-1
PRE_CHECKS:
  - [PASS] Global table orders-prod exists
  - [PASS] All current replicas ACTIVE (us-east-1: ACTIVE, us-west-2: ACTIVE)
  - [PASS] No replica in CREATING or DELETING state
  - [PASS] Target region eu-west-1 does not have an existing replica
  - [PASS] Caller IAM role has dynamodb:UpdateGlobalTable
  - [PASS] Caller IAM role has dynamodb:CreateTable in eu-west-1
  - [WARN] PITR is ENABLED in us-east-1 and us-west-2 — enable in
    eu-west-1 after replica creation
STEPS:
  1. CONFIRM: About to add replica region eu-west-1 to global table
     orders-prod. This will create a new table in eu-west-1 and copy
     data from an existing replica. Estimated time: 15-30 minutes for
     ~50 GB. Proceed? (yes/no)
  2. aws dynamodb update-global-table \
       --global-table-name orders-prod \
       --replica-updates '[{"Create":{"RegionName":"eu-west-1"}}]'
  3. Poll: aws dynamodb describe-global-table \
       --global-table-name orders-prod \
       --query 'GlobalTableDescription.ReplicationGroup[?RegionName==`eu-west-1`].ReplicaStatus'
     Wait for ACTIVE.
  4. Enable PITR in eu-west-1:
      aws dynamodb update-continuous-backups \
        --table-name orders-prod --region eu-west-1 \
        --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
POST_VERIFY:
  - (pending execution)
REPLICA_STATUS:
  - us-east-1: ACTIVE
  - us-west-2: ACTIVE
  - eu-west-1: CREATING (will transition to ACTIVE)
NOTES:
  - PITR is NOT automatically enabled in eu-west-1 — step 4 is required.
  - Replicated write cost increases: each write now consumes 3x WCU.
  - ReplicationLatency for eu-west-1 may be higher (geographic distance).
```

## What the skill caught that a generic assistant misses

1. **Per-region PITR independence.** A generic assistant treats PITR as
   a single setting. The skill explicitly calls out that PITR must be
   enabled separately in eu-west-1 and includes it as a mandatory step
   in the plan.

2. **Replicated write cost scaling.** A generic assistant does not
   mention cost. The skill notes that each write now consumes 3x WCU
   (3 replicas) instead of 2x, so the operator can budget accordingly.

3. **ReplicationLatency by geography.** A generic assistant does not
   flag that eu-west-1 may have higher latency than us-west-2 due to
   distance from us-east-1. The skill includes this as a NOTE.

4. **The pre-check gate.** A generic assistant jumps straight to the
   CLI command. The skill runs a deterministic pre-check sequence
   (replica status, IAM permissions, existing replica check) before
   emitting the READY plan.

## Slash-command invocation

```
/aws:operate-dynamodb-global-tables
```

Or via the orchestrator:

```
/aws:pipeline
You: "add eu-west-1 replica to orders-prod global table"
```

The orchestrator emits `[Phase: Operate | Skills routed:
dynamodb-global-tables-operator]` and hands off to this skill for the
VERDICT.

## Live-account execution flow (requires AWS CLI)

```bash
# Pre-flight: check current global table state.
aws dynamodb describe-global-table --global-table-name orders-prod \
  --query 'GlobalTableDescription.ReplicationGroup[*].{region:RegionName,status:ReplicaStatus}'

# Execute the add-replica operation.
aws dynamodb update-global-table \
  --global-table-name orders-prod \
  --replica-updates '[{"Create":{"RegionName":"eu-west-1"}}]'

# Poll for ACTIVE (expected: 15-30 minutes for 50 GB).
aws dynamodb describe-global-table --global-table-name orders-prod \
  --query 'GlobalTableDescription.ReplicationGroup[?RegionName==`eu-west-1`].ReplicaStatus'

# Post-operation: enable PITR in eu-west-1.
aws dynamodb update-continuous-backups \
  --table-name orders-prod --region eu-west-1 \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

# Verify: write a test item in us-east-1, read it in eu-west-1.
aws dynamodb put-item --table-name orders-prod --region us-east-1 \
  --item '{"orderId":{"S":"replication-test-001"},"status":{"S":"TEST"}}'
aws dynamodb get-item --table-name orders-prod --region eu-west-1 \
  --key '{"orderId":{"S":"replication-test-001"}}' \
  --query 'Item.status.S' --output text
# Expected output: TEST (confirms replication is working)
```
