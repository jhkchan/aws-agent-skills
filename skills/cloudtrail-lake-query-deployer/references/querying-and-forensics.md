# Querying and Forensic Patterns — CloudTrail Lake Query Deployer

Deep reference on SQL query syntax for CloudTrail Lake, StartQuery
and GetQueryResults API usage, time-based filtering for cost
optimization, and common forensic investigation query patterns.
Loaded on demand by the skill — kept out of the main SKILL.md body
so the provisioning procedure stays scannable.

## Query API mechanics

### Two-step query process

CloudTrail Lake uses an asynchronous two-step query model:

1. **StartQuery** — submit the SQL statement, receive a QueryId
2. **GetQueryResults** — poll with the QueryId until results are ready

```bash
# Step 1: Start query
QUERY_ID=$(aws cloudtrail-data start-query \
  --query-statement "SELECT eventName, eventTime FROM <eds-id> WHERE eventTime > '2026-08-10T00:00:00Z' AND eventTime < '2026-08-11T00:00:00Z' LIMIT 10" \
  --query 'QueryId' --output text)

# Step 2: Check status
aws cloudtrail-data describe-query --query-id "$QUERY_ID"
# Status: RUNNING, FINISHED, FAILED, CANCELLED, TIMED_OUT

# Step 3: Get results (when FINISHED)
aws cloudtrail-data get-query-results --query-id "$QUERY_ID"
```

### Cancel a running query

```bash
aws cloudtrail-data cancel-query --query-id "$QUERY_ID"
```

Use this for long-running queries that scan too much data.

## SQL syntax

### Supported clauses

CloudTrail Lake SQL supports:

| Clause | Example |
|---|---|
| SELECT | `SELECT eventName, eventTime, userIdentity.arn` |
| FROM | `FROM <eds-id>` |
| WHERE | `WHERE eventName = 'DeleteBucket'` |
| AND / OR | `AND eventTime > '...' AND eventTime < '...'` |
| ORDER BY | `ORDER BY eventTime DESC` |
| LIMIT | `LIMIT 100` |
| LIKE | `WHERE userIdentity.arn LIKE '%admin%'` |
| IN | `WHERE eventName IN ('DeleteBucket', 'DeleteTrail')` |
| count() | `SELECT count(*) FROM <eds-id> WHERE ...` |

### Accessing nested JSON fields

CloudTrail events are JSON. Nested fields use dot notation:

```sql
SELECT
  userIdentity.arn,
  userIdentity.type,
  eventName,
  eventSource,
  eventTime,
  sourceIPAddress,
  userAgent,
  resources[0].ARN,
  responseElements.statusCode
FROM <eds-id>
WHERE eventTime > '2026-08-10T00:00:00Z'
```

### Time-based filtering (CRITICAL for cost)

ALWAYS specify a time range. Without it, the query scans ALL events
in the EDS.

```sql
-- GOOD: narrow time range
SELECT * FROM <eds-id>
WHERE eventTime > '2026-08-10T00:00:00Z'
  AND eventTime < '2026-08-11T00:00:00Z'
  AND eventName = 'DeleteBucket'

-- BAD: no time range (scans everything)
SELECT * FROM <eds-id>
WHERE eventName = 'DeleteBucket'
```

The time range is the PRIMARY cost lever. Each query's cost is
proportional to the GB of data scanned within the time range.

## Forensic query patterns

### Pattern 1: Who deleted a specific resource?

```sql
SELECT
  userIdentity.arn,
  eventName,
  eventTime,
  sourceIPAddress,
  userAgent,
  resources[0].ARN as resource_arn
FROM <eds-id>
WHERE eventTime > '2026-08-10T00:00:00Z'
  AND eventTime < '2026-08-11T00:00:00Z'
  AND eventName IN (
    'DeleteBucket', 'DeleteTrail', 'DeleteVpc',
    'DeleteDBInstance', 'DeleteSecurityGroup',
    'DeleteRole', 'DeleteUser', 'DeleteKeyPair'
  )
ORDER BY eventTime DESC
```

### Pattern 2: What did a specific user do?

```sql
SELECT
  eventName,
  eventSource,
  eventTime,
  resourceName,
  sourceIPAddress,
  userAgent
FROM <eds-id>
WHERE eventTime > '2026-08-10T00:00:00Z'
  AND eventTime < '2026-08-11T00:00:00Z'
  AND userIdentity.arn = 'arn:aws:iam::123456789012:user/suspicious-user'
ORDER BY eventTime DESC
```

### Pattern 3: Console login from unusual IP

```sql
SELECT
  userIdentity.arn,
  sourceIPAddress,
  eventTime,
  responseElements.ConsoleLogin as login_result
FROM <eds-id>
WHERE eventTime > '2026-08-10T00:00:00Z'
  AND eventName = 'ConsoleLogin'
  AND sourceIPAddress NOT LIKE '10.%'
  AND sourceIPAddress NOT LIKE '172.16.%'
  AND sourceIPAddress NOT LIKE '192.168.%'
ORDER BY eventTime DESC
```

### Pattern 4: Root account activity

```sql
SELECT
  eventName,
  eventTime,
  sourceIPAddress,
  userIdentity.type
FROM <eds-id>
WHERE eventTime > '2026-08-10T00:00:00Z'
  AND userIdentity.type = 'Root'
ORDER BY eventTime DESC
```

### Pattern 5: Failed API calls (error hunting)

```sql
SELECT
  eventName,
  eventSource,
  errorCode,
  errorMessage,
  eventTime,
  userIdentity.arn,
  sourceIPAddress
FROM <eds-id>
WHERE eventTime > '2026-08-10T00:00:00Z'
  AND errorCode IS NOT NULL
ORDER BY eventTime DESC
LIMIT 50
```

### Pattern 6: IAM changes (privilege escalation)

```sql
SELECT
  eventName,
  userIdentity.arn,
  requestParameters,
  eventTime
FROM <eds-id>
WHERE eventTime > '2026-08-10T00:00:00Z'
  AND eventName IN (
    'AttachRolePolicy', 'AttachUserPolicy',
    'PutRolePolicy', 'PutUserPolicy',
    'CreateRole', 'CreateUser',
    'AssumeRole', 'UpdateAssumeRolePolicy'
  )
ORDER BY eventTime DESC
```

### Pattern 7: S3 data access audit

```sql
SELECT
  userIdentity.arn,
  eventName,
  resources[0].ARN as s3_object,
  sourceIPAddress,
  eventTime
FROM <data-eds-id>
WHERE eventTime > '2026-08-10T00:00:00Z'
  AND eventName IN ('GetObject', 'PutObject', 'DeleteObject')
  AND resources[0].ARN LIKE '%sensitive-bucket%'
ORDER BY eventTime DESC
LIMIT 100
```

## Cost estimation per query

```bash
# After running a query, check bytes scanned
aws cloudtrail-data describe-query \
  --query-id "$QUERY_ID" \
  --query '{Status:QueryStatus,BytesScanned:BytesScanned}'

# Cost = BytesScanned * $0.005/GB
# Example: 5 GB scanned = $0.025 per query
```

## Terraform examples

```hcl
# Event data store
resource "aws_cloudtrail_event_data_store" "mgmt" {
  name                     = "mgmt-events-eds"
  include_management_events = true
  retention_period          = 90

  tags = {
    Environment = "production"
  }
}

# Advanced event selectors for data events
resource "aws_cloudtrail_event_data_store" "s3_data" {
  name                     = "s3-data-eds"
  include_management_events = false
  retention_period          = 365

  advanced_event_selector {
    name = "S3 audit bucket events"

    field_selector {
      field  = "eventCategory"
      equals = ["Data"]
    }

    field_selector {
      field  = "resources.type"
      equals = ["AWS::S3::Object"]
    }

    field_selector {
      field      = "resources.ARN"
      starts_with = ["arn:aws:s3:::audit-bucket/"]
    }
  }
}
```

## Step 6 — Forensic query patterns

### Who deleted a specific resource?

```sql
SELECT userIdentity.arn, eventName, eventTime, sourceIPAddress, userAgent
FROM <eds-id>
WHERE eventTime > '2026-08-10T00:00:00Z'
  AND eventTime < '2026-08-11T00:00:00Z'
  AND eventName IN ('DeleteBucket', 'DeleteTrail', 'DeleteVpc', 'DeleteDBInstance')
ORDER BY eventTime DESC
```

### What did a specific user do?

```sql
SELECT eventName, eventSource, eventTime, resourceName, sourceIPAddress
FROM <eds-id>
WHERE eventTime > '2026-08-10T00:00:00Z'
  AND eventTime < '2026-08-11T00:00:00Z'
  AND userIdentity.arn = 'arn:aws:iam::123456789012:user/suspicious-user'
ORDER BY eventTime DESC
```

### Console login from unusual IP?

```sql
SELECT userIdentity.arn, sourceIPAddress, eventTime, responseElements
FROM <eds-id>
WHERE eventTime > '2026-08-10T00:00:00Z'
  AND eventName = 'ConsoleLogin'
  AND sourceIPAddress NOT LIKE '10.%'
  AND sourceIPAddress NOT LIKE '172.16.%'
ORDER BY eventTime DESC
```

### Root account activity?

```sql
SELECT eventName, eventTime, sourceIPAddress, userIdentity.type
FROM <eds-id>
WHERE eventTime > '2026-08-10T00:00:00Z'
  AND userIdentity.type = 'Root'
ORDER BY eventTime DESC
```
