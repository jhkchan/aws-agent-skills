# Eval prompt: trail-logging-disabled

Diagnose the CloudTrail missing-events incident for the following
trail. Walk the symptom-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, ROOT_CAUSE, LAYER, EVIDENCE,
REMEDIATION).

Symptom: the security team reports zero CloudTrail events for
`prod-audit-trail` since 14:00 UTC yesterday. The trail was created
correctly via the AWS CLI but `get-trail-status` returns
`IsLogging: false`. No StopLogging CloudTrail event was found — the
trail was never started after creation.

```text
TrailName: prod-audit-trail
HomeRegion: us-east-1
IsMultiRegionTrail: true

get-trail-status --name prod-audit-trail:
  isLogging: false
  latestDeliveryTime: null
  startLoggingTime: null
  stopLoggingTime: null

lookup-events for StopLogging in last 7 days:
  { "Events": [] }
  No StopLogging event found — the trail was never started.

describe-trails output (excerpt):
  Name: prod-audit-trail
  S3BucketName: prod-cloudtrail-logs
  IsMultiRegionTrail: true
  IncludeGlobalServiceEvents: true
  KmsKeyId: null

s3 ls s3://prod-cloudtrail-logs/AWSLogs/111111111111/CloudTrail/:
  (empty — no log files have ever been delivered)
```

The trail was created but never started. Identify the layer and the
remediation to prevent recurrence.
