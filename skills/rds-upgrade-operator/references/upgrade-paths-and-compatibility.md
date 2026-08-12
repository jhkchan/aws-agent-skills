# RDS and Aurora Engine Upgrade Paths and Compatibility Reference

Load this reference when planning or executing an RDS or Aurora engine
upgrade. The tables below cover the valid upgrade paths, parameter group
family transitions, option group migrations, and driver compatibility
for each supported engine.

## PostgreSQL upgrade paths

### Valid major version upgrade paths (Aurora PostgreSQL)

| Source version | Target version | Direct upgrade? | Notes |
|---|---|---|---|
| 11.x | 12.x | Yes | Run `ANALYZE` after upgrade; planner statistics rebuilt |
| 12.x | 13.x | Yes | `default_statistics_target` default changed; review param group |
| 13.x | 14.x | Yes | `MERGE` statement added; `pg_hba.conf` defaults tightened |
| 14.x | 15.x | Yes | Row-level security improvements; `MAINTAIN` privilege |
| 11.x | 14.x | No | Must go through 12, then 13, then 14 (sequential) |
| 12.x | 15.x | No | Must go through 13, then 14, then 15 (sequential) |

### Valid minor version upgrade paths

Minor upgrades are always valid within the same major version. For
example, 14.10 to 14.11, 14.9 to 14.11. `AutoMinorVersionUpgrade: true`
schedules the current preferred minor patch in the maintenance window.

### PostgreSQL parameter group families

| Engine version | Parameter group family |
|---|---|
| PostgreSQL 11 | `aurora-postgresql11` |
| PostgreSQL 12 | `aurora-postgresql12` |
| PostgreSQL 13 | `aurora-postgresql13` |
| PostgreSQL 14 | `aurora-postgresql14` |
| PostgreSQL 15 | `aurora-postgresql15` |

A major upgrade REQUIRES a parameter group from the target family. The
source family's group is NOT compatible.

### PostgreSQL parameter changes across versions

| Parameter | PG 13 default | PG 14 default | PG 15 default | Action |
|---|---|---|---|---|
| `default_statistics_target` | 100 | 1000 | 1000 | Review — higher value = longer ANALYZE but better plans |
| `shared_preload_libraries` | (empty) | Stricter validation | Stricter validation | Verify all libraries are loaded in the target param group |
| `password_encryption` | scram-sha-256 | scram-sha-256 | scram-sha-256 | Verify application supports SCRAM (most modern drivers do) |
| `huge_pages` | try | try | try | Verify OS / instance type supports huge pages |

### PostgreSQL driver compatibility

| Driver | Minimum version for PG 14+ | Notes |
|---|---|---|
| PostgreSQL JDBC | 42.2.x | 42.5+ recommended |
| psycopg2 (Python) | 2.9+ | 2.9.9+ recommended |
| pgx (Go) | 4.x | 5.x recommended |
| node-postgres (Node.js) | 8.0+ | |
| npgsql (.NET) | 4.0+ | 6.0+ recommended |

## MySQL / Aurora MySQL upgrade paths

### Valid major version upgrade paths (Aurora MySQL)

| Source version | Target version | Direct upgrade? | Notes |
|---|---|---|---|
| 5.6.x | 5.7.x | Yes | |
| 5.7.x | 8.0.x (Aurora 3.x) | Yes | `caching_sha2_password` default; MEMCACHED removed |
| 5.6.x | 8.0.x | No | Must go through 5.7 first |

### Aurora MySQL version mapping

| Aurora MySQL version | MySQL Community version |
|---|---|
| Aurora MySQL 2.x | MySQL 5.7 |
| Aurora MySQL 3.x | MySQL 8.0 |

### MySQL parameter group families

| Engine version | Parameter group family |
|---|---|
| Aurora MySQL 5.6 | `aurora-mysql5.6` |
| Aurora MySQL 5.7 | `aurora-mysql5.7` |
| Aurora MySQL 8.0 | `aurora-mysql8.0` |

### MySQL 8.0 breaking changes

| Change | Impact | Mitigation |
|---|---|---|
| Default auth plugin: `caching_sha2_password` | Older drivers cannot authenticate | Upgrade driver OR set `default_authentication_plugin = mysql_native_password` in target param group |
| MEMCACHED option removed | Applications using InnoDB Memcached stop working | Remove the option from the target option group; use an external cache |
| `query_cache_size` removed | Queries that relied on query cache may change performance | No action needed (query cache was already deprecated in 5.7) |
| Reserved words added | Queries using new reserved words as identifiers fail | Rename identifiers or use backticks |
| `ORDER BY` without `LIMIT` may return different order | Application logic depending on implicit ordering breaks | Add explicit `ORDER BY` clauses |

### MySQL driver compatibility

| Driver | Minimum version for MySQL 8.0 | Notes |
|---|---|---|
| MySQL Connector/J (Java) | 8.0.x | 5.1.x does NOT support caching_sha2_password |
| MySQL Connector/Python | 8.0.x | |
| mysql2 (Ruby) | 0.5.x | |
| go-sql-driver/mysql (Go) | 1.6+ | |
| mysql2 (Node.js) | 2.3+ | |

## Option group migration

Each engine version has its own option group family. During a major
upgrade, you must attach an option group from the target family.

### Common option group changes (Aurora MySQL 5.7 to 8.0)

| Option in 5.7 | Status in 8.0 | Action |
|---|---|---|
| `MEMCACHED` | Removed | Remove from target option group |
| `MARIADB_AUDIT_PLUGIN` | Replaced by Advanced Auditing | Enable Advanced Auditing separately |
| `SQLNET` (Oracle) | N/A for MySQL | N/A |
| `STATISTICS` | Replaced by Performance Insights | Enable Performance Insights on the cluster |

## Blue/green deployment compatibility

Blue/green deployments support the following upgrade scenarios:

| Source | Target | Supported? |
|---|---|---|
| Aurora MySQL 5.7 | Aurora MySQL 8.0 | Yes |
| Aurora PostgreSQL 13 | Aurora PostgreSQL 14 | Yes |
| Aurora PostgreSQL 14 | Aurora PostgreSQL 15 | Yes |
| RDS MySQL 5.7 | RDS MySQL 8.0 | Yes |
| RDS PostgreSQL 13 | RDS PostgreSQL 14 | Yes |
| Cross-engine (MySQL to PostgreSQL) | No | Use AWS DMS instead |

## Global database upgrade constraints

| Constraint | Detail |
|---|---|
| Engine version must support global databases | Check `SupportsGlobalDatabases` in `describe-db-engine-versions` |
| Primary Region upgraded first | Secondaries are rebuilt from the upgraded primary |
| Secondary Region downtime during rebuild | The secondary cluster is unavailable during the rebuild |
| Sequential rebuild | Secondaries rebuild one at a time, not in parallel |
| Cross-Region replication resumes automatically | After the secondary rebuild completes, replication resumes |

## Aurora Serverless v1 and v2

| Feature | Serverless v1 | Serverless v2 |
|---|---|---|
| In-place major upgrade | Not supported | Supported (MySQL 8.0, PostgreSQL 14+) |
| Upgrade path | Snapshot restore to a v2 cluster | In-place modify |
| Engine versions | MySQL 5.6, 5.7 | MySQL 8.0, PostgreSQL 13+ |

To upgrade Aurora Serverless v1: take a snapshot, restore to a new
Serverless v2 cluster running the target engine version, then cutover
the application endpoint.
