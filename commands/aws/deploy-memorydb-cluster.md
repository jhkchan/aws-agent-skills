---
description: Provision an Amazon MemoryDB for Redis cluster (durable in-memory database) with production-grade defaults (Multi-AZ shard-level failover, TLS on by default, named ACLs, data tiering, snapshots). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create memorydb cluster"
  - "provision memorydb"
  - "deploy memorydb"
  - "memorydb cluster"
  - "memorydb redis"
  - "memorydb acl"
  - "memorydb multi-az"
  - "memorydb data tiering"
  - "memorydb multi-region"
  - "memorydb snapshots"
  - "memorydb tls"
  - "memorydb shard count"
  - "memorydb replica count"
  - "memorydb subnet group"
  - "memorydb encryption"
  - "memorydb parameter group"
  - "durable redis aws"
  - "in-memory database aws"
routes_to: memorydb-cluster-deployer
---

# /aws:deploy-memorydb-cluster

Activate the `memorydb-cluster-deployer` skill and provision an
Amazon MemoryDB for Redis cluster (durable in-memory database) with
production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. MemoryDB vs ElastiCache (boundary call — durable DB vs cache)
2. Node type + shard count + replica count
3. Multi-AZ with shard-level failover
4. Network + security (VPC, subnet group, security group, port 6379)
5. Encryption (TLS at-rest + in-transit, on by default)
6. ACLs (user-based access control — REQUIRED)
7. Parameter groups (maxmemory-policy)
8. Snapshots (automated + manual)
9. Data tiering (SSD cost optimization — one-way door)
10. Multi-Region / recent features

## When to use

- You need to create a new MemoryDB cluster with production defaults.
- You are sizing nodes, shards, and replicas for a durable workload.
- You need to design a Multi-AZ topology with shard-level failover.
- You need to harden TLS and configure named ACLs.
- You need to enable data tiering for a large hot/cold dataset.
- You need to enable Multi-Region for cross-region reads / DR.
- You want to validate that a cluster design meets production baseline.
- You need copy-pasteable provisioning commands or Terraform templates.

## When NOT to use

- **ElastiCache** (disposable cache, cache-miss acceptable, no
  durability requirement) — ElastiCache is cheaper for non-durable
  data. Use `elasticache-cache-deployer` instead.
- **Self-managed Redis on EC2** — not MemoryDB.
- **Non-Redis databases** (DynamoDB, RDS, etc.) — not MemoryDB.
- **Auditing an existing MemoryDB cluster's posture** — use an
  auditor skill instead.

## How to invoke

### Slash command

```
/aws:deploy-memorydb-cluster
```

Then provide: cluster name, region, engine version, node type, shard
count, replica count, workload description (data size, write rate,
hot/cold pattern), Multi-AZ preference, ACL details (named ACL with
least-privilege users), and any optional features (data tiering,
Multi-Region, snapshots).

### Natural language

Any of these routes to the same skill:

- "create a production MemoryDB cluster with Multi-AZ"
- "provision a durable Redis database on MemoryDB"
- "set up MemoryDB with data tiering for a large dataset"
- "enable Multi-Region on my MemoryDB cluster"
- "configure a named ACL for MemoryDB"

### CLI routing

```bash
node cli/bin/cli.js route "create a memorydb cluster"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or harden
MemoryDB clusters. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-memorydb-cluster

     Provision a production MemoryDB cluster "prod-memorydb" in
     us-east-1. Durable in-memory database — data MUST survive node
     failure. 3 shards with 1 replica each for Multi-AZ.
     db.r6g.24xlarge. Engine 7.0. Customer CMK alias/prod-memorydb-kms.
     Named ACL prod-acl with users app-rw (read-write) and analytics-ro
     (read-only). Snapshots 7 days, window 03:00-05:00 UTC. Subnet
     group prod-memorydb-subnet spans 3 AZs. Security group
     sg-memorydb123 inbound 6379 from sg-app456. Account: 123456789012.

Skill:
  MEMORYDB: prod-memorydb
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Service: MemoryDB (durable in-memory database, NOT ElastiCache cache)
    [✓] Engine version: 7.0
    [✓] Node type: db.r6g.24xlarge (306.15 GiB usable per shard)
    [✓] Shard count: 3 (918.45 GiB total usable)
    [✓] Replicas per shard: 1 (Multi-AZ failover)
    [✓] Multi-AZ with shard-level failover: Enabled
    [✓] Subnet group: prod-memorydb-subnet (3 AZs)
    [✓] Security group: sg-memorydb123 (inbound 6379 from sg-app456)
    [✓] TLS at rest: Enabled (customer CMK alias/prod-memorydb-kms)
    [✓] TLS in transit: Enabled
    [✓] ACL: prod-acl (users: app-rw, analytics-ro; NOT open-access)
    [✓] Snapshot retention: 7 days (03:00-05:00 UTC)
  VERIFICATION_COMMANDS:
    aws memorydb describe-clusters --cluster-name prod-memorydb --show-shard-node-info
    aws memorydb describe-acls --acl-name prod-acl
    aws kms describe-key --key-id alias/prod-memorydb-kms
```

## References

- Skill definition: `skills/memorydb-cluster-deployer/SKILL.md`
- Topology and tiering guide: `skills/memorydb-cluster-deployer/references/topology-and-tiering.md`
- Provisioning CLI commands: `skills/memorydb-cluster-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/memorydb-cluster-deployer/evals/evals.json`
