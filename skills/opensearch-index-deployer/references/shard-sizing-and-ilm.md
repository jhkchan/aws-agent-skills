# Shard Sizing and ILM — OpenSearch Index Deployer

Deep reference on shard sizing strategy (the 10-50 GB per shard
heuristic, primary vs replica trade-offs, over-sharding costs), ILM
policy configuration (hot/warm/cold phases, rollover alias mechanics,
force merge timing), and storage tiering cost optimization. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Shard sizing fundamentals

### Why shard size matters

Each shard is an independent Lucene index. More shards means:

- More cluster state overhead (each shard is tracked in cluster state).
- More memory for shard overhead (each shard has its own data
  structures: term dictionaries, doc values, etc.).
- More file handles and threads.
- Slower recovery during node failures (more shards to relocate).

Fewer, larger shards are generally more efficient than many small
shards. But shards that are too large (>50 GB) cause slow searches and
slow recovery.

### The 10-50 GB sweet spot

```text
< 10 GB per shard:
  Overhead dominates. Each shard has ~50-200 MB of fixed overhead.
  A 1 GB shard wastes 5-20% of its resources on overhead.
  → Reduce primary shard count.

10-50 GB per shard:
  Optimal range. Overhead is amortized. Searches are fast.
  Recovery is manageable.
  → This is the target.

> 50 GB per shard:
  Searches become slower (more data to scan per shard).
  Recovery takes longer (more data to copy).
  Force merge creates very large segments (slow to read).
  → Increase primary shard count or use ILM rollover.
```

### Calculating shard count from data volume

```text
Estimated daily data volume: 150 GB (before replicas)
Desired shard size: 30 GB (middle of 10-50 GB range)

Primary shard count = ceil(150 / 30) = 5

With 1 replica:
  Total storage = 150 GB * (1 + 1 replica) = 300 GB
  Total shards = 5 primary + 5 replica = 10 shards

With 2 replicas:
  Total storage = 150 GB * (1 + 2 replicas) = 450 GB
  Total shards = 5 primary + 10 replica = 15 shards
```

### Over-sharding detection

```bash
# Check average shard size across indices
curl -s "https://<endpoint>/_cat/indices?v&h=index,pri,rep,store.size,pri.store.size" \
  -u "user:pass"

# Look for indices with many small shards (pri.store.size < 5 GB)
# If most shards are < 5 GB, you are over-sharded
```

### Using the split and shrink APIs

The split API creates a new index with MORE primary shards (must be a
multiple of the original). The shrink API creates a new index with
FEWER primary shards.

**Split (increase shards):**

```json
POST /logs-small/_split/logs-large
{
  "settings": {
    "index.number_of_shards": 10
  }
}
```

**Shrink (decrease shards):**

```json
POST /logs-over-sharded/_shrink/logs-right-sized
{
  "settings": {
    "index.number_of_shards": 2,
    "index.number_of_replicas": 1
  }
}
```

Both require the source index to be read-only (block writes first).

## ILM policy configuration

### Hot/warm/cold architecture

OpenSearch domains with dedicated node types:

```text
Cluster node configuration:
  Hot nodes:    SSD storage, high CPU/memory (e.g., r6gd.4xlarge)
    → Active write indices, recent data
    → Highest cost per GB

  Warm nodes:   SSD or HDD, moderate CPU/memory (e.g., r6gd.2xlarge)
    → Read-only indices, force-merged
    → ~50% lower cost than hot

  Cold nodes:   HDD or searchable cold storage, minimal CPU
    → Rarely queried indices
    → ~80% lower cost than hot
```

### ILM policy anatomy

```json
{
  "policy": {
    "description": "Lifecycle: rollover, warm, cold, delete",
    "default_state": "hot",
    "states": [
      {
        "name": "hot",
        "actions": [
          {
            "rollover": {
              "min_size": "50gb",
              "min_age": "1d",
              "min_doc_count": 100000000
            }
          }
        ],
        "transitions": [
          {
            "state_name": "warm",
            "conditions": { "min_index_age": "7d" }
          }
        ]
      },
      {
        "name": "warm",
        "actions": [
          { "force_merge": { "max_num_segments": 1 } },
          { "allocate": {
              "include": { "data": "warm" }
            }
          }
        ],
        "transitions": [
          {
            "state_name": "cold",
            "conditions": { "min_index_age": "30d" }
          }
        ]
      },
      {
        "name": "cold",
        "actions": [
          { "allocate": {
              "include": { "data": "cold" }
            }
          }
        ],
        "transitions": [
          {
            "state_name": "delete",
            "conditions": { "min_index_age": "90d" }
          }
        ]
      },
      {
        "name": "delete",
        "actions": [ { "delete": {} } ],
        "transitions": []
      }
    ]
  }
}
```

### Rollover alias mechanics

The rollover action creates a new write index and points the alias to
it. The initial index MUST have the alias set as the write index.

```json
// Correct: initial index with write alias
PUT /logs-app-000001
{
  "aliases": {
    "logs-app-write": { "is_write_index": true }
  }
}

// WRONG: alias without is_write_index
PUT /logs-app-000001
{
  "aliases": {
    "logs-app-write": {}
  }
}
// → Rollover fails: "alias [logs-app-write] does not point to a write index"
```

### Common ILM pitfalls

1. **Rollover alias not set as write index.** The ILM rollover action
   fails. Always set `"is_write_index": true` on the initial index.

2. **ILM policy not attached to the index.** The policy must be
   referenced via index setting
   `"plugins.index_state_management.policy_id"` or via an ISM template
   matching the index pattern.

3. **Node attributes missing for allocate action.** The allocate action
   requires node attributes (e.g., `data: warm`). Verify the domain's
   warm/cold nodes have the correct attributes.

4. **Force merge on write-active index.** In the warm phase, force
   merge runs on a rollover'd index (no longer receiving writes). If
   the rollover didn't happen, force merge runs on the write index and
   creates an unmergeable segment.

## Force merge best practices

Force merge reduces the number of Lucene segments. Optimal for read-
only indices in the warm/cold tier.

```text
Before force merge (10 segments):
  Segment 1: 5 GB
  Segment 2: 3 GB
  ... (8 more small segments)
  Total: 15 GB across 10 segments
  → More file handles, more I/O per search

After force merge (1 segment):
  Segment 1: 15 GB
  → Fewer file handles, faster searches, less I/O
```

**Always block writes before force merge:**

```json
PUT /logs-app-2026.07.01/_settings
{
  "index": { "blocks": { "write": true } }
}

POST /logs-app-2026.07.01/_forcemerge?max_num_segments=1
```

## Terraform examples

```hcl
resource "aws_opensearch_domain" "main" {
  domain_name = "my-domain"

  cluster_config {
    instance_type  = "r6gd.4xlarge.search"
    instance_count = 3

    warm_count         = 3
    warm_type          = "r6gd.2xlarge.search"
    warm_enabled       = true

    cold_storage_enabled = true

    zone_awareness_enabled = true
    zone_awareness_config {
      availability_zone_count = 3
    }
  }

  ebs_options {
    ebs_enabled = true
    volume_size = 100
    volume_type = "gp3"
  }
}

# Index creation via opensearch provider
# Note: index management is typically done via API calls, not Terraform
# Use a local-exec provisioner or a CI job for index creation.
```

```hcl
# Component template as JSON
locals {
  common_mappings = jsonencode({
    template = {
      mappings = {
        properties = {
          "@timestamp" = { type = "date" }
          source       = { type = "keyword" }
        }
      }
    }
  })
}

# Apply via curl in a null_resource
resource "null_resource" "component_template" {
  triggers = {
    mappings = local.common_mappings
  }

  provisioner "local-exec" {
    command = <<-EOT
      curl -X PUT "https://${aws_opensearch_domain.main.endpoint}/_component_template/common-mappings" \
        -H "Content-Type: application/json" \
        -d '${local.common_mappings}'
    EOT
  }
}
```

## Expert heuristic: shard sizing (10-50 GB per shard)
A baseline model says "use the default 5 shards." The correct heuristic
sizes shards to the 10-50 GB range, adjusting primary count to data
volume.

```text
Estimated index size (primary data, no replicas):
  ├── < 10 GB  → 1 primary shard (1 shard at <10 GB is efficient)
  ├── 10-50 GB → 1 primary shard (sweet spot)
  ├── 50-100 GB → 2 primary shards (25-50 GB each)
  ├── 100-250 GB → 5 primary shards (20-50 GB each)
  ├── 250-500 GB → 10 primary shards (25-50 GB each)
  ├── 500 GB-1 TB → 20 primary shards (25-50 GB each)
  └── 1 TB+ → use data streams + ILM rollover (avoid single huge index)

Replica count decision:
  ├── HA requirement → minimum 1 replica (survives 1 node loss)
  ├── Read QPS is high → 2-3 replicas (each replica serves search)
  └── Cost-sensitive dev/staging → 0 replicas (cluster yellow, no HA)
```

**Key implication:** over-sharding is the #1 OpenSearch performance
killer. Too many small shards create overhead in cluster state, merge
scheduling, and memory. Target 10-50 GB per shard. When in doubt,
fewer larger shards is better than many small shards.

## Expert heuristic: replica count for read throughput
Replicas serve two purposes: high availability AND read scaling. Each
replica shard can independently serve search queries.

```text
1 primary + 0 replicas = 1x read capacity (no HA)
1 primary + 1 replica  = 2x read capacity (survives 1 node loss)
1 primary + 2 replicas = 3x read capacity (survives 2 node loss)
1 primary + 3 replicas = 4x read capacity
```

**Key implication:** for read-heavy workloads (product search, log
dashboards), adding replicas is cheaper than scaling instances. For
write-heavy workloads (ingestion pipelines), invest in more primary
shards or larger instances instead.

## Expert heuristic: ILM rollover for storage tiering
ILM automates the transition of indices through hot, warm, cold, and
delete phases, reducing cost for time-series data.

```text
HOT:   active write index, SSD, high-compute nodes
  → rollover when: max_age (1d) OR max_size (50gb)
WARM:  read-only, force merge to 1 segment, fewer compute resources
  → transition when: 7d after rollover
COLD:  rarely searched, minimal compute, cheapest storage
  → transition when: 30d after rollover
DELETE: permanently remove
  → delete when: 90d after rollover
```

**Key implication:** without ILM, indices accumulate on hot nodes
forever, driving cost. ILM rollover + tiering can cut OpenSearch costs
by 50-70% for time-series workloads.
