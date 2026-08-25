# Advanced Patterns — cloudtrail-lake-query-deployer

## Configuration dependency graph (novel heuristic)

CloudTrail Lake configurations are NOT independent. The EDS must exist
before events are ingested. Ingestion type must be decided before
creating the EDS (cannot be changed after creation for some types).
Data protection must be configured before queries return results. Use
this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Event data store (EDS) | None (creates an empty store) | EDS type (management, data, insight, network) CANNOT be changed after creation | event ingestion, querying |
| Event ingestion | EDS exists; CloudTrail enabled in account | ingestion starts automatically for management events; data events need advanced selectors | queryable events |
| Advanced event selectors | EDS exists; data event ingestion enabled | selectors filter which data events are stored; overly broad selectors increase ingestion cost | filtered data events |
| SQL query | EDS exists; events ingested | query scans raw JSON; cost proportional to data scanned; time filter reduces cost | query results |
| Multi-account EDS | Organizations enabled; management account | EDS in management account ingests from all member accounts | org-wide querying |
| Retention | EDS exists | retention period 7-3653 days; set at creation, can be updated; shorter retention = less storage cost | data lifecycle |
| Data protection | EDS exists | policy masks PII fields before query results; original values inaccessible via queries | compliance |
| Athena federation | EDS exists; Athena workgroup configured | Athena queries the EDS via a Lake Formation integration | Athena-based analysis |

**The EDS-type-immutability row is the one a baseline model misses.**
When creating an EDS, you choose what type of events to ingest
(management, data, Insights, network). This type CANNOT be changed
after creation. If you need to add data events to a management-only
EDS, you must create a new EDS. The procedure below forces an explicit
event-type decision.

**Cross-dependency gotchas:**
- Management events are ingested automatically once the EDS is created.
  Data events require advanced event selectors to specify which
  resources generate data events.
- The billing model is per-GB ingested PLUS per-GB scanned by queries.
  Broad data event ingestion (e.g., all S3 GetObject) generates
  enormous volume. Use advanced selectors to limit to specific buckets
  or event types.
- Multi-account EDS ingests from ALL member accounts automatically once
  Organizations integration is configured. There is no per-account
  selector at ingestion time.
- Data protection policies operate on the EDS. Once applied, ALL queries
  against that EDS have PII masked. There is no per-query bypass.

## Expert heuristic: per-GB billing model

A baseline model may not understand the CloudTrail Lake billing model.
The correct heuristic recognizes two separate charges: ingestion and
query scanning.

```text
EDS billing:
  1. Ingestion: $X per GB ingested (events written to the EDS)
     → Management events: ~0.008 GB per million events
     → Data events: varies (S3, Lambda, DynamoDB)
     → Network events: large volume (VPC Flow Log style)

  2. Query scan: $Y per GB scanned by queries
     → Each query scans the raw JSON events in the time range
     → Narrowing time range reduces scanned data
     → No indexes = full scan within the time range

Cost optimization:
  → Use advanced selectors to limit data events (don't ingest all S3)
  → Always specify time range in queries (don't scan all history)
  → Use partitioning hints where available
```

**Key implication:** the dominant cost for data-event EDS is ingestion.
The dominant cost for management-event EDS is query scanning (if queries
are frequent). Both costs must be considered.

## Expert heuristic: queries scan raw JSON, not indexes

A baseline model may assume CloudTrail Lake uses a search index. The
correct heuristic recognizes that queries perform full scans of raw
JSON events within the specified time range.

```text
Query: SELECT * FROM eds-id WHERE eventName = 'DeleteBucket'
  → Scans ALL events in the time range
  → No index on eventName
  → Time range = primary cost lever

Optimal query:
  SELECT userIdentity.arn, eventName, eventTime, sourceIPAddress
  FROM <eds-id>
  WHERE eventTime > '2026-08-10T00:00:00Z'
    AND eventTime < '2026-08-11T00:00:00Z'
    AND eventName = 'DeleteBucket'
  → Scans only events in the 24-hour window
  → Much cheaper than scanning 90 days
```

## Expert heuristic: data protection masks PII before results

A baseline model may treat data protection as a display filter. The
correct heuristic recognizes that masking happens at the EDS level,
before query results are returned.

```text
Without data protection policy:
  Query: SELECT * FROM eds-id WHERE eventName = 'AssumeRole'
  Result: {"userIdentity": {"arn": "arn:aws:iam::123:user/dev@corp.com", ...}}
  → Full email visible

With data protection policy (mask emailAddress):
  Query: SELECT * FROM eds-id WHERE eventName = 'AssumeRole'
  Result: {"userIdentity": {"arn": "arn:aws:iam::123:user:****", ...}}
  → Email masked in ALL queries, permanently
```

## Billing model

| Charge | Rate (approximate) | Notes |
|---|---|---|
| Ingestion | ~$0.75/GB ingested | Management events: low volume; Data events: varies |
| Query scan | ~$0.005/GB scanned | Proportional to time range queried |

**Cost estimation:**

```text
Management events:
  ~0.008 GB per million events
  1M events/day → 0.24 GB/month → ~$0.18/month ingestion
  Query scanning 30 days: ~7.2 GB → ~$0.04 per full-scan query

Data events (S3 GetObject on all buckets):
  ~0.001 KB per event → 1B events = 1 GB
  Heavy S3 usage → 10 GB/day → ~$225/month ingestion
  → Use advanced selectors to reduce!
```
