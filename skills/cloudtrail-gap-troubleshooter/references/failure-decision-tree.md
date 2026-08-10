# CloudTrail Gap Failure Decision Tree — Reference

Supplementary reference for the CloudTrail Gap Troubleshooter skill.
Walks the full symptom-to-cause tree with worked examples per category.

## Logging pipeline and where each failure category strikes

```
   API call in account
        │
        ▼
   CloudTrail service captures event
        │
        ├── management event? ──► included by default
        │
        ├── data event? ──► [A] MISSING_DATA_EVENTS
        │                     └── no DataResources configured
        │
        ├── in trail's region?
        │   ├── NO (single-region trail) ──► [F] MULTI_REGION_GAP
        │   └── YES ──► continue
        │
        ├── org trail covers this account?
        │   ├── NO (member not in org or shadow stopped) ──► [E] ORG_TRAIL_GAP
        │   └── YES ──► continue
        │
        ▼
   CloudTrail delivers to S3 (~5 min latency, max 15 min)
        │
        ├── isLogging: false? ──► [B] TRAIL_NOT_LOGGING
        │
        ├── bucket policy blocks PutObject? ──► [G] BUCKET_POLICY_BLOCKING
        │
        ├── KMS key policy blocks GenerateDataKey? ──► [G] BUCKET_POLICY_BLOCKING
        │
        ├── delivery > 15 min late? ──► [C] DELIVERY_DELAYED
        │
        ▼
   S3 log file lands
        │
        ▼
   Insights analyzes write mgmt events (7-day baseline)
        │
        ├── Insights disabled? ──► [D] INSIGHTS_DISABLED
        │
        ├── baseline not yet established? ──► [D] INSIGHTS_DISABLED
        │
        ▼
   Insights finding emitted to CloudTrail-Insight/ S3 prefix
```

Category letters map to the steps in SKILL.md:

- A = MISSING_DATA_EVENTS (Step 2)
- B = TRAIL_NOT_LOGGING (Step 3)
- C = DELIVERY_DELAYED (Step 4)
- D = INSIGHTS_DISABLED (Step 5)
- E = ORG_TRAIL_GAP (Step 6)
- F = MULTI_REGION_GAP (Step 7a)
- G = BUCKET_POLICY_BLOCKING (Step 7b)

**Rule:** when multiple categories apply, resolve in pipeline order. A
stopped trail (B) produces zero events, so no point diagnosing A or D
until logging is restored.

## Category A: MISSING_DATA_EVENTS

The trail is logging management events but not data events.

### Worked example — S3 GetObject missing

**Symptom:** operator runs `aws s3 cp s3://my-bucket/secret .` and
expects to see a `GetObject` event in CloudTrail. `lookup-events` for
`EventName=GetObject` returns zero results. Management events
(`CreateBucket`, `PutBucketPolicy`) appear normally.

**Walk:**

1. `aws cloudtrail describe-trails --trail-name-list corp-trail`:
   `IsMultiRegionTrail: true`, `IsLogging: true` (trail is healthy).
2. `aws cloudtrail get-event-selectors --trail-name corp-trail`:
   ```json
   [{"ReadWriteType":"All","IncludeManagementEvents":true,
     "DataResources":[]}]
   ```
   `DataResources` is empty — no data events are configured.
3. `aws cloudtrail lookup-events --lookup-attributes
   AttributeKey=EventName,AttributeValue=GetObject`: 0 results.
4. `aws cloudtrail lookup-events --lookup-attributes
   AttributeKey=EventName,AttributeValue=CreateBucket`: 4 results —
   management events are flowing.

**Root cause:** MISSING_DATA_EVENTS — S3 data events not configured
(catalog #1).

**Fix:**

```bash
aws cloudtrail put-event-selectors --trail-name corp-trail \
  --event-selectors '[{"ReadWriteType":"All","IncludeManagementEvents":true,"DataResources":[{"Type":"AWS::S3::Object","Values":["arn:aws:s3:::audit-bucket/"]}]}]'
```

Note: scope to specific bucket prefixes to control cost.

### Worked example — Lambda Invoke missing

**Symptom:** operator invokes a Lambda function; no `Invoke` event in
CloudTrail. Other Lambda management events (`CreateFunction`) appear.

**Walk:**

1. `get-event-selectors --trail-name corp-trail` returns:
   ```json
   [{"ReadWriteType":"All","IncludeManagementEvents":true,
     "DataResources":[{"Type":"AWS::S3::Object","Values":["arn:aws:s3"]}]}]
   ```
   Only S3 data events configured; Lambda data events absent.
2. To add Lambda, include `AWS::Lambda::Function` in DataResources.

**Root cause:** MISSING_DATA_EVENTS — Lambda data events not configured.

**Fix:**

```bash
aws cloudtrail put-event-selectors --trail-name corp-trail \
  --event-selectors '[{"ReadWriteType":"All","IncludeManagementEvents":true,"DataResources":[
    {"Type":"AWS::S3::Object","Values":["arn:aws:s3"]},
    {"Type":"AWS::Lambda::Function","Values":["arn:aws:lambda"]}
  ]}]'
```

## Category B: TRAIL_NOT_LOGGING

The trail is configured but not actively logging.

### Worked example — Trail stopped via stop-logging

**Symptom:** no log files in S3 for 4 hours. `get-trail-status` shows
`IsLogging: false`, `StopLoggingTime: 2026-08-09T14:00Z`. The operator
does not remember stopping it.

**Walk:**

1. `aws cloudtrail get-trail-status --name corp-trail`:
   ```
   IsLogging: false
   StopLoggingTime: 2026-08-09T14:00:00Z
   LatestDeliveryTime: 2026-08-09T13:58:00Z
   ```
2. CloudTrail event history for `StopLogging` shows the event was
   made by an IAM user `security-auditor` at 14:00Z yesterday —
   inadvertent stop.
3. No bucket-policy or KMS issue; the trail config itself is fine.

**Root cause:** TRAIL_NOT_LOGGING — inadvertent stop-logging
(catalog #2).

**Fix:**

```bash
aws cloudtrail start-logging --name corp-trail
aws cloudtrail get-trail-status --name corp-trail  # verify isLogging=true
```

Add a CloudWatch alarm on the trail's `NumberOfNotificationsDelivered`
metric to catch silent stops in the future.

### Worked example — Trail created via Terraform but never started

**Symptom:** brand-new trail created via Terraform produces no events.
`get-trail-status` shows `IsLogging: false`, `StartLoggingTime` empty.

**Walk:**

1. `aws cloudtrail describe-trails --trail-name-list new-trail`:
   configuration looks correct.
2. `aws cloudtrail get-trail-status --name new-trail`:
   `IsLogging: false`. No `StartLoggingTime`.
3. Terraform `aws_cloudtrail` resource does NOT automatically call
   `start-logging` — it only creates the trail. The
   `aws_cloudtrail` resource has no `start_logging` argument. You
   must use the `aws_cloudtrail_logging` resource (or
   `start-logging` CLI) separately.

**Root cause:** TRAIL_NOT_LOGGING — IaC omitted start-logging
(catalog #11).

**Fix:**

```bash
aws cloudtrail start-logging --name new-trail
```

And update Terraform:

```hcl
resource "aws_cloudtrail" "new" { /* ... */ }

resource "aws_cloudtrail_logging" "new" {
  name = aws_cloudtrail.new.id
  enable = true
}
```

## Category C: DELIVERY_DELAYED

### Worked example — Cross-region bucket adds latency

**Symptom:** log files arrive in S3 30-45 minutes after the event.
Trail is in `us-east-1`, S3 bucket is in `eu-west-1`.

**Walk:**

1. `get-trail-status --name corp-trail`:
   `LatestDeliveryTime` lags `now` by ~35 min.
2. `aws s3api get-bucket-location --bucket <bucket>`: `eu-west-1`.
3. `describe-trails --trail-name-list corp-trail --query
   'trailList[0].HomeRegion'`: `us-east-1`.
4. Cross-region delivery adds latency.

**Root cause:** DELIVERY_DELAYED — cross-region bucket (catalog #4
variant).

**Fix:** move the bucket to `us-east-1`, OR accept the latency, OR use
CloudTrail Lake for near-real-time needs.

### Worked example — Org trail member-account delay

**Symptom:** org trail delivers management account events in ~5 min.
Member account events lag by 20-30 min.

**Walk:**

1. In the management account: `get-trail-status` shows healthy
   delivery.
2. In the member account: events appear in the org bucket ~25 min
   after they happen.
3. This is the expected org-trail aggregation delay.

**Root cause:** DELIVERY_DELAYED — org trail member aggregation
(expected, not a defect).

**Fix:** no fix needed. Document the expected delay in operator
runbooks. Use CloudTrail Lake for cross-account near-real-time needs.

## Category D: INSIGHTS_DISABLED

### Worked example — Insights never enabled

**Symptom:** operator expects an Insights finding for a spike in
`AttachRolePolicy` calls. None appears. Trail has been logging for
months.

**Walk:**

1. `aws cloudtrail get-insight-selectors --trail-name corp-trail`:
   ```json
   {"InsightSelectors":[]}
   ```
   Empty selector list — Insights is OFF.
2. `aws cloudtrail get-trail-status --name corp-trail`: `IsLogging:
   true`. Trail is healthy; Insights just isn't enabled.

**Root cause:** INSIGHTS_DISABLED — Insights not enabled (catalog #7).

**Fix:**

```bash
aws cloudtrail put-insight-selectors --trail-name corp-trail \
  --insight-selectors '[{"InsightType":"ApiCallRateInsight"},{"InsightType":"ApiErrorRateInsight"}]'
```

Then wait 7 days for the baseline to establish before expecting
findings.

### Worked example — Insights enabled but baseline not elapsed

**Symptom:** Insights was enabled 3 days ago. Operator expects a
finding for anomalous activity today. Nothing appears.

**Walk:**

1. `get-insight-selectors`: selectors present.
2. `get-trail-status`: logging.
3. The trail's `StartLoggingTime` for Insights is 3 days ago. The
   baseline period is 7 days.

**Root cause:** INSIGHTS_DISABLED — baseline period not elapsed
(catalog #8, expected behavior).

**Fix:** wait 4 more days. Document in onboarding.

## Category E: ORG_TRAIL_GAP

### Worked example — Member shadow trail stopped

**Symptom:** org trail logs the management account and 9 of 10
members. Member account `222222222222` has no events in the org
bucket for the past day.

**Walk:**

1. Management account: `describe-trails` shows the org trail;
   `get-trail-status` shows `IsLogging: true`.
2. In member `222222222222`: `describe-trails --show-shadow-trails`:
   ```
   [{Name: corp-org-trail, IsShadowTrail: true, IsLogging: false,
     IsOrganizationTrail: true}]
   ```
   The shadow trail is stopped in this member.
3. CloudTrail event history in the member shows a `StopLogging` event
   from an automated script that ran yesterday.

**Root cause:** ORG_TRAIL_GAP — member shadow trail stopped
(catalog #9).

**Fix:** in the member account (use member-account credentials):

```bash
aws cloudtrail start-logging --name corp-org-trail
aws cloudtrail get-trail-status --name corp-org-trail  # verify isLogging=true
```

### Worked example — Delegated admin confusion

**Symptom:** org trail sometimes logs, sometimes stops. Two trails
exist with the same name.

**Walk:**

1. Management account: `describe-trails --query
   'trailList[?IsOrganizationTrail]'` returns the trail.
2. Delegated admin account (per
   `aws organizations list-delegated-administrators
   --service-principal cloudtrail.amazonaws.com`): `describe-trails`
   also returns an org trail with the SAME name.
3. Both trails write to the same S3 bucket but alternately stop each
   other. CloudTrail only supports ONE org trail per org.

**Root cause:** ORG_TRAIL_GAP — delegated admin confusion (catalog
#10).

**Fix:** delete the trail from one of the accounts. The trail should
exist ONLY in the management account OR the delegated admin, not both.

## Category F: MULTI_REGION_GAP

### Worked example — Single-region trail misses us-west-2 events

**Symptom:** operator runs `aws s3api create-bucket --bucket test
--region us-west-2 --create-bucket-configuration ...`. Expects to see
`CreateBucket` in CloudTrail. Lookup returns nothing.

**Walk:**

1. `describe-trails --trail-name-list corp-trail`:
   `IsMultiRegionTrail: false`, `HomeRegion: us-east-1`.
2. `lookup-events --region us-west-2 --lookup-attributes
   AttributeKey=EventName,AttributeValue=CreateBucket`: returns the
   event (the event IS being captured in us-west-2's local event
   history, just not delivered to the trail's S3 bucket).
3. `lookup-events --region us-east-1`: does not include the
   us-west-2 event.

**Root cause:** MULTI_REGION_GAP — single-region trail (catalog #6).

**Fix:**

```bash
aws cloudtrail update-trail --name corp-trail \
  --is-multi-region-trail \
  --include-global-service-events
```

`--include-global-service-events` is needed to capture IAM/STS/Route 53
events that are only delivered to the trail's home region (us-east-1)
by default.

## Category G: BUCKET_POLICY_BLOCKING

### Worked example — Missing bucket-owner-full-control condition

**Symptom:** trail claims `IsLogging: true`. No log files in S3 for
hours. Bucket exists and is in the same region.

**Walk:**

1. `get-trail-status`: `IsLogging: true`, `LatestDeliveryTime:
   empty`.
2. `aws s3api get-bucket-policy --bucket <bucket> --query Policy
   --output text | jq '.Statement[] | select(.Principal.Service ==
   "cloudtrail.amazonaws.com")'`:
   ```json
   {
     "Effect": "Allow",
     "Principal": {"Service": "cloudtrail.amazonaws.com"},
     "Action": "s3:PutObject",
     "Resource": "arn:aws:s3:::<bucket>/AWSLogs/<account>/CloudTrail/*"
   }
   ```
   Note: NO `Condition` requiring `s3:x-amz-acl:
   bucket-owner-full-control`. Without this, the bucket owner (the
   account) does not own the objects and CloudTrail's delivery fails
   silently on some configurations.
3. CloudTrail event history shows no `PutObject` failures — the
   writes succeed but land with the wrong ACL, or are rejected by
   the bucket's Block Public Access if it requires ownership.

**Root cause:** BUCKET_POLICY_BLOCKING — missing ACL condition
(catalog #4 variant).

**Fix:** update the bucket policy:

```json
{
  "Effect": "Allow",
  "Principal": {"Service": "cloudtrail.amazonaws.com"},
  "Action": "s3:PutObject",
  "Resource": "arn:aws:s3:::<bucket>/AWSLogs/<account>/CloudTrail/*",
  "Condition": {
    "StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}
  }
}
```

### Worked example — KMS key policy missing CloudTrail

**Symptom:** trail with `KmsKeyId: arn:aws:kms:us-east-1:...:key/xyz`.
`IsLogging: true`. No log files in S3.

**Walk:**

1. `get-trail-status`: `IsLogging: true`, `LatestDeliveryTime: empty`.
2. Bucket policy: looks correct.
3. `aws kms get-key-policy --key-id <key-id> --policy-name default
   --query Policy --output text | jq '.Statement[] | select(
   .Principal.Service == "cloudtrail.amazonaws.com")'`:
   returns nothing — the KMS key policy does NOT allow CloudTrail.
4. CloudTrail cannot `GenerateDataKey` to encrypt log files. Delivery
   fails silently.

**Root cause:** BUCKET_POLICY_BLOCKING — KMS key policy (catalog #5).

**Fix:** add a statement to the KMS key policy:

```json
{
  "Effect": "Allow",
  "Principal": {"Service": "cloudtrail.amazonaws.com"},
  "Action": ["kms:GenerateDataKey*", "kms:DescribeKey"],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "aws:SourceArn": "arn:aws:cloudtrail:us-east-1:<account>:trail/<trail-name>"
    },
    "StringLike": {
      "kms:ViaService": "s3.us-east-1.amazonaws.com"
    }
  }
}
```

The `aws:SourceArn` condition is a security best practice — it
prevents the key from being used by trails in other accounts.

## Cross-category decision flowchart

```
START
  │
  ▼
Is the trail in describe-trails?
  ├── NO ──► describe-trails --show-shadow-trails ──► [B] TRAIL_NOT_LOGGING (deleted)
  │
  ▼ YES
get-trail-status: IsLogging?
  ├── false ──► [B] TRAIL_NOT_LOGGING ──► start-logging
  │
  ▼ true
Are ANY events flowing (lookup-events > 0)?
  ├── NO ──► Check bucket policy (Step 7b)
  │            ├── missing Allow ──► [G] BUCKET_POLICY_BLOCKING
  │            ├── explicit Deny ──► [G] BUCKET_POLICY_BLOCKING
  │            └── KMS key policy missing ──► [G] BUCKET_POLICY_BLOCKING
  │
  ▼ YES (management events flow)
Missing event is a data-plane event (GetObject / PutItem / Invoke)?
  ├── YES ──► get-event-selectors ──► [A] MISSING_DATA_EVENTS
  │
  ▼ NO
Missing event from a different region than the trail's home region?
  ├── YES ──► IsMultiRegionTrail? false ──► [F] MULTI_REGION_GAP
  │
  ▼ NO
Missing event from a specific member account?
  ├── YES ──► [E] ORG_TRAIL_GAP ──► check member shadow trail
  │
  ▼ NO
Delivery latency > 15 min?
  ├── YES ──► [C] DELIVERY_DELAYED ──► check bucket region, Health
  │
  ▼ NO
Insights not producing findings?
  ├── YES ──► get-insight-selectors ──► [D] INSIGHTS_DISABLED
  │
  ▼
NEED_MORE_INFO — gather more context
```

## Common diagnostic shortcuts

- If the operator expects a specific event (GetObject, PutItem,
  Invoke), it is almost always a data-events configuration gap.
  Check `get-event-selectors` first.
- If `get-trail-status` shows `IsLogging: false`, just call
  `start-logging`. Do not over-diagnose.
- If a trail was created via Terraform / CloudFormation and never
  produced events, the IaC omitted `start-logging`. The trail exists
  but is stopped.
- If Insights was enabled recently, wait 7 days before declaring it
  broken.
- If only specific member accounts are missing, check the member
  shadow trail status, not the management account trail.
- If the bucket is in a different region, expect delivery latency.
- If CloudTrail is working in the console's "Event history" but not
  in S3, the trail config (bucket / policy / KMS) is the issue, not
  CloudTrail itself.
- If `lookup-events` returns events but the operator's SIEM (Splunk,
  OpenSearch) does not, the gap is in the SIEM ingestion, not
  CloudTrail.
