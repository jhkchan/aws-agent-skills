# Diagnostic Commands (load on demand) — Athena Query Failure Troubleshooter

Pre-flight command listings and safety checks moved verbatim from SKILL.md. Loaded on demand.

---

## Account-wide pre-flight commands (moved from SKILL.md)

```bash
# 1. Query execution details (state, error, bytes scanned, timing)
aws athena get-query-execution \
  --query-execution-id <id> --output json

# 2. Workgroup configuration (result location, enforcement, limits)
aws athena get-work-group \
  --work-group <name> --output json

# 3. Glue table definition (SerDe, columns, location, properties)
aws glue get-table \
  --database-name <db> --name <table> --output json

# 4. Glue partitions (check for stale / missing partition metadata)
aws glue get-partitions \
  --database-name <db> --table-name <table> --output json | \
  jq '.Partitions | length'

# 5. S3 data bucket verification (does the data exist and what format?)
aws s3 ls s3://<bucket>/<prefix>/ --recursive --summarize \
  --profile <p> | head -20

aws s3api head-object \
  --bucket <bucket> --key <key-of-a-data-file> --output json

# 6. CloudWatch: Athena query metrics (bytes scanned, query count)
aws cloudwatch get-metric-statistics --namespace AWS/Athena \
  --metric-name TotalExecutionTime \
  --dimensions Name=WorkGroup,Value=<wg> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

---

## Pre-flight safety checks (run before any state-changing SQL) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing SQL
  (`DROP TABLE`, `CREATE TABLE`, `ALTER TABLE`, `MSCK REPAIR`,
  `CREATE TABLE AS SELECT`), emit and await operator approval.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`get-query-execution`, `get-work-group`, `glue get-table`,
  `glue get-partitions`, `s3 ls`, `s3api head-object`,
  `iam simulate-principal-policy`). Do not perform state-changing
  operations as diagnostic probes.

- **DROP TABLE** removes the Glue table definition but does NOT delete
  S3 data. It is recoverable (recreate the table with the same DDL).
  However, it invalidates any downstream queries referencing the table.

- **ALTER TABLE SET LOCATION** changes where Athena reads data from.
  Pointing it at the wrong prefix returns wrong or empty results.
  Always verify the S3 path before applying.

- **ALTER TABLE SET TBLPROPERTIES** for partition projection is safe
  and non-destructive. It changes how Athena resolves partitions; it
  does not move data. Verify with a test query after applying.

- **CREATE TABLE AS SELECT** writes data to S3. It consumes storage
  and incurs scan charges. Verify the `external_location` (or
  workgroup result location) has sufficient capacity and the right
  permissions before running.

- **MSCK REPAIR TABLE** lists S3 prefixes and creates Glue partition
  entries. For large tables it can be slow and may time out. Test on
  a small partition range first.

- **IAM policy changes** affect every principal using the role. Tighten
  policies gradually; verify with `simulate-principal-policy` before
  and after.

- **Bulk remediation batch limit.** If the diagnosis identifies the
  same root cause across multiple tables (e.g., a wrong SerDe across
  a set of CSV tables), batch remediation into groups of at most 5
  tables, emit a single CONFIRM per batch, and verify between batches.
