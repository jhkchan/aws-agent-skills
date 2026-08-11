# End-to-end usage scenario: cloudtrail-lake-operator

A walkthrough showing the skill planning a create-eds operation for
an organization-scoped CloudTrail management event store with SSE-KMS,
with all pre-checks passing and the operator confirming at the
CONFIRM gate. Contrasted with the BLOCKED case where a query for S3
data events returns zero rows because the EDS was created with
EventCategory: Management only.

## Input (user prompt)

> We need a CloudTrail Lake EDS for governance audit covering all
> accounts in our AWS Organization `o-abc123def`. The EDS should
> ingest management events, retain them for 1 year, and use our
> customer-managed KMS key `edS-cmk`. Region: us-east-1.

```json
{
  "Operation": "create-eds",
  "Name": "org-governance-edS",
  "Region": "us-east-1",
  "OrganizationScope": true,
  "EventCategory": ["Management"],
  "RetentionPeriodDays": 365,
  "KmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/edS-cmk",
  "CallerIsManagementAccount": true
}
```

## Skill output

```text
OPERATION: create-eds
VERDICT: READY
TARGET: new EDS "org-governance-edS" (region: us-east-1,
          ingestion: Management events, organization scope)
PRE_CHECKS:
  - [PASS] Caller is the management account 111111111111
  - [PASS] --retention-period 365 within [90, 3653]
  - [PASS] --kms-key-id arn:aws:kms:us-east-1:111111111111:key/edS-cmk
    exists, key policy grants cloudtrail.amazonaws.com
    kms:GenerateDataKey + kms:Decrypt
  - [PASS] AdvancedEventSelectors reference Management category
  - [PASS] --is-organization-service: AWS Organizations access for
    CloudTrail is enabled
  - [PASS] --termination-protection-enabled: true (default)
STEPS:
  1. CONFIRM: About to create organization-scoped Event Data Store
     "org-governance-edS" in account 111111111111 region us-east-1.
     Ingests Management events for ALL accounts in org o-abc123def.
     Retention: 365 days. SSE-KMS with key edS-cmk. First-day
     ingestion: ~5-50M events depending on activity. Proceed?
     (yes/no)
  2. aws cloudtrail create-event-data-store \
       --name org-governance-edS \
       --kms-key-id arn:aws:kms:us-east-1:111111111111:key/edS-cmk \
       --retention-period 365 \
       --termination-protection-enabled \
       --is-organization-service \
       --advanced-event-selectors file:///tmp/selectors.json
  3. aws cloudtrail list-event-data-stores --name-suffix org-governance-edS
POST_VERIFY: (pending execution)
NOTES:
  - This EDS ingests Management events from ALL member accounts in
    org o-abc123def. For S3 object-level data events you need a
    SEPARATE EDS (or update this EDS) with EventCategory: Data.
  - Cost estimate at 25M events/day: ~$25/day ingestion +
    ~$0.05/GB-month storage. Lake Formation grants required for any
    downstream reader.
  - The KMS key policy MUST list cloudtrail.amazonaws.com — without
    it, ingestion silently fails. Verify with
    aws kms get-key-policy --key-id edS-cmk --policy-name default.
  - This EDS is org-scoped; member accounts CANNOT create their own
    org EDS. Member-account standalone EDS for their own events is
    still allowed.
```

## Contrast — BLOCKED case (EDS EventCategory mismatch)

If the operator then runs a query filtering on
`eventSource = 's3.amazonaws.com'` expecting object-level GetObject
events, the pre-check gate fires and surfaces that the EDS only
captures Management events. No fix CLI executes:

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
    EventCategory: Data.
  - Fix: update the EDS to add the Data category:
    aws cloudtrail update-event-data-store \
      --event-data-store arn:aws:cloudtrail:us-east-1:111111111111:event-data-store/eds-001 \
      --advanced-event-selectors file:///tmp/selectors-with-data.json
    New events arriving after the update will include Data events.
    Historical events before the update are NOT backfilled.
```

## What the skill caught that a generic assistant misses

1. **Regional vs global confusion.** A generic assistant may suggest
   cross-Region queries without surfacing that Lake is Regional.
   The skill surfaces the Region alignment pre-check.

2. **EventCategory mismatch.** A generic assistant assumes zero
   rows means "no events" and suggests widening the time window.
   The skill reads the EDS config and identifies that Management
   events do not include S3 object-level data events.

3. **Organization scope.** A generic assistant omits the
   `--is-organization-service` flag check. The skill confirms the
   caller is the management account and Organizations access is
   enabled before recommending creation.

4. **KMS key policy vs IAM.** A generic assistant verifies the IAM
   role and stops. The skill checks the destination KMS key policy
   separately — IAM alone is not sufficient for SSE-KMS EDS.

5. **Cost estimate.** A generic assistant emits the CLI without
   cost framing. The skill surfaces the ingestion + storage cost
   band for the operator's expected event volume.

6. **Partition pruning signal.** For any query, the skill surfaces
   `PARTITION_PRUNING: <verified | missing>`. A generic assistant
   never flags the missing-eventTime-filter case.

7. **Backfill limitation.** A generic assistant implies that adding
   the Data category recovers historical data events. The skill
   explicitly notes that only NEW events after the update are
   captured; historical events are NOT backfilled.

## Slash-command invocation

```
/aws:operate-cloudtrail-lake
```

Or via the orchestrator:

```
/aws:pipeline
You: "create a cloudtrail lake eds for org governance audit"
```

The orchestrator emits
`[Phase: Operate | Skills routed: cloudtrail-lake-operator]` and
hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "create cloudtrail lake eds for management events"
# [Phase: Operate | Skills routed: cloudtrail-lake-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the EDS is created:

```bash
# Smoke-test query: top 10 events in the last hour
QUERY_ID=$(aws cloudtrail start-query \
  --query-statement "SELECT eventName, COUNT(*) AS cnt FROM eds-001 WHERE eventTime >= date_add('hour', -1, now()) GROUP BY eventName ORDER BY cnt DESC LIMIT 10" \
  --query-statement-encoding UTF-8 \
  --output text --query QueryId \
  --profile default)

# Poll until FINISHED
for i in $(seq 1 60); do
  STATUS=$(aws cloudtrail describe-query \
    --event-data-store arn:aws:cloudtrail:us-east-1:111111111111:event-data-store/eds-001 \
    --query-id "$QUERY_ID" \
    --query QueryStatus --output text --profile default)
  if [ "$STATUS" = "FINISHED" ] || [ "$STATUS" = "FAILED" ]; then
    echo "Terminal: $STATUS"
    break
  fi
  sleep 10
done

# Fetch results
aws cloudtrail get-query-results \
  --event-data-store arn:aws:cloudtrail:us-east-1:111111111111:event-data-store/eds-001 \
  --query-id "$QUERY_ID" \
  --profile default

# CloudWatch alarm on query latency
aws cloudwatch put-metric-alarm \
  --alarm-name cloudtrail-lake-slow-query \
  --namespace CloudTrail/Lake \
  --metric-name QueryRunTimeInSeconds \
  --threshold 300 --comparison-operator GreaterThanThreshold \
  --period 300 --evaluation-periods 1 \
  --profile default

# Configure Athena federation (one-time per Region)
aws serverlessrepo create-cloud-formation-change-set \
  --application-id arn:aws:serverlessrepo:us-east-1:296578776971:applications/AthenaCloudTrailLakeConnector \
  --stack-name athena-cloudtraillake-connector \
  --capabilities CAPABILITY_IAM \
  --parameters ParameterKey=AthenaCatalogName,ParameterValue=cloudtraillake
```
