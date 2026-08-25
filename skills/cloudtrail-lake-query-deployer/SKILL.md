---
name: cloudtrail-lake-query-deployer
description: 'Provisions AWS CloudTrail Lake with production defaults: event data store (EDS) creation, ingestion (management events, data events, Insights), SQL query via StartQuery/GetQueryResults, time-based filtering, advanced event selectors, federation to Athena/Athena workgroup, multi-account EDS (via Organizations), retention (7-3653 days), billing model (per GB ingested + per GB scanned), CloudWatch integration for query alerts, saved queries, common forensic query patterns (who deleted X, what did user Y do), and data protection policy (mask PII in events). Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a CloudTrail Lake event data store, configuring multi-account event ingestion, running forensic SQL queries on CloudTrail events, setting up Athena federation. Triggers: cloudtrail lake, event data store, cloudtrail lake query, start query cloudtrail, athena federation cloudtrail, cloudtrail forensic query, EDS retention, cloudtrail data protection, multi-account cloudtrail lake.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with cloudtrail-lake and athena access. Works with Terraform aws_cloudtrail_event_data_store resources and CloudFormation AWS::CloudTrail::EventDataStore templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, cloudtrail-lake, cloudops, deploy, governance, event-data-store, auditing, forensics, sql-query, data-protection
  dependencies: aws-orchestrator
  keywords: aws, cloudtrail lake, event data store, EDS, cloudtrail query, forensic query, athena federation, data protection, multi-account cloudtrail, cloudops, deploy, governance
  when_to_use: Invoke when the user wants to create CloudTrail Lake event data stores, configure multi-account event ingestion, run SQL forensic queries on CloudTrail events, set up Athena federation, configure data protection (PII masking), or manage EDS retention. Do NOT invoke for standard CloudTrail trails (use cloudtrail skills), CloudWatch Logs (use cloudwatch skills), or AWS Config (use config skills).
---

# CloudTrail Lake Query Deployer

An AWS CloudOps agent skill that provisions AWS CloudTrail Lake with
correct defaults. The skill walks the operator through event data
store (EDS) creation, event ingestion configuration (management, data,
Insights), SQL query execution (StartQuery/GetQueryResults), advanced
event selectors, Athena federation, multi-account EDS via Organizations,
retention configuration, billing model understanding (per-GB ingested +
per-GB scanned), data protection policy (PII masking), and common
forensic query patterns, captures EDS and query decisions, explains why
each default matters, and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

cloudtrail lake, event data store, cloudtrail lake query, start query
cloudtrail, athena federation cloudtrail, cloudtrail forensic query,
EDS retention, cloudtrail data protection, multi-account cloudtrail
lake.

## STRICT output contract

When this skill is invoked with a CloudTrail Lake provisioning request
(create an EDS, configure ingestion, set up querying, configure data
protection, enable multi-account, or a partial configuration), the
agent MUST respond with the READY_TO_DEPLOY checklist defined in the
"Output format" section using the literal all-caps labels
`CLOUDTRAIL_LAKE:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the checklist
(marked `[x]`), and `READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — CloudTrail Lake vs standard trails | Core concept |
| Step 2 — Event data store (EDS) creation | Core infrastructure |
| Step 3 — Event ingestion (management, data, Insights) | Event types |
| Step 4 — Advanced event selectors | Fine-grained filtering |
| Step 5 — SQL query (StartQuery + GetQueryResults) | Querying |
| Step 6 — Forensic query patterns | Common investigations |
| Step 7 — Multi-account EDS via Organizations | Multi-account |
| Step 8 — Retention and billing | Cost management |
| Step 9 — Data protection (PII masking) | Compliance |
| Step 10 — Athena federation and CloudWatch | Integration |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/querying-and-forensics.md | Query + forensic detail |
| references/eds-and-multi-account.md | EDS + multi-account detail |

## Mindset

**One-line takeaway:** CloudTrail Lake stores CloudTrail events in an
event data store (EDS) that you query with SQL. Pricing is per-GB
ingested (not per-event) plus per-GB scanned by queries. Queries scan
raw JSON events (not pre-indexed). Data protection policies mask PII
fields BEFORE query results are returned.

Three misconceptions dominate CloudTrail Lake misdesign at provisioning
time:

- **"CloudTrail Lake is just another CloudTrail trail."** It is NOT.
  Standard CloudTrail trails deliver events to S3 (and optionally
  CloudWatch Logs). CloudTrail Lake stores events in an event data
  store optimized for SQL querying. You do NOT need an S3 bucket or
  CloudWatch Logs group — the EDS is a managed store with its own
  retention and billing. Trails are for archival and delivery; Lake is
  for querying and forensics.

- **"Queries use a pre-indexed search engine."** They do NOT. CloudTrail
  Lake queries scan raw JSON event records. There is no pre-built index.
  This means query performance is proportional to the amount of data
  scanned (per-GB scanned billing). Time-based filtering is critical —
  narrowing the time window reduces scanned data and cost.

- **"Data protection is a post-query filter."** It is NOT. Data
  protection policies mask PII fields at the EDS level BEFORE query
  results are returned. The masked values never appear in query output.
  This is a storage-level transformation, not a presentation filter.
  The original values are not accessible via queries once the policy
  is in effect.

## Configuration dependency graph (novel heuristic)

> Configuration dependency graph moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

## Expert heuristic: per-GB billing model

> Per-GB billing heuristic moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

## Expert heuristic: queries scan raw JSON, not indexes

> Raw-JSON scan heuristic moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

## Expert heuristic: data protection masks PII before results

> PII masking heuristic moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| CloudTrail enabled in account | EDS ingests from CloudTrail events | `aws cloudtrail describe-trails` |
| Event type decided (management, data, Insights, network) | EDS type is immutable after creation | Confirm event type requirements |
| Retention period decided (7-3653 days) | Affects storage cost and compliance | Confirm retention requirement |
| Organizations setup (if multi-account) | Multi-account EDS requires Orgs | `aws organizations describe-organization` |
| Data protection requirements identified | PII fields to mask | Confirm which fields need masking |
| IAM permissions for CloudTrail Lake | Both create and query APIs need permissions | Verify `cloudtrail-data:*` and `cloudtrail:*` |
| Athena workgroup (if Athena federation) | Federation requires a workgroup | `aws athena list-work-groups` |
| Budget / cost expectations set | Per-GB ingested + per-GB scanned billing | Confirm budget for ingestion and querying |

If any prerequisite is missing, output
`VERDICT: PREREQUISITES_MISSING` and cite the specific gap.

## Step 1 — CloudTrail Lake vs standard trails

| Feature | Standard CloudTrail Trail | CloudTrail Lake (EDS) |
|---|---|---|
| Storage | S3 bucket | Managed event data store |
| Query | Athena (requires setup) or S3 Select | Native SQL (StartQuery API) |
| Billing | S3 storage + Athena if queried | Per-GB ingested + per-GB scanned |
| Retention | S3 lifecycle rules | 7-3653 days (EDS managed) |
| Multi-account | Organization trail (S3 delivery) | Organization EDS (managed ingestion) |
| Data protection | None (raw events) | PII masking policy |
| Insights | Optional (separate trail) | Built-in EDS type |
| Setup complexity | S3 bucket, bucket policy, IAM | EDS creation (single API call) |

**CloudTrail Lake is for:** forensic querying, compliance auditing,
security investigation, and operational analysis where SQL querying
on managed storage is preferred over S3 + Athena setup.

## Step 2 — Event data store (EDS) creation

Create an EDS for management events:

```bash
EDS_ID=$(aws cloudtrail create-event-data-store \
  --name "mgmt-events-eds" \
  --no-include-management-events \
  --query 'EventDataStoreArn' --output text)

# Wait — management events EDS:
EDS_ID=$(aws cloudtrail create-event-data-store \
  --name "mgmt-events-eds" \
  --include-management-events \
  --query 'EventDataStoreArn' --output text)

echo "EDS ARN: $EDS_ID"
```

**Create a data events EDS:**

```bash
DATA_EDS_ID=$(aws cloudtrail create-event-data-store \
  --name "data-events-eds" \
  --no-include-management-events \
  --query 'EventDataStoreArn' --output text)
```

**Create an Insights EDS:**

```bash
INSIGHTS_EDS_ID=$(aws cloudtrail create-event-data-store \
  --name "insights-eds" \
  --no-include-management-events \
  --query 'EventDataStoreArn' --output text)
```

**EDS ARN format:**

```text
arn:aws:cloudtrail:us-east-1:123456789012:eventdatastore/abc123-def456
```

The EDS ID in the ARN is used as the table name in SQL queries.

## Step 3 — Event ingestion (management, data, Insights)

### Management events

Management events (control plane API calls) are ingested automatically
when the EDS is created with `--include-management-events`.

### Data events

Data events (data plane API calls like S3 GetObject, DynamoDB
GetItem) require advanced event selectors:

```bash
aws cloudtrail put-event-selectors \
  --event-data-store "$DATA_EDS_ID" \
  --advanced-event-selectors '[
    {
      "Name": "Log S3 events for specific buckets",
      "FieldSelectors": [
        {"Field": "eventCategory", "Equals": ["Data"]},
        {"Field": "resources.type", "Equals": ["AWS::S3::Object"]},
        {"Field": "resources.ARN", "StartsWith": ["arn:aws:s3:::my-sensitive-bucket/"]}
      ]
    }
  ]'
```

### Insights events

CloudTrail Insights analyzes management events for anomalous patterns
(spike in API calls, error rate increase). Insights require a separate
EDS or an Insights-enabled management EDS:

```bash
aws cloudtrail put-insight-selectors \
  --event-data-store "$EDS_ID" \
  --insight-selectors '[{"InsightType": "ApiCallRateInsight"},{"InsightType":"ApiErrorRateInsight"}]'
```

## Step 4 — Advanced event selectors

Advanced selectors provide fine-grained control over which data events
are ingested. This is critical for cost management.

```bash
# Only S3 PutObject and DeleteObject events on specific bucket
aws cloudtrail put-event-selectors \
  --event-data-store "$DATA_EDS_ID" \
  --advanced-event-selectors '[
    {
      "Name": "S3 write events only",
      "FieldSelectors": [
        {"Field": "eventCategory", "Equals": ["Data"]},
        {"Field": "resources.type", "Equals": ["AWS::S3::Object"]},
        {"Field": "eventName", "Equals": ["PutObject","DeleteObject","CopyObject"]},
        {"Field": "resources.ARN", "StartsWith": ["arn:aws:s3:::audit-bucket/"]}
      ]
    }
  ]'
```

**Selector fields:**

| Field | Example Values | Description |
|---|---|---|
| eventCategory | Data, Management | Event type filter |
| resources.type | AWS::S3::Object, AWS::Lambda::Function, AWS::DynamoDB::Table | Resource type |
| eventName | PutObject, GetItem, Invoke | Specific API call |
| resources.ARN | arn:aws:s3:::bucket/ | Resource ARN prefix |
| readOnly | true, false | Read vs write events |

## Step 5 — SQL query (StartQuery + GetQueryResults)

CloudTrail Lake uses SQL for querying events. The EDS ID is the table
name.

**Start a query:**

```bash
QUERY_ID=$(aws cloudtrail-data start-query \
  --query-statement "SELECT userIdentity.arn, eventName, eventTime, sourceIPAddress FROM $EDS_ID WHERE eventTime > '2026-08-10T00:00:00Z' AND eventTime < '2026-08-11T00:00:00Z' AND eventName = 'DeleteBucket'" \
  --query 'QueryId' --output text)
```

**Get query results:**

```bash
aws cloudtrail-data get-query-results \
  --query-id "$QUERY_ID"
```

**Query status:**

```bash
aws cloudtrail-data describe-query \
  --query-id "$QUERY_ID" \
  --query 'QueryStatus'
# Expected: RUNNING, FINISHED, FAILED, CANCELLED
```

**Always specify a time range** to reduce scanned data and cost.

## Step 6 — Forensic query patterns

> The four forensic query patterns moved verbatim to [references/querying-and-forensics.md](references/querying-and-forensics.md) — load on demand.

## Step 7 — Multi-account EDS via Organizations

> Multi-account EDS detail moved verbatim to [references/eds-and-multi-account.md](references/eds-and-multi-account.md) — load on demand.

## Step 8 — Retention and billing

### Retention

```bash
# Create EDS with 90-day retention
aws cloudtrail create-event-data-store \
  --name "90-day-eds" \
  --include-management-events \
  --retention-period 90

# Update retention of existing EDS
aws cloudtrail update-event-data-store \
  --event-data-store "$EDS_ID" \
  --retention-period 180
```

Retention range: 7 to 3653 days (10 years).

### Billing model

> Billing rate table and cost estimation moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

## Step 9 — Data protection (PII masking)

Data protection policies mask PII fields in events before query results
are returned.

**Create a data protection policy:**

```bash
aws cloudtrail put-data-protection-policy \
  --event-data-store "$EDS_ID" \
  --policy-document '{
    "Configuration": {
      "Mode": "Mask",
      "MaskingStyle": "REPLACE_WITH_MASK"
    },
    "Identifiers": [
      "arn:aws:dataprotection:us-east-1:aws:data-identifier/EmailAddress",
      "arn:aws:dataprotection:us-east-1:aws:data-identifier/PhoneNumber"
    ]
  }'
```

**What gets masked:**

| Identifier | What it matches | Example |
|---|---|---|
| EmailAddress | Email patterns | user@corp.com → **** |
| PhoneNumber | Phone patterns | +1-555-123-4567 → **** |
| AwsSecretKey | AWS key patterns | AKIA... → **** |
| CreditCard | Card numbers | 4111... → **** |

**Key implication:** once applied, ALL queries against the EDS have PII
masked. There is no per-query bypass. The original values are not
accessible via the query API.

## Step 10 — Athena federation and CloudWatch

> Athena federation and CloudWatch alert setup moved verbatim to [references/eds-and-multi-account.md](references/eds-and-multi-account.md) — load on demand.

## NEVER do these things

1. **NEVER create an EDS without deciding the event type first.** The
   EDS type (management, data, Insights) is immutable after creation.
   Creating a management-only EDS when you need data events requires a
   new EDS.

2. **NEVER query without a time range.** Queries without time bounds
   scan ALL events in the EDS, maximizing cost. Always specify
   `eventTime >` and `eventTime <` conditions.

3. **NEVER ingest all data events without selectors.** Ingesting every
   S3, Lambda, and DynamoDB data event generates enormous volume and
   cost. Use advanced event selectors to limit to specific resources
   and event names.

4. **NEVER assume queries are indexed.** CloudTrail Lake queries scan
   raw JSON. There is no index. Query performance and cost are
   proportional to data scanned.

5. **NEVER forget the separate query API.** The `cloudtrail-data` API
   (start-query, get-query-results) is DIFFERENT from the `cloudtrail`
   API (create-event-data-store, put-event-selectors). Different IAM
   permissions are needed.

6. **NEVER apply data protection without testing.** Once a data
   protection policy is applied, PII is masked in ALL queries
   permanently. Test with a non-production EDS first.

7. **NEVER set maximum retention without considering compliance.** A
   7-day retention may violate compliance requirements for audit log
   retention. Verify the minimum retention required by your framework.

8. **NEVER assume multi-account EDS is per-account selective.** Once
   `--organization-enabled` is set, the EDS ingests from ALL member
   accounts. There is no per-account inclusion/exclusion at the EDS
   level.

9. **NEVER confuse EDS billing with S3 billing.** EDS billing is per-
   GB ingested + per-GB scanned. S3 billing is per-GB stored + per-
   request. The cost models are fundamentally different.

10. **NEVER forget to cancel long-running queries.** Use
    `cancel-query` to stop expensive queries that scan too much data.
    Monitor query execution time.

## Output format

```text
CLOUDTRAIL_LAKE: <eds-name> (<eds-id>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Event data store: <eds-name> (<eds-id>)
  [✓|✗] Event type: Management | Data | Insights | Network
  [✓|✗] Advanced selectors: <selector summary> or "management events only"
  [✓|✗] Retention: <days> days (7-3653)
  [✓|✗] Multi-account: Organization EDS (all member accounts) | Single account
  [✓|✗] Data protection: <PII fields masked> or "none"
  [✓|✗] Query API: cloudtrail-data (StartQuery + GetQueryResults)
  [✓|✗] Athena federation: <enabled or "not configured">
  [✓|✗] CloudWatch alerting: <alarm name> or "none"
  [✓|✗] Billing: $X/GB ingested + $Y/GB scanned
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws cloudtrail list-event-data-stores
  aws cloudtrail-data start-query --query-statement "SELECT count(*) FROM <eds-id> WHERE eventTime > '...'"
  aws cloudtrail get-data-protection-policy --event-data-store-id <eds-id>
```

### Worked example — management events EDS with data protection

```text
CLOUDTRAIL_LAKE: mgmt-events-eds (arn:aws:cloudtrail:us-east-1:123456789012:eventdatastore/abc123)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Event data store: mgmt-events-eds (arn:aws:cloudtrail:us-east-1:123456789012:eventdatastore/abc123)
  [✓] Event type: Management events
  [✓] Advanced selectors: management events only (no data events)
  [✓] Retention: 90 days
  [✓] Multi-account: Organization EDS (5 member accounts)
  [✓] Data protection: EmailAddress, PhoneNumber masked
  [✓] Query API: cloudtrail-data (StartQuery + GetQueryResults)
  [✓] Athena federation: enabled (workgroup: ct-lake-wg)
  [✓] CloudWatch alerting: cloudtrail-lake-query-failures
  [✓] Billing: $0.75/GB ingested + $0.005/GB scanned
  [✓] Tags: Environment=production, Domain=security
VERIFICATION_COMMANDS:
  aws cloudtrail list-event-data-stores
  aws cloudtrail-data start-query --query-statement "SELECT count(*) FROM arn:aws:cloudtrail:us-east-1:123456789012:eventdatastore/abc123 WHERE eventTime > '2026-08-10T00:00:00Z'"
  aws cloudtrail get-data-protection-policy --event-data-store-id abc123
```

## Error handling

> Error-handling deep dives moved verbatim to [references/error-handling.md](references/error-handling.md) — load on demand.

## References (load on demand)

- [references/querying-and-forensics.md](references/querying-and-forensics.md) — StartQuery/GetQueryResults mechanics, time-window filtering, and the forensic query patterns (Step 6)
- [references/eds-and-multi-account.md](references/eds-and-multi-account.md) — EDS types and immutability, advanced selectors, multi-account org EDS (Step 7), retention, Athena federation + CloudWatch alerts (Step 10)
- [references/advanced-patterns.md](references/advanced-patterns.md) — configuration dependency graph, per-GB billing / raw-JSON scan / PII masking heuristics, billing cost model
- [references/error-handling.md](references/error-handling.md) — error-handling deep dives: empty queries, high query cost, masking, multi-account ingestion, EDS creation failures

## Domain

AWS CloudOps / CloudTrail Lake Event Data Store Provisioning &
Forensic SQL Query Analysis.

## AWS documentation

- **CloudTrail Lake** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake.html
- **Event data stores** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/eds-introduction.html
- **CloudTrail Lake queries** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/query-format.html
- **Advanced event selectors** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/filtering-data-events.html
- **Data protection** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/lake-data-protection.html
- **Multi-account EDS** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/organization-eventdata-store.html
- **CloudTrail Lake pricing** — https://aws.amazon.com/cloudtrail/pricing/
- **cloudtrail-data CLI** — https://docs.aws.amazon.com/cli/latest/reference/cloudtrail-data/
