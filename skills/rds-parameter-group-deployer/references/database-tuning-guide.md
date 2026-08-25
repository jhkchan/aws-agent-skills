# Database Tuning Guide — RDS Parameter Group Deployer

Deep reference on PostgreSQL and MySQL parameter tuning, Aurora-specific
parameters, Aurora Serverless v2 capacity interactions, and static-vs-
dynamic parameter classification.

## PostgreSQL memory architecture

PostgreSQL has a multi-process architecture. Each connection is a
separate OS process with its own memory. Key memory areas:

### shared_buffers (static)

The shared memory pool for data pages. All backends share this cache.

- **Default:** `{DBInstanceClassMemory/4}` (25% of instance RAM).
- **Recommended:** 25% of instance RAM for OLTP workloads.
- **Static:** requires DB instance reboot.
- **Formula syntax:** `{DBInstanceClassMemory/4}` or absolute `{6GB}`.

The remaining RAM is used by:
- OS page cache (for sequential scans and WAL)
- Per-connection memory (work_mem, maintenance_work_mem)
- Background processes (autovacuum, wal writer)

### work_mem (dynamic)

Per-query sort/hash memory. Each query can use up to `work_mem` PER
sort/hash node. A complex query with 3 sorts uses 3× work_mem.

- **Default:** `4MB`.
- **Recommended:** 8-16MB for OLTP; 32-64MB for analytics.
- **Formula:** `(available_RAM - shared_buffers) / max_connections / 4`.
  This gives a safe ceiling. Set work_mem below this.
- **Pitfall:** setting work_mem too high with many concurrent connections
  causes OOM. 200 connections × 16MB work_mem × 3 sort nodes = 9.6 GB
  just for sorts.

### maintenance_work_mem (dynamic)

Memory for VACUUM, CREATE INDEX, ALTER TABLE operations.

- **Default:** `64MB`.
- **Recommended:** 256MB-1GB for production. Higher = faster VACUUM
  and index creation.
- **Impact:** low concurrency (only maintenance operations use this).

### effective_cache_size (dynamic)

A PLANNER HINT — does NOT allocate memory. Tells the planner how much
total cache (PostgreSQL shared_buffers + OS page cache) is available.

- **Default:** `4GB`.
- **Recommended:** 50-75% of instance RAM.
- **Impact:** too low = planner favors sequential scans over index
  scans. Too high = planner over-estimates cache hits.

### wal_buffers (dynamic)

Write-Ahead Log buffer. Committed transactions write to WAL before
the data pages.

- **Default:** `-1` (auto-tuned to 1/32 of shared_buffers, min 64KB,
  max 16MB).
- **Recommended:** `16MB` (or leave at `-1`).

## PostgreSQL planner and autovacuum tuning

### random_page_cost (dynamic)

Cost the planner assigns to a random page fetch (index lookup).
Lower values make the planner prefer index scans.

- **Default:** `4.0` (designed for spinning disks).
- **Recommended for SSD/EBS:** `1.1` (SSD random I/O is nearly as fast
  as sequential).
- **Impact:** dramatically changes query plans. Set to 1.1 on all
  modern RDS instances (gp3/io2 storage).

### autovacuum parameters (dynamic)

Autovacuum reclaims dead tuples from UPDATE/DELETE operations.

| Parameter | Default | Recommended (write-heavy) | Notes |
|---|---|---|---|
| `autovacuum` | `1` | `1` | NEVER disable in production |
| `autovacuum_naptime` | `1min` | `30s` | Time between autovacuum runs per table |
| `autovacuum_vacuum_threshold` | `50` | `50` (default is fine) | Min dead tuples before vacuum |
| `autovacuum_vacuum_scale_factor` | `0.2` | `0.05-0.1` | Fraction of table that must be dead |
| `autovacuum_analyze_scale_factor` | `0.1` | `0.05` | Fraction of table for auto-analyze |

**Scale factor tuning:** for large tables (millions of rows),
`0.2` means 20% of rows must be dead before vacuum triggers. Set
`0.05` for write-heavy tables to vacuum more aggressively.

### checkpoint_completion_target (dynamic)

Spreads checkpoint I/O over this fraction of `checkpoint_timeout`.

- **Default:** `0.9` (since PostgreSQL 14).
- **Recommended:** `0.9` — spreads I/O over 90% of the checkpoint
  window, reducing write spikes.

### log_min_duration_statement (dynamic)

Logs queries that exceed this duration (in milliseconds).

- **Default:** `-1` (disabled).
- **Recommended:** `1000` (1 second) for production.
- **Lower values** (`100`, `250`) for staging or debugging.

## MySQL InnoDB tuning

### innodb_buffer_pool_size (dynamic in 8.0+)

The main InnoDB cache for data pages and indexes. The single largest
memory consumer.

- **Default:** `{DBInstanceClassMemory*3/4}` (75% of instance RAM).
- **Recommended:** 75% for dedicated MySQL instances.
- **ApplyType:** dynamic on MySQL 8.0+ (can resize without reboot).
  Static on older versions.
- **Formula:** `{DBInstanceClassMemory*3/4}`.

### innodb_log_file_size (dynamic in 8.0+)

The redo log file size. Larger = fewer checkpoint flushes = better
write performance.

- **Default:** engine-specific.
- **Recommended:** 1-4GB for write-heavy workloads.

### innodb_flush_log_at_trx_commit (dynamic)

Controls ACID durability vs performance.

| Value | Behavior | Risk |
|---|---|---|
| `1` | fsync every transaction commit (full ACID) | No data loss (safe) |
| `2` | fsync once per second | Up to 1 second of data loss on OS crash |
| `0` | fsync once per second, never on commit | Up to 1 second of data loss |

**Production:** use `1` for financial/durable workloads. Use `2`
for read-heavy or eventually-consistent workloads where 1 second of
data loss is acceptable.

### sync_binlog (dynamic)

Controls binary log fsync behavior. Similar trade-off to
`innodb_flush_log_at_trx_commit`.

| Value | Behavior |
|---|---|
| `1` | fsync binlog every transaction (durable) |
| `0` | OS controls fsync (faster, risk of binlog loss on crash) |

### slow_query_log and long_query_time (dynamic)

| Parameter | Default | Recommended | Notes |
|---|---|---|---|
| `slow_query_log` | `0` | `1` | Enable slow query logging |
| `long_query_time` | `10` | `1` | Log queries > 1 second |
| `log_queries_not_using_indexes` | `0` | `1` | Log queries without indexes |

### character_set_server and collation_server (static)

- **Default:** `latin1` / `latin1_swedish_ci`.
- **Recommended:** `utf8mb4` / `utf8mb4_unicode_ci`.
- **Static:** requires reboot. Set BEFORE loading data — changing
  after data is loaded does not convert existing tables.

## Aurora-specific parameters

### Aurora cluster vs instance parameter groups

Aurora uses BOTH parameter group types:

1. **DBClusterParameterGroup** — applies to ALL instances in the
   cluster. Set cluster-level parameters here.
2. **DBParameterGroup** (optional, per instance) — overrides specific
   parameters for individual instances.

Parameters set in the instance group OVERRIDE the cluster group.
Remove the instance-level override to inherit the cluster value.

### Aurora MySQL parameters

| Parameter | What it controls |
|---|---|
| `aurora_enable_repl_bin_log_filter` | Filters binary log events on replicas to reduce replication lag |
| `aurora_enable_hash_join` | Enables hash join for large analytical queries (faster JOINs on big tables) |
| `aurora_enable_parallel_query` | Parallel query processing across Aurora storage nodes |
| `aurora_parallel_query` | Legacy toggle for parallel query |
| `max_connections_scale_threshold` | Connection scaling threshold |

### Aurora PostgreSQL parameters

Aurora PostgreSQL uses most of the same parameters as community
PostgreSQL, with Aurora-specific additions:

| Parameter | What it controls |
|---|---|
| `max_connections` | Derived from instance class: `LEAST({DBInstanceClassMemory/9531392}, 5000)` |
| `rds.force_ssl` | Force SSL connections (default `1` on newer versions) |
| `rds.logical_replication` | Enable logical replication (for DMS, pglogical) |
| `shared_preload_libraries` | Preloaded libraries (pg_stat_statements, auto_explain) |

### Aurora max_connections scaling

In Aurora, `max_connections` scales with the instance class. The
default formula is:

```text
LEAST({DBInstanceClassMemory/9531392}, 5000)
```

This means: `min(RAM_in_bytes / ~9.5MB, 5000)`.

**Rule:** NEVER set max_connections above this formula. Doing so risks
OOM when all connections are active. If you need more connections, use
RDS Proxy or PgBouncer for connection pooling.

## Aurora Serverless v2 capacity and parameter interactions

Aurora Serverless v2 scales capacity in ACUs (0.5-128 ACU per
instance). The CPU, memory, and network capacity scale with ACU.

### Capacity configuration (on the cluster, not parameter group)

```bash
aws rds modify-db-cluster \
  --db-cluster-identifier <cluster-id> \
  --serverless-v2-scaling-configuration MinCapacity=2,MaxCapacity=16
```

- `MinCapacity`: 0.5-128 ACU. The minimum capacity when idle.
- `MaxCapacity`: 0.5-128 ACU. The maximum capacity under load.
- `SecondsUntilAutoPause`: not applicable (Serverless v2 does not
  pause to zero — minimum is 0.5 ACU).

### Parameter tuning for Serverless v2

The key challenge: the instance class CHANGES dynamically with ACU.
Memory available at 2 ACU (~8 GB) is vastly different from 16 ACU
(~64 GB). Parameter values must adapt.

**Rules for Serverless v2 parameters:**

1. **ALWAYS use formula values** for memory parameters:
   - `shared_buffers` = `{DBInstanceClassMemory/4}` (NOT `6GB`)
   - `effective_cache_size` = `{DBInstanceClassMemory*3/4}`
   - `work_mem` = `4MB` (conservative — at 2 ACU, memory is tight)

2. **max_connections:** use the Aurora formula
   `LEAST({DBInstanceClassMemory/9531392}, 5000)`. The formula
   adapts to the dynamic capacity.

3. **Conservative work_mem:** at minimum ACU, high work_mem × many
   connections = OOM. Set `4MB` (not `16MB`).

4. **autovacuum:** keep aggressive settings
   (`autovacuum_naptime=30s`, `autovacuum_vacuum_scale_factor=0.05`).
   At low ACU, autovacuum may lag — aggressive settings help.

5. **Never set absolute values:** `shared_buffers=6GB` will cause OOM
   when the instance scales to 2 ACU (which has ~8GB RAM total, with
   6GB of that going to shared_buffers alone).

## Static vs dynamic parameter reference

### PostgreSQL static parameters (require reboot)

| Parameter | Notes |
|---|---|
| `shared_buffers` | Main shared memory pool |
| `max_worker_processes` | Max background worker processes |
| `max_parallel_workers` | Max parallel query workers |
| `wal_level` | WAL logging level |
| `max_wal_senders` | Max WAL replication senders |
| `max_replication_slots` | Max logical replication slots |
| `hot_standby` | Whether replicas accept queries |
| `shared_preload_libraries` | Preloaded libraries (requires restart) |

### MySQL static parameters (require reboot)

| Parameter | Notes |
|---|---|
| `max_connections` | Max concurrent connections |
| `character_set_server` | Default character set |
| `collation_server` | Default collation |
| `innodb_log_files_in_group` | Number of redo log files |
| `table_open_cache` | Table cache size |
| `thread_cache_size` | Thread cache size |

### Verifying ApplyType

```bash
# Check if a parameter is static or dynamic
aws rds describe-db-parameters --db-parameter-group-name default.postgres15 \
  --query 'Parameters[?ParameterName==`shared_buffers`].{Name:ParameterName,ApplyType:ApplyType}'

# List all static parameters
aws rds describe-db-parameters --db-parameter-group-name default.postgres15 \
  --query 'Parameters[?ApplyType==`static`].ParameterName' --output text

# List all dynamic parameters that have been modified from default
aws rds describe-db-parameters --db-parameter-group-name <name> \
  --query 'Parameters[?ApplyType==`dynamic` && Source!=`engine-default`].{Name:ParameterName,Value:ParameterValue}'
```

## Step 3 — common static and dynamic parameters

**Common static parameters (require reboot):**

| Parameter | Engine | What it controls |
|---|---|---|
| `shared_buffers` | PostgreSQL | Shared memory pool for data pages |
| `max_connections` | PostgreSQL (some versions) | Maximum concurrent connections |
| `log_directory` | PostgreSQL | Log file directory |
| `timezone` | PostgreSQL | Server timezone |
| `innodb_buffer_pool_size` | MySQL (some versions) | InnoDB buffer pool size |
| `max_connections` | MySQL | Maximum concurrent connections |
| `character_set_server` | MySQL | Default character set |

**Common dynamic parameters (no reboot):**

| Parameter | Engine | What it controls |
|---|---|---|
| `work_mem` | PostgreSQL | Per-query sort/hash memory |
| `wal_buffers` | PostgreSQL | WAL write-ahead log buffer |
| `checkpoint_completion_target` | PostgreSQL | Checkpoint spreading |
| `maintenance_work_mem` | PostgreSQL | Maintenance operation memory |
| `random_page_cost` | PostgreSQL | Planner cost for random I/O |
| `slow_query_log` | MySQL | Enable slow query logging |
| `long_query_time` | MySQL | Slow query threshold (seconds) |
| `general_log` | MySQL | Enable general query log |

## Step 5 — Common PostgreSQL tuning parameters

| Parameter | Default | Recommended (production) | Type | Notes |
|---|---|---|---|---|
| `max_connections` | `{AWSTemplate` or engine default | 100-200 (scale with instance class) | static | Each connection consumes memory. Use a connection pooler (PgBouncer/RDS Proxy) for high connection counts. |
| `shared_buffers` | `{DBInstanceClassMemory/4}` | 25% of instance RAM | static | PostgreSQL's main cache. Use curly-brace formula or absolute value (`{6GB}`). |
| `work_mem` | `4MB` | 8-16MB | dynamic | Per-sort/hash memory. Too high with many connections = OOM. Formula: `(RAM - shared_buffers) / max_connections / 2`. |
| `maintenance_work_mem` | `64MB` | 256MB-1GB | dynamic | VACUUM, CREATE INDEX, ALTER TABLE memory. |
| `wal_buffers` | `-1` (auto) | 16MB | dynamic | WAL write buffer. `-1` = auto-tuned to 1/32 of shared_buffers. |
| `checkpoint_completion_target` | `0.9` | `0.9` | dynamic | Spreads checkpoint I/O over 90% of checkpoint_timeout. |
| `effective_cache_size` | `4GB` (default) | 50-75% of instance RAM | dynamic | Planner hint for total OS+PG cache. Does NOT allocate memory. |
| `random_page_cost` | `4` | `1.1` (SSD storage) | dynamic | Cost of random page fetch. Lower for EBS/SSD. |
| `log_min_duration_statement` | `-1` (disabled) | `1000` (log queries > 1s) | dynamic | Slow query logging in milliseconds. |
| `autovacuum` | `1` | `1` | dynamic | Enable autovacuum. Never disable in production. |
| `autovacuum_naptime` | `1min` | `30s` for write-heavy | dynamic | Time between autovacuum runs per table. |

**Memory formula syntax:** RDS supports `{DBInstanceClassMemory/N}` to
set values as a fraction of instance RAM. Use this instead of
absolute values for portability across instance classes.

## Step 6 — Common MySQL tuning parameters

| Parameter | Default | Recommended (production) | Type | Notes |
|---|---|---|---|---|
| `innodb_buffer_pool_size` | `{DBInstanceClassMemory*3/4}` | 75% of instance RAM | dynamic (8.0+) | Main InnoDB cache. Largest consumer of MySQL memory. |
| `max_connections` | `{AWSTemplate}` or 150 | 200-500 (scale with instance class) | static | Each connection consumes thread stack + sort buffer. |
| `slow_query_log` | `0` | `1` | dynamic | Enable slow query logging. |
| `long_query_time` | `10` | `1` (log queries > 1s) | dynamic | Slow query threshold in seconds. |
| `innodb_log_file_size` | engine default | 1-4GB | dynamic (8.0+) | Redo log file size. Larger = fewer checkpoint flushes. |
| `innodb_flush_log_at_trx_commit` | `1` | `1` (durability) or `2` (performance) | dynamic | `1` = ACID (fsync every commit). `2` = fsync once per second (risk of 1s data loss on crash). |
| `sync_binlog` | `1` | `1` (durability) or `0` (performance) | dynamic | `1` = fsync binlog every transaction. |
| `character_set_server` | `latin1` | `utf8mb4` | dynamic | Default character set. |
| `collation_server` | `latin1_swedish_ci` | `utf8mb4_unicode_ci` | dynamic | Default collation. |
| `binlog_format` | `MIXED` (Aurora) / `ROW` | `ROW` | dynamic | Binary log format. `ROW` for replication reliability. |
| `table_definition_cache` | engine default | 2000+ for many tables | dynamic | Table definition (.frm) cache. |

## Step 7 — Aurora-specific parameters

Aurora has cluster-level parameters not available in regular RDS:

| Parameter | Engine | What it controls |
|---|---|---|
| `aurora_enable_repl_bin_log_filter` | Aurora MySQL | Binary log filtering on replicas |
| `aurora_enable_hash_join` | Aurora MySQL | Hash join for large analytical queries |
| `aurora_enable_parallel_query` | Aurora MySQL | Parallel query processing |
| `aurora_pq` | Aurora MySQL (older) | Parallel query toggle |
| `max_connections` | Aurora PostgreSQL | Connection limit (scales with instance class) |

**Aurora max_connections scaling:** in Aurora, `max_connections` is
derived from the instance class by default (using
`LEAST({DBInstanceClassMemory/9531392}, 5000)`). Override only if
you need fewer connections, never more — exceeding the formula can
cause OOM.

## Step 8 — Aurora Serverless v2 capacity

Aurora Serverless v2 manages capacity in ACUs (Aurora Capacity
Units, 0.5-128 ACU per instance). Capacity scaling is configured on
the cluster via `ServerlessV2ScalingConfiguration`, NOT in the
parameter group:

```bash
aws rds modify-db-cluster \
  --db-cluster-identifier <cluster-id> \
  --serverless-v2-scaling-configuration MinCapacity=2,MaxCapacity=16 \
  --apply-immediately
```

**Parameter group tuning for Serverless v2:**

| Parameter | Recommendation | Why |
|---|---|---|
| `max_connections` | Set based on MAX ACU | At scale-up, more connections are needed. Tune for the peak, not the minimum. |
| `shared_buffers` | Use `{DBInstanceClassMemory/4}` formula | The formula adapts to the dynamic instance class. Avoid absolute values. |
| `work_mem` | Conservative (4-8MB) | At minimum ACU, memory is tight. High work_mem × many connections = OOM. |
| `effective_cache_size` | Use `{DBInstanceClassMemory*3/4}` formula | Adapts to dynamic capacity. |

**NEVER set absolute memory values** for Aurora Serverless v2.
The instance class changes dynamically — an absolute `shared_buffers`
value tuned for 16 ACU will cause OOM at 2 ACU. Always use the
`{DBInstanceClassMemory/N}` formula syntax.

