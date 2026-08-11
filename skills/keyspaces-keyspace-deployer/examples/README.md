# End-to-End Example: Amazon Keyspaces Deployment

A walkthrough showing how to use the `keyspaces-keyspace-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an Amazon Keyspaces keyspace and table for a
user event store with on-demand capacity, PITR, CMK encryption, and a
VPC endpoint for private access. The deployment needs:

- Keyspace: `event_store`
- Table: `user_events`
- Partition key: `(user_id, event_date)` — high cardinality, time-
  bucketed
- Clustering key: `event_time DESC` — newest events first
- Capacity: on-demand (PAY_PER_REQUEST)
- PITR: enabled (35-day continuous backup)
- Encryption: customer-managed KMS key (`alias/keyspaces-cmk`)
- VPC endpoint: private access via PrivateLink
- Region: `us-east-1`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-keyspaces-keyspace
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an Amazon Keyspaces keyspace called event_store
      with a table user_events. Partition key user_id plus
      event_date. Clustering key event_time DESC. On-demand
      capacity. Enable PITR. Use CMK alias/keyspaces-cmk.
      Create a VPC endpoint in vpc-aaa11122."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a keyspaces keyspace"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
KEYSPACES: event_store.user_events
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Keyspace: event_store — ACTIVE
  [✓] Table: user_events — partition key: (user_id, event_date), clustering key: event_time DESC
  [✓] Partition key cardinality: HIGH (user_id UUID + date → millions of partitions)
  [✓] Capacity mode: On-demand (PAY_PER_REQUEST)
  [✓] Point-in-time recovery: ENABLED
  [✓] TTL: default_time_to_live=604800 (7 days)
  [✓] Encryption at rest: Customer-managed key (alias/keyspaces-cmk)
  [✓] Client-side encryption: Not configured (server-side CMK sufficient)
  [✓] Connectivity: Cassandra driver + SigV4 (port 9142, SSL)
  [✓] VPC endpoint: vpce-aaa11122 (private DNS enabled)
  [✓] CloudWatch metrics: ConsumedReadCapacityUnits, ConsumedWriteCapacityUnits
  [✓] Tags: Environment=production, Team=data-platform
VERIFICATION_COMMANDS:
  aws keyspaces get-keyspace --keyspace-name event_store
  aws keyspaces get-table --keyspace-name event_store --table-name user_events
  aws cloudwatch get-metric-statistics --namespace AWS/Cassandra --metric-name ConsumedWriteCapacityUnits --dimensions Name=Keyspace,Value=event_store Name=TableName,Value=user_events --start-time 2026-08-05T00:00:00 --end-time 2026-08-05T01:00:00 --period 300 --statistics Sum
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the keyspace
aws keyspaces create-keyspace \
  --keyspace-name event_store \
  --tags Key=Environment,Value=production Key=Team,Value=data-platform

# Step 2: Verify the CMK exists
aws kms describe-key --key-id alias/keyspaces-cmk --query 'KeyMetadata.KeyId' --output text

# Step 3: Create the table with schema, PITR, CMK, and on-demand capacity
aws keyspaces create-table \
  --keyspace-name event_store \
  --table-name user_events \
  --schema-definition '{
    "allColumns": [
      {"name": "user_id", "type": "uuid"},
      {"name": "event_date", "type": "date"},
      {"name": "event_time", "type": "timestamp"},
      {"name": "event_type", "type": "text"},
      {"name": "payload", "type": "blob"}
    ],
    "partitionKeys": [
      {"name": "user_id", "type": "uuid"},
      {"name": "event_date", "type": "date"}
    ],
    "clusteringKeys": [
      {"name": "event_time", "type": "timestamp", "orderBy": "DESC"}
    ]
  }' \
  --capacity-spec '{"throughputMode": "PAY_PER_REQUEST"}' \
  --point-in-time-recovery-enabled \
  --encryption-spec '{
    "type": "CUSTOMER_MANAGED_KEYS",
    "kmsKeyIdentifier": "alias/keyspaces-cmk"
  }' \
  --tags Key=Environment,Value=production Key=Team,Value=data-platform

# Step 4: Create the VPC endpoint for private access
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-aaa11122 \
  --service-name com.amazonaws.us-east-1.cassandra \
  --subnet-ids subnet-aaa111 subnet-bbb222 \
  --security-group-ids sg-keyspaces-client \
  --vpc-endpoint-type Interface \
  --private-dns-enabled

# Step 5: Set default TTL (via CQL)
# Connect via Cassandra driver and execute:
# ALTER TABLE event_store.user_events WITH default_time_to_live = 604800;
```

---

## Step 4 — Post-deployment verification

```bash
# Verify keyspace is ACTIVE
aws keyspaces get-keyspace --keyspace-name event_store

# Verify table schema, capacity, PITR, and encryption
aws keyspaces get-table \
  --keyspace-name event_store \
  --table-name user_events

# Verify VPC endpoint
aws ec2 describe-vpc-endpoints \
  --filters Name=service-name,Values=com.amazonaws.us-east-1.cassandra

# Monitor consumed capacity
aws cloudwatch get-metric-statistics \
  --namespace AWS/Cassandra \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=Keyspace,Value=event_store Name=TableName,Value=user_events \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum Average \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Partition key | Single column (user_id) | Composite (user_id, event_date) | Time-bucketing prevents unbounded partition growth; single column = growing partitions forever |
| PITR | Assumes it is on by default | Explicitly enables PITR | PITR is DISABLED by default in Keyspaces; must be explicitly enabled per table |
| VPC endpoint | Creates without private DNS | Private DNS enabled | Without private DNS, the Cassandra driver resolves to the public endpoint and traffic traverses the internet |
| Port | 9042 (default Cassandra) | 9142 (Keyspaces) | Keyspaces requires SSL on port 9142; port 9042 does not work |
| Authentication | Username/password | SigV4 with IAM credentials | Keyspaces uses AWS SigV4 authentication; there are no passwords |
| Clustering key | Not specified | event_time DESC | Without a clustering key, rows are unordered within a partition; range queries are not efficient |
| CMK | Not configured | Customer-managed key (alias/keyspaces-cmk) | Default is AWS-owned key (no CloudTrail audit, no rotation control); CMK provides auditability |

---

## Related artifacts

- **Skill definition:** `skills/keyspaces-keyspace-deployer/SKILL.md`
- **Capacity and cost guide:** `skills/keyspaces-keyspace-deployer/references/capacity-and-cost.md`
- **Schema and encryption guide:** `skills/keyspaces-keyspace-deployer/references/schema-and-encryption.md`
- **Slash command:** `commands/aws/deploy-keyspaces-keyspace.md`
- **Eval suite:** `skills/keyspaces-keyspace-deployer/evals/evals.json`
- **Legacy test cases:** `skills/keyspaces-keyspace-deployer/eval/test-cases.yaml`
