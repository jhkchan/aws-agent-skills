---
description: Provision an Amazon OpenSearch Service domain (managed cluster or Serverless) with production-grade defaults (Multi-AZ, dedicated masters, encryption, FGAC, VPC-only). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create opensearch domain"
  - "provision opensearch"
  - "deploy opensearch"
  - "set up opensearch"
  - "opensearch managed cluster"
  - "opensearch serverless"
  - "opensearch multi-az"
  - "opensearch dedicated master"
  - "opensearch ultrawarm"
  - "opensearch cold storage"
  - "opensearch encryption"
  - "opensearch fgac"
  - "opensearch vpc"
  - "opensearch vector search"
  - "opensearch shard count"
  - "opensearch snapshot repository"
  - "opensearch streaming ingestion"
  - "elasticsearch domain"
  - "opensearch t3.small.search"
  - "opensearch r6g.search"
routes_to: opensearch-domain-deployer
---

# /aws:deploy-opensearch-domain

Activate the `opensearch-domain-deployer` skill and provision an
Amazon OpenSearch Service domain (managed cluster or Serverless) with
production-grade defaults.

## What it does

The skill walks a 10-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Deployment type (managed cluster vs Serverless — immutable)
2. Instance types (t3 / r6g / c6g / m6g / i3 .search)
3. Multi-AZ (3-zone) + dedicated master nodes
4. Storage (EBS gp3 vs io1 vs instance-store NVMe)
5. Encryption (at-rest KMS + in-transit TLS)
6. Network access + fine-grained access control (FGAC)
7. Indexing (shard count, replica count)
8. Snapshots (automated + manual to S3)
9. UltraWarm / cold storage (tiered storage)
10. OpenSearch Serverless / vector search (latest features)

## When to use

- You need to create a new OpenSearch domain with production defaults.
- You are choosing between managed cluster and Serverless.
- You need to design a Multi-AZ production topology.
- You need to size shards and instances for a workload.
- You need to enable fine-grained access control (FGAC).
- You need to set up UltraWarm or cold storage for cost optimization.
- You need copy-pasteable provisioning commands or Terraform templates.

## How to invoke

### Slash command

```
/aws:deploy-opensearch-domain
```

Then provide: domain name, region, deployment type (managed or
Serverless), workload description (data size, query pattern, ingest
rate), Multi-AZ preference, encryption preference, and any optional
features (UltraWarm, cold storage, vector search, Serverless).

### Natural language

Any of these routes to the same skill:

- "create a production OpenSearch domain"
- "provision an OpenSearch managed cluster with Multi-AZ"
- "deploy OpenSearch Serverless for vector search"
- "set up UltraWarm for log retention"
- "size OpenSearch instances for a 5 TB workload"

### CLI routing

```bash
node cli/bin/cli.js route "create an opensearch domain"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or harden
OpenSearch domains. The output checklist feeds into verification
pipelines and audit skills (opensearch-domain-auditor for
post-deployment audit).

## Example

```
You: /aws:deploy-opensearch-domain

     Provision a production OpenSearch domain "prod-search" in
     us-east-1. Search application, ~500 GB indices, latency-sensitive.
     Managed cluster with 6 data nodes (r6g.2xlarge.search) Multi-AZ
     with 3 dedicated masters (c6g.large.search). EBS gp3 100GB per
     node. Customer CMK alias/prod-opensearch-kms. VPC-only — subnets
     subnet-0aaa/0bbb/0ccc, SG sg-search123 inbound 443 from sg-app456.
     FGAC with IAM master user. Snapshots 14 days. Account: 123456789012.

Skill:
  DOMAIN: prod-search
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Deployment type: managed cluster
    [✓] Instance type: r6g.2xlarge.search
    [✓] Instance count: 6 data nodes (2 per AZ × 3 AZs)
    [✓] Multi-AZ (3-zone): Enabled
    [✓] Dedicated master nodes: 3 × c6g.large.search
    [✓] Storage: EBS gp3 100GB per node
    [✓] Encryption at rest: Enabled (customer CMK)
    [✓] Encryption in transit (TLS): Enabled (TLS 1.2 minimum)
    [✓] Network access: VPC-only
    [✓] FGAC: IAM master user
    [✓] Shard count rule: 30-50 GB per shard applied
    [✓] Replica count: 1
    [✓] Automated snapshots: Enabled (retention 14 days)
  VERIFICATION_COMMANDS:
    aws opensearch describe-domain --domain-name prod-search
    aws opensearch describe-domain-config --domain-name prod-search
    aws kms describe-key --key-id alias/prod-opensearch-kms
    aws iam get-role --role-name opensearch-master
```

## References

- Skill definition: `skills/opensearch-domain-deployer/SKILL.md`
- Topology and indexing guide: `skills/opensearch-domain-deployer/references/topology-and-indexing.md`
- Provisioning CLI commands: `skills/opensearch-domain-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/opensearch-domain-deployer/evals/evals.json`
