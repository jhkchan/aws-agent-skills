# Source CDC Requirements Reference

Load this reference when diagnosing source-side CDC configuration issues
for DMS replication tasks. Covers the CDC mechanism, required parameters,
and verification queries for each supported source engine.

## MySQL (and MariaDB, Aurora MySQL)

### CDC mechanism

Binary log (binlog). DMS acts as a MySQL replication slave, reading
binlog events for row-level changes.

### Required configuration

| Parameter | Required value | How to check | How to fix |
|---|---|---|---|
| `binlog_format` | `ROW` | `show variables like 'binlog_format';` | RDS parameter group: set `binlog_format=ROW`, reboot |
| `binlog_row_image` | `FULL` | `show variables like 'binlog_row_image';` | RDS parameter group: set `binlog_row_image=FULL`, reboot |
| `binlog_retention_hours` | >= 24 (RDS default 0!) | `show variables like 'binlog_retention_hours';` | RDS parameter group: set `binlog_retention_hours=24`, no reboot |
| `server_id` | > 0 (self-managed MySQL) | `show variables like 'server_id';` | my.cnf: `server-id=1`, restart |
| `log_bin` | ON | `show variables like 'log_bin';` | my.cnf: `log_bin=mysql-bin`, restart |
| `binlog_checksum` | CRC4 (default) | `show variables like 'binlog_checksum';` | Default is fine |

### Required DMS user privileges

```sql
GRANT SELECT, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO '<dms-user>'@'%';
-- For specific database:
GRANT SELECT ON <db>.* TO '<dms-user>'@'%';
```

`REPLICATION SLAVE` allows reading the binlog. `REPLICATION CLIENT`
allows `SHOW MASTER STATUS` / `SHOW BINARY LOGS`.

### Common failure modes

- **`binlog_retention_hours=0` on RDS (default):** Binlogs are purged
  immediately after they're no longer needed by any MySQL replication
  slave. If DMS falls behind or restarts, the binlog is gone. The task
  cannot recover — it must be restarted in full-load-and-cdc mode.
  This is the #1 silent CDC stall on RDS MySQL.

- **`binlog_format=STATEMENT` or `MIXED`:** DMS requires `ROW` for
  deterministic row-level replication. `STATEMENT` mode logs SQL text;
  DMS cannot parse it for CDC.

- **`binlog_row_image=MINIMAL` (MySQL 5.6+):** DMS requires `FULL` to
  get all column values for UPDATE/DELETE events.

- **DMS user missing `REPLICATION SLAVE`:** The user can `SELECT` but
  cannot read the binlog. Task fails with "Access denied" or
  "Binary log is not enabled."

## PostgreSQL (and Aurora PostgreSQL)

### CDC mechanism

Logical replication slot (`pglogical` extension for Aurora/RDS
PostgreSQL, or `test_decoding` for self-managed).

### Required configuration

| Parameter | Required value | How to check | How to fix |
|---|---|---|---|
| `wal_level` | `logical` | `select name, setting from pg_settings where name='wal_level';` | RDS parameter group: set `wal_level=logical`, REBOOT required |
| `max_replication_slots` | >= 1 (per DMS task) | `select name, setting from pg_settings where name='max_replication_slots';` | RDS parameter group, reboot |
| `max_wal_senders` | >= 1 (per concurrent DMS task) | `select name, setting from pg_settings where name='max_wal_senders';` | RDS parameter group, reboot |
| `pglogical` extension | installed | `select * from pg_extension where extname='pglogical';` | `CREATE EXTENSION pglogical;` |
| Replication slot | exists, active | `select * from pg_replication_slots where slot_name like 'awsdms_%';` | DMS creates the slot at task start |

### Required DMS user privileges

```sql
-- The DMS user needs:
ALTER ROLE <dms-user> WITH REPLICATION;
GRANT USAGE ON SCHEMA _replication TO <dms-user>;
GRANT ALL ON ALL TABLES IN SCHEMA _replication TO <dms-user>;
-- For pglogical:
GRANT pglogical TO <dms-user>;
```

For RDS PostgreSQL, the master user has `rds_superuser` / `rds_replication`
role. Create a dedicated DMS user with `rds_replication`.

### Common failure modes

- **`wal_level=replica` (RDS default):** Logical replication requires
  `wal_level=logical`. Changing requires a REBOOT. If the source was
  restored from a snapshot with a different parameter group,
  `wal_level` may revert to `replica`.

- **`pglogical` extension not installed:** The task fails with "could
  not access file $libdir/pglogical" or "function pglogical.create_slot
  does not exist." Run `CREATE EXTENSION pglogical;` on the source.

- **Replication slot dropped:** If the DMS task is deleted, the slot
  may be orphaned or dropped. Restarting the task in CDC-only mode
  fails because there's no slot to resume from. Use full-load-and-cdc
  to create a new slot.

- **`max_replication_slots` too low:** Each DMS CDC task needs one
  slot. If other consumers (other DMS tasks, logical replication
  subscribers) consume all slots, the task cannot create its slot.

## Microsoft SQL Server

### CDC mechanism

MS-Replication (SQL Server 2008+) or MS-CDC (SQL Server 2012+). DMS
reads the transaction log or the CDC capture tables.

### Required configuration

| Setting | Required value | How to check | How to fix |
|---|---|---|---|
| Database enabled for MS-CDC | `is_cdc_enabled=1` | `select name, is_cdc_enabled from sys.databases where name='<db>';` | `use <db>; exec sys.sp_cdc_enable_db;` |
| Database enabled for MS-Replication | `is_published=1` | `select name, is_published from sys.databases where name='<db>';` | SSMS: enable publication, or `sp_replicationdboption` |
| DMS user role | `sysadmin` (MS-Replication) or `db_owner` (MS-CDC) | `select name, type_desc from sys.server_principals where name='<dms-user>';` | `ALTER SERVER ROLE sysadmin ADD MEMBER <dms-user>;` |
| SQL Server Agent | running (MS-CDC capture jobs) | `xp_sqlagent_enum_jobs` or SSMS | Start SQL Server Agent service |

### Common failure modes

- **SQL Server Express:** Does NOT support MS-Replication or MS-CDC.
  DMS cannot do CDC from Express. Upgrade to Web, Standard, or
  Enterprise.

- **SQL Server Agent stopped:** MS-CDC capture jobs run in the Agent.
  If the Agent is stopped, CDC capture stops and DMS sees no new
  changes. CDCLatencySource climbs.

- **DMS user not `sysadmin`:** MS-Replication requires `sysadmin`
  (server-level). MS-CDC requires `db_owner` (database-level). A user
  with just `SELECT` cannot read the transaction log.

## Oracle

### CDC mechanism

Oracle LogMiner (default) or Binary Reader. DMS reads the archived redo
logs or online redo logs via LogMiner.

### Required configuration

| Setting | Required value | How to check | How to fix |
|---|---|---|---|
| `ARCHIVELOG` mode | enabled | `select log_mode from v$database;` | `ALTER DATABASE ARCHIVELOG;` (requires mount state) |
| Supplemental logging | `SUPPLEMENTAL_LOG_DATA_MIN: YES` | `select supplemental_log_data_min from v$database;` | `ALTER DATABASE ADD SUPPLEMENTAL LOG DATA;` |
| DMS user role | `LOGMINING` (12c+) or `EXECUTE on DBMS_LOGMNR` | `select granted_role from dba_role_privs where grantee='<dms-user>';` | `GRANT LOGMINING TO <dms-user>;` or `GRANT EXECUTE ON DBMS_LOGMNR TO <dms-user>;` |
| DMS user privileges | `SELECT ANY TRANSACTION`, `SELECT ANY DICTIONARY` | check `dba_sys_privs` | `GRANT SELECT ANY TRANSACTION, SELECT ANY DICTIONARY TO <dms-user>;` |

### Common failure modes

- **`NOARCHIVELOG` mode:** DMS cannot read changes without archive
  logs. Switch to `ARCHIVELOG` mode (requires downtime).

- **Supplemental logging not enabled:** Without supplemental logging,
  LogMiner does not capture enough column data for UPDATE/DELETE.
  Enable minimal supplemental logging at minimum; for tables with
  composite keys, enable `ALL COLUMNS` supplemental logging.

- **`ORA-01331: LogMiner session does not exist`:** The DMS user lacks
  `EXECUTE on DBMS_LOGMNR` or the `LOGMINING` role. Grant the role.

## Amazon DocumentDB

### CDC mechanism

DocumentDB change streams (not binlog, not logical replication).

### Required configuration

| Parameter | Required value | How to check | How to fix |
|---|---|---|---|
| `change_streams` | `enabled` | Check the cluster parameter group | Cluster parameter group: set `change_streams=enabled`, apply |
| `change_streams_log_retention_duration` | >= 3600 (1 hour) | Check the cluster parameter group | Set to a value sufficient for CDC recovery |

### Common failure modes

- **Change streams disabled:** The DMS task cannot capture changes.
  Enable change streams on the cluster parameter group.

- **Log retention too short:** If the retention is shorter than the
  DMS task's recovery window, changes are lost. Set to at least 24h.
