# CloudTrail Lake PartiQL Syntax & Query Optimization Reference

Load this reference when planning or running a CloudTrail Lake
PartiQL query. Covers the supported SQL subset, the Lake event
schema, partitioning mechanics, and the optimization patterns that
actually move the needle on `BytesScanned` and `QueryRunTimeInSeconds`.

## Supported PartiQL subset

CloudTrail Lake accepts a PartiQL dialect. The supported operations
are:

| Operation | Supported | Notes |
|---|---|---|
| `SELECT` | YES | The only DML. No INSERT/UPDATE/DELETE. |
| `WHERE` | YES | Filter; MUST include `eventTime` for partition pruning. |
| `GROUP BY` | YES | Aggregation grouping. |
| `ORDER BY` | YES | Sort; works on aggregated or non-aggregated columns. |
| `LIMIT` | YES | Row cap. Use for smoke tests. |
| `JOIN` | YES | Same-Region EDS only. Cross-Region JOIN requires Athena federation. |
| `WITH` (CTE) | YES | Common table expressions for multi-step queries. |
| Aggregates: `COUNT`, `SUM`, `AVG`, `MIN`, `MAX` | YES | Standard semantics. |
| Window functions | PARTIAL | `ROW_NUMBER()`, `RANK()` supported. |
| `CAST` | YES | Type conversion. |
| `LIKE`, `IN`, `BETWEEN` | YES | Standard predicates. |
| Subqueries | YES | In WHERE and FROM. |

## CloudTrail Lake event schema (most-used columns)

| Column | Type | Notes |
|---|---|---|
| `eventTime` | TIMESTAMP | Partition key. ALWAYS filter on this. |
| `eventVersion` | STRING | CloudTrail event version. |
| `userIdentity` | STRUCT | Nested; access via `userIdentity.accountId`, `userIdentity.type`, `userIdentity.arn`, `userIdentity.principalId`, etc. |
| `eventSource` | STRING | The AWS service that emitted (e.g., `s3.amazonaws.com`, `iam.amazonaws.com`). |
| `eventName` | STRING | The API name (e.g., `GetObject`, `AssumeRole`). |
| `awsRegion` | STRING | Region of the event. NOT `region`. |
| `sourceIpAddress` | STRING | Caller IP. |
| `userAgent` | STRING | Caller UA string. |
| `requestParameters` | STRUCT | API input. Highly variable shape. |
| `responseElements` | STRUCT | API output (when applicable). |
| `errorCode` | STRING | For failed events (e.g., `AccessDenied`, `ThrottlingException`). |
| `errorMessage` | STRING | Detailed error text. |
| `resources` | ARRAY<STRUCT> | Resources affected; each has `ARN` and `type`. |
| `recipientAccountId` | STRING | The account the event occurred in (for cross-account AssumeRole). |
| `serviceEventDetails` | STRUCT | Service-generated event payload. |
| `tlsDetails` | STRUCT | TLS version, cipher suite (when applicable). |
| `eventCategory` | STRING | `Management`, `Data`, `ConfigConfiguration`, `AuditManagerEvidence`, `NetworkActivity`, `Insights`. |
| `readOnly` | BOOLEAN | True for read APIs. |
| `managementEvent` | BOOLEAN | True for management events. |
| `eventCycleCounter` | INTEGER | Internal counter. |

For non-AWS events, additional fields:

| Column | Type | Notes |
|---|---|---|
| `userIdentity.sessionContext` | STRUCT | Partner session info. |
| `additionalEventData` | STRUCT | Partner-specific payload. |

## Partitioning mechanics

Lake auto-partitions each EDS on `eventTime` at hourly granularity
as of 2026. A query's `WHERE eventTime BETWEEN ts1 AND ts2` clause
is what enables partition pruning.

```
EDS (100 GB over 90 days)
├── Partition 2026-08-01T00 (1.2 GB)
├── Partition 2026-08-01T01 (0.9 GB)
├── ...
├── Partition 2026-08-10T22 (1.4 GB)
└── Partition 2026-08-10T23 (1.1 GB)

Query: WHERE eventTime BETWEEN '2026-08-10T00:00:00Z'
                    AND '2026-08-10T23:59:59Z'
  → planner prunes to ~24 partitions of ~1.2 GB each
  → BytesScanned ~28 GB (vs 100 GB unfiltered)
```

As of 2025, multi-column partitioning adds `eventSource` as a
secondary partition key, so a query filtering on both `eventTime`
AND `eventSource = 's3.amazonaws.com'` scans only the S3-event
slices within the time window.

## Optimization patterns that actually work

### 1. Always include `eventTime` (the only must-have)

```sql
-- GOOD: partition pruning active
SELECT eventName, COUNT(*) AS cnt
FROM <eds-id>
WHERE eventTime BETWEEN '2026-08-03' AND '2026-08-10'
GROUP BY eventName
ORDER BY cnt DESC

-- BAD: full-table scan, expensive, slow
SELECT eventName, COUNT(*) AS cnt
FROM <eds-id>
GROUP BY eventName
```

### 2. Project only the columns you need

Lake is columnar. `SELECT *` scans every column; selecting 3
columns out of 30 cuts bytes scanned by ~10x.

```sql
-- GOOD
SELECT eventTime, userIdentity.accountId, eventName
FROM <eds-id>
WHERE eventTime >= date_add('day', -7, now())

-- BAD
SELECT *
FROM <eds-id>
WHERE eventTime >= date_add('day', -7, now())
```

### 3. Add `eventSource` for service-specific queries

```sql
-- GOOD: multi-column partition pruning active
SELECT userIdentity.accountId, eventName, COUNT(*) AS cnt
FROM <eds-id>
WHERE eventTime >= date_add('day', -7, now())
  AND eventSource = 's3.amazonaws.com'
GROUP BY userIdentity.accountId, eventName
```

### 4. Use `LIMIT` for smoke tests

Before scaling up to a 90-day window, run with a 1-hour window and
LIMIT 10 to confirm columns and semantics.

### 5. Use a CTE for multi-step analysis

```sql
WITH login_events AS (
  SELECT eventTime, userIdentity.accountId, sourceIpAddress
  FROM <eds-id>
  WHERE eventTime >= date_add('day', -7, now())
    AND eventName = 'ConsoleLogin'
)
SELECT userIdentity.accountId, COUNT(*) AS login_count
FROM login_events
GROUP BY userIdentity.accountId
HAVING COUNT(*) > 50
ORDER BY login_count DESC
```

### 6. JOIN across same-Region EDS

```sql
SELECT a.eventTime, a.userIdentity.accountId, a.eventName,
       b.resourceArn
FROM <eds-mgmt-id> a, <eds-data-id> b
WHERE a.eventTime BETWEEN '2026-08-10T00:00:00Z' AND '2026-08-10T23:59:59Z'
  AND b.eventTime BETWEEN '2026-08-10T00:00:00Z' AND '2026-08-10T23:59:59Z'
  AND a.userIdentity.sessionId = b.userIdentity.sessionId
LIMIT 1000
```

Both EDS MUST be in the same Region as the query API call.

### 7. Use `recipientAccountId` for cross-account AssumeRole analysis

```sql
SELECT eventTime, userIdentity.accountId AS sourceAccount,
       recipientAccountId AS targetAccount, eventName
FROM <eds-id>
WHERE eventTime >= date_add('day', -1, now())
  AND eventName = 'AssumeRole'
  AND userIdentity.accountId != recipientAccountId
```

## Common query shapes (cheat sheet)

### Top callers by event count

```sql
SELECT userIdentity.arn, COUNT(*) AS cnt
FROM <eds-id>
WHERE eventTime >= date_add('day', -7, now())
GROUP BY userIdentity.arn
ORDER BY cnt DESC
LIMIT 20
```

### Failed API calls by service

```sql
SELECT eventSource, eventName, COUNT(*) AS cnt
FROM <eds-id>
WHERE eventTime >= date_add('day', -1, now())
  AND errorCode IS NOT NULL
GROUP BY eventSource, eventName
ORDER BY cnt DESC
```

### Cross-account AssumeRole heatmap

```sql
SELECT userIdentity.accountId AS src,
       recipientAccountId AS dst,
       COUNT(*) AS cnt
FROM <eds-id>
WHERE eventTime >= date_add('day', -7, now())
  AND eventName = 'AssumeRole'
GROUP BY userIdentity.accountId, recipientAccountId
ORDER BY cnt DESC
```

### S3 data-event outlier detection

```sql
SELECT userIdentity.accountId, requestParameters.bucketName,
       COUNT(*) AS get_cnt
FROM <eds-id>
WHERE eventTime >= date_add('hour', -1, now())
  AND eventSource = 's3.amazonaws.com'
  AND eventName = 'GetObject'
GROUP BY userIdentity.accountId, requestParameters.bucketName
HAVING COUNT(*) > 10000
ORDER BY get_cnt DESC
```

### Anomalous ConsoleLogin by source IP

```sql
SELECT sourceIpAddress, userIdentity.accountId,
       COUNT(*) AS attempts
FROM <eds-id>
WHERE eventTime >= date_add('day', -1, now())
  AND eventName = 'ConsoleLogin'
  AND responseElements = 'Failure'
GROUP BY sourceIpAddress, userIdentity.accountId
HAVING COUNT(*) > 10
ORDER BY attempts DESC
```

## Anti-patterns (also in SKILL.md)

- `SELECT *` — projects all 30+ columns including the heavy
  `requestParameters` and `responseElements` STRUCTs. Always project
  only what you need.
- Missing `eventTime` filter — full-table scan.
- Filtering on `region` (wrong column name) — silently produces zero
  rows. The Lake column is `awsRegion`.
- Cross-Region JOIN — runtime error. Use Athena federation.
- DML other than SELECT — Lake is read-only via PartiQL.

## AWS documentation pointers

- CloudTrail Lake SQL queries — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/query-language.html
- Lake event schema — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference.html
- Lake query examples — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/lake-query-examples.html
- Lake query optimization — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/lake-query-best-practices.html
