# Athena Federation & Non-AWS Ingestion Reference

Load this reference when planning Athena federation on top of
CloudTrail Lake, cross-account or cross-Region analysis, non-AWS
event ingestion via PutAuditEvents, or QuickSight dashboards on top
of Athena. Covers the CloudTrailLake connector setup, Lake Formation
grants, the non-AWS Partner registration flow, and the QuickSight
service role trust.

## Athena CloudTrailLake federation

Athena federation lets you query CloudTrail Lake EDS via standard
Athena SQL, including cross-account and cross-Region analysis.

### Architecture

```
[Athena query] -> [Athena workgroup] -> [Lambda: CloudTrailLake connector]
                                            │
                                            ▼
                                    [CloudTrail Lake EDS]
                                            │
                                            ▼
                                      [KMS decrypt]
                                            │
                                            ▼
                                    [Results to S3]
```

The connector Lambda is deployed in the same Region as the EDS. The
Lambda issues a Lake query on the operator's behalf, paginates
results, and returns them to Athena as a federated row set.

### Connector deployment (one-time per Region)

```bash
# Deploy from Serverless Application Repository
aws serverlessrepo create-cloud-formation-change-set \
  --application-id arn:aws:serverlessrepo:us-east-1:296578776971:applications/AthenaCloudTrailLakeConnector \
  --stack-name athena-cloudtraillake-connector \
  --capabilities CAPABILITY_IAM \
  --parameters ParameterKey=AthenaCatalogName,ParameterValue=cloudtraillake

# Wait for stack CREATE_COMPLETE, then note the connector Lambda ARN
```

### Lake Formation grant (mandatory)

The connector Lambda's execution role needs Lake Formation permission
on the underlying EDS. Without this grant, federated queries return
`AccessDenied`.

```bash
aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::111111111111:role/AthenaCloudTrailLakeConnectorRole \
  --permissions SELECT \
  --resource '{ "LFTagPolicy": { "CatalogId": "111111111111", "ResourceType": "TABLE", "Expression": [{"TagKey": "cloudtraillake", "TagValues": ["org-governance-edS"]}] } }'
```

Or, for a simpler resource-based grant:

```bash
aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::111111111111:role/AthenaCloudTrailLakeConnectorRole \
  --permissions SELECT \
  --resource '{ "Database": {"CatalogId": "111111111111", "Name": "cloudtraillake"} }'
```

### Workgroup configuration

The Athena workgroup must have:
- An output S3 bucket for query results.
- A workgroup role that the connector can assume.
- The workgroup role must have `cloudtrail:GetQuery`,
  `cloudtrail:StartQuery`, `cloudtrail:GetQueryResults` on the EDS
  ARN.
- For SSE-KMS EDS: `kms:Decrypt` on the EDS KMS key.

### Cross-account / cross-Region patterns

For cross-account analysis (one account querying another's EDS):

1. Deploy the connector Lambda in the querying account.
2. Grant the connector role cross-account access to the EDS via
   Lake Formation resource link.
3. The connector role assumes a cross-account role that has
   `cloudtrail:StartQuery` on the target EDS.

For cross-Region analysis (query EDS in another Region):

1. Deploy connector Lambda instances in EACH Region you need to
   query.
2. The Athena query references each connector's Lambda ARN.

```sql
-- Cross-Region JOIN via two connectors
SELECT us_east_1.eventName, eu_west_1.eventName
FROM lambda:cloudtraillake_us_east_1.<eds-id-us-east-1> us_east_1
JOIN lambda:cloudtraillake_eu_west_1.<eds-id-eu-west-1> eu_west_1
  ON us_east_1.userIdentity.sessionId = eu_west_1.userIdentity.sessionId
WHERE us_east_1.eventTime >= date_add('day', -1, now())
  AND eu_west_1.eventTime >= date_add('day', -1, now())
```

### Cost

Federated query cost = Athena $5/TB scanned on the result set + Lake
$0.005/GB scanned on the underlying EDS. Federation overhead is the
Lambda marshalling; for small result sets it is negligible.

## Non-AWS event ingestion

### Architecture

```
[Partner SaaS app]
        │
        ▼
[Partner backend]
        │
        ▼
[PutAuditEvents API call] (signed by Partner IAM role)
        │
        ▼
[CloudTrail Lake EDS] (with EventCategory: non-AWS)
        │
        ▼
[Available in PartiQL queries]
```

### Partner registration flow

1. Operator selects a Partner from the CloudTrail Lake partner
   program (30+ as of 2026: CrowdStrike, Datadog, Splunk, Wiz,
   Okta, etc.).
2. Operator navigates to the Partner's UI and initiates the
   integration. The Partner calls AWS APIs to register an event
   source.
3. AWS creates a `PartnerEventSource` in the operator's account.
4. The operator attaches it to an EDS via `update-event-data-store`
   with `EventCategory: non-AWS`.
5. The Partner pushes events via `PutAuditEvents`.

The operator NEVER directly registers a Partner event source; the
Partner initiates. The operator only attaches the registered source
to an EDS.

### PutAuditEvents API

```bash
aws cloudtrail put-audit-events \
  --event-data-store arn:aws:cloudtrail:us-east-1:111111111111:event-data-store/eds-non-aws-001 \
  --audit-events \
    '[{"id":"evt-001","event-queue-time":"2026-08-10T22:00:00Z","event-queue-name":"partner-queue","event-payload":"{\"eventVersion\":\"1.0\",\"eventTime\":\"2026-08-10T21:55:00Z\",\"source\":\"partner.crowdstrike\",\"detailType\":\"Detection\",\"detail\":{\"severity\":\"HIGH\",\"description\":\"Suspicious process spawn\"}}"}]'
```

The caller must be a Partner IAM role with `cloudtrail:PutAuditEvents`
on the EDS ARN plus `kms:GenerateDataKey` on the EDS KMS key.

### EDS configuration for non-AWS

```bash
aws cloudtrail create-event-data-store \
  --name non-aws-audit-edS \
  --no-termination-protection-enabled \
  --kms-key-id arn:aws:kms:us-east-1:111111111111:key/non-aws-cmk \
  --retention-period 365 \
  --advanced-event-selectors '[{"Name": "non-AWS-events","FieldSelectors": [{"Field": "eventCategory","Equals": ["non-AWS"]}]}]'
```

The `eventCategory` filter MUST be `non-AWS`. The Partner event
source attaches at runtime; the EDS does not reference the Partner
by name in its config.

### Querying non-AWS events

Non-AWS events use the same Lake schema, with `eventSource` set to
the Partner namespace (e.g., `partner.crowdstrike`). `userIdentity`
reflects the Partner session.

```sql
SELECT eventTime, eventSource, eventName,
       additionalEventData.severity AS severity,
       additionalEventData.description AS description
FROM <eds-non-aws-id>
WHERE eventTime >= date_add('hour', -1, now())
  AND additionalEventData.severity = 'HIGH'
ORDER BY eventTime DESC
```

## QuickSight on top of Athena-on-Lake

QuickSight cannot query Lake directly. The canonical BI pattern:

1. Configure an Athena workgroup that federates to Lake via the
   connector (above).
2. Register the Athena workgroup as a QuickSight data source.
3. Create QuickSight datasets from the Athena workgroup's tables.
4. Build dashboards.

### QuickSight service role trust

The QuickSight service role must be allowed to assume the Athena
workgroup role:

```json
// Athena workgroup role trust policy
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "quicksight.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

The QuickSight service role must also have `athena:StartQueryExecution`,
`athena:GetQueryResults`, `athena:GetWorkGroup`, plus S3 read on the
Athena output bucket.

### Materialization pattern (for recurring analytics)

Direct QuickSight-on-Athena-on-Lake re-scans Lake on every dashboard
load. For recurring analytics, materialize via Athena CTAS:

```sql
-- In Athena, materialize a 7-day rollup to S3
CREATE TABLE materialized_logins_last_7d
WITH (format='parquet', location='s3://athena-results-111111111111/materialized/logins/')
AS
SELECT userIdentity.accountId, eventTime, sourceIpAddress
FROM lambda:cloudtraillake(<eds-id>)
WHERE eventTime >= date_add('day', -7, now())
  AND eventName = 'ConsoleLogin'
```

Then point QuickSight at the materialized Parquet. Re-materialize
nightly via a scheduled Lambda.

## Common failure modes (also in SKILL.md)

- Athena federated query returns `AccessDenied` — Lake Formation
  grant missing on the connector Lambda role. Add via
  `aws lakeformation grant-permissions`.
- `PutAuditEvents` returns `AccessDenied` — Partner role missing
  `cloudtrail:PutAuditEvents`. Attach the IAM policy. Or the
  Partner event source is not registered.
- QuickSight cannot connect — QuickSight role cannot assume Athena
  workgroup role. Add trust policy.
- Federated query is slow — same partition-or-perish rule applies;
  ensure the SQL includes `eventTime` filter.

## AWS documentation pointers

- Athena CloudTrail Lake connector — https://docs.aws.amazon.com/athena/latest/ug/cloudtrail-lake.html
- Athena federation overview — https://docs.aws.amazon.com/athena/latest/ug/connect-to-a-data-source.html
- CloudTrail Lake non-AWS events — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/query-non-aws-events.html
- CloudTrail Lake partners — https://aws.amazon.com/cloudtrail/partners/
- QuickSight + Athena — https://docs.aws.amazon.com/quicksight/latest/user/create-a-data-source-athena.html
- Lake Formation grants — https://docs.aws.amazon.com/lake-formation/latest/dg/granting-table-permissions.html
