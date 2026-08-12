# Eval prompt: data-events-not-enabled

Diagnose the CloudTrail missing-events incident for the following
trail. Walk the symptom-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, ROOT_CAUSE, LAYER, EVIDENCE,
REMEDIATION).

Symptom: `prod-audit-trail` has `IsLogging: true` and management
events are delivering on schedule, but the operator expects S3
GetObject events — `lookup-events` for `s3.amazonaws.com:GetObject`
returns zero results in the last 24 hours. Management events
(ListBuckets, CreateBucket) are present.

```text
TrailName: prod-audit-trail
IsMultiRegionTrail: true

get-trail-status --name prod-audit-trail:
  isLogging: true
  latestDeliveryTime: 2026-08-11T19:22:14Z
  (Wall clock: 2026-08-11T19:26:00Z — healthy.)

get-event-selectors --trail-name prod-audit-trail:
  EventSelectors: [
    {
      "ReadWriteType": "All",
      "IncludeManagementEvents": true,
      "DataResources": []
    }
  ]
  NOTE: DataResources is empty — no data-plane events captured.

lookup-events for s3.amazonaws.com:GetObject (last 24h):
  { "Events": [] }

lookup-events for s3.amazonaws.com (last 24h):
  Returns ListBuckets, CreateBucket, PutBucketPolicy —
  management events present; only data-plane events missing.
```

Management events are default-on but data events (S3 GetObject,
Lambda InvokeFunction) are opt-in. A trail with default event
selectors captures ZERO data-plane API calls.
