---
description: Provision an Amazon Keyspaces (Cassandra-compatible) keyspace and table with production-grade defaults (partition key, clustering key, on-demand vs provisioned capacity with auto-scaling, PITR, TTL, KMS encryption at rest, client-side envelope encryption, VPC endpoint, CloudWatch metrics). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create keyspace"
  - "create cassandra table"
  - "amazon keyspaces"
  - "keyspaces table"
  - "on-demand capacity keyspaces"
  - "provisioned autoscaling keyspaces"
  - "point-in-time recovery keyspaces"
  - "cassandra cql"
  - "partition key cassandra"
  - "clustering key cassandra"
  - "keyspace vpc endpoint"
  - "client-side encryption kms"
  - "keyspaces ttl"
  - "keyspaces kms encryption"
  - "deploy keyspaces"
  - "cassandra compatible"
routes_to: keyspaces-keyspace-deployer
---

# /aws:deploy-keyspaces-keyspace

Activate the `keyspaces-keyspace-deployer` skill and provision an
Amazon Keyspaces keyspace and table with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Keyspace creation (namespace for tables)
2. Table schema (partition key, clustering key, columns — immutable)
3. Capacity mode (on-demand vs provisioned)
4. Point-in-time recovery (PITR — disabled by default)
5. TTL (time-to-live for auto-expiry)
6. Encryption at rest (KMS: AWS-owned, AWS-managed, or CMK)
7. Client-side encryption (KMS envelope encryption)
8. Connectivity (Cassandra driver + SigV4, port 9142, SSL)
9. VPC endpoint (PrivateLink for private access)
10. CloudWatch metrics (ConsumedReadCapacityUnits, ConsumedWriteCapacityUnits)
11. Auto-scaling (target tracking for provisioned mode)
12. Recent features (multi-region, tiered pricing)

## When to use

- You need to create a Keyspaces keyspace or table.
- You are choosing between on-demand and provisioned capacity.
- You need point-in-time recovery on a table.
- You need KMS encryption at rest with a customer-managed key.
- You need client-side envelope encryption for field-level encryption.
- You need a VPC endpoint for private Keyspaces access.
- You need auto-scaling on a provisioned table.

## When NOT to use

- **Amazon DynamoDB** — different service, use DynamoDB skills.
- **Amazon ElastiCache** — in-memory cache, use ElastiCache skills.
- **Self-managed Cassandra on EC2/EKS** — not a managed service.

## How to invoke

### Slash command

```
/aws:deploy-keyspaces-keyspace
```

Then provide: keyspace name, table name, columns and types, partition
key, clustering key (if any), capacity mode (on-demand or provisioned
with units), PITR decision, TTL decision, KMS key (if CMK), VPC
endpoint (if private access), tags.

### Natural language

Any of these routes to the same skill:

- "create a Keyspaces keyspace called my_app_keyspace"
- "create a Cassandra table with partition key user_id"
- "enable point-in-time recovery on my Keyspaces table"
- "set up provisioned capacity with auto-scaling for Keyspaces"
- "configure client-side encryption for Keyspaces via KMS"
- "create a VPC endpoint for Keyspaces"

### CLI routing

```bash
node cli/bin/cli.js route "create a keyspaces keyspace"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Keyspaces
keyspaces or tables. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-keyspaces-keyspace

     Create an Amazon Keyspaces keyspace called event_store
     with a table user_events. Partition key user_id plus
     event_date. Clustering key event_time DESC. On-demand
     capacity. Enable PITR. Use CMK alias/keyspaces-cmk.
     Tags: Environment=production.

Skill:
  KEYSPACES: event_store.user_events
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Keyspace: event_store — ACTIVE
    [✓] Table: user_events — partition key: (user_id, event_date)
    [✓] Capacity mode: On-demand (PAY_PER_REQUEST)
    [✓] PITR: ENABLED
    [✓] Encryption: Customer-managed key (alias/keyspaces-cmk)
  VERIFICATION_COMMANDS:
    aws keyspaces get-keyspace --keyspace-name event_store
    aws keyspaces get-table --keyspace-name event_store --table-name user_events
```

## References

- Skill definition: `skills/keyspaces-keyspace-deployer/SKILL.md`
- Capacity and cost guide: `skills/keyspaces-keyspace-deployer/references/capacity-and-cost.md`
- Schema and encryption guide: `skills/keyspaces-keyspace-deployer/references/schema-and-encryption.md`
- Eval suite: `skills/keyspaces-keyspace-deployer/evals/evals.json`
