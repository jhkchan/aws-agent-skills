---
name: keyspaces-keyspace-deployer
description: 'Provisions Amazon Keyspaces (Cassandra-compatible) keyspaces and tables with production defaults: keyspace creation (create-keyspace), table creation (create-table) with partition key, clustering key, and regular columns, capacity mode selection (on-demand vs provisioned with auto- scaling), point-in-time recovery (PITR), TTL (time-to-live), encryption at rest with KMS, client-side encryption via KMS envelope encryption, schema management through CQL, VPC endpoints for private access, CloudWatch metrics (ConsumedWriteCapacityUnits, ConsumedReadCapacityUnits), and the RU-based cost model. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Keyspace, creating a Cassandra table, configuring on-demand or provisioned capacity, enabling PITR, setting. Triggers: create keyspace, create cassandra table, amazon keyspaces, on-demand capacity, provisioned autoscaling, point-in-time recovery, cassandra CQL, partition key, clustering key, keyspace VPC endpoint, client-side encryption KMS.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with keyspaces access. Works with Terraform aws_keyspaces_keyspace / aws_keyspaces_table resources and CloudFormation AWS::Cassandra::Keyspace / AWS::Cassandra::Table templates. CQL access via the open-source DataStax cassandra-driver with SigV4 authentication.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, keyspaces, cassandra, cloudops, deploy, databases, provisioning, partition-key, clustering-key, on-demand, provisioned, pitr, kms, vpc-endpoint
  dependencies: aws-orchestrator
  keywords: aws, keyspaces, cassandra, cloudops, deploy, provisioning, keyspace, table, partition key, clustering key, on-demand, provisioned, autoscaling, pitr, ttl, kms encryption, client-side encryption, vpc endpoint, cql, cloudwatch metrics
  when_to_use: Invoke when the user wants to create an Amazon Keyspaces keyspace or table, configure capacity mode (on-demand or provisioned with auto- scaling), enable point-in-time recovery, set TTL, configure KMS encryption at rest, set up client-side envelope encryption, connect via the Cassandra driver with SigV4, or create a VPC endpoint for private Keyspaces access. Do NOT invoke for Amazon DynamoDB (use DynamoDB skills), Amazon ElastiCache (use ElastiCache skills), or self-managed Cassandra on EC2/EKS.
---

# Amazon Keyspaces Keyspace Deployer

An AWS CloudOps agent skill that provisions Amazon Keyspaces (Cassandra-
compatible) keyspaces and tables with correct defaults. The skill walks
the operator through keyspace creation, table schema design (partition
key for distribution, clustering key for sort order), capacity mode
selection (on-demand vs provisioned with auto-scaling), point-in-time
recovery, TTL, encryption at rest with KMS, client-side envelope
encryption, CQL connectivity, VPC endpoints for private access, and
CloudWatch observability, captures all schema and capacity decisions,
explains why each default matters, and emits a READY_TO_DEPLOY checklist
with copy-pasteable verification commands.

## Activation keywords

create keyspace, create Cassandra table, Amazon Keyspaces, on-demand
capacity, provisioned autoscaling, point-in-time recovery, Cassandra
CQL, partition key, clustering key, Keyspaces VPC endpoint, client-side
encryption KMS.

## STRICT output contract

When this skill is invoked with a Keyspaces-provisioning request
(create a keyspace, create a table, configure capacity mode, enable
PITR, set TTL, configure encryption, set up connectivity, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `KEYSPACES:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Keyspace creation | Core keyspace model |
| Step 2 — Table schema (partition key, clustering key, columns) | Schema design |
| Step 3 — Capacity mode (on-demand vs provisioned) | Capacity decision |
| Step 4 — Point-in-time recovery (PITR) | Backup/recovery |
| Step 5 — TTL (time-to-live) | Data expiry |
| Step 6 — Encryption at rest (KMS) | Encryption |
| Step 7 — Client-side encryption (KMS envelope) | Application encryption |
| Step 8 — Connectivity (Cassandra driver + SigV4) | CQL access |
| Step 9 — VPC endpoint for private access | Network security |
| Step 10 — CloudWatch metrics and observability | Monitoring |
| Step 11 — Auto-scaling for provisioned mode | Capacity scaling |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/capacity-and-cost.md | Capacity mode + cost crossover detail |
| references/schema-and-encryption.md | Schema + encryption detail |

## Mindset

**One-line takeaway:** Amazon Keyspaces is a serverless, Cassandra-
compatible database. The keyspace is the namespace; the table holds
data. The partition key determines data distribution across the
underlying storage; the clustering key determines sort order within a
partition. Capacity mode is the primary cost lever: on-demand charges
per request (RU-based), provisioned charges per capacity unit reserved
with auto-scaling. PITR must be explicitly enabled per table — it is
NOT on by default.

Three misconceptions dominate Keyspaces misdesign at provisioning time:

- **"The partition key is just a primary key."** It is not. The
  partition key determines which storage node holds the data. A low-
  cardinality partition key (e.g., a status column with 3 values)
  creates hot partitions and uneven distribution. A high-cardinality
  partition key (e.g., user_id, device_id) distributes data evenly.
  Cardinality matters more than uniqueness.

- **"On-demand is always simpler, so always use it."** On-demand is
  simpler (no capacity planning), but costs more per request at steady
  state. The crossover point where provisioned (with auto-scaling)
  becomes cheaper is typically around 10-15% sustained utilization of
  the provisioned capacity. For predictable workloads, provisioned with
  auto-scaling is significantly cheaper.

- **"PITR is enabled by default like DynamoDB."** In Keyspaces, PITR
  is DISABLED by default. Each table must explicitly enable PITR. A
  baseline model may assume it is on. The procedure below forces an
  explicit decision.

## Configuration dependency graph (novel heuristic)

Keyspaces configurations are NOT independent. The keyspace must exist
before the table. The table schema (partition key, clustering key) is
immutable after creation — it CANNOT be changed without dropping and
recreating the table. Capacity mode can be switched but has cost
implications. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Keyspace | AWS account with Keyspaces available in the region | keyspace name must be unique within account+region (3-48 chars, alphanumeric + underscore) | table creation |
| Table | keyspace exists | partition key + clustering key are IMMUTABLE after creation — cannot ALTER; must drop and recreate | data read/write via CQL |
| Capacity mode (on-demand) | table exists | can switch to provisioned later; on-demand charges per RU consumed | pay-per-request billing |
| Capacity mode (provisioned) | table exists; auto-scaling policy optional | can switch to on-demand later; provisioned charges per capacity unit whether used or not | reserved capacity billing |
| PITR | table exists | DISABLED by default — must explicitly enable per table; continuous backup of last 35 days | point-in-time restore |
| TTL | table exists | column-level TTL via CQL INSERT/UPDATE; table default TTL via schema | automatic row expiry |
| Encryption at rest (KMS) | table exists; KMS key available | AWS-owned key by default; customer-managed key (CMK) for granular control | at-rest encryption |
| Client-side encryption | application-side KMS key | transparent to Keyspaces; encrypted before write, decrypted after read | field-level encryption |
| VPC endpoint | VPC exists; private DNS enabled | Interface VPC endpoint (AWS PrivateLink) for private access without internet | private network access |
| CloudWatch metrics | table exists | metrics are automatic (no enable needed); ConsumedReadCapacityUnits, ConsumedWriteCapacityUnits | observability + autoscaling trigger |
| Auto-scaling | provisioned capacity mode | target tracking on ConsumedWriteCapacityUnits or ConsumedReadCapacityUnits | automatic capacity adjustment |

**The partition-key-immutability row is the one a baseline model
misses.** In DynamoDB, you can delete and recreate a table with a new
key schema relatively easily. In Keyspaces, the Cassandra data model
means the partition key and clustering key are baked into the table
definition and CANNOT be altered. Changing the key schema requires
dropping the table (losing all data) and recreating it. The procedure
below forces an explicit schema review before creation.

**Cross-dependency gotchas:**
- The partition key choice is PERMANENT. Changing it requires dropping
  the table. Design the schema carefully before creating the table.
- Clustering key is also permanent. It determines sort order within a
  partition. Choose it based on query patterns (range scans, time-
  ordered data).
- Switching capacity mode (on-demand to provisioned or vice versa) is
  allowed but takes effect immediately. Switching frequently can cause
  billing surprises.
- PITR is per-table, not per-keyspace. Each table must have PITR
  explicitly enabled.
- Client-side encryption is transparent to Keyspaces — the data is
  encrypted before it reaches Keyspaces. Keyspaces sees ciphertext.
  This means server-side CQL queries (e.g., WHERE clauses on encrypted
  columns) do NOT work as expected because they compare ciphertext, not
  plaintext.

## Expert heuristic: partition key cardinality for distribution

> **Moved verbatim** → [references/schema-and-encryption.md](references/schema-and-encryption.md) § "Expert heuristic: partition key cardinality for distribution".
> Load when: designing the table schema — why low-cardinality partition keys create hot partitions; composite time-bucketed keys.

## Expert heuristic: clustering key for sort order

> **Moved verbatim** → [references/schema-and-encryption.md](references/schema-and-encryption.md) § "Expert heuristic: clustering key for sort order".
> Load when: choosing the clustering key — sort order within a partition and range-query alignment.

## Expert heuristic: on-demand vs provisioned RU crossover

> **Moved verbatim** → [references/capacity-and-cost.md](references/capacity-and-cost.md) § "Expert heuristic: on-demand vs provisioned RU crossover".
> Load when: choosing capacity mode — on-demand vs provisioned cost crossover math and workload profiles.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS region supports Keyspaces | Keyspaces is available in most regions but not all | `aws keyspaces list-keyspaces --region <region>` |
| Keyspace name (if creating table in existing keyspace) | Tables require a keyspace | `aws keyspaces get-keyspace --keyspace-name <name>` |
| Partition key identified | Partition key is immutable after table creation — must be chosen before creating the table | Schema design review |
| Clustering key identified (if range queries needed) | Clustering key is immutable after table creation | Query pattern analysis |
| KMS key ID (if using CMK for encryption) | Customer-managed key must exist before referencing | `aws kms describe-key --key-id <key-id>` |
| VPC ID (if creating VPC endpoint) | Interface endpoint requires a VPC | `aws ec2 describe-vpcs --vpc-ids <vpc-id>` |
| IAM permissions for keyspaces:* | Provisioning requires keyspace/table create permissions | Verify IAM policy |
| Capacity mode decision | On-demand vs provisioned is a cost decision | Workload analysis |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Keyspace creation

A keyspace is the top-level namespace for tables. Each keyspace is
unique within an AWS account and region.

```bash
# Create a keyspace
aws keyspaces create-keyspace \
  --keyspace-name my_app_keyspace \
  --tags Key=Environment,Value=production Key=Team,Value=data-platform

# Verify the keyspace exists and is ACTIVE
aws keyspaces get-keyspace \
  --keyspace-name my_app_keyspace
```

**Naming constraints:** 3-48 characters, alphanumeric and underscore
only. Must start with a letter.

**Replication:** Keyspaces is fully managed and automatically
replicates data across multiple Availability Zones within the chosen
region. No replication factor configuration is needed (unlike self-
managed Cassandra).

## Step 2 — Table schema (partition key, clustering key, columns)

Table schema is defined using CQL (Cassandra Query Language). The
partition key determines distribution; the clustering key determines
sort order within a partition.

```bash
# Create a table with partition key + clustering key
aws keyspaces create-table \
  --keyspace-name my_app_keyspace \
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
  --point-in-time-recovery-enabled \
  --tags Key=Environment,Value=production
```

**Critical:** the partition key and clustering key are IMMUTABLE after
creation. Changing them requires dropping the table (losing all data)
and recreating. Design the schema based on query patterns BEFORE
creating the table.

**Column types supported:** ascii, bigint, blob, boolean, decimal,
double, float, inet, int, list, map, set, text, timestamp, timeuuid,
tinyint, tuple, uuid, varchar, varint.

## Step 3 — Capacity mode (on-demand vs provisioned)

```bash
# Set capacity mode to on-demand (pay per request)
aws keyspaces update-table \
  --keyspace-name my_app_keyspace \
  --table-name user_events \
  --capacity-spec '{"throughputMode": "PAY_PER_REQUEST"}'

# Set capacity mode to provisioned (with explicit capacity units)
aws keyspaces update-table \
  --keyspace-name my_app_keyspace \
  --table-name user_events \
  --capacity-spec '{
    "throughputMode": "PROVISIONED",
    "provisionedThroughput": {
      "readCapacityUnits": 1000,
      "writeCapacityUnits": 500
    }
  }'
```

**On-demand:** charges per RU consumed. No minimum commitment. Best for
unpredictable or spiky workloads, or new workloads with unknown
traffic.

**Provisioned:** charges per capacity unit-hour regardless of usage.
Best for steady, predictable workloads. Pair with auto-scaling (Step
11) to handle bursts.

## Step 4 — Point-in-time recovery (PITR)

PITR provides continuous backup of the last 35 days. It is DISABLED by
default — must be explicitly enabled per table.

```bash
# Enable PITR on a table
aws keyspaces update-table \
  --keyspace-name my_app_keyspace \
  --table-name user_events \
  --point-in-time-recovery-enabled

# Verify PITR status
aws keyspaces get-table \
  --keyspace-name my_app_keyspace \
  --table-name user_events \
  --query 'capacitySummary' --output json
```

**Critical:** PITR is per-table, NOT per-keyspace. Each table must
explicitly enable it. A baseline model may assume PITR is on by
default (as in DynamoDB). In Keyspaces, it is OFF by default.

## Step 5 — TTL (time-to-live)

> **Moved verbatim** → [references/schema-and-encryption.md](references/schema-and-encryption.md) § "Step 5 — TTL (time-to-live)".
> Load when: configuring TTL — CQL USING TTL inserts and default_time_to_live.

## Step 6 — Encryption at rest (KMS)

> **Moved verbatim** → [references/schema-and-encryption.md](references/schema-and-encryption.md) § "Step 6 — Encryption at rest (KMS)".
> Load when: configuring encryption at rest — AWS-owned vs AWS-managed vs customer-managed KMS, CMK create/set commands.

## Step 7 — Client-side encryption (KMS envelope)

> **Moved verbatim** → [references/schema-and-encryption.md](references/schema-and-encryption.md) § "Step 7 — Client-side encryption (KMS envelope)".
> Load when: configuring client-side envelope encryption — KMS DEK generation plus the Cassandra driver Python example.

## Step 8 — Connectivity (Cassandra driver + SigV4)

> **Moved verbatim** → [references/schema-and-encryption.md](references/schema-and-encryption.md) § "Step 8 — Connectivity (Cassandra driver + SigV4)".
> Load when: connecting via CQL — SigV4 auth provider, port 9142, SSL, and driver requirements.

## Step 9 — VPC endpoint for private access

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 9 — VPC endpoint for private access".
> Load when: creating the interface VPC endpoint — PrivateLink, --private-dns-enabled, security group TCP 9142.

## Step 10 — CloudWatch metrics and observability

> **Moved verbatim** → [references/capacity-and-cost.md](references/capacity-and-cost.md) § "Step 10 — CloudWatch metrics and observability".
> Load when: setting up observability — the CloudWatch metric table and get-metric-statistics examples.

## Step 11 — Auto-scaling for provisioned mode

> **Moved verbatim** → [references/capacity-and-cost.md](references/capacity-and-cost.md) § "Step 11 — Auto-scaling for provisioned mode".
> Load when: enabling auto-scaling on provisioned tables — register-scalable-target and the target tracking policy.

## Step 12 — Recent features

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 12 — Recent features".
> Load when: checking 2023-2026 feature availability — client-side encryption library, multi-region replication, tiered on-demand pricing.

## NEVER do these things

1. **NEVER use a low-cardinality partition key.** The partition key
   determines data distribution. Low cardinality (e.g., status column
   with 3 values) creates hot partitions and uneven distribution. Aim
   for high-cardinality partition keys (user_id, device_id,
   session_id).

2. **NEVER assume the partition key or clustering key can be changed.**
   They are IMMUTABLE after table creation. Changing them requires
   dropping the table (losing all data) and recreating. Design the
   schema based on query patterns BEFORE creating the table.

3. **NEVER assume PITR is enabled by default.** In Keyspaces, PITR is
   DISABLED by default. Each table must explicitly enable it. A baseline
   model may confuse this with DynamoDB where PITR is also off by
   default but the assumption is common.

4. **NEVER connect to Keyspaces on port 9042 without SSL.** Keyspaces
   requires SSL/TLS on port 9142. Port 9042 (the default Cassandra
   port) does NOT work. Always use SSL with the AmazonRootCA1
   certificate.

5. **NEVER use username/password authentication.** Keyspaces uses AWS
   SigV4 authentication with IAM credentials. There are no passwords.
   The Cassandra driver's `PlainTextAuthProvider` does NOT work.

6. **NEVER create a VPC endpoint without private DNS.** Without
   `--private-dns-enabled`, the Cassandra driver resolves to the public
   Keyspaces endpoint and traffic traverses the internet. Private DNS
   is REQUIRED for true private access.

7. **NEVER use WHERE clauses on client-side encrypted columns.**
   Client-side encryption is transparent to Keyspaces. Server-side CQL
   queries compare ciphertext, not plaintext. WHERE clauses on
   encrypted columns return wrong results. Design the schema so
   encrypted columns are NOT used in WHERE clauses.

8. **NEVER switch capacity mode frequently.** Switching between
   on-demand and provisioned takes effect immediately. Frequent
   switching can cause billing surprises. Choose the mode based on
   workload analysis and commit for a billing period.

9. **NEVER provision capacity without auto-scaling for variable
   workloads.** Provisioned capacity without auto-scaling leads to
   throttling during bursts or over-provisioning during dips. Always
   pair provisioned mode with target tracking auto-scaling.

10. **NEVER forget TTL for ephemeral data.** Without TTL, time-series
    data accumulates indefinitely, increasing storage cost and query
    latency. Set TTL on event logs, session data, and other ephemeral
    rows to auto-expire.

## Output format

```text
KEYSPACES: <keyspace-name>.<table-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Keyspace: <keyspace-name> — ACTIVE
  [✓|✗] Table: <table-name> — schema (partition key: <pk>, clustering key: <ck>)
  [✓|✗] Partition key cardinality: HIGH (<cardinality>) | LOW (hot partition risk)
  [✓|✗] Capacity mode: On-demand | Provisioned (read: <rcu>, write: <wcu>) with auto-scaling
  [✓|✗] Point-in-time recovery: ENABLED | DISABLED
  [✓|✗] TTL: default_time_to_live=<seconds> | Not set
  [✓|✗] Encryption at rest: AWS-owned key | Customer-managed key (<kms-key-id>)
  [✓|✗] Client-side encryption: KMS envelope (<kms-key-alias>) | Not configured
  [✓|✗] Connectivity: Cassandra driver + SigV4 (port 9142, SSL)
  [✓|✗] VPC endpoint: <vpce-id> (private DNS enabled) | Public access
  [✓|✗] CloudWatch metrics: ConsumedReadCapacityUnits, ConsumedWriteCapacityUnits
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws keyspaces get-keyspace --keyspace-name <keyspace-name>
  aws keyspaces get-table --keyspace-name <keyspace-name> --table-name <table-name>
  aws cloudwatch get-metric-statistics --namespace AWS/Cassandra --metric-name ConsumedWriteCapacityUnits --dimensions Name=Keyspace,Value=<keyspace> Name=TableName,Value=<table> --start-time <time> --end-time <time> --period 300 --statistics Sum
```

### Worked example — on-demand keyspace with PITR and CMK encryption

```text
KEYSPACES: my_app_keyspace.user_events
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Keyspace: my_app_keyspace — ACTIVE
  [✓] Table: user_events — schema (partition key: user_id+event_date, clustering key: event_time DESC)
  [✓] Partition key cardinality: HIGH (user_id UUID + date → millions of partitions)
  [✓] Capacity mode: On-demand (PAY_PER_REQUEST)
  [✓] Point-in-time recovery: ENABLED
  [✓] TTL: default_time_to_live=604800 (7 days)
  [✓] Encryption at rest: Customer-managed key (arn:aws:kms:us-east-1:123456789012:key/abc123)
  [✓] Client-side encryption: Not configured (server-side CMK sufficient)
  [✓] Connectivity: Cassandra driver + SigV4 (port 9142, SSL)
  [✓] VPC endpoint: vpce-aaa11122 (private DNS enabled)
  [✓] CloudWatch metrics: ConsumedReadCapacityUnits, ConsumedWriteCapacityUnits
  [✓] Tags: Environment=production, Team=data-platform
VERIFICATION_COMMANDS:
  aws keyspaces get-keyspace --keyspace-name my_app_keyspace
  aws keyspaces get-table --keyspace-name my_app_keyspace --table-name user_events
  aws cloudwatch get-metric-statistics --namespace AWS/Cassandra --metric-name ConsumedWriteCapacityUnits --dimensions Name=Keyspace,Value=my_app_keyspace Name=TableName,Value=user_events --start-time 2026-08-05T00:00:00 --end-time 2026-08-05T01:00:00 --period 300 --statistics Sum
```

## Error handling

> **Moved verbatim** → [references/error-handling.md](references/error-handling.md) § "Error handling".
> Load when: a create/connect/restore call fails — ValidationException, SSL handshake, SigV4 auth, throttling, VPC endpoint, PITR restore.

## References (load on demand)

- [references/schema-and-encryption.md](references/schema-and-encryption.md) — partition-key cardinality and clustering-key heuristics, TTL, at-rest and client-side KMS encryption, Cassandra driver + SigV4 connectivity (moved verbatim; existing deep reference)
- [references/capacity-and-cost.md](references/capacity-and-cost.md) — on-demand vs provisioned RU crossover heuristic, CloudWatch metrics, provisioned auto-scaling (moved verbatim; existing deep reference)
- [references/advanced-patterns.md](references/advanced-patterns.md) — VPC endpoint private access and recent AWS features (2023-2026)
- [references/error-handling.md](references/error-handling.md) — ValidationException, SSL/SigV4 connection failures, throttling, VPC endpoint failures, PITR restore failures

## Domain

AWS CloudOps / Amazon Keyspaces (Cassandra-Compatible) Keyspace and
Table Provisioning, Schema Management, and Capacity Planning.

## AWS documentation

- **Amazon Keyspaces Developer Guide** — https://docs.aws.amazon.com/keyspaces/latest/devguide/what-is-keyspaces.html
- **Create keyspace** — https://docs.aws.amazon.com/keyspaces/latest/devguide/create-keyspace.html
- **Create table** — https://docs.aws.amazon.com/keyspaces/latest/devguide/getting-started.choice-of-partition-key.html
- **Capacity modes** — https://docs.aws.amazon.com/keyspaces/latest/devguide/capacity-mode.html
- **Point-in-time recovery** — https://docs.aws.amazon.com/keyspaces/latest/devguide/point-in-time-recovery.html
- **TTL** — https://docs.aws.amazon.com/keyspaces/latest/devguide/how-to-ttl.html
- **Encryption at rest** — https://docs.aws.amazon.com/keyspaces/latest/devguide/encryption-at-rest.html
- **Client-side encryption** — https://docs.aws.amazon.com/keyspaces/latest/devguide/client-side-encryption.html
- **Cassandra driver connectivity** — https://docs.aws.amazon.com/keyspaces/latest/devguide/programmatic.credentials.html
- **VPC endpoints** — https://docs.aws.amazon.com/keyspaces/latest/devguide/vpc-endpoints.html
- **CloudWatch metrics** — https://docs.aws.amazon.com/keyspaces/latest/devguide/metrics-dimensions.html
- **Auto-scaling** — https://docs.aws.amazon.com/keyspaces/latest/devguide/auto-scaling.html
