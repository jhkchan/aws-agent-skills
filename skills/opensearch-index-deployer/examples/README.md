# End-to-End Example: OpenSearch Index Deployment

A walkthrough showing how to use the `opensearch-index-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a production logs index on Amazon OpenSearch
Service with ILM tiering, strict dynamic mapping, and a rollover
alias. The index needs:

- Domain: search-mydomain-abc123.us-east-1.es.amazonaws.com
- Index name: logs-app-000001 (initial write index)
- Estimated data: 150 GB/day
- Dynamic mapping: strict
- Shards: 5 primary, 1 replica
- ILM policy: rollover at 50 GB / 1 day, warm at 7d, delete at 90d
- Rollover alias: logs-app-write
- Index template: logs-template (pattern: logs-app-*)
- Tags: Environment=production, Application=app-logs

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-opensearch-index
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an OpenSearch index for application logs on domain
      search-mydomain-abc123.us-east-1.es.amazonaws.com. 150 GB/day.
      Strict mapping. 5 primary shards, 1 replica. ILM rollover at
      50 GB or 1 day, warm at 7 days, delete at 90 days. Rollover
      alias logs-app-write."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an opensearch index"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
OPENSEARCH_INDEX: logs-app-000001 (search-mydomain-abc123.us-east-1.es.amazonaws.com)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Domain endpoint: search-mydomain-abc123.us-east-1.es.amazonaws.com
  [✓] Cluster health: green
  [✓] Index name: logs-app-000001
  [✓] Dynamic mapping: strict
  [✓] Primary shards: 5 (target: 30 GB/shard, estimated 150 GB total)
  [✓] Replica shards: 1 (read throughput: 2x, HA: yes)
  [✓] ILM policy: logs-ilm-policy (rollover: 50gb | 1d)
  [✓] Rollover alias: logs-app-write (is_write_index: true)
  [✓] Index template: logs-template (pattern: logs-app-*)
  [✓] Data stream: disabled (using rollover alias)
  [✓] k-NN vector search: disabled
  [✓] Snapshot repository: automated-only
  [✓] Tags: Environment=production, Application=app-logs
VERIFICATION_COMMANDS:
  curl -s "https://search-mydomain-abc123.us-east-1.es.amazonaws.com/logs-app-000001" -u "user:pass"
  curl -s "https://search-mydomain-abc123.us-east-1.es.amazonaws.com/_cat/indices/logs-app-000001?v" -u "user:pass"
  curl -s "https://search-mydomain-abc123.us-east-1.es.amazonaws.com/_cluster/health/logs-app-000001?pretty" -u "user:pass"
```

---

## Step 3 — Provisioning commands

### Create the ILM policy

```json
PUT _ilm/policy/logs-ilm-policy
{
  "policy": {
    "description": "Logs lifecycle: rollover at 50GB/1day, warm after 7d, delete after 90d",
    "default_state": "hot",
    "states": [
      {
        "name": "hot",
        "actions": [],
        "transitions": [{ "state_name": "warm", "conditions": { "min_index_age": "7d" } }]
      },
      {
        "name": "warm",
        "actions": [{ "force_merge": { "max_num_segments": 1 } }],
        "transitions": [{ "state_name": "delete", "conditions": { "min_index_age": "90d" } }]
      },
      {
        "name": "delete",
        "actions": [{ "delete": {} }],
        "transitions": []
      }
    ],
    "ism_template": { "index_patterns": ["logs-app-*"], "priority": 100 }
  }
}
```

### Create the index template

```json
PUT _index_template/logs-template
{
  "index_patterns": ["logs-app-*"],
  "template": {
    "settings": {
      "number_of_shards": 5,
      "number_of_replicas": 1
    },
    "mappings": {
      "dynamic": "strict",
      "properties": {
        "@timestamp": { "type": "date" },
        "message": { "type": "text" },
        "level": { "type": "keyword" },
        "service": { "type": "keyword" },
        "duration_ms": { "type": "integer" }
      }
    }
  },
  "priority": 200,
  "version": 1
}
```

### Create the initial index with rollover alias

```json
PUT /logs-app-000001
{
  "settings": {
    "index": {
      "number_of_shards": 5,
      "number_of_replicas": 1,
      "plugins.index_state_management.rollover_alias": "logs-app-write"
    }
  },
  "aliases": {
    "logs-app-write": { "is_write_index": true },
    "logs-app-read": {}
  }
}
```

### Trigger the first rollover

```json
POST logs-app-write/_rollover
{
  "conditions": { "max_size": "50gb", "max_age": "1d" }
}
```

---

## Step 4 — Post-deployment verification

```bash
# Index exists and has correct settings
curl -s "https://<endpoint>/logs-app-000001?pretty" -u "user:pass"

# Index shard allocation and size
curl -s "https://<endpoint>/_cat/indices/logs-app-000001?v" -u "user:pass"

# ILM status for the index
curl -s "https://<endpoint>/_plugins/_ism/explain/logs-app-000001?pretty" -u "user:pass"

# Alias configuration
curl -s "https://<endpoint>/_alias/logs-app-write?pretty" -u "user:pass"

# Cluster health
curl -s "https://<endpoint>/_cluster/health/logs-app-000001?pretty" -u "user:pass"
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Shard count | Default 5 shards regardless of size | 5 shards for 150 GB (30 GB/shard) | Must target 10-50 GB per shard for performance |
| ILM rollover | Policy without rollover alias | Rollover alias with is_write_index=true | Rollover fails without the write index flag |
| Dynamic mapping | Default (true) | strict | Production needs explicit field mapping to prevent type guessing |
| Template timing | Created after the index | Created before the index | Templates only apply to new indices |
| Force merge | On write-active index | Only on read-only (warm phase) | Force merging write-active creates unmergeable segments |
| k-NN | Enable after creation | Must be set at creation (immutable) | index.knn is immutable |

---

## Related artifacts

- **Skill definition:** `skills/opensearch-index-deployer/SKILL.md`
- **Shard sizing and ILM guide:** `skills/opensearch-index-deployer/references/shard-sizing-and-ilm.md`
- **Templates and data streams guide:** `skills/opensearch-index-deployer/references/templates-and-data-streams.md`
- **Slash command:** `commands/aws/deploy-opensearch-index.md`
- **Eval suite:** `skills/opensearch-index-deployer/evals/evals.json`
- **Legacy test cases:** `skills/opensearch-index-deployer/eval/test-cases.yaml`
