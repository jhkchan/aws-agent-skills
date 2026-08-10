---
description: Provision an ElastiCache (Redis or Memcached) cluster with production-grade defaults (engine selection, cluster mode, Multi-AZ failover, encryption, AUTH, snapshots). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create elasticache cluster"
  - "provision elasticache"
  - "provision redis cluster"
  - "provision memcached cluster"
  - "deploy elasticache"
  - "elasticache redis"
  - "elasticache memcached"
  - "redis replication group"
  - "redis cluster mode"
  - "elasticache multi-az"
  - "redis failover"
  - "elasticache encryption"
  - "elasticache auth token"
  - "elasticache tls"
  - "elasticache subnet group"
  - "elasticache parameter group"
  - "maxmemory-policy"
  - "elasticache snapshot"
  - "global datastore"
  - "elasticache serverless"
  - "cache node type"
  - "redis vs memcached"
routes_to: elasticache-cache-deployer
---

# /aws:deploy-elasticache-cache

Activate the `elasticache-cache-deployer` skill and provision an
ElastiCache (Redis or Memcached) cluster with production-grade defaults.

## What it does

The skill walks a 10-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Engine selection (Redis vs Memcached — immutable)
2. Cluster mode decision (enabled vs disabled — write scaling)
3. Node type sizing (cache.t3 / r6g / x2g / m6g)
4. Multi-AZ + automatic failover (Redis only)
5. Network + security (VPC, subnet group, security group, ports)
6. Encryption + AUTH + TLS (Redis only)
7. Parameter groups (maxmemory-policy, timeout, tcp-keepalive)
8. Snapshots / backups (Redis only)
9. ElastiCache Serverless / Global Datastore (latest features)
10. CloudWatch alarms (operational hygiene)

## When to use

- You need to create a new ElastiCache cluster with production defaults.
- You are choosing between Redis and Memcached for a workload.
- You need to design a Multi-AZ Redis failover topology.
- You need to size cache nodes for a workload.
- You want to validate that a cluster design meets production baseline.
- You need copy-pasteable provisioning commands or Terraform templates.

## How to invoke

### Slash command

```
/aws:deploy-elasticache-cache
```

Then provide: cluster name, region, engine choice (Redis or Memcached),
workload description (cache vs store, write rate, data size), Multi-AZ
preference, encryption preference, and any optional features (snapshots,
Global Datastore, Serverless).

### Natural language

Any of these routes to the same skill:

- "create a production ElastiCache Redis cluster"
- "provision a Redis replication group with Multi-AZ"
- "deploy a Memcached cache"
- "set up a Global Datastore for cross-region Redis"
- "size cache nodes for a high-throughput workload"

### CLI routing

```bash
node cli/bin/cli.js route "create an elasticache cluster"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or harden
ElastiCache clusters. The output checklist feeds into verification
pipelines and audit skills (elasticache-cluster-auditor for
post-deployment audit).

## Example

```
You: /aws:deploy-elasticache-cache

     Provision a production Redis cluster "prod-cache" in us-east-1.
     Cluster mode enabled with 3 shards, 1 replica per shard.
     cache.r6g.2xlarge nodes. General cache workload. Customer CMK
     alias/prod-cache-kms. TLS + AUTH. Snapshots 7 days, window
     03:00-05:00 UTC. Subnet group prod-cache-subnet spans 3 AZs.
     Security group sg-cache123 inbound 6379 from sg-app456.
     Account: 123456789012.

Skill:
  CACHE: prod-cache
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Engine: redis
    [✓] Cluster mode: ENABLED (3 shards)
    [✓] Node type: cache.r6g.2xlarge (31.17 GiB usable per shard)
    [✓] Replicas: 1 per shard (3 total) — Multi-AZ failover
    [✓] Multi-AZ with automatic failover: Enabled
    [✓] Subnet group: prod-cache-subnet (3 AZs)
    [✓] Security group: sg-cache123 (inbound 6379 from sg-app456)
    [✓] Encryption at rest: Enabled (customer CMK alias/prod-cache-kms)
    [✓] Encryption in transit (TLS): Enabled
    [✓] AUTH token: Enabled (Secrets Manager)
    [✓] Parameter group: maxmemory-policy=allkeys-lru
    [✓] Snapshot retention: 7 days (03:00-05:00 UTC)
  VERIFICATION_COMMANDS:
    aws elasticache describe-replication-groups --replication-group-id prod-cache
    aws elasticache describe-cache-clusters --cache-cluster-id prod-cache-0001 --show-cache-node-info
    aws kms describe-key --key-id alias/prod-cache-kms
```

## References

- Skill definition: `skills/elasticache-cache-deployer/SKILL.md`
- Engine and topology guide: `skills/elasticache-cache-deployer/references/engine-and-topology.md`
- Provisioning CLI commands: `skills/elasticache-cache-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/elasticache-cache-deployer/evals/evals.json`
