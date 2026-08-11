---
description: Provision an Amazon DocumentDB (MongoDB-compatible) cluster with production-grade defaults (multi-AZ replication, r5/t3 instance types, storage autoscaling with ceiling, change streams for CDC, indexing strategy, KMS encryption, backup retention, global clusters, parameter groups, TLS). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create documentdb cluster"
  - "deploy documentdb"
  - "documentdb cluster"
  - "documentdb instance"
  - "documentdb change streams"
  - "documentdb global cluster"
  - "documentdb storage autoscaling"
  - "documentdb subnet group"
  - "documentdb parameter group"
  - "documentdb kms encryption"
  - "documentdb backup retention"
  - "documentdb index"
  - "mongo shell connect documentdb"
  - "mongodb compatible database"
  - "documentdb"
routes_to: documentdb-cluster-deployer
---

# /aws:deploy-documentdb-cluster

Activate the `documentdb-cluster-deployer` skill and provision an Amazon
DocumentDB cluster with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Cluster architecture (cluster + instances, shared storage volume)
2. Instance types (r5 for production, t3 for development)
3. Storage autoscaling (ceiling configuration, STORAGE_FULL prevention)
4. Multi-AZ replication (primary + replicas, failover priority)
5. Subnet groups and security groups (network configuration)
6. Parameter groups (change streams, audit logs, TLS)
7. KMS encryption (customer-managed key, immutable at creation)
8. Backup retention and point-in-time recovery
9. Change streams for CDC (retention, resume tokens)
10. Indexing strategy (no query optimizer — index before query)
11. Global clusters (cross-region DR, managed failover)
12. MongoDB compatibility and connecting (engine version, mongo shell)
13. TLS configuration (enabled by default)
14. CloudWatch metrics (CPU, storage, connections, replica lag)

## When to use

- You need to create a DocumentDB cluster.
- You are configuring change streams for a CDC pipeline.
- You are setting up a DocumentDB global cluster for cross-region DR.
- You need to manage storage autoscaling ceilings.
- You need to plan indexes for DocumentDB queries.
- You are migrating from MongoDB to DocumentDB.
- You need to configure backup retention and point-in-time recovery.

## When NOT to use

- **Amazon RDS** — use RDS skills for relational databases.
- **Amazon DynamoDB** — use DynamoDB skills for key-value/NoSQL.
- **Amazon ElastiCache** — use ElastiCache skills for in-memory cache.
- **Amazon Neptune** — use Neptune skills for graph databases.
- **Amazon OpenSearch** — use OpenSearch skills for search/analytics.

## How to invoke

### Slash command

```
/aws:deploy-documentdb-cluster
```

Then provide: cluster name, engine version, instance class, instance
count, subnet group, security group, KMS key (if customer-managed),
backup retention, change streams decision, storage ceiling, indexing
requirements, tags.

### Natural language

Any of these routes to the same skill:

- "create a DocumentDB cluster with change streams"
- "set up a DocumentDB global cluster for DR"
- "enable change streams on DocumentDB for CDC"
- "configure DocumentDB storage autoscaling"
- "create indexes on DocumentDB"

### CLI routing

```bash
node cli/bin/cli.js route "create a documentdb cluster"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create DocumentDB
clusters. The output checklist feeds into verification pipelines and
downstream audit skills.

## Example

```
You: /aws:deploy-documentdb-cluster

     Create a DocumentDB cluster named orders-docdb in us-east-1.
     Engine 5.0, r5.large with 1 primary and 2 replicas.
     Enable change streams with 2-day retention. KMS key
     arn:aws:kms:us-east-1:123456789012:key/abc123.
     Backup 7 days. Storage ceiling 10 TB.
     Indexes on status+created_at and email.

Skill:
  DOCUMENTDB_CLUSTER: orders-docdb (5.0.0)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Instance class: db.r5.large — production
    [✓] Change streams: enabled (retention: 2 days)
    [✓] Storage autoscaling ceiling: 10 TB
    [✓] Indexing strategy: compound + single indexes
  VERIFICATION_COMMANDS:
    aws docdb describe-db-clusters --db-cluster-identifier orders-docdb --region us-east-1
    aws docdb describe-db-instances --query 'DBInstances[?DBClusterIdentifier==`orders-docdb`]' --region us-east-1
```

## References

- Skill definition: `skills/documentdb-cluster-deployer/SKILL.md`
- Storage and change streams guide: `skills/documentdb-cluster-deployer/references/storage-and-changestreams.md`
- Global clusters and indexing guide: `skills/documentdb-cluster-deployer/references/global-clusters-and-indexing.md`
- Eval suite: `skills/documentdb-cluster-deployer/evals/evals.json`
