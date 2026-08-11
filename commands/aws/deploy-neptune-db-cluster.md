---
description: Provision an Amazon Neptune DB cluster (graph database) with production-grade defaults (Multi-AZ failover, TLS, IAM auth, customer CMK, Streams, bulk load from S3). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create neptune cluster"
  - "provision neptune"
  - "provision graph database"
  - "deploy neptune"
  - "neptune db cluster"
  - "neptune gremlin"
  - "neptune sparql"
  - "neptune opencypher"
  - "neptune multi-az"
  - "neptune reader instance"
  - "neptune failover"
  - "neptune encryption"
  - "neptune_enforce_ssl"
  - "neptune_query_timeout"
  - "neptune iam database auth"
  - "neptune parameter group"
  - "neptune subnet group"
  - "neptune kms"
  - "neptune bulk load"
  - "neptune loader"
  - "neptune streams"
  - "neptune snapshot"
  - "graph database aws"
routes_to: neptune-db-cluster-deployer
---

# /aws:deploy-neptune-db-cluster

Activate the `neptune-db-cluster-deployer` skill and provision an
Amazon Neptune DB cluster (graph database) with production-grade
defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Neptune DB vs Neptune Analytics (boundary call)
2. Instance class + cluster size (writer + readers)
3. Multi-AZ with reader promotion
4. Network + security (VPC, subnet group, security group, port 8182)
5. Encryption (KMS at creation — immutable)
6. Parameter groups (neptune_enforce_ssl, neptune_query_timeout)
7. IAM database auth (token-based access)
8. Bulk load from S3 (Neptune Loader)
9. Query languages (Gremlin, SPARQL, openCypher)
10. Streams / snapshots / recent features

## When to use

- You need to create a new Neptune DB cluster with production defaults.
- You are sizing writer and reader instances for a graph workload.
- You need to design a Multi-AZ topology with reader promotion.
- You need to harden TLS via neptune_enforce_ssl and IAM database auth.
- You need to bulk load graph data from S3 via the Neptune Loader.
- You need to enable Neptune Streams for change data capture.
- You want to validate that a cluster design meets production baseline.
- You need copy-pasteable provisioning commands or Terraform templates.

## When NOT to use

- **Neptune Analytics** (PageRank, connected-components, batch graph
  algorithms on a large static graph) — Neptune Analytics is a
  SEPARATE service with its own `aws graph` API. This skill only
  provisions Neptune DB.
- **Self-managed Neo4j / JanusGraph on EC2** — not Neptune.
- **Auditing an existing Neptune cluster's posture** — use an
  auditor skill instead.

## How to invoke

### Slash command

```
/aws:deploy-neptune-db-cluster
```

Then provide: cluster name, region, engine version, instance class,
workload description (graph size, query depth, write rate), Multi-AZ
preference, encryption preference (customer CMK ARN or AWS-managed),
query languages (Gremlin / SPARQL / openCypher), and any optional
features (Streams, bulk load source, snapshots).

### Natural language

Any of these routes to the same skill:

- "create a production Neptune DB cluster with Multi-AZ"
- "provision a Gremlin property-graph database"
- "set up a SPARQL endpoint on Neptune"
- "load graph data into Neptune from S3"
- "enable Neptune Streams for change capture"

### CLI routing

```bash
node cli/bin/cli.js route "create a neptune db cluster"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or harden
Neptune DB clusters. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-neptune-db-cluster

     Provision a production Neptune DB cluster "prod-graph" in
     us-east-1. Gremlin property-graph, ~200M vertices + 1B edges.
     1 writer + 2 readers across 3 AZs. db.r6g.8xlarge. Engine
     1.3.2.0. Customer CMK alias/prod-graph-kms. neptune_enforce_ssl=1,
     IAM database auth, neptune_query_timeout=30000, Streams enabled.
     Snapshots 7 days. Deletion protection. Subnet group
     prod-neptune-subnet. Security group sg-neptune123 inbound 8182
     from sg-app456. Account: 123456789012.

Skill:
  NEPTUNE: prod-graph
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Service: Neptune DB (NOT Analytics)
    [✓] Engine version: 1.3.2.0 (pinned)
    [✓] Writer instance: db.r6g.8xlarge
    [✓] Reader instances: 2 (across us-east-1b, us-east-1c for Multi-AZ)
    [✓] Multi-AZ with reader promotion: Enabled
    [✓] Subnet group: prod-neptune-subnet (3 AZs)
    [✓] Security group: sg-neptune123 (inbound 8182 from sg-app456)
    [✓] Encryption at rest: Enabled (customer CMK alias/prod-graph-kms)
    [✓] TLS / neptune_enforce_ssl: Enabled
    [✓] IAM database auth: Enabled
    [✓] Parameter group: neptune_query_timeout=30000, neptune_streams=1
    [✓] Snapshot retention: 7 days
    [✓] Deletion protection: Enabled
  VERIFICATION_COMMANDS:
    aws neptune describe-db-clusters --db-cluster-identifier prod-graph
    aws neptune describe-db-instances --db-instance-identifier prod-graph-instance-1
    aws kms describe-key --key-id alias/prod-graph-kms
```

## References

- Skill definition: `skills/neptune-db-cluster-deployer/SKILL.md`
- Instance and topology guide: `skills/neptune-db-cluster-deployer/references/instance-and-topology.md`
- Provisioning CLI commands: `skills/neptune-db-cluster-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/neptune-db-cluster-deployer/evals/evals.json`
