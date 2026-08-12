---
name: redshift-data-api-deployer
description: >-
  Deploys AWS Redshift Data API configurations with production defaults:
  query execution without persistent connection (ExecuteStatement,
  BatchExecuteStatement, DescribeStatement, GetStatementResult),
  database authentication via Secrets Manager (no password in code),
  temporary credentials (GetClusterCredentials), statement lifecycle
  (SUBMITTED/STARTED/FINISHED/FAILED/ABORTED), result pagination
  (NextToken), abort statement (AbortStatement), ListStatements,
  integration with Lambda (poll DescribeStatement or EventBridge
  notification), cancel via StatementId, 24-hour timeout, 24-hour
  result expiry after completion, CloudTrail audit logging, and zero
  additional cost (free — standard Redshift charges apply). Emits a
  READY_TO_DEPLOY checklist with verification commands. Use when
  running Redshift queries without a persistent connection, executing
  SQL from Lambda, batch-executing statements, or replacing JDBC/ODBC
  drivers with API calls. Triggers: redshift data api, execute
  statement, batch execute statement, describe statement, get statement
  result, redshift lambda query, redshift secrets manager, redshift
  temporary credentials, abort statement, redshift query without
  connection.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with redshift-data
  access. Works with Terraform aws_redshiftdata_statement resources,
  CloudFormation AWS::Redshift::Data, and boto3
  redshift-data client.
keywords:
  - aws
  - redshift
  - data api
  - execute statement
  - batch execute
  - describe statement
  - get statement result
  - secrets manager
  - temporary credentials
  - cloudops
  - deploy
  - serverless query
  - statement lifecycle
  - cloudtrail
tags:
  - aws
  - redshift
  - data-api
  - cloudops
  - deploy
  - analytics
  - serverless-query
  - secrets-manager
  - cloudtrail
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - redshift
    - data-api
    - cloudops
    - deploy
    - analytics
    - serverless-query
    - secrets-manager
    - cloudtrail
  dependencies:
    - aws-orchestrator
  keywords:
    - redshift data api
    - execute statement
    - batch execute statement
    - describe statement
    - get statement result
    - redshift lambda query
    - redshift secrets manager authentication
    - redshift temporary credentials
    - abort statement
    - redshift query without connection
  when_to_use: >-
    Invoke when the user wants to run Redshift queries via the Data API
    (no persistent connection), execute SQL from Lambda, batch-execute
    statements, authenticate via Secrets Manager or temporary credentials,
    poll statement lifecycle, paginate results, abort long-running queries,
    or replace JDBC/ODBC connection management with API calls. Do NOT
    invoke for Redshift cluster provisioning (use redshift-cluster-
    deployer), Redshift Serverless (use redshift-serverless-deployer),
    or query troubleshooting (use redshift-query-troubleshooter).
---

# Redshift Data API Deployer

An AWS CloudOps agent skill that deploys Redshift Data API query
configurations with correct defaults. The skill walks the connection-
free query model, Secrets Manager vs temporary credential
authentication, statement lifecycle (SUBMITTED through FINISHED/FAILED),
result pagination and 24-hour expiry, Lambda integration patterns (poll
vs EventBridge), abort/cancel by StatementId, CloudTrail audit, and
the zero-cost pricing model, captures the query topology, explains why
each default matters, and emits a READY_TO_DEPLOY checklist with
copy-pasteable verification commands.

## Activation keywords

Redshift Data API, ExecuteStatement, BatchExecuteStatement,
DescribeStatement, GetStatementResult, Redshift Lambda query, Redshift
Secrets Manager authentication, Redshift temporary credentials, abort
statement, Redshift query without connection, statement lifecycle.

## STRICT output contract

When this skill is invoked with a Redshift-Data-API deployment request
(run queries without a persistent connection, execute SQL from Lambda,
batch-execute statements, or authenticate via Secrets Manager), the
agent MUST respond with the READY_TO_DEPLOY checklist defined in the
"Output format" section using the literal all-caps labels
`DATA_API:`, `VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`.
Do NOT preface the checklist with prose, headings, or disclaimers —
emit the block as the first lines of the response. This contract is
what assertion-based evals and downstream provisioning pipelines rely
on; deviating from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Connection-free query model | Core Data API concept |
| Step 2 — Authentication (Secrets Manager vs temp credentials) | Auth decision |
| Step 3 — ExecuteStatement | Single-query execution |
| Step 4 — BatchExecuteStatement | Batch SQL execution |
| Step 5 — Statement lifecycle | SUBMITTED through FINISHED/FAILED |
| Step 6 — DescribeStatement and GetStatementResult | Polling + results |
| Step 7 — Result pagination and 24-hour expiry | Result handling |
| Step 8 — Lambda integration (poll vs EventBridge) | Serverless patterns |
| Step 9 — Abort statement (cancel by StatementId) | Cancel long queries |
| Step 10 — ListStatements and CloudTrail audit | Query governance |
| Step 11 — Cost model and quotas | Pricing + limits |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/authentication-and-secrets.md | Auth + Secrets detail |
| references/statement-lifecycle-and-results.md | Lifecycle + results detail |

## Mindset

**One-line takeaway:** The Redshift Data API lets you run SQL queries
against a Redshift cluster or Redshift Serverless workgroup WITHOUT a
persistent JDBC/ODBC connection. You submit a statement via API, it
returns a StatementId, you poll DescribeStatement for status, and when
FINISHED you call GetStatementResult to retrieve rows. Results expire
24 hours after completion. There is NO additional cost — standard
Redshift charges apply.

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

## Configuration dependency graph (novel heuristic)

Data API configurations are NOT independent. The authentication method
determines what parameters are required. The cluster/workgroup must
exist before queries can run. Result retrieval depends on statement
completion. Use this graph to sequence deployment.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Cluster/workgroup identifier | Redshift cluster or Serverless workgroup exists | If the cluster is paused, queries queue until resumed | query execution |
| Authentication: Secrets Manager | Secret ARN exists; secret contains valid DB credentials | Secret must be type Redshift; DBUser/DBName/Password/EngineHost/Port fields required | password-free auth |
| Authentication: temp credentials | IAM principal has redshift:GetClusterCredentials | Temp creds expire after 15 min (configurable DurationSeconds) | IAM-federated auth |
| Database name | Must match a database on the cluster | If wrong, ExecuteStatement returns "database does not exist" | query target |
| DbUser (for temp creds) | Must be an existing Redshift user | AutoCreate option can create the user if set to true | user context |
| ExecuteStatement | Cluster identifier + auth + database + SQL text | StatementId is unique per API call; SQL is case-sensitive | async query |
| BatchExecuteStatement | Cluster + auth + database + SQL list | Each SQL in the batch runs sequentially; one failure aborts remaining | batch SQL |
| DescribeStatement | StatementId from ExecuteStatement | Polling too frequently can hit API rate limits | status check |
| GetStatementResult | Statement status is FINISHED | Results expire 24 hours after FINISHED; expired results are gone | row retrieval |
| AbortStatement | Statement is SUBMITTED or STARTED | Cannot abort a FINISHED statement (no-op) | cancel long queries |

**The result-expiry row is the one a baseline model misses.** Results
are NOT permanent. The 24-hour clock starts when the statement reaches
FINISHED — not when the statement was submitted. If a query runs for 23
hours (within the 24-hour timeout) and finishes, results are available
for 24 hours AFTER that. But if a workflow submits a query, waits 25
hours, then calls GetStatementResult, the results are already gone.

**Cross-dependency gotchas:**
- Secrets Manager auth and temp credentials auth are mutually exclusive
  per API call. You specify EITHER SecretArn OR (DbUser with
  temp credentials), not both.
- BatchExecuteStatement runs SQL statements sequentially within the
  batch. If statement 3 of 5 fails, statements 4 and 5 do NOT run.
  The batch is NOT transactional by default.
- DescribeStatement returns the status but NOT the rows. You must call
  GetStatementResult separately to retrieve data rows.
- GetStatementResult paginates with NextToken. Large result sets require
  multiple calls.

## Expert heuristic: Secrets Manager vs temporary credentials

A baseline model says "use Secrets Manager for auth." The correct
heuristic recognizes that the choice depends on your security model,
credential rotation needs, and whether you already have a Secrets
Manager setup.

```text
Authentication decision:
  ├── Have a Secrets Manager secret for Redshift?
  │     → Use SecretArn (recommended for production)
  │     → Credentials auto-rotated via Secrets Manager rotation
  │     → No password in application code
  │
  ├── Need IAM-federated access without a secret store?
  │     → Use temporary credentials (GetClusterCredentials)
  │     → IAM principal needs redshift:GetClusterCredentials
  │     → Creds expire after DurationSeconds (default 900s)
  │     → Can use AutoCreate to auto-provision DB users from IAM
  │
  └── Connecting from Lambda?
        → Both work; Secrets Manager is simpler for Lambda
        → Temp credentials avoid the Secrets Manager API call per
          invocation (cache creds for DurationSeconds)
        → Temp creds + AutoCreate enables IAM-based per-user access
```

**Key implication:** for Lambda workloads, temp credentials with
caching can reduce API calls (no Secrets Manager call per invocation).
For centralized credential management, Secrets Manager is better.

## Expert heuristic: Lambda polling vs EventBridge notification

The Data API is asynchronous. After ExecuteStatement, you do not get
results immediately. Two patterns exist for getting results.

```text
Pattern 1 — Lambda polling (simpler, higher cost):
  1. Lambda calls ExecuteStatement → gets StatementId
  2. Lambda calls DescribeStatement in a loop (with sleep)
  3. When status = FINISHED, Lambda calls GetStatementResult

  Pros: simple, self-contained, no additional services
  Cons: Lambda is billed for the entire poll duration; sleep adds cost;
        long-running queries may hit Lambda timeout (15 min max)

Pattern 2 — EventBridge notification (async, cheaper):
  1. Lambda calls ExecuteStatement → gets StatementId
  2. Lambda returns immediately (no polling)
  3. EventBridge rule matches "Redshift Data API Status Change"
  4. EventBridge triggers a target Lambda when status changes
  5. Target Lambda checks if FINISHED, calls GetStatementResult

  Pros: no Lambda billing for idle polling; handles long queries (>15 min)
  Cons: more infrastructure (EventBridge rule + target Lambda); async
        pattern is harder to reason about
```

**Key implication:** for queries under 15 minutes, Lambda polling is
simpler. For queries that may exceed 15 minutes (Lambda timeout), use
EventBridge notification.

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

## Prerequisites (verify before provisioning)

Before emitting deployment commands, verify these prerequisites. If any
are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Redshift cluster or Serverless workgroup exists | Data API queries a cluster/workgroup | `aws redshift describe-clusters` or `aws redshift-serverless list-workgroups` |
| Database name confirmed | Queries target a specific database | Check `DBName` in cluster details |
| Secrets Manager secret (if using SecretArn auth) | Provides DB credentials without passwords in code | `aws secretsmanager describe-secret --secret-id <id>` |
| IAM permission for temp creds (if using GetClusterCredentials) | Allows generating short-lived DB credentials | Check IAM policy for `redshift:GetClusterCredentials` |
| IAM permission for redshift-data API | Lambda/caller needs redshift-data permissions | Check IAM policy for `redshift-data:ExecuteStatement` etc. |
| Network access to Redshift (if not publicly accessible) | Data API connects to the cluster over the network | Verify cluster is publicly accessible OR run from within VPC |
| SQL statement(s) prepared | ExecuteStatement requires SQL text | Prepare and validate SQL syntax |
| Lambda function (if Lambda integration) | Lambda invokes the Data API | Confirm Lambda function exists with correct IAM role |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Connection-free query model

The Data API eliminates persistent connections. Instead of:

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

**Key implication:** the Data API is stateless. Each API call is an
independent HTTP request. There is no connection pool, no idle
timeout, no max-connections limit. This simplifies serverless
deployments (Lambda, Fargate, Step Functions).

## Step 2 — Authentication (Secrets Manager vs temp credentials)

| Feature | Secrets Manager | Temp Credentials |
|---|---|---|
| Parameter | `SecretArn` | `DbUser` + IAM |
| Password in code | No (stored in secret) | No (IAM-generated) |
| Credential rotation | Automatic via Secrets Manager rotation | N/A (short-lived, auto-generated) |
| Expiry | Until secret is rotated | DurationSeconds (default 900s, max 3600s) |
| AutoCreate users | No | Yes (AutoCreate: true provisions IAM-mapped DB users) |
| Cost | Secrets Manager storage ($0.40/secret/month) | No additional cost |
| Recommended for | Production with centralized credential management | IAM-federated, per-user access |

**Secrets Manager auth:**

```bash
aws redshift-data execute-statement \
  --cluster-identifier my-redshift-cluster \
  --secret-arn arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx \
  --database dev \
  --sql "SELECT * FROM sales LIMIT 10" \
  --statement-name "query-sales"
```

**Temp credentials auth:**

```bash
# Step 1: Get temp credentials
CREDS=$(aws redshift get-cluster-credentials \
  --cluster-identifier my-redshift-cluster \
  --db-user my_iam_user \
  --db-name dev \
  --duration-seconds 3600)

DB_USER=$(echo "$CREDS" | jq -r '.DbUser')
DB_PASSWORD=$(echo "$CREDS" | jq -r '.DbPassword')

# Step 2: Use temp creds with Data API (via DbUser parameter)
aws redshift-data execute-statement \
  --cluster-identifier my-redshift-cluster \
  --db-user "$DB_USER" \
  --database dev \
  --sql "SELECT * FROM sales LIMIT 10"
```

## Step 3 — ExecuteStatement

ExecuteStatement submits a single SQL statement asynchronously.

```bash
STATEMENT_ID=$(aws redshift-data execute-statement \
  --cluster-identifier my-redshift-cluster \
  --secret-arn arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx \
  --database dev \
  --sql "SELECT COUNT(*) FROM sales WHERE sale_date >= '2026-01-01'" \
  --query 'Id' --output text)

echo "StatementId: $STATEMENT_ID"
```

**Parameters:**

| Parameter | Required | Description |
|---|---|---|
| `ClusterIdentifier` or `WorkgroupName` | Yes | Target cluster or Serverless workgroup |
| `Database` | Yes | Database name |
| `Sql` | Yes | SQL text |
| `SecretArn` | One of (auth) | Secrets Manager secret ARN |
| `DbUser` | One of (auth) | Temp credentials DB user |
| `StatementName` | No | Human-readable name |
| `WithEvent` | No | If true, sends EventBridge event on completion |
| `Parameters` | No | Parameterized query values |

**WithEvent:** setting `--with-event` causes the Data API to emit an
EventBridge event when the statement status changes. This enables the
async Lambda pattern.

## Step 4 — BatchExecuteStatement

BatchExecuteStatement runs multiple SQL statements sequentially in a
single API call.

```bash
aws redshift-data batch-execute-statement \
  --cluster-identifier my-redshift-cluster \
  --secret-arn arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx \
  --database dev \
  --sqls \
    "CREATE TEMP TABLE temp_sales AS SELECT * FROM sales WHERE sale_date >= '2026-01-01'" \
    "SELECT COUNT(*) FROM temp_sales" \
    "DROP TABLE temp_sales"
```

**Key behaviors:**
- Statements run sequentially (not parallel).
- If statement N fails, statements N+1 through end do NOT run.
- The batch is NOT transactional by default (no automatic rollback).
- Returns a single StatementId for the entire batch.
- Each statement's status can be checked via DescribeStatement.

**Common mistake:** assuming BatchExecuteStatement is transactional.
It is NOT. For transactional batches, wrap in BEGIN/COMMIT:

```sql
BEGIN;
CREATE TEMP TABLE temp_sales AS SELECT * FROM sales;
SELECT COUNT(*) FROM temp_sales;
COMMIT;
```

## Step 5 — Statement lifecycle

Each statement goes through a lifecycle:

```text
SUBMITTED → STARTED → FINISHED (success)
                  ↘ FAILED (error)
                  ↘ ABORTED (cancelled)

Time:
  SUBMITTED:  API accepted the request, query is queued
  STARTED:    Redshift began executing the query
  FINISHED:   Query completed successfully, results available
  FAILED:     Query failed (SQL error, timeout, resource)
  ABORTED:    Query was cancelled (AbortStatement or cluster shutdown)
```

**DescribeStatement:**

```bash
aws redshift-data describe-statement \
  --id "$STATEMENT_ID" \
  --query '{Status:Status, ResultRows:ResultRows, HasResultSet:HasResultSet, Error:Error}' \
  --output table
```

**Lifecycle transitions:**

| Transition | Trigger | Duration |
|---|---|---|
| SUBMITTED → STARTED | Redshift scheduler picks up the query | Depends on WLM queue |
| STARTED → FINISHED | Query execution completes | Depends on query complexity (max 24 hours) |
| STARTED → FAILED | SQL error or resource limit | Immediate |
| STARTED → ABORTED | AbortStatement or cluster event | Immediate |

**Timeout:** a statement automatically fails after 24 hours (query
timeout). Use AbortStatement to cancel sooner.

## Step 6 — DescribeStatement and GetStatementResult

**DescribeStatement** checks status and metadata (no rows):

```bash
aws redshift-data describe-statement --id "$STATEMENT_ID"
```

Returns: Status, ResultRows (count), HasResultSet, Error (if failed),
Duration, RedshiftPid, RedshiftQueryId.

**GetStatementResult** retrieves the actual data rows (when FINISHED):

```bash
aws redshift-data get-statement-result \
  --id "$STATEMENT_ID" \
  --output json
```

Returns: ColumnMetadata (schema) and Records (rows as arrays of typed
values).

**Key distinction:** DescribeStatement gives you STATUS;
GetStatementResult gives you DATA. You must call DescribeStatement first
to confirm FINISHED before calling GetStatementResult.

## Step 7 — Result pagination and 24-hour expiry

**Pagination:** GetStatementResult returns up to 100 MB per call. For
larger result sets, use NextToken to paginate.

```bash
NEXT_TOKEN=""
while true; do
  if [ -z "$NEXT_TOKEN" ]; then
    RESULT=$(aws redshift-data get-statement-result --id "$STATEMENT_ID" --output json)
  else
    RESULT=$(aws redshift-data get-statement-result --id "$STATEMENT_ID" --next-token "$NEXT_TOKEN" --output json)
  fi
  
  echo "$RESULT" | jq '.Records'
  
  NEXT_TOKEN=$(echo "$RESULT" | jq -r '.NextToken // empty')
  [ -z "$NEXT_TOKEN" ] && break
done
```

**24-hour expiry:** results are available for 24 hours after FINISHED.
After that, GetStatementResult returns an error. For results needed
beyond 24 hours:

1. **UNLOAD to S3:** `UNLOAD ('SELECT ...') TO 's3://bucket/path/'`
   writes results directly to S3, bypassing GetStatementResult entirely.
2. **Immediate persistence:** call GetStatementResult immediately and
   write rows to S3/DynamoDB.
3. **Materialized view:** create a materialized view from the query
   results for persistent access.

## Step 8 — Lambda integration (poll vs EventBridge)

### Pattern 1: Lambda polling

```python
import boto3
import time

redshift_data = boto3.client('redshift-data')

def lambda_handler(event, context):
    # Submit the query
    response = redshift_data.execute_statement(
        ClusterIdentifier='my-redshift-cluster',
        SecretArn='arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx',
        Database='dev',
        Sql='SELECT COUNT(*) FROM sales'
    )
    statement_id = response['Id']
    
    # Poll for completion
    while True:
        desc = redshift_data.describe_statement(Id=statement_id)
        status = desc['Status']
        
        if status == 'FINISHED':
            result = redshift_data.get_statement_result(Id=statement_id)
            return { 'rows': result['Records'] }
        elif status in ('FAILED', 'ABORTED'):
            raise Exception(f"Query {status}: {desc.get('Error', 'Unknown')}")
        
        time.sleep(1)  # Poll interval
```

### Pattern 2: EventBridge notification

```python
# Step 1: Submit query with WithEvent=True
response = redshift_data.execute_statement(
    ClusterIdentifier='my-redshift-cluster',
    SecretArn='arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx',
    Database='dev',
    Sql='SELECT COUNT(*) FROM sales',
    WithEvent=True  # Emit EventBridge on completion
)
return { 'statementId': response['Id'] }

# Step 2: EventBridge rule triggers target Lambda
# Event pattern: { "source": ["aws.redshift-data"], "detail-type": ["Redshift Data Statement Status Change"] }
def result_handler(event, context):
    statement_id = event['detail']['statementId']
    status = event['detail']['status']
    
    if status == 'FINISHED':
        result = redshift_data.get_statement_result(Id=statement_id)
        return { 'rows': result['Records'] }
```

## Step 9 — Abort statement (cancel by StatementId)

AbortStatement cancels a running query by StatementId.

```bash
aws redshift-data abort-statement \
  --statement-id "$STATEMENT_ID"
```

**Key behaviors:**
- Can only abort statements in SUBMITTED or STARTED status.
- Aborting a FINISHED statement is a no-op (returns success but does
  nothing).
- Abort is asynchronous — the statement moves to ABORTED after the
  cancel propagates to Redshift.
- Useful for long-running queries that exceed a timeout.

## Step 10 — ListStatements and CloudTrail audit

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

## Step 11 — Cost model and quotas

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

## Step 12 — Recent features

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

## NEVER do these things

1. **NEVER assume results are available beyond 24 hours after
   FINISHED.** Results expire after 24 hours. Persist immediately if
   needed longer. Use UNLOAD to S3 for large datasets.

2. **NEVER hardcode database passwords in Lambda code.** Use Secrets
   Manager (SecretArn) or temporary credentials (GetClusterCredentials).
   Passwords in code are a security risk and break credential rotation.

3. **NEVER assume BatchExecuteStatement is transactional.** It is NOT.
   If statement 3 of 5 fails, statements 4-5 do NOT run, but there is no
   automatic rollback of statements 1-2. Wrap in BEGIN/COMMIT for
   transactional behavior.

4. **NEVER call GetStatementResult before checking DescribeStatement
   status.** GetStatementResult only works when status is FINISHED.
   Calling it for a STARTED statement returns an error.

5. **NEVER poll DescribeStatement too aggressively.** The rate limit is
   1 call per second per statement. Polling faster causes throttling
   errors. Use 1-5 second intervals.

6. **NEVER forget the Secrets Manager IAM permission.** The Lambda
   execution role needs `secretsmanager:GetSecretValue` on the secret
   ARN. Without it, ExecuteStatement fails with "access denied."

7. **NEVER use the Data API for sub-second interactive queries.** The
   async polling overhead (submit + poll + retrieve) adds latency. For
   interactive workloads, use a persistent JDBC/ODBC connection.

8. **NEVER assume AbortStatement is synchronous.** It initiates the
   cancel but the statement moves to ABORTED asynchronously. Poll
   DescribeStatement to confirm the ABORTED status.

9. **NEVER pass SQL with user input without parameterization.** Use the
   `Parameters` field for parameterized queries to prevent SQL injection.
   CloudTrail logs the full SQL text, so injection attempts are visible
   in audit logs.

10. **NEVER forget the 24-hour statement timeout.** A statement auto-
    fails after 24 hours. For ETL workloads that may exceed this, split
    the query into smaller batches.

## Output format

```text
DATA_API: <cluster-id|workgroup-name> (<auth-method: SECRET_ARN|TEMP_CREDS>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Cluster/Workgroup: <identifier> (exists)
  [✓|✗] Database: <db-name>
  [✓|✗] Authentication: SecretArn | TempCredentials
  [✓|✗] Secret ARN: <arn> (valid, has redshift credentials)
  [✓|✗] IAM role: redshift-data:ExecuteStatement | DescribeStatement | GetStatementResult
  [✓|✗] IAM role: secretsmanager:GetSecretValue (if SecretArn auth)
  [✓|✗] IAM role: redshift:GetClusterCredentials (if temp creds auth)
  [✓|✗] SQL: <prepared/validated>
  [✓|✗] Result handling: immediate retrieval | UNLOAD to S3 | EventBridge pattern
  [✓|✗] 24-hour result expiry: persistence plan defined
  [✓|✗] Polling pattern: Lambda poll (interval <Ns>) | EventBridge async
  [✓|✗] Abort plan: AbortStatement by StatementId
  [✓|✗] CloudTrail audit: enabled
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws redshift-data describe-statement --id <statement-id>
  aws redshift-data get-statement-result --id <statement-id>
  aws redshift-data list-statements --status FINISHED --max-results 10
```

### Worked example — Lambda query with Secrets Manager auth

```text
DATA_API: my-redshift-cluster (SECRET_ARN)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Cluster/Workgroup: my-redshift-cluster (exists, available)
  [✓] Database: dev
  [✓] Authentication: SecretArn
  [✓] Secret ARN: arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx
  [✓] IAM role: redshift-data:ExecuteStatement, DescribeStatement, GetStatementResult
  [✓] IAM role: secretsmanager:GetSecretValue on redshift-creds-xxx
  [✓] SQL: SELECT COUNT(*) FROM sales WHERE sale_date >= '2026-01-01'
  [✓] Result handling: immediate retrieval + write to DynamoDB
  [✓] 24-hour result expiry: results persisted to DynamoDB within 1 minute of FINISHED
  [✓] Polling pattern: Lambda poll (interval 2s, max 60 iterations)
  [✓] Abort plan: AbortStatement if poll exceeds 60 iterations
  [✓] CloudTrail audit: enabled (SQL text logged)
  [✓] Tags: Environment=production, Workflow=sales-counter
VERIFICATION_COMMANDS:
  aws redshift-data describe-statement --id <statement-id>
  aws redshift-data get-statement-result --id <statement-id>
  aws redshift-data list-statements --status FINISHED --max-results 10
```

## Error handling

### ExecuteStatement returns "Cluster not found"
- The cluster identifier is wrong or the cluster does not exist. Verify
  with `aws redshift describe-clusters`.

### DescribeStatement returns "AccessDenied"
- The IAM role lacks `redshift-data:DescribeStatement`. Add the
  permission to the Lambda execution role.

### GetStatementResult returns "Statement result expired"
- More than 24 hours have passed since FINISHED. Results are gone.
  Re-run the query or use UNLOAD to persist to S3.

### Statement stays in SUBMITTED indefinitely
- The cluster may be paused or the WLM queue is full. Check cluster
  status with `aws redshift describe-clusters`. For Serverless, the
  workgroup may be scaling up.

### BatchExecuteStatement partially succeeds
- The batch is NOT transactional. Earlier statements may have committed
  before a later statement failed. Wrap in BEGIN/COMMIT for atomicity.

### Lambda timeout during polling
- The query takes longer than Lambda's 15-minute timeout. Switch to the
  EventBridge async pattern (WithEvent=True + EventBridge rule).

## Domain

AWS CloudOps / Amazon Redshift Data API Serverless Query Execution.

## AWS documentation

- **Redshift Data API** — https://docs.aws.amazon.com/redshift/latest/mgmt/data-api.html
- **ExecuteStatement** — https://docs.aws.amazon.com/redshift/latest/APIReference/API_ExecuteStatement.html
- **BatchExecuteStatement** — https://docs.aws.amazon.com/redshift/latest/APIReference/API_BatchExecuteStatement.html
- **DescribeStatement** — https://docs.aws.amazon.com/redshift/latest/APIReference/API_DescribeStatement.html
- **GetStatementResult** — https://docs.aws.amazon.com/redshift/latest/APIReference/API_GetStatementResult.html
- **GetClusterCredentials** — https://docs.aws.amazon.com/redshift/latest/APIReference/API_GetClusterCredentials.html
- **Authorizing Data API** — https://docs.aws.amazon.com/redshift/latest/mgmt/data-api-auth.html
- **Data API quotas** — https://docs.aws.amazon.com/redshift/latest/mgmt/data-api.html#data-api-limits
- **Redshift Data API pricing** — https://aws.amazon.com/redshift/pricing/
