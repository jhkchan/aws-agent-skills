# Advanced patterns — rds-parameter-group-deployer (load on demand)

Moved verbatim from SKILL.md; load only when needed.

## Reasoning framework — constraints 3-7 (static/dynamic, value types, association, Aurora, Serverless v2)

3. **Static vs dynamic parameters — static requires reboot.**
   Dynamic parameters apply immediately (or at the next connection,
   depending on the parameter). Static parameters require a DB
   instance reboot to take effect. The `ApplyMethod` field controls
   this: `immediate` for dynamic, `pending-reboot` for static.
   Setting `ApplyMethod: immediate` on a static parameter does NOT
   force immediate application — RDS silently treats it as
   `pending-reboot`.

4. **Parameter value types — string, integer, boolean.** RDS
   enforces the parameter's data type at `ModifyDBParameterGroup`
   time. An integer parameter rejects string values. Some
   parameters accept PostgreSQL memory units (`{6GB}`, `{128MB}`)
   with the curly-brace syntax. Check the parameter's
   `DataType` and `AllowedValues` via `DescribeDBParameters`
   before setting.

5. **Association — DB instance or cluster must be modified.**
   Creating a parameter group does NOT apply it to any instance.
   You must call `ModifyDBInstance` (or `ModifyDBCluster` for
   Aurora) with the new parameter group name. For static
   parameters, the instance must be rebooted after the
   modification. Use `ApplyImmediately: true` for fast application,
   or `false` for the next maintenance window.

6. **Aurora-specific — cluster vs instance parameter groups.**
   Aurora clusters require a `DBClusterParameterGroup` for
   cluster-level parameters (e.g., `aurora_enable_repl_bin_log_filter`).
   Individual instances can have a DBParameterGroup for instance-
   level overrides. Some parameters like `max_connections` in
   Aurora scale based on the instance class and are managed
   differently than in regular RDS.

7. **Aurora Serverless v2 — capacity parameters.** Aurora
   Serverless v2 uses `ServerlessV2ScalingConfiguration` (min/max
   ACU) on the cluster, not parameter group values. However, some
   parameters (like `max_connections`) interact with the capacity
   range. The parameter group should be tuned for the maximum
   capacity to avoid connection exhaustion at scale-up.

## Step 1 — family selection tables (PostgreSQL, MySQL, other engines, find-family CLI)

**PostgreSQL families:**

| Engine version | Family | Cluster family (Aurora) |
|---|---|---|
| PostgreSQL 17 | `postgres17` | `aurora-postgresql17` |
| PostgreSQL 16 | `postgres16` | `aurora-postgresql16` |
| PostgreSQL 15 | `postgres15` | `aurora-postgresql15` |
| PostgreSQL 14 | `postgres14` | `aurora-postgresql14` |
| PostgreSQL 13 | `postgres13` | `aurora-postgresql13` |

**MySQL families:**

| Engine version | Family | Cluster family (Aurora) |
|---|---|---|
| MySQL 8.0 | `mysql8.0` | `aurora-mysql8.0` |
| MySQL 5.7 | `mysql5.7` | `aurora-mysql5.7` |

**Other engines:**

| Engine | Family pattern |
|---|---|
| SQL Server | `sqlserver-se-15.00`, `sqlserver-ex-15.00`, `sqlserver-web-15.00` |
| Oracle | `oracle-ee-19`, `oracle-se2-19` |
| MariaDB | `mariadb10.6`, `mariadb10.11` |

**Find the correct family for a DB instance:**

```bash
aws rds describe-db-instances --db-instance-identifier <id> \
  --query 'DBInstances[].{Engine:Engine,EngineVersion:EngineVersion}'
aws rds describe-db-engine-versions --engine postgres \
  --query 'DBEngineVersions[].DBParameterGroupFamily'
```

## Recent AWS features (2024-2026)

- **Aurora Serverless v2 capacity up to 128 ACU (2024-2025):**
  MaxCapacity increased to 128 ACU per instance. Parameter groups
  for Serverless v2 clusters should use formula values
  (`{DBInstanceClassMemory/N}`) to adapt to the dynamic capacity
  range.

- **PostgreSQL 17 support (2024-2025):** new parameter group family
  `postgres17` / `aurora-postgresql17`. Includes new parameters for
  logical replication, JSON improvements, and improved vacuum
  balancing.

- **MySQL 8.4 support (2025):** new family `mysql8.4`. Includes
  expanded `innodb_buffer_pool_size` dynamic tuning and new
  optimization parameters.

- **Dynamic innodb_buffer_pool_size (MySQL 8.0+, 2024):** the
  buffer pool size can now be changed dynamically (no reboot
  required) on MySQL 8.0+. Previously static.

- **RDS Optimized Writes (2024-2025):** transaction commit
  optimization for write-heavy MySQL workloads. Enabled via
  `innodb_flush_log_at_trx_commit=1` with optimized writes on
  the instance configuration.

- **RDS Optimized Reads (2024-2025):** uses local NVMe SSD for
  temporary tables and sort buffers. Configure `work_mem` and
  `temp_buffers` to take advantage of faster temp storage.

- **Parameter group formula expansion (2024):** more parameters
  support the `{DBInstanceClassMemory/N}` formula syntax, enabling
  portable tuning across instance classes.

## Edge-case handling

- **Wrong family discovered after creation.** The family is
  immutable. You must create a new parameter group with the correct
  family, re-apply all parameter values, and associate the new
  group with the DB instance. The old group can be deleted after
  the new one is verified.

- **Static parameter does not take effect.** The parameter requires
  a reboot. Call `RebootDBInstance` or `RebootDBCluster`. Check
  `DescribePendingMaintenanceActions` for pending parameter changes.

- **Parameter value rejected.** Check the parameter's `DataType`
  and `AllowedValues` via `DescribeDBParameters`. Integer parameters
  reject strings. Some PostgreSQL parameters require memory units
  in curly braces (`{6GB}`). MySQL parameters use plain integers
  (bytes) or string enums.

- **Aurora instance vs cluster parameter conflict.** An instance
  DBParameterGroup overrides the DBClusterParameterGroup. If a
  parameter is set in both, the instance value wins. Remove the
  instance-level override to inherit the cluster value.

- **Serverless v2 OOM after scale-down.** Absolute memory values
  (e.g., `shared_buffers = 6GB`) cause OOM when ACU scales below
  the memory needed. Always use formula syntax
  (`{DBInstanceClassMemory/4}`) for memory parameters.

- **Parameter group change causes failover.** On Aurora clusters,
  modifying the DBClusterParameterGroup triggers a rolling
  instance reboot. The writer reboots first, then readers. Plan
  for a brief connection drop during failover.

