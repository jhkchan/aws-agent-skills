# CDC Prerequisites by Engine — DMS Endpoint Deployer

Deep reference on Change Data Capture (CDC) prerequisites for each
source engine supported by AWS DMS. CDC requires source-database-level
configuration that is OUTSIDE DMS. Without these prerequisites, the
endpoint connects but CDC tasks fail. Loaded on demand by the skill —
kept out of the main SKILL.md body so the provisioning procedure stays
scannable.

## PostgreSQL CDC

### Prerequisites

```sql
-- Check wal_level (MUST be 'logical')
SHOW wal_level;

-- Check max_replication_slots (MUST be >= 1)
SHOW max_replication_slots;

-- Check max_wal_senders (MUST be >= 1)
SHOW max_wal_senders;
```

### Fix if wal_level is not logical

```sql
-- In postgresql.conf (requires restart):
wal_level = logical
max_replication_slots = 5
max_wal_senders = 5

-- Or via ALTER SYSTEM:
ALTER SYSTEM SET wal_level = 'logical';
-- Then restart PostgreSQL
```

### DMS endpoint configuration

```text
Extra connection attributes:
  PluginName=pglogical        -- or test_decoding
  slotName=dms_replication_slot
```

DMS auto-creates the logical replication slot. The DMS user must have
the `REPLICATION` attribute:

```sql
ALTER ROLE dms_user WITH REPLICATION;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dms_user;
```

### Common failures

- **"could not create replication slot"** — wal_level is not logical.
  Fix: set `wal_level=logical` and restart PostgreSQL.
- **"replication slot already exists"** — another DMS task is using
  the same slot name. Use a unique slot name per task.
- **"permission denied for pglogical"** — the DMS user lacks
  replication privileges. Grant `REPLICATION`.

## Oracle CDC

### Prerequisites

```sql
-- Check ARCHIVELOG mode (MUST be ARCHIVELOG)
ARCHIVE LOG LIST;

-- Check supplemental logging (MUST be at least minimal)
SELECT supplemental_log_data_min FROM v$database;

-- Check force logging (optional but recommended)
SELECT force_logging FROM v$database;
```

### Fix if prerequisites missing

```sql
-- Enable ARCHIVELOG mode (requires restart in mount mode):
SHUTDOWN IMMEDIATE;
STARTUP MOUNT;
ALTER DATABASE ARCHIVELOG;
ALTER DATABASE OPEN;

-- Enable supplemental logging:
ALTER DATABASE ADD SUPPLEMENTAL LOG DATA;

-- Enable force logging (optional):
ALTER DATABASE FORCE LOGGING;

-- Enable table-level supplemental logging for all columns:
ALTER TABLE my_schema.my_table ADD SUPPLEMENTAL LOG DATA (ALL) COLUMNS;
```

### DMS user privileges

```sql
-- Grant required privileges to the DMS user:
GRANT SELECT ANY TRANSACTION TO dms_user;
GRANT EXECUTE ON DBMS_LOGMNR TO dms_user;
GRANT SELECT ON DBA_REGISTRY TO dms_user;
-- For Binary Reader, also need:
GRANT SELECT ON V_$ARCHIVED_LOG TO dms_user;
GRANT SELECT ON V_$LOG TO dms_user;
GRANT SELECT ON V_$LOGFILE TO dms_user;
```

### DMS endpoint configuration

```text
Binary Reader (recommended for high-volume CDC):
  useLogminerReader=N
  AdditionalArchivedLogDestId=1
  ExtraArchivedLogDestIds=2    -- if multiple archive destinations

LogMiner (default, lower volume):
  -- No special attributes needed; DMS uses LogMiner by default
```

### Common failures

- **"supplemental logging not enabled"** — UPDATE/DELETE changes are
  missed. Fix: enable supplemental logging.
- **"ARCHIVELOG not enabled"** — CDC cannot capture changes. Fix:
  enable ARCHIVELOG mode.
- **"ORA-01031: insufficient privileges"** — DMS user lacks DBA or
  SELECT ANY TRANSACTION privileges.

## MySQL CDC

### Prerequisites

```sql
-- Check binary logging (MUST be ON)
SHOW VARIABLES LIKE 'log_bin';

-- Check binlog format (MUST be ROW)
SHOW VARIABLES LIKE 'binlog_format';

-- Check binlog row image (MUST be FULL)
SHOW VARIABLES LIKE 'binlog_row_image';
```

### Fix if prerequisites missing

```sql
-- In my.cnf/my.ini (requires restart):
[mysqld]
log_bin = mysql-bin
binlog_format = ROW
binlog_row_image = FULL
server_id = 1
```

### DMS user privileges

```sql
CREATE USER 'dms_user'@'%' IDENTIFIED BY '<password>';
GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'dms_user'@'%';
GRANT SELECT ON *.* TO 'dms_user'@'%';
```

### DMS endpoint configuration

```text
Extra connection attributes:
  eventsPollInterval=5          -- seconds between log reads
  initstmt=SET FOREIGN_KEY_CHECKS=0
```

## SQL Server CDC

### Prerequisites

```sql
-- Check SQL Server Agent is running (required for CDC capture job)
-- Check database CDC is enabled
SELECT name, is_cdc_enabled FROM sys.databases WHERE name = 'mydb';

-- Check table CDC is enabled
SELECT name, is_tracked_by_cdc FROM sys.tables;
```

### Fix if prerequisites missing

```sql
-- Enable database CDC (requires sysadmin role):
USE mydb;
GO
EXEC sys.sp_cdc_enable_db;
GO

-- Enable table CDC:
EXEC sys.sp_cdc_enable_table
  @source_schema = 'dbo',
  @source_name = 'my_table',
  @role_name = NULL;
GO
```

SQL Server Agent MUST be running for the CDC capture job to work.

### DMS user privileges

The DMS user must be in the `db_owner` role (or `sysadmin`).

### Common failures

- **"SQL Server Agent not running"** — CDC capture job never starts.
  Start SQL Server Agent.
- **"CDC not enabled on database"** — Run `sp_cdc_enable_db`.

## MongoDB CDC

### Prerequisites

- MUST be a replica set (standalone is NOT supported for CDC).
- DMS user needs `clusterMonitor` and `readWrite` roles.

```javascript
// Verify replica set
rs.status()
```

### DMS endpoint configuration

```text
Extra connection attributes:
  NestingLevel=ONE             -- or NONE for flat document structure
  ExtractDocId=true            -- include _id in the change event
  DocsToInvestigate=50         -- number of documents to sample for schema
```

### Common failures

- **"standalone instance"** — standalone MongoDB does not support CDC.
  Convert to a replica set.
- **"authentication failed"** — verify the DMS user has the correct
  roles on the database.

## Engine version compatibility

| Source engine | DMS engine version required |
|---|---|
| PostgreSQL 12 | 3.4.6+ |
| PostgreSQL 14 | 3.4.7+ |
| PostgreSQL 16 | 3.5.x |
| Oracle 19c | 3.4.4+ |
| Oracle 21c | 3.5.x |
| MySQL 8.0 | 3.4.6+ |
| SQL Server 2019 | 3.4.6+ |
| MongoDB 5.0 | 3.4.7+ |
| MongoDB 6.0 (change streams) | 3.5.x |

Always check the latest DMS documentation for current compatibility.
## Expert heuristic: source-specific CDC prerequisites (moved from SKILL.md)


A baseline model says "create the endpoint and enable CDC." The correct
heuristic recognizes that CDC prerequisites are OUTSIDE DMS — they are
on the source database itself.

```text
CDC prerequisites by engine:
  PostgreSQL:
    ├── wal_level=logical (check: SHOW wal_level)
    ├── max_replication_slots >= 1 (check: SHOW max_replication_slots)
    ├── Endpoint extra attr: PluginName=pglogical (or test_decoding)
    └── Replication slot auto-created by DMS

  Oracle:
    ├── ARCHIVELOG mode enabled (check: ARCHIVE LOG LIST)
    ├── Supplemental logging: ALTER DATABASE ADD SUPPLEMENTAL LOG DATA
    ├── Force logging (optional): ALTER DATABASE FORCE LOGGING
    └── DMS user privileges: SELECT ANY TRANSACTION, EXECUTE on DBMS_LOGMNR

  MySQL:
    ├── Binary logging enabled (log_bin=ON)
    ├── binlog_format=ROW
    ├── binlog_row_image=FULL
    └── DMS user: REPLICATION SLAVE, REPLICATION CLIENT, SELECT

  SQL Server:
    ├── SQL Server Agent running
    ├── CDC enabled on database (sys.sp_cdc_enable_db)
    ├── CDC enabled on tables (sys.sp_cdc_enable_table)
    └── DMS user in db_owner role (or sysadmin)

  MongoDB:
    ├── Replica set (standalone NOT supported for CDC)
    └── DMS user with clusterMonitor and readWrite roles
```

**Key implication:** the #1 cause of DMS CDC failures is missing
source-database prerequisites. The endpoint connection test passes
(basic connectivity works), but CDC tasks fail with errors like
"could not create replication slot" (PostgreSQL) or "supplemental
logging not enabled" (Oracle). Always verify source prerequisites
BEFORE creating the endpoint.

