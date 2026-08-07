# End-to-End Example: DynamoDB Table Deployment

A walkthrough showing how to use the `dynamodb-table-deployer` skill from
invocation through verification. Mirrors the structured-eval pattern of
shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a high-throughput production session store. The table
needs:

- High-cardinality partition key (UUID v4 sessionId) for even write distribution
- KEYS_ONLY GSI on userId for reverse lookup (sparse — anonymous sessions omitted)
- On-demand capacity mode (bursty traffic)
- SSE-KMS with a customer-managed CMK
- PITR (35-day recovery window)
- TTL on `expiresAt` (24-hour session expiry)
- DynamoDB Streams with `NEW_AND_OLD_IMAGES` (downstream Lambda publishes events)
- Deletion protection

Table name: `prod-sessions`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-dynamodb-table
```

Then paste the requirements.

### Option B: Natural language

```
You: "Provision a production DynamoDB table named prod-sessions in us-east-1
      for a high-throughput session store. Session IDs are UUID v4. Need a GSI
      on userId (some sessions are anonymous). Use SSE-KMS with
      alias/prod-dynamodb-key. Sessions expire after 24h via TTL on expiresAt.
      Enable DynamoDB Streams NEW_AND_OLD_IMAGES for downstream Lambda. Traffic
      is bursty. Tags: Environment=production, Workload=session-store.
      Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a dynamodb table for sessions"
```

Output:

```
[Phase: Deploy | Skills routed: dynamodb-table-deployer]

Primary route: dynamodb-table-deployer (score: 22)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
TABLE: prod-sessions
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Partition key: sessionId (String) — UUID v4, high-cardinality for even write distribution
  [✓] Sort key: None (single-item lookup pattern)
  [✓] LSIs: None (no range-query requirement on alternate sort attribute)
  [✓] GSIs: gsi_by_userId (userId→sessionId, KEYS_ONLY projection, sparse — only items with userId)
  [✓] Capacity mode: PAY_PER_REQUEST (bursty session traffic, unpredictable peaks)
  [✓] Encryption: SSE-KMS customer CMK (alias/prod-dynamodb-key)
  [✓] PITR: Enabled (35-day window)
  [✓] TTL: Enabled (attribute: expiresAt — session token expiry, ~48h deletion lag acceptable)
  [✓] Streams: NEW_AND_OLD_IMAGES (downstream Lambda publishes session-change events)
  [✓] Table class: STANDARD (frequently accessed)
  [✓] Deletion protection: Enabled
  [✓] Resource-based policy: None (single-account)
  [✓] Global Tables: Single-region (us-east-1)
VERIFICATION_COMMANDS:
  aws dynamodb describe-table --table-name prod-sessions
  aws dynamodb describe-continuous-backups --table-name prod-sessions
  aws dynamodb describe-time-to-live --table-name prod-sessions
  aws kms describe-key --key-id alias/prod-dynamodb-key
```

---

## Step 3 — Provisioning commands

The skill generates the copy-pasteable CLI sequence (from
`references/provisioning-cli-commands.md`):

```bash
# Step 1: Create the table with all immutable properties at creation
aws dynamodb create-table \
  --table-name prod-sessions \
  --attribute-definitions \
    AttributeName=sessionId,AttributeType=S \
    AttributeName=userId,AttributeType=S \
  --key-schema \
    AttributeName=sessionId,KeyType=HASH \
  --global-secondary-indexes '[{
    "IndexName":"gsi_by_userId",
    "KeySchema":[{"AttributeName":"userId","KeyType":"HASH"}],
    "Projection":{"ProjectionType":"KEYS_ONLY"}
  }]' \
  --billing-mode PAY_PER_REQUEST \
  --table-class STANDARD \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=arn:aws:kms:us-east-1:123456789012:alias/prod-dynamodb-key \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
  --deletion-protection-enabled

# Step 2: Enable PITR
aws dynamodb update-continuous-backups \
  --table-name prod-sessions \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

# Step 3: Enable TTL
aws dynamodb update-time-to-live \
  --table-name prod-sessions \
  --time-to-live-specification Enabled=true,AttributeName=expiresAt

# Step 4: CloudWatch alarms (recommended)
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-sessions-throttles" \
  --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=prod-sessions \
  --statistic Sum --period 60 --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 --alarm-actions <sns-arn>
```

---

## Step 4 — Post-deployment verification

Run the verification commands from the checklist to confirm every
configuration was applied:

```bash
# Table config — KeySchema, BillingMode, SSEDescription, StreamSpecification,
# GlobalSecondaryIndexes, DeletionProtectionEnabled
aws dynamodb describe-table --table-name prod-sessions

# PITR — ContinuousBackupsStatus: ENABLED, PointInTimeRecoveryStatus: ENABLED
aws dynamodb describe-continuous-backups --table-name prod-sessions

# TTL — TimeToLiveStatus: ENABLED, AttributeName: expiresAt
aws dynamodb describe-time-to-live --table-name prod-sessions

# KMS key — KeyState: Enabled, Enabled: true
aws kms describe-key --key-id alias/prod-dynamodb-key
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| GSI projection type | `ALL` "for convenience" | `KEYS_ONLY` + sparse pattern | `ALL` doubles write cost on a high-throughput table; `KEYS_ONLY` with the userId sort key makes the index sparse (anonymous sessions excluded automatically). |
| Partition key rationale | Just picks `sessionId` | Verifies UUID v4 cardinality and even distribution | If sessionId were sequential, the table would hot-partition. The skill forces an explicit distribution check. |
| StreamViewType | `NEW_IMAGE` (default) | `NEW_AND_OLD_IMAGES` | Downstream Lambda needs both pre- and post-update state to compute diffs for change-event publishing. `NEW_IMAGE` alone is insufficient. |
| Capacity mode | Provisioned (5/5 RCUs/WCUs) | PAY_PER_REQUEST | Bursty session traffic; on-demand handles spikes within the burst bucket. Provisioned with autoscaling has a 3-5 minute scale-out lag. |
| Deletion protection | Forgotten | Enabled at create-table | Production session store; protects against accidental `delete-table`. |
| TTL attribute caveat | Just enables TTL | Notes 48-hour deletion lag + "items without attribute are never expired" | Operator must ensure every item has `expiresAt` set; otherwise sessions persist forever. |

---

## Related artifacts

- **Skill definition:** `skills/dynamodb-table-deployer/SKILL.md`
- **Key design and capacity guide:** `skills/dynamodb-table-deployer/references/key-design-and-capacity.md`
- **Provisioning CLI commands:** `skills/dynamodb-table-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-dynamodb-table.md`
- **Eval suite:** `skills/dynamodb-table-deployer/evals/evals.json`
- **Legacy test cases:** `skills/dynamodb-table-deployer/eval/test-cases.yaml`
