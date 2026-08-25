# Advanced Patterns — Redshift Data API Deployer

Misconception deep dives, result-persistence patterns, batch transactionality, audit detail, cost model and quotas, and recent features moved verbatim from SKILL.md. Loaded on demand.

## Mindset — the three dominant misconceptions

Three misconceptions dominate Redshift Data API misdesign at deployment
time:

- **"The Data API is a replacement for a connection pool."** It is not
  a pool — it is a connection-FREE query submission model. You do NOT
  maintain connections. Each ExecuteStatement is an independent HTTP
  API call that runs asynchronously. You never manage connection
  lifecycle, timeouts, or pooling. The trade-off: you poll for results
  (DescribeStatement) instead of receiving them synchronously over a
  connection. For sub-second interactive queries, the overhead of
  polling may be unacceptable. For batch, scheduled, and serverless
  workloads, the Data API eliminates all connection management.

- **"Results are available indefinitely."** They are NOT. Query results
  from GetStatementResult are available for 24 hours AFTER the
  statement completes (FINISHED). After 24 hours, the results are
  permanently deleted. If you need results longer than 24 hours, you
  MUST persist them (write to S3, DynamoDB, or another store) before
  expiry. A common failure is a workflow that runs a query, waits more
  than 24 hours, then tries to retrieve results — the call fails with
  "Statement result expired."

- **"Secrets Manager is the only authentication option."** It is not.
  The Data API supports two authentication methods: (1) Secrets Manager
  (store database credentials as a secret, reference by ARN — no
  password in code), and (2) temporary credentials (GetClusterCredentials
  generates short-lived IAM-based credentials). Secrets Manager is
  recommended for production because it centralizes credential rotation.
  Temporary credentials are useful for IAM-federated access without
  a secret store.

## Expert heuristic: result persistence before 24-hour expiry

Results expire 24 hours after FINISHED. If your downstream processing
may be delayed, persist results immediately.

```text
Unsafe pattern:
  1. Submit query (ExecuteStatement)
  2. Query finishes (FINISHED)
  3. ... 25 hours pass ...
  4. Call GetStatementResult → FAILS ("result expired")

Safe pattern:
  1. Submit query (ExecuteStatement)
  2. Query finishes (FINISHED)
  3. Immediately call GetStatementResult
  4. Write results to S3/DynamoDB
  5. Downstream reads from S3/DynamoDB (no expiry)

Safe pattern with UNLOAD:
  1. Submit UNLOAD query: UNLOAD ('SELECT ...') TO 's3://bucket/path/'
  2. Data lands directly in S3 (bypasses GetStatementResult entirely)
  3. No 24-hour expiry concern
```

**Key implication:** for large result sets, use UNLOAD to write directly
to S3 instead of GetStatementResult. This avoids the 24-hour expiry and
the 100 MB GetStatementResult payload limit.

## Step 1 — traditional vs Data API model

```text
Traditional JDBC/ODBC:
  1. Open connection (TCP handshake, auth, session setup)
  2. Execute query (synchronous, blocks until results)
  3. Read results (stream over the connection)
  4. Close connection

Data API (HTTP-based, async):
  1. ExecuteStatement (HTTP POST → returns StatementId immediately)
  2. Poll DescribeStatement (HTTP GET → returns status)
  3. GetStatementResult (HTTP GET → returns rows when FINISHED)
  → No connection to close. No session to manage.
```

## Step 4 — batch transactionality (BEGIN/COMMIT wrap)

**Common mistake:** assuming BatchExecuteStatement is transactional.
It is NOT. For transactional batches, wrap in BEGIN/COMMIT:

```sql
BEGIN;
CREATE TEMP TABLE temp_sales AS SELECT * FROM sales;
SELECT COUNT(*) FROM temp_sales;
COMMIT;
```

## Step 10 — ListStatements and CloudTrail audit detail

**ListStatements** lists recent statements (for governance):

```bash
aws redshift-data list-statements \
  --status ALL \
  --max-results 50 \
  --output table
```

Filters: by status (SUBMITTED, STARTED, FINISHED, FAILED, ABORTED),
by statement name, by role-level.

**CloudTrail** logs all Data API calls for audit:

```text
CloudTrail events for Redshift Data API:
  ExecuteStatement    → logged with SQL text, cluster, database, auth
  BatchExecuteStatement → logged with SQL list
  DescribeStatement   → logged (status check)
  GetStatementResult  → logged (data retrieval)
  AbortStatement      → logged (cancel)
  ListStatements      → logged (governance query)
```

**Key implication:** all SQL text is visible in CloudTrail. This is
valuable for audit but means sensitive SQL should not contain hardcoded
secrets (use parameterized queries instead).

## Step 11 — cost model and quotas

**Cost:** the Data API is FREE. There is NO additional charge beyond
standard Redshift pricing. You pay for:
- Redshift cluster compute (already running) — or Redshift Serverless
  RPU-hours
- Standard API request costs (free tier covers most use cases)
- Secrets Manager storage (if using SecretArn: $0.40/secret/month)

**Quotas:**

| Quota | Value | Adjustable |
|---|---|---|
| Statement timeout | 24 hours | No |
| Result availability after FINISHED | 24 hours | No |
| GetStatementResult max payload per call | 100 MB | No |
| Concurrent statements per cluster | 50 | Yes (Service Quotas) |
| BatchExecuteStatement max SQLs per batch | 1 (single SQL per call for Serverless; multiple for provisioned) | No |
| DescribeStatement rate | 1 per second per statement | No |

## Step 12 — recent features (2023-2026)

**Recent AWS features (2023-2026):**

- **Redshift Serverless Data API (2023-2024):** Full Data API support
  for Redshift Serverless workgroups. Use `WorkgroupName` instead of
  `ClusterIdentifier`.

- **Parameterized queries (2023-2024):** The `Parameters` field on
  ExecuteStatement enables parameterized SQL (prevents SQL injection).
  Parameters are passed as name-value pairs.

- **ListStatements filtering (2023-2024):** Enhanced filtering on
  ListStatements by status, statement name, and role-level. Useful for
  governance dashboards.

- **EventBridge status change events (2023-2024):** The `WithEvent`
  parameter on ExecuteStatement emits an EventBridge event when the
  statement status changes. Enables async Lambda patterns without
  polling.

- **UNLOAD via Data API (2024-2025):** UNLOAD queries can be submitted
  via the Data API, enabling serverless data export to S3 without a
  persistent connection.

- **Improved CloudTrail logging (2024-2025):** CloudTrail now includes
  the full SQL text and parameter values for all Data API calls,
  enhancing audit capabilities.
