# Eval prompt: read-only-filter

Diagnose the CloudTrail missing-events incident for the following
trail. Walk the symptom-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, ROOT_CAUSE, LAYER, EVIDENCE,
REMEDIATION).

Symptom: only write events (CreateBucket, RunInstances, PutObject)
are appearing in CloudTrail lookup-events. Read events (ListBuckets,
DescribeInstances, GetObject) are missing. The operator expects to
see all management events.

```text
TrailName: prod-audit-trail
IsMultiRegionTrail: true

get-trail-status --name prod-audit-trail:
  isLogging: true
  latestDeliveryTime: 2026-08-11T19:22:14Z
  (Wall clock: 2026-08-11T19:26:00Z — healthy delivery.)

get-event-selectors --trail-name prod-audit-trail:
  EventSelectors: [
    {
      "ReadWriteType": "WriteOnly",
      "IncludeManagementEvents": true,
      "DataResources": []
    }
  ]
  NOTE: ReadWriteType is "WriteOnly" — read events are excluded.

lookup-events for s3.amazonaws.com:ListBuckets (last 24h):
  { "Events": [] }

lookup-events for s3.amazonaws.com:CreateBucket (last 24h):
  Returns 14 events — write events are present.
```

The event selector's `ReadWriteType: WriteOnly` filters out
read-only operations (ListBuckets, DescribeInstances, GetObject).
The default is `All`. Identify the layer and the selector
remediation.
