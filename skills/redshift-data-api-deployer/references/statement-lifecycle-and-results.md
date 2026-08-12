# Statement Lifecycle and Results — Redshift Data API Deployer

Deep reference on the statement lifecycle (SUBMITTED through
FINISHED/FAILED/ABORTED), DescribeStatement polling mechanics,
GetStatementResult data format, result pagination (NextToken), 24-hour
result expiry, AbortStatement, ListStatements, and CloudTrail audit.
Loaded on demand by the skill — kept out of the main SKILL.md body so
the deployment procedure stays scannable.

## Statement lifecycle in detail

### Lifecycle states

```text
                    ┌──────────┐
                    │SUBMITTED │  ← API accepted, query queued
                    └────┬─────┘
                         │
                    ┌────▼─────┐
        ┌───────────┤ STARTED  ├───────────┐
        │           └──────────┘           │
        │                                  │
   ┌────▼─────┐                      ┌────▼─────┐
   │ FINISHED │                      │  FAILED  │
   └──────────┘                      └──────────┘
   Results available                  Error in Error field
   for 24 hours                       (SQL error, timeout, resource)

                    ┌──────────┐
                    │ ABORTED  │  ← Cancelled via AbortStatement
                    └──────────┘   or cluster event
```

### State descriptions

| State | Meaning | Duration |
|---|---|---|
| SUBMITTED | API accepted the request; query is in the WLM queue | Depends on WLM queue length |
| STARTED | Redshift began executing the query | Depends on query complexity (max 24 hours) |
| FINISHED | Query completed successfully | Results available for 24 hours |
| FAILED | Query failed (SQL error, timeout, resource limit) | Error message in DescribeStatement |
| ABORTED | Query was cancelled (AbortStatement or cluster event) | No results available |

### Automatic timeout

A statement automatically transitions to FAILED after 24 hours. This is
the hard timeout — it cannot be extended.

## DescribeStatement

### Polling pattern

```python
import time

def wait_for_completion(client, statement_id, poll_interval=2, max_polls=300):
    for _ in range(max_polls):
        desc = client.describe_statement(Id=statement_id)
        status = desc['Status']
        
        if status == 'FINISHED':
            return desc
        elif status in ('FAILED', 'ABORTED'):
            error = desc.get('Error', 'Unknown error')
            raise Exception(f"Statement {status}: {error}")
        
        time.sleep(poll_interval)
    
    # Timeout — abort the statement
    client.abort_statement(StatementId=statement_id)
    raise TimeoutError(f"Statement {statement_id} timed out after {max_polls * poll_interval}s")
```

### DescribeStatement response fields

```json
{
  "Id": "abc12345-...",
  "Status": "FINISHED",
  "StatementName": "query-sales",
  "ResultRows": 42,
  "HasResultSet": true,
  "Duration": 15420,
  "RedshiftPid": 12345,
  "RedshiftQueryId": 67890,
  "Error": null,
  "CreatedAt": "2026-08-11T00:00:00Z",
  "UpdatedAt": "2026-08-11T00:00:15Z"
}
```

| Field | Description |
|---|---|
| Status | Current lifecycle state |
| ResultRows | Number of rows in the result (when FINISHED) |
| HasResultSet | Whether GetStatementResult will return data |
| Duration | Execution time in milliseconds |
| RedshiftPid | Process ID on the Redshift cluster |
| RedshiftQueryId | Internal Redshift query ID (for STV tables) |
| Error | Error message (when FAILED) |

### Rate limiting

DescribeStatement has a rate limit of 1 call per second per statement.
Polling faster causes throttling errors. Recommended poll interval: 2-5
seconds.

## GetStatementResult

### Data format

```json
{
  "Records": [
    [{"longValue": 1}, {"stringValue": "alpha"}, {"doubleValue": 100.5}],
    [{"longValue": 2}, {"stringValue": "beta"}, {"doubleValue": 200.0}],
    [{"longValue": 3}, {"stringValue": "gamma"}, {"doubleValue": 300.75}]
  ],
  "ColumnMetadata": [
    {"name": "id", "typeName": "int4"},
    {"name": "name", "typeName": "varchar"},
    {"name": "value", "typeName": "float8"}
  ],
  "NextToken": null,
  "TotalNumRows": 3
}
```

Each row is an array of typed values. Types include: `longValue`,
`stringValue`, `doubleValue`, `booleanValue`, `isNull` (for NULLs).

### Parsing results in Python

```python
def parse_result(result):
    columns = [col['name'] for col in result['ColumnMetadata']]
    rows = []
    for record in result['Records']:
        row = {}
        for i, cell in enumerate(record):
            for key, value in cell.items():
                if key == 'isNull':
                    row[columns[i]] = None
                else:
                    row[columns[i]] = value
        rows.append(row)
    return rows
```

### Pagination

GetStatementResult returns up to 100 MB per call. For larger results,
use NextToken:

```python
def get_all_results(client, statement_id):
    all_records = []
    next_token = None
    
    while True:
        if next_token:
            result = client.get_statement_result(
                Id=statement_id,
                NextToken=next_token
            )
        else:
            result = client.get_statement_result(Id=statement_id)
        
        all_records.extend(result['Records'])
        next_token = result.get('NextToken')
        
        if not next_token:
            break
    
    return all_records
```

### 24-hour result expiry

Results are available for 24 hours after the statement reaches FINISHED.
After 24 hours, GetStatementResult returns:

```json
{
  "Error": {
    "Message": "Statement result has expired",
    "Code": "ResourceNotFoundException"
  }
}
```

**Mitigation strategies:**

1. **UNLOAD to S3** (recommended for large results):
```sql
UNLOAD ('SELECT * FROM customers') 
TO 's3://my-bucket/exports/customers/'
IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftS3Role'
FORMAT PARQUET;
```

2. **Immediate persistence** (for small results):
```python
# Call GetStatementResult immediately after FINISHED
# Write to DynamoDB, S3, or another store
```

3. **Materialized view** (for repeated access):
```sql
CREATE MATERIALIZED VIEW mv_customer_counts AS
SELECT region, COUNT(*) FROM customers GROUP BY region;
```

## AbortStatement

### Cancelling a running query

```bash
aws redshift-data abort-statement --statement-id "$STATEMENT_ID"
```

**Key behaviors:**
- Can abort SUBMITTED or STARTED statements.
- Aborting FINISHED/FAILED/ABORTED is a no-op (returns success).
- Abort is asynchronous — poll DescribeStatement to confirm ABORTED.
- After abort, no results are available (GetStatementResult fails).

### When to abort

```text
Abort triggers:
  ├── Lambda timeout approaching (poll loop exceeded max iterations)
  ├── Query running longer than expected SLA
  ├── User-initiated cancel (UI "Stop" button)
  └── Resource contention (cluster overloaded)
```

## ListStatements

### Querying statement history

```bash
aws redshift-data list-statements \
  --status FINISHED \
  --max-results 50
```

Filters:
- `--status`: SUBMITTED, STARTED, FINISHED, FAILED, ABORTED, ALL
- `--statement-name`: filter by name
- `--role-level`: USER (only caller's statements) or ALL (account-wide)

### Statement list response

```json
{
  "Statements": [
    {
      "Id": "abc12345-...",
      "StatementName": "query-sales",
      "Status": "FINISHED",
      "CreatedAt": "2026-08-11T00:00:00Z",
      "UpdatedAt": "2026-08-11T00:00:15Z",
      "ResultRows": 42
    }
  ],
  "NextToken": null
}
```

## CloudTrail audit

### What CloudTrail logs

Every Data API call is logged in CloudTrail:

| API | Logged fields |
|---|---|
| ExecuteStatement | ClusterIdentifier, Database, Sql, SecretArn/DbUser, StatementName |
| BatchExecuteStatement | ClusterIdentifier, Database, Sqls (list), auth |
| DescribeStatement | Id |
| GetStatementResult | Id |
| AbortStatement | StatementId |
| ListStatements | Status, MaxResults |

**Key implication:** the full SQL text appears in CloudTrail. This is
valuable for audit but means:
1. Do NOT put sensitive data (PII, secrets) directly in SQL text.
2. Use parameterized queries for user-supplied input.
3. CloudTrail log encryption is important for compliance.

### Querying CloudTrail for Data API events

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=redshift-data.amazonaws.com \
  --start-time 2026-08-11T00:00:00Z \
  --end-time 2026-08-11T23:59:59Z \
  --max-results 50
```

## Quotas summary

| Quota | Value | Adjustable |
|---|---|---|
| Statement timeout | 24 hours | No |
| Result availability after FINISHED | 24 hours | No |
| GetStatementResult max payload | 100 MB per call | No |
| DescribeStatement rate | 1/second/statement | No |
| Concurrent statements per cluster | 50 | Yes |
| ListStatements max results | 100 | No |

## Terraform example

```hcl
# IAM role for Lambda to use Data API
resource "aws_iam_role" "redshift_query_role" {
  name = "RedshiftDataQueryRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "redshift_data_policy" {
  name = "RedshiftDataPolicy"
  role = aws_iam_role.redshift_query_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "redshift-data:ExecuteStatement",
          "redshift-data:DescribeStatement",
          "redshift-data:GetStatementResult",
          "redshift-data:AbortStatement",
          "redshift-data:ListStatements"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = "secretsmanager:GetSecretValue"
        Resource = aws_secretsmanager_secret.redshift_creds.arn
      }
    ]
  })
}

# Secrets Manager secret for Redshift credentials
resource "aws_secretsmanager_secret" "redshift_creds" {
  name = "redshift/my-redshift-cluster"
}

resource "aws_secretsmanager_secret_version" "redshift_creds" {
  secret_id = aws_secretsmanager_secret.redshift_creds.id
  secret_string = jsonencode({
    username            = "admin"
    password            = var.redshift_password
    engine              = "redshift"
    host                = aws_redshift_cluster.main.endpoint
    port                = 5439
    dbClusterIdentifier = aws_redshift_cluster.main.cluster_identifier
  })
}
```
