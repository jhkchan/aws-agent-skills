---
description: Diagnoses Amazon Athena query failures through a thirteen-category diagnostic tree (SerDe mismatch, column type mismatch, stale partitions, partition projection, S3/Glue permissions, CTAS output location, query timeout, format inference, nested types, date parsing) — emits ROOT_CAUSE_IDENTIFIED with the specific failure layer or INSUFFICIENT_DATA.
nl_triggers:
  - "Athena query failed"
  - "Athena column returns NULL"
  - "Athena zero rows"
  - "Athena access denied S3"
  - "Athena SerDe error"
  - "OpenCSVSerDe Athena"
  - "LazySimpleSerDe Athena"
  - "column type mismatch Athena"
  - "partition projection Athena"
  - "MSCK REPAIR Athena"
  - "stale partitions Athena"
  - "CTAS Athena permission denied"
  - "CREATE TABLE AS SELECT Athena"
  - "workgroup output location Athena"
  - "Athena query timeout"
  - "Athena 30 minute limit"
  - "Athena format inference"
  - "nested type ARRAY STRUCT Athena"
  - "date parsing Athena"
  - "troubleshoot Athena query"
routes_to: athena-query-failure-troubleshooter
---

# /aws:troubleshoot-athena-query

Activate the `athena-query-failure-troubleshooter` skill and diagnose
an Amazon Athena query failure through the thirteen-category diagnostic
tree.

## What it does

Reads a symptom description (error message from get-query-execution,
observed behaviour "column returns NULL", "query returns zero rows",
"CTAS failed with access denied") plus the DDL and query context, then
walks the symptom-driven diagnostic tree to a root cause with positive
evidence:

1. **Pre-flight** — query execution state (`get-query-execution`),
   workgroup configuration (`get-work-group`), Glue table definition
   (`glue get-table`), Glue partitions (`glue get-partitions`), S3
   data verification (`s3 ls`, `s3api head-object`). Short-circuits on
   SUCCEEDED status with wrong data (SerDe mismatch), FAILED with
   HIVE_BAD_DATA (format inference), or CANCELLED near 30 minutes
   (timeout).
2. **Symptom entry** — map the error/behaviour to one of: NULL columns
   (SerDe), zero rows (stale partitions), Access Denied (S3/Glue
   permission), CTAS failure (output location), timeout, format
   inference error, nested type error, date parse error, column type
   mismatch, wrong table location.
3. **Layer-specific probes** —
   - SerDe mismatch/property: glue get-table SerDe vs actual S3 file
     format; SerDeProperties (separatorChar, quoteChar) vs actual
     delimiter.
   - Stale partitions / partition projection: glue get-partitions
     count; partition projection TBLPROPERTIES check; MSCK REPAIR
     vs ALTER TABLE SET TBLPROPERTIES.
   - S3 permission: simulate-principal-policy on s3:GetObject,
     s3:ListBucket; bucket policy check.
   - Glue permission: simulate-principal-policy on glue:GetTable,
     glue:GetPartitions; Lake Formation list-permissions.
   - CTAS output location: workgroup EnforceWorkGroupConfiguration +
     OutputLocation; IAM s3:PutObject on result bucket.
   - Query timeout: EngineExecutionTimeInMillis vs 30-min limit; data
     scan volume.
   - Format inference: s3api head-object + sample download; file
     format vs table STORED AS.
   - Nested type: DDL column definition for ARRAY/STRUCT/MAP; accessor
     syntax.
   - Date parse: DDL DATE vs TIMESTAMP vs STRING; Trino date functions.
   - Column type mismatch: DDL type vs actual data values ("N/A" in
     INT column).
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that matches
   the symptom) or INSUFFICIENT_DATA (a probe requires data not
   provided).

Emits a deterministic diagnostic block per target:

```text
TARGET: <database.table / query-execution-id>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <S3_PERMISSION | GLUE_PERMISSION | SERDE_MISMATCH |
        COLUMN_TYPE_MISMATCH | PARTITION_PROJECTION | TABLE_LOCATION |
        STALE_PARTITIONS | CTAS_OUTPUT_LOCATION | WORKGROUP_OUTPUT |
        QUERY_TIMEOUT | FORMAT_INFERENCE | SERDE_PROPERTY |
        NESTED_TYPE_ERROR | DATE_PARSE_ERROR | UNKNOWN>
EVIDENCE:
  - <observed symptom — error message or wrong-data behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with SQL or CLI command>
  2. <verification query after the fix>
```

## When to invoke

Paste a symptom description and ask any of:

- "Athena query returns NULL columns"
- "Athena query returns zero rows"
- "Athena Access Denied s3://"
- "CTAS failed with permission error"
- "Athena SerDe mismatch"
- "OpenCSVSerDe separatorChar"
- "Athena partition projection"
- "Athena MSCK REPAIR"
- "Athena query timeout 30 minutes"
- "Athena HIVE_BAD_DATA"
- "Athena nested ARRAY STRUCT"
- "Athena date parse error"

A bare database.table + "query failed" or "returns NULL" also routes
here via the orchestrator.

## Inputs

- Symptom description: error message, observed behaviour (NULL columns,
  zero rows, wrong data, timeout).
- Query context: database name, table name, query text, QueryExecutionId
  (for live diagnosis), workgroup name.
- DDL: the CREATE TABLE statement (SerDe, SerDeProperties, columns,
  LOCATION, TBLPROPERTIES).
- For live-account diagnosis: the skill uses `get-query-execution`,
  `get-work-group`, `glue get-table`, `glue get-partitions`,
  `s3 ls`, `s3api head-object`, `iam simulate-principal-policy`,
  `lakeformation list-permissions`.

## Outputs

- One diagnostic block per target table/query.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: DROP+CREATE with correct SerDe, ALTER TABLE SET
  TBLPROPERTIES for partition projection, MSCK REPAIR, IAM policy edit,
  Lake Formation grant, workgroup config change, or query rewrite.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for Athena query failures).
- `/aws:optimize-athena-query` for performance tuning on
  slow-but-successful queries (this skill diagnoses failures, not
  performance).
- `/aws:audit-athena-workgroup` for workgroup configuration posture
  audits (result location enforcement, byte cutoff, encryption).
- `/aws:troubleshoot-iam-permission` for deeper diagnosis when the
  query failure is caused by an SCP, permissions boundary, or
  cross-account role chain.
