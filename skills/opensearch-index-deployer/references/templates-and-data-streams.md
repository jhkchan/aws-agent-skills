# Templates and Data Streams — OpenSearch Index Deployer

Deep reference on index templates (legacy vs composable, component
template composition, priority resolution), data streams (backing
indices, lifecycle, append-only semantics), and alias-based reindex
workflows. Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## Index templates

### Legacy vs composable templates

OpenSearch supports two template types:

- **Legacy templates** (`_template`): older format, single template per
  pattern. Deprecated in favor of composable templates.
- **Composable templates** (`_index_template`): modern format,
  supports `composed_of` referencing component templates, `priority`,
  and `version`.

Always use composable templates for new work.

### Composable template structure

```json
PUT _index_template/app-logs-template
{
  "index_patterns": ["app-logs-*"],
  "template": {
    "settings": {
      "number_of_shards": 5,
      "number_of_replicas": 1,
      "index.plugins.index_state_management.policy_id": "logs-ilm-policy",
      "index.plugins.index_state_management.rollover_alias": "app-logs-write"
    },
    "mappings": {
      "dynamic": "strict",
      "properties": {
        "@timestamp": { "type": "date" },
        "message": { "type": "text" },
        "level": { "type": "keyword" },
        "service": { "type": "keyword" },
        "host": { "type": "keyword" },
        "duration_ms": { "type": "integer" }
      }
    },
    "aliases": {
      "app-logs-read": {}
    }
  },
  "composed_of": ["common-mappings", "common-settings"],
  "priority": 200,
  "version": 1
}
```

### Component template composition

Component templates are reusable building blocks referenced by
`composed_of`. Multiple index templates can share the same component.

```json
// Component: common field mappings
PUT _component_template/common-mappings
{
  "template": {
    "mappings": {
      "properties": {
        "@timestamp": { "type": "date" },
        "env": { "type": "keyword" },
        "source": { "type": "keyword" }
      }
    }
  }
}

// Component: common settings
PUT _component_template/common-settings
{
  "template": {
    "settings": {
      "number_of_replicas": 1,
      "index.refresh_interval": "1s"
    }
  }
}

// Index template composes both
PUT _index_template/logs-template
{
  "index_patterns": ["logs-*"],
  "template": {
    "settings": { "number_of_shards": 5 },
    "mappings": {
      "properties": {
        "message": { "type": "text" }
      }
    }
  },
  "composed_of": ["common-mappings", "common-settings"],
  "priority": 200
}
```

### Merge order and priority

When multiple templates match an index pattern:

```text
1. All matching templates are collected.
2. Templates are ordered by priority (higher priority wins).
3. Settings and mappings are merged:
   - Settings: higher-priority template overrides.
   - Mappings: higher-priority template properties win.
   - For composed_of components: applied in order within each template,
     then templates in priority order.
4. If priority is equal, the template name is used as tiebreaker.
```

### Template application timing

Templates apply ONLY when an index is created. They do NOT
retroactively update existing indices.

```text
Timeline:
  1. PUT _index_template/my-template   ← template created
  2. PUT /my-index                     ← template applied (if pattern matches)
  3. PUT _index_template/my-template   ← template updated
  4. PUT /my-index                     ← ERROR (index already exists)
  5. GET /my-index/_mapping            ← old mapping (NOT updated by step 3)

To update existing indices:
  → Reindex to a new index (which will match the updated template)
  → Or use PUT mapping API (limited to adding new fields, not changing types)
```

## Data streams

### What is a data stream?

A data stream is a collection of hidden backing indices designed for
time-series, append-only data. Each document requires an
`@timestamp` field.

```text
Data stream: metrics-ds
  ├── .ds-metrics-ds-2026.08.05-000001  (backing index 1, write index)
  ├── .ds-metrics-ds-2026.08.05-000002  (backing index 2, rolled)
  └── .ds-metrics-ds-2026.08.05-000003  (backing index 3, previous write)

Write → goes to the latest backing index (write index)
Read  → searches across ALL backing indices
Rollover → creates a new backing index, old ones become read-only
```

### Data stream template

```json
PUT _index_template/metrics-ds-template
{
  "index_patterns": ["metrics-ds*"],
  "data_stream": {
    "timestamp_field": "@timestamp"
  },
  "template": {
    "settings": {
      "number_of_shards": 10,
      "number_of_replicas": 1,
      "index.plugins.index_state_management.policy_id": "metrics-ilm-policy"
    },
    "mappings": {
      "dynamic": "strict",
      "properties": {
        "@timestamp": { "type": "date" },
        "metric_name": { "type": "keyword" },
        "value": { "type": "double" },
        "tags": { "type": "keyword" },
        "host": { "type": "keyword" }
      }
    }
  },
  "priority": 500,
  "version": 1
}
```

### Creating and using a data stream

```json
// Create the data stream
PUT _data_stream/metrics-ds

// Ingest (append-only — do NOT specify a document ID)
POST metrics-ds/_doc
{
  "@timestamp": "2026-08-05T10:30:00.000Z",
  "metric_name": "cpu_usage",
  "value": 72.5,
  "tags": ["web-server", "us-east-1a"],
  "host": "i-abc123"
}

// Search across all backing indices
GET metrics-ds/_search
{
  "query": {
    "range": {
      "@timestamp": {
        "gte": "2026-08-05T00:00:00.000Z",
        "lt": "2026-08-06T00:00:00.000Z"
      }
    }
  }
}

// Manual rollover (if not using ILM auto-rollover)
POST metrics-ds/_rollover
{
  "conditions": {
    "max_age": "1d",
    "max_docs": 100000000
  }
}
```

### Data stream vs rollover alias

| Feature | Data Stream | Rollover Alias |
|---|---|---|
| ID assignment | Auto-generated (append-only) | Manual or auto |
| Updates/deletes | On backing indices | On the index |
| @timestamp required | Yes | No |
| Template type | Data stream template | Index template |
| Hidden backing indices | Yes (prefixed with `.ds-`) | No (visible indices) |
| Best for | Pure time-series (logs, metrics) | Semi-structured (events, products) |

### Deleting old data from a data stream

```json
// Delete by age using the data stream lifecycle or ILM
// Manual deletion of old backing indices:
DELETE .ds-metrics-ds-2026.05.01-000001

// Or use the modify_data_stream API to remove backing indices:
POST _data_stream/metrics-ds/_modify
{
  "actions": [
    {
      "remove_backing_index": {
        "index": ".ds-metrics-ds-2026.05.01-000001"
      }
    }
  ]
}
```

## Alias-based reindex workflow

### When to reindex

Reindexing is required when you need to change:
- Field types (immutable after creation)
- Analyzer configuration
- Dynamic setting (true → strict)
- Shard count (if not using split/shrink)

### Zero-downtime reindex workflow

```text
Step 1: Application writes and reads from index "products-v1"
         Alias: products → products-v1

Step 2: Create "products-v2" with new mappings
         Alias: products → products-v1 (unchanged)

Step 3: Reindex (background, non-blocking)
         POST _reindex?wait_for_completion=false
         Source: products-v1 → Dest: products-v2

Step 4: Monitor reindex progress
         GET _tasks/<task_id>

Step 5: Atomic alias swap
         Remove: products → products-v1
         Add: products → products-v2
         (Single POST _aliases call = atomic = zero downtime)

Step 6: Application now reads/writes to "products-v2" via alias
         Delete products-v1 when confident
```

### Reindex with query filtering

```json
POST _reindex?wait_for_completion=false
{
  "source": {
    "index": "products-v1",
    "query": {
      "bool": {
        "must": [
          { "term": { "is_active": true } }
        ]
      }
    }
  },
  "dest": {
    "index": "products-v2"
  }
}
```

### Reindex with script for field transformation

```json
POST _reindex?wait_for_completion=false
{
  "source": { "index": "products-v1" },
  "dest": { "index": "products-v2" },
  "script": {
    "source": """
      if (ctx._source.metadata != null) {
        ctx._source.metadata_list = ctx._source.metadata;
        ctx._source.remove('metadata');
      }
    """,
    "lang": "painless"
  }
}
```

### Monitoring reindex progress

```bash
# Check task status
curl -s "https://<endpoint>/_tasks/<task_id>?detailed=true" -u "user:pass"

# Check reindexed document count
curl -s "https://<endpoint>/_cat/indices/products-v2?v" -u "user:pass"
```
