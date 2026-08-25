# Error Handling — Redshift Query Troubleshooter

Per-step error and pattern tables and the per-layer remediation guidance moved verbatim from SKILL.md. Loaded on demand.

## Step 2 — WLM_QUEUE_TIMEOUT fixes

- Add query slots to the queue (`wlm_json_configuration`).
- Route long-running queries to a separate queue with higher timeout.
- Reduce the number of concurrent queries in the overloaded queue.

## Step 3 — common lock patterns

Common lock patterns:

| Pattern | Cause |
|---|---|
| Long-running SELECT blocking a COPY or INSERT | The SELECT holds a shared lock; the write needs an exclusive lock. |
| COPY blocking all queries on the table | COPY acquires an exclusive lock during load. Concurrent queries wait. |
| Two transactions deadlocking | Each holds a lock the other needs. Redshift detects and rolls back one. |
| VACUUM FULL blocking writes | VACUUM FULL requires exclusive access. Schedule during low-write windows. |

## Step 3 — TABLE_LOCK fixes

- Identify and optionally terminate the blocking PID
  (`pg_terminate_backend(<pid>)`).
- For COPY lock contention: batch COPYs outside peak query hours.
- For VACUUM: schedule during low-write windows or use VACUUM DELETE
  (only reclaims deleted rows, lighter lock).

## Step 4b — S3ServiceException diagnosis

If the error is `S3ServiceException: Access Denied`, the cluster's IAM
role does not have `s3:GetObject` on the target bucket/prefix.

## Step 4c — common COPY format errors

Common COPY format errors:

| Error | Cause |
|---|---|
| `Delimiter not found` | Wrong DELIMITER (e.g., data is pipe-separated but COPY uses comma). |
| `Invalid digit, Value '.', Base 10` | Data has non-numeric values in a numeric column. Check `raw_field_value`. |
| `Character not in repertoire` | Encoding mismatch between the file and the COPY command. Add `ENCODING AS UTF8`. |
| `Extra column(s) found` | More columns in the data than the table. Add `FILLRECORD` / `FILLMISSING` or fix the data. |
| `Missing column(s)` | Fewer columns than the table. Check the file format. |

## Step 4d — manifest mismatch behaviour

If a mandatory file in the manifest does not exist, COPY fails. If
`mandatory: false` and the file is missing, COPY skips it silently
(the most common data-loss-via-COPY issue).

## Step 7 — nested loop causes

Common causes:

| Cause | Example |
|---|---|
| Missing join condition | `SELECT * FROM a, b WHERE a.x > 1` (no join between a and b) |
| Data type mismatch on join column | `a.id (int)` joined to `b.id (varchar)` -- no hash join possible |
| Join on a UDF output | `ON my_udf(a.x) = b.y` -- UDF output can't be hashed |
| Cross join intended but on large tables | `CROSS JOIN` on large tables; add a filter or redesign |

## Step 8 — connection patterns and fixes

Common patterns:

| Pattern | Fix |
|---|---|
| Many short-lived connections from an app | Use a connection pooler (pgbouncer, RDS Proxy). |
| Long-running analytical sessions holding connections | Reduce idle session timeout; close connections after queries complete. |
| ETL tool opening many parallel connections | Limit parallelism in the ETL tool's config. |

## Step 9 — common SSL issues

Common SSL issues:

| Issue | Fix |
|---|---|
| `require_ssl = true` but client does not use SSL | Enable SSL in the client connection string (`sslmode=require`). |
| Self-signed cert on non-prod cluster | Use `sslmode=verify-ca` (not `verify-full`) or add the cert to the trust store. |
| JDBC driver SSL handshake failure | Add `ssl=true&sslmode=require` to the JDBC URL. |
| Certificate expired after cluster cert rotation | Download the new cert from the AWS console and update the trust store. |

## Step 10 — common VACUUM issues

Common VACUUM issues:

| Issue | Fix |
|---|---|
| Concurrent writes holding locks | Schedule VACUUM during low-write windows. |
| Very large unsorted region | Run `VACUUM SORT ONLY` or increase maintenance window. |
| Table has many deleted rows | Run `VACUUM DELETE ONLY` (faster than full VACUUM). |
| `max_formatted_blocks` exceeded | The table's sorted region is too large for a single sort pass. Consider deep copy. |

## Step 11 — encoding diagnosis and fixes

If the server encoding is UTF8 but the data contains characters not
representable in the client encoding (or vice versa), COPY and query
results fail with encoding errors.

Common fixes:

| Issue | Fix |
|---|---|
| COPY from a Latin-1 file into a UTF8 table | Add `ENCODING AS LATIN1` or convert the file to UTF8. |
| Client receiving UTF8 data but expecting Latin-1 | `SET client_encoding TO 'UTF8';` in the session. |
| Mixed-encoding data in one file | Clean the data; Redshift requires consistent encoding per COPY. |

## Remediation guidance per layer

### For WLM_QUEUE_TIMEOUT

- Add query slots to the overloaded queue (increase
  `num_query_tasks` in the WLM config).
- Route long-running queries to a dedicated queue with more slots.
- Reduce concurrent query volume (throttle ETL or reporting jobs).
- Consider Automatic WLM (lets Redshift manage slot allocation
  dynamically).

### For TABLE_LOCK

- Identify and optionally terminate the blocking PID.
- Schedule COPY operations outside peak query hours.
- Use staging tables + swap (ALTER TABLE RENAME) to minimize lock
  duration for data loads.

### For COPY_IAM_ROLE

```sql
-- Add s3:GetObject to the cluster's IAM role policy
-- Via CLI: aws iam put-role-policy --role-name <role> ...
COPY <table> FROM 's3://...'
  IAM_ROLE 'arn:aws:iam::<account>:role/<role-name>'
  ...
```

### For COPY_DATA_FORMAT

- Fix the DELIMITER, FORMAT, or ENCODING based on STL_LOAD_ERRORS.
- Use `FILLRECORD` / `FILLMISSING` for ragged data files.
- Use `ACCEPTINVCHARS` to replace invalid characters with `?`.
- Validate the data file encoding before COPY.

### For DIST_KEY_SKEW

```sql
-- Change distribution to KEY on the join column
ALTER TABLE <fact_table> ALTER DISTSTYLE KEY DISTKEY (<join_column>);

-- For small dimension tables, use ALL
ALTER TABLE <dim_table> ALTER DISTSTYLE ALL;

-- After changing, update statistics
ANALYZE <table>;
```

### For SORT_KEY_MISALIGNMENT

```sql
-- Add or change sort key
ALTER TABLE <table> ALTER SORTKEY (<filter_column>);

-- For multiple independent filter columns
ALTER TABLE <table> ALTER SORTKEY INTERLEAVED (<col1>, <col2>);

-- After changing, VACUUM to sort the data
VACUUM SORT ONLY <table>;
ANALYZE <table>;
```

### For NESTED_LOOP_JOIN

- Add the missing join condition.
- Fix data type mismatches on join columns (CAST or ALTER COLUMN
  TYPE).
- Avoid joining on UDF outputs.
- Use explicit JOIN syntax (not comma-separated FROM).

### For CONNECTION_LIMIT

- Implement connection pooling (pgbouncer, application-level pool).
- Reduce idle connection lifetime.
- Scale the cluster to a node type with more connection capacity.

### For SSL_TLS_ERROR

- Set `sslmode=require` (or `verify-ca`) in the client connection
  string.
- Ensure `require_ssl` in the parameter group matches the client
  capability.
- Download the latest Redshift CA certificate from AWS.

### For VACUUM_BLOCKED

- Schedule VACUUM during low-write windows.
- Use `VACUUM DELETE ONLY` for reclaiming deleted rows.
- Use `VACUUM SORT ONLY` for re-sorting unsorted rows.
- Consider a deep copy for severely fragmented tables.

### For ENCODING_CONVERSION

- `SET client_encoding TO 'UTF8';` for the session.
- Add `ENCODING AS UTF8` or `ENCODING AS LATIN1` to the COPY command.
- Clean mixed-encoding data before loading.
