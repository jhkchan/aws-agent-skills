# Worked Examples — cloudtrail-lake-operator

## Worked example — diagnose-empty-query (BLOCKED with fix)

```text
OPERATION: diagnose-empty-query
VERDICT: BLOCKED
TARGET: EDS org-governance-edS (region: us-east-1)
        (query: SELECT userIdentity.accountId, eventName, COUNT(*)
         FROM edS WHERE eventTime >= '2026-08-01' AND eventSource =
         's3.amazonaws.com' GROUP BY userIdentity.accountId, eventName)
PRE_CHECKS:
  - [PASS] EDS exists, Status: ENABLED
  - [PASS] SQL syntactically valid
  - [PASS] SQL references Lake-supported columns
  - [FAIL] EDS EventCategory list: [Management] only. The query
    filters on eventSource = 's3.amazonaws.com' for S3 data events,
    which require the Data category. Management events only include
    S3 control-plane APIs (CreateBucket, etc.), not object-level
    GetObject/PutObject.
  - [PASS] SQL includes eventTime partition filter
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
NOTES:
  - Root cause: the EDS "org-governance-edS" was created with
    EventCategory: Management only. The query expects S3 object-level
    data events (GetObject, PutObject, etc.) which require
    EventCategory: Data. The Management category only includes
    S3 control-plane events (CreateBucket, DeleteBucket, etc.).
  - Fix: update the EDS to add the Data category:
    aws cloudtrail update-event-data-store \
      --event-data-store arn:aws:cloudtrail:us-east-1:111111111111:event-data-store/eds-001 \
      --advanced-event-selectors file:///tmp/selectors-with-data.json
    New events arriving after the update will include Data events.
    Historical events before the update are NOT backfilled.
  - If you only need Management events, fix the query instead:
    drop the eventSource = 's3.amazonaws.com' filter or change it
    to target Management-only sources like
    'cloudtrail.amazonaws.com'.
```

## Worked example — federate-via-athena (COMPLETED)

```text
OPERATION: federate-via-athena
VERDICT: COMPLETED
TARGET: EDS org-governance-edS (region: us-east-1) federated via
        Athena workgroup gov-analytics
        (query: cross-account correlation of IAM API calls)
PRE_CHECKS:
  - [PASS] Athena workgroup gov-analytics exists, state ENABLED
  - [PASS] CloudTrailLake connector Lambda deployed in us-east-1
  - [PASS] Lake Formation grant: connector Lambda role has SELECT
    on the underlying EDS
  - [PASS] Athena workgroup role has cloudtrail:GetQuery,
    cloudtrail:StartQuery, cloudtrail:GetQueryResults on EDS
  - [PASS] Athena workgroup role has kms:Decrypt on edS-cmk
STEPS:
  1. CONFIRM: About to run a federated Athena query against
     org-governance-edS via the CloudTrailLake connector in
     workgroup gov-analytics. Output goes to
     s3://athena-results-111111111111/gov/. Athena + Lake scan
     costs apply. Proceed? (yes/no)
  2. aws athena start-query-execution \
       --query-string "SELECT userIdentity.accountId, eventName, eventTime FROM lambda:cloudtraillake(org-governance-edS) WHERE eventTime >= date_add('day', -7, now()) AND eventName IN ('AssumeRole','ConsoleLogin') ORDER BY eventTime DESC LIMIT 1000" \
       --work-group gov-analytics \
       --result-configuration OutputLocation=s3://athena-results-111111111111/gov/
  3. aws athena get-query-results --query-execution-id <exec-id>
POST_VERIFY:
  - [PASS] Athena QueryExecution State: SUCCEEDED
  - [PASS] Result rows: 842 (within expected 500-1500 band)
  - [PASS] Athena DataScannedInBytes: 4.2 GB (within 1-10 GB bound)
  - [PASS] Lake describe-query QueryStatus: FINISHED, BytesScanned
    3.9 GB (close to Athena DataScanned; federation overhead small)
  - [PASS] Output object exists at
    s3://athena-results-111111111111/gov/<exec-id>.csv
  - [PASS] Spot-check 3 rows: userIdentity.accountId, eventName,
    eventTime match raw Lake query
NOTES:
  - Federated query cost = Athena $5/TB * 0.0042 TB + Lake
    $0.005/GB * 3.9 GB ~= $0.02 + $0.019 = $0.04 total. Federation
    overhead is small.
  - For recurring analytics, consider materializing results to S3
    via CTAS (CREATE TABLE AS SELECT) in Athena, then point
    QuickSight at the materialized table to avoid re-scanning Lake.
  - The CloudTrailLake connector Lambda runs in the same Region as
    the EDS. For multi-Region federation, deploy connector
    instances in each Region.
```
