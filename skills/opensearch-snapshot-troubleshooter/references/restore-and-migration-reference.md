# OpenSearch Restore & UltraWarm/Cold Migration Reference

Supplementary reference for the OpenSearch Snapshot Troubleshooter
skill. Loaded on-demand when a diagnostic needs restore rename
syntax, alias-conflict resolution, UltraWarm/Cold tier requirements,
or shard-recovery throttling settings.

## Restore API

### Basic restore

```bash
curl -X POST "https://$ENDPOINT/_snapshot/<repo>/<snap>/_restore?wait_for_completion=false" \
  -H 'Content-Type: application/json' -d '{"indices": "logs-*"}'
```

### Rename on restore (avoid alias/index conflicts)

```bash
curl -X POST "https://$ENDPOINT/_snapshot/<repo>/<snap>/_restore" \
  -H 'Content-Type: application/json' -d '{
    "indices": "logs-*",
    "rename_pattern": "logs-",
    "rename_replacement": "restored-logs-"
  }'
```

`rename_pattern` is a regex; `rename_replacement` supports `$1`-style
backreferences. Clashes with existing names after rename still fail.

### Restore with index settings override

```bash
curl -X POST "https://$ENDPOINT/_snapshot/<repo>/<snap>/_restore" \
  -H 'Content-Type: application/json' -d '{
    "indices": "logs-*",
    "index_settings": {
      "index.number_of_replicas": 1,
      "index.refresh_interval": "30s"
    }
  }'
```

Use this to lower replicas on restore (faster) and raise after the
cluster is stable.

## Restore conflict scenarios

| Conflict | Symptom | Fix |
|---|---|---|
| Index exists with same name | `resource_already_allocated_exception` | Rename on restore, or delete the index (CONFIRM first) |
| Alias exists pointing to a different index | Restore silently skips the index | Re-point or delete the alias before restore |
| Open index with same name is being written to | Restore fails to open shard | Close or delete the live index first |
| Index template matches and auto-creates | Restore conflicts with auto-created index | Disable the template during restore, or rename |

## Monitor restore progress

```bash
# All recoveries
curl -sS "https://$ENDPOINT/_cat/recovery?v&h=index,shard,time,stage,percent,bytes_percent"

# Specific index
curl -sS "https://$ENDPOINT/_cat/recovery/<index>?v&active_only=true"
```

Stages: `INIT` → `INDEX` → `VERIFY_INDEX` → `TRANSLOG` → `FINALIZE`.
A shard stuck at `INDEX` for a long time is bottlenecked by network
or disk; stuck at `TRANSLOG` is replaying operations.

## Restore throttle settings

| Setting | Default | Effect |
|---|---|---|
| `cluster.routing.allocation.node_concurrent_recoveries` | 2 | Shard recoveries per node (raise to speed up) |
| `indices.recovery.max_bytes_per_sec` | 40mb (managed) | Per-node recovery bandwidth |
| `indices.recovery.max_concurrent_file_chunks` | 2 | Concurrent file chunks per recovery |

Raising these speeds up restore but increases CPU and network load.
Test during off-peak before applying cluster-wide.

## UltraWarm tier

### Enabling warm

```bash
aws opensearch update-domain-config --domain-name <domain> \
  --cluster-config WarmEnabled=true,WarmCount=3,WarmType=ultrawarm1.medium.search \
  --profile <p>
```

Requirements:

- `WarmCount` minimum 3 (managed OpenSearch enforces this).
- `WarmType` must be an `ultrawarm1.*` instance type.
- Enabling warm triggers a blue/green deployment; the domain
  endpoint does NOT change.

### Migrating an index to warm

```bash
curl -X POST "https://$ENDPOINT/_plugins/_ism/add/<index>" \
  -H 'Content-Type: application/json' -d '{"policy_id": "<warm-policy>"}'
```

Or the one-shot migrate API:

```bash
curl -X POST "https://$ENDPOINT/_plugins/_ultrawarm/migrate/<index>"
```

Migration requirements:

- Index MUST have at least one assigned replica (warm nodes hold
  the primary; the hot node holds the replica during transition).
- Index MUST be green. Yellow or red indices fail migration.
- No snapshot can be running on the index during migration.
- `WarmCount` must be >= 3.

### Migration failure signatures

| Error | Cause |
|---|---|
| `migration_failed: allocation_error` | No warm node has capacity; raise `WarmCount` |
| `migration_failed: primary_not_found` | Primary shard missing; fix cluster health |
| `migration_failed: snapshot_in_progress` | Snapshot running on the index; wait or cancel |
| `migration_failed: no_warm_node` | `WarmEnabled: false` or `WarmCount: 0` |

## Cold storage

Cold storage is a searchable archive tier backed by S3. Cold
indices are queried via the `cold-search` plugin (slower; disk-
backed).

### Requirements

- Warm tier MUST be enabled first.
- Cold node count minimum 1 (managed minimum).
- Migration path: hot → warm → cold (NOT hot → cold directly).

### Migrating to cold

Set the ISM policy action:

```json
{
  "actions": [
    {"warm_migration": {}},
    {"cold_migration": {"start_time": "2026-08-11T03:00:00Z"}}
  ]
}
```

Cold migration requires the index to be on warm first. Attempting
`cold_migration` on a hot-only index fails.

## Snapshot-to-warm/cold interaction

- A snapshot CANNOT be taken while a warm/cold migration is in
  progress on the index. The snapshot returns
  `process_cluster_event_timeout_exception` or stalls at `INIT`.
- A warm migration CANNOT start while a snapshot is in `IN_PROGRESS`
  on the index. The migration returns `migration_failed:
  snapshot_in_progress`.
- Coordinate ISM policies and snapshot schedules to avoid overlap.

## Cluster-state health and snapshot interaction

| Cluster status | Snapshot behaviour | Restore behaviour |
|---|---|---|
| Green | Snapshot succeeds; restore succeeds | Normal |
| Yellow (replicas missing) | Snapshot of primaries succeeds; may be slow | Restore succeeds; new cluster may stay yellow |
| Red (primaries missing) | Snapshot goes `PARTIAL` or `FAILED` | Restore fails or produces a partial index |

Always resolve cluster red BEFORE relying on a snapshot for DR.
