# Example usage: cloudtrail-missing-events-troubleshooter

A walkthrough showing the skill diagnosing a "CloudTrail events are
missing" incident that initially looks like a generic trail outage,
demonstrating the symptom-to-layer triage, the management-vs-data
events opt-in trap, the evidence-backed ROOT_CAUSE_IDENTIFIED
verdict, and the event-selector remediation.

## Input (user prompt)

> Our security team is investigating an S3 data exfiltration
> incident. They need the S3 GetObject events from account
> 222222222222 over the last 24 hours — but CloudTrail
> `lookup-events` returns zero results. Management events
> (ListBuckets, CreateBucket) ARE present. We've been told
> "CloudTrail captures everything" — help us figure out why the
> GetObject events are missing.

```text
TrailName: prod-audit-trail
IsMultiRegionTrail: true

aws cloudtrail get-trail-status --name prod-audit-trail:
  isLogging: true
  latestDeliveryTime: 2026-08-11T19:22:14Z
  (Wall clock: 2026-08-11T19:26:00Z — healthy.)

aws cloudtrail get-event-selectors --trail-name prod-audit-trail:
  EventSelectors: [
    {
      "ReadWriteType": "All",
      "IncludeManagementEvents": true,
      "DataResources": []
    }
  ]

aws cloudtrail lookup-events
  --lookup-attributes AttributeKey=EventSource,AttributeValue=s3.amazonaws.com
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject
  --start-time $(date -d '-24 hours' +%s) --end-time $(date +%s):
  { "Events": [] }

(S3 access logs for the target bucket confirm GetObject calls ARE
happening — they just are not in CloudTrail.)
```

## Skill output

```text
TARGET: prod-audit-trail
VERDICT: ROOT_CAUSE_IDENTIFIED
ROOT_CAUSE: Trail has IsLogging: true and management events are
  delivering on schedule, but the operator expects S3 GetObject
  events — and the trail's event selector has no DataResources
  configured for AWS::S3::Object. Data events are opt-in; the
  default event selector captures only management events. The
  "CloudTrail captures everything" assumption is incorrect for
  data-plane API calls.
LAYER: DATA_EVENTS_NOT_ENABLED
EVIDENCE:
  - Symptom: lookup-events for s3.amazonaws.com:GetObject in the
    last 24 hours returns zero results; management events
    (ListBuckets, CreateBucket, PutBucketPolicy) are present.
  - Probe: get-event-selectors --trail-name prod-audit-trail
    returns EventSelectors: [{ReadWriteType: All,
    IncludeManagementEvents: true}] — no DataResources array.
    S3 data-plane events are not being captured.
  - Passing: get-trail-status returns IsLogging: true,
    LatestDeliveryTime: 4 minutes ago (trail is healthy);
    describe-trails returns IsMultiRegionTrail: true (no scope
    gap); bucket policy includes the cloudtrail.amazonaws.com
    principal (no delivery block).
REMEDIATION:
  1. Add S3 data events to the trail's event selector. For ALL
     buckets:
     aws cloudtrail put-event-selectors --trail-name prod-audit-trail \
       --event-selectors '[{
         "ReadWriteType": "All",
         "IncludeManagementEvents": true,
         "DataResources": [{
           "Type": "AWS::S3::Object",
           "Values": ["arn:aws:s3:::"]
         }]
       }]'
  2. Verify with lookup-events 10-15 minutes after the change.
  3. For the ongoing investigation: S3 server access logs are the
     only source of GetObject events for the window before the
     event selector is updated.
CONFIRM: Before updating the event selector, emit and await:
  "CONFIRM: About to enable S3 data events on prod-audit-trail.
   Data events are billed at $0.10 per 100,000 events. Proceed?
   (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **Distinguished management events from data events.** A generic
   assistant says "CloudTrail captures everything." The skill
   recognises that management events are default-on but data events
   (GetObject, InvokeFunction) are opt-in.

2. **Identified the empty DataResources array.** The skill reads
   `get-event-selectors` and notes that `DataResources: []` — no
   data-plane events are being captured.

3. **Ruled out trail health with positive evidence.** The skill's
   `IsLogging: true`, `LatestDeliveryTime: 4 minutes ago`, and
   bucket-policy checks rule out trail-side causes before
   diagnosing the selector-side cause.

4. **Flagged the cost impact.** Data events are billed at $0.10 per
   100,000 events. The CONFIRM gate names the cost explicitly.

5. **Recommended the S3 access log fallback for the investigation.**
   Enabling data events now does NOT backfill events — S3 access
   logs are the only source for the investigation window.

## Slash-command invocation

```
/aws:troubleshoot-cloudtrail-missing-events
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why prod-audit-trail is missing S3 GetObject events"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: cloudtrail-missing-events-troubleshooter]`
and hands off to this skill for the diagnostic block.
