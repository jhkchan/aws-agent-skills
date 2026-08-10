# Eval prompt: s3-data-events-not-configured

Diagnose the following CloudTrail gap. Walk the MISSING_DATA_EVENTS
diagnostic tree and emit the standard VERDICT block (INCIDENT, VERDICT,
ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

An operator on AWS expects to see S3 `GetObject` events in CloudTrail
for audit purposes. The trail is `corp-trail`. The account is
`111111111111`.

## Known facts

- `aws cloudtrail lookup-events --lookup-attributes
  AttributeKey=EventName,AttributeValue=GetObject` returns **0
  results** for the past 24 hours.
- `aws cloudtrail lookup-events --lookup-attributes
  AttributeKey=EventName,AttributeValue=CreateBucket` returns 4
  results for the past 24 hours (management events are flowing).
- `aws cloudtrail describe-trails --trail-name-list corp-trail` shows:
  - `IsMultiRegionTrail: true`
  - `IsOrganizationTrail: false`
  - `IsLogging: true`
  - `S3BucketName: corp-trail-logs`
  - `HomeRegion: us-east-1`
- `aws cloudtrail get-trail-status --name corp-trail` shows:
  - `IsLogging: true`
  - `LatestDeliveryTime: 2026-08-10T...` (recent, healthy)
- `aws cloudtrail get-event-selectors --trail-name corp-trail` returns:
  ```json
  [{"ReadWriteType":"All","IncludeManagementEvents":true,"DataResources":[]}]
  ```

## Symptom

The operator expects S3 GetObject events to be captured by CloudTrail
for security audit. Management events (CreateBucket, PutBucketPolicy)
appear in lookup-events; data events (GetObject) do not.
