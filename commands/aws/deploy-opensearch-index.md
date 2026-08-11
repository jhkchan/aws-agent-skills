---
description: Provision an Amazon OpenSearch Service index with production-grade defaults (shard sizing for 10-50 GB per shard, replica count for read throughput, ILM hot/warm/cold tiering, strict dynamic mapping, alias-based zero-downtime reindex, index templates, data streams, k-NN vector search, search pipelines, snapshot management). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create opensearch index"
  - "deploy opensearch index"
  - "opensearch shard sizing"
  - "opensearch ilm policy"
  - "opensearch index lifecycle"
  - "opensearch alias reindex"
  - "opensearch index template"
  - "opensearch knn vector"
  - "opensearch data stream"
  - "opensearch snapshot repository"
  - "opensearch force merge"
  - "opensearch search pipeline"
  - "opensearch component template"
  - "opensearch mapping"
routes_to: opensearch-index-deployer
---

# /aws:deploy-opensearch-index

Activate the `opensearch-index-deployer` skill and provision an Amazon
OpenSearch Service index with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Domain connectivity and auth (sigv4 or basic auth)
2. Index mappings (dynamic vs strict, keyword vs text, nested vs object)
3. Shard sizing (primary + replica for 10-50 GB per shard)
4. ILM policies (hot/warm/cold tiering, force merge, delete)
5. Alias management for zero-downtime reindexing
6. Index templates and component templates
7. Rollover aliases and data streams for time-series
8. k-NN vector search configuration (HNSW, FAISS, space types)
9. Search pipeline configuration (normalizers, processors)
10. Snapshot management (automated + manual to S3)
11. Force merge for read-only indices
12. Recent features (FAISS filtering, semantic search, cold storage)

## When to use

- You need to create an OpenSearch index with correct shard sizing.
- You are setting up ILM policies for storage tiering.
- You need zero-downtime reindexing via aliases.
- You are deploying k-NN vector search indices.
- You need data streams for time-series ingestion.
- You are configuring index templates or component templates.
- You need search pipeline configuration.

## When NOT to use

- **OpenSearch domain provisioning** — use opensearch-domain-deployer
  for cluster-level configuration (instance type, EBS, access policy).
- **OpenSearch Serverless** — use opensearch-serverless-deployer for
  serverless collections.
- **Domain auditing** — use opensearch-domain-auditor for auditing
  existing domains.

## How to invoke

### Slash command

```
/aws:deploy-opensearch-index
```

Then provide: domain endpoint, auth method, index name, estimated data
volume, shard count, replica count, ILM policy (if needed), alias name
(if reindex), mapping strictness, k-NN config (if vector search), data
stream (if time-series), tags.

### Natural language

Any of these routes to the same skill:

- "create an OpenSearch index for logs with ILM"
- "set up a k-NN vector search index"
- "configure shard sizing for 500 GB index"
- "create an index template for my logs pattern"
- "set up a data stream for metrics"

### CLI routing

```bash
node cli/bin/cli.js route "create an opensearch index"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or
configure OpenSearch indices. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-opensearch-index

     Create an OpenSearch index for application logs on domain
     search-mydomain-abc123.us-east-1.es.amazonaws.com. 150 GB/day.
     Strict mapping. 5 primary shards, 1 replica. ILM rollover at
     50 GB or 1 day, warm at 7 days, delete at 90 days. Rollover
     alias logs-app-write.

Skill:
  OPENSEARCH_INDEX: logs-app-000001
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Primary shards: 5 (30 GB/shard)
    [✓] Replica shards: 1
    [✓] ILM policy: logs-ilm-policy (rollover: 50gb | 1d)
    [✓] Rollover alias: logs-app-write (is_write_index: true)
    [✓] Dynamic mapping: strict
  VERIFICATION_COMMANDS:
    curl -s "<endpoint>/logs-app-000001" -u "user:pass"
    curl -s "<endpoint>/_cat/indices/logs-app-000001?v" -u "user:pass"
```

## References

- Skill definition: `skills/opensearch-index-deployer/SKILL.md`
- Shard sizing and ILM guide: `skills/opensearch-index-deployer/references/shard-sizing-and-ilm.md`
- Templates and data streams guide: `skills/opensearch-index-deployer/references/templates-and-data-streams.md`
- Eval suite: `skills/opensearch-index-deployer/evals/evals.json`
