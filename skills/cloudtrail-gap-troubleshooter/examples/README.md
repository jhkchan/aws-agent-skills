# End-to-end usage scenario: cloudtrail-gap-troubleshooter

A walkthrough showing the skill diagnosing a CloudTrail gap where S3
GetObject events are missing because data events were never
configured. This exercises Step 1 (symptom identification), Step 2
(MISSING_DATA_EVENTS), and the remediation workflow.

## Input (user prompt)

> My `corp-trail` is multi-region and shows IsLogging: true. I made
> several S3 GetObject calls today for audit, but `lookup-events`
> returns zero GetObject events. CreateBucket events show up fine.
> `get-event-selectors` returns
> `[{"ReadWriteType":"All","IncludeManagementEvents":true,
> "DataResources":[]}]`.

## Skill output

```text
INCIDENT: 111111111111 / corp-trail — operator expects GetObject
events for audit; lookup-events returns 0 GetObject events
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: MISSING_DATA_EVENTS — trail's event selectors have empty
DataResources; only management events are logged
EVIDENCE:
  - describe-trails: corp-trail IsMultiRegionTrail: true,
    IsLogging: true, HomeRegion: us-east-1 (trail is healthy and
    in scope)
  - get-trail-status: IsLogging: true, LatestDeliveryTime recent
    (delivery is working)
  - get-event-selectors:
    [{"ReadWriteType":"All","IncludeManagementEvents":true,
      "DataResources":[]}]
    (empty DataResources = no data events configured)
  - lookup-events CreateBucket: 4 results in last 24h (management
    events flowing)
  - lookup-events GetObject: 0 results in last 24h (data events
    absent, as expected with empty DataResources)
ROOT_CAUSE_CATALOG: #1 (data events not configured)
REMEDIATION:
  1. Add an S3 data event selector scoped to the audit bucket
     (recommended: scope by ARN prefix to control cost):
     aws cloudtrail put-event-selectors --trail-name corp-trail \
       --event-selectors '[{"ReadWriteType":"All","IncludeManagementEvents":true,"DataResources":[{"Type":"AWS::S3::Object","Values":["arn:aws:s3:::audit-bucket/"]}]}]'
     Note: for per-bucket scoping or read/write filtering, use
     --advanced-event-selectors instead.
  2. Verify by making a test S3 read and checking lookup-events in
     5-15 minutes:
     aws s3 cp s3://audit-bucket/test . && \
     aws cloudtrail lookup-events \
       --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
       --start-time $(date -u -v-20M +%Y-%m-%dT%H:%M:%SZ)
  3. Monitor CloudTrail billing — S3 data events on a busy bucket
     can multiply costs 10-100x. If cost is a concern, use
     --advanced-event-selectors with WriteOnly filtering or a tighter
     ARN prefix.
```

## What the skill caught that a generic assistant misses

1. **The data-events-vs-management-events distinction.** A generic
   assistant correctly identifies "you need data events" but does not
   cross-reference the existing `get-event-selectors` output to
   confirm the diagnosis. The skill walks the operator through the
   exact selector check and shows the empty `DataResources` as
   evidence.

2. **The cost-warning callout.** A generic assistant rarely mentions
   that enabling data events can 10-100x the CloudTrail bill. The
   skill scopes the recommendation to a specific bucket prefix
   (`arn:aws:s3:::audit-bucket/`) and offers advanced event selectors
   for finer control.

3. **The verification loop.** A generic assistant says "wait 15
   minutes and check." The skill gives the exact verification command
   (test S3 read + lookup-events with explicit start-time) so the
   operator can confirm the fix end-to-end.

4. **The put-event-selectors command.** A generic assistant often
   points to the console. The skill provides the exact CLI command
   with the canonical JSON selector structure, ready to copy-paste.

## Slash-command invocation

```
/aws:troubleshoot-cloudtrail-gap
```

Or via the orchestrator:

```
/aws:pipeline
You: "CloudTrail corp-trail missing S3 GetObject events"
```

The orchestrator emits `[Phase: Troubleshoot | Skills routed:
cloudtrail-gap-troubleshooter]` and hands off to this skill for the
VERDICT.

## Live-account diagnostic flow (requires AWS CLI)

When the operator has credentials:

```bash
# Confirm the trail is healthy.
aws cloudtrail describe-trails --trail-name-list corp-trail \
  --query 'trailList[0].{name:Name,multi:IsMultiRegionTrail,logging:IsLogging,s3:S3BucketName,kms:KmsKeyId}'

aws cloudtrail get-trail-status --name corp-trail \
  --query '{isLogging:IsLogging,latestDelivery:LatestDeliveryTime}'

# Confirm data events are not configured (the smoking gun).
aws cloudtrail get-event-selectors --trail-name corp-trail

# Confirm management events ARE flowing.
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateBucket \
  --start-time $(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ) \
  --max-results 3

# Confirm the missing event is a data event.
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
  --start-time $(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ) \
  --max-results 3

# Apply the fix.
aws cloudtrail put-event-selectors --trail-name corp-trail \
  --event-selectors '[{"ReadWriteType":"All","IncludeManagementEvents":true,"DataResources":[{"Type":"AWS::S3::Object","Values":["arn:aws:s3:::audit-bucket/"]}]}]'

# Verify.
aws s3 cp s3://audit-bucket/cloudtrail-test /tmp/ && \
  sleep 600 && \
  aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
    --start-time $(date -u -v-15M +%Y-%m-%dT%H:%M:%SZ) \
    --max-results 5
```

The empty `DataResources` array plus flowing management events is
the pathognomonic signature of MISSING_DATA_EVENTS — no further
investigation needed before applying the fix.
