---
name: cloudtrail-missing-events-troubleshooter
description: >-
  Diagnoses AWS CloudTrail missing-events incidents across eleven
  failure categories: trail logging inadvertently disabled
  (stop-logging, IaC that omitted start-logging), S3 bucket policy
  missing cloudtrail.amazonaws.com write permission, organization
  trail vs member account trail overlap (org trail shadows member),
  management events vs data events vs Insight events filtering
  (data events must be explicitly enabled), read-only vs write-only
  event selector mismatch, multi-region trail vs single-region
  scope, log file validation (S3 digest integrity failures),
  CloudWatch Logs delivery delay beyond the 5-15 minute window,
  CloudTrail Lake event data store query issues, AWS service not
  logging (not all services in all regions), event source filtering
  / log file prefix errors, and KMS key disabled preventing log
  encryption. Walks symptoms to a verified root cause with
  evidence-backed probes and emits ROOT_CAUSE_IDENTIFIED or
  INSUFFICIENT_DATA.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and describe-trails / get-trail-status / get-event-selectors JSON. Live-account diagnosis uses aws cloudtrail describe-trails, get-trail-status, get-event-selectors, get-insight-selectors, lookup-events, aws s3api get-bucket-policy, get-bucket-location, aws kms describe-key, aws organizations
  list-delegated-administrators, describe-organization, and aws logs filter-log-events (AWS CLI v2, SSO or key-based credentials).
keywords:
- CloudTrail
- audit logging
- missing events
- trail not logging
- trail disabled
- stop-logging
- S3 bucket policy
- cloudtrail.amazonaws.com
- organization trail
- member account trail
- org trail shadows member
- management events
- data events
- S3 data events
- Lambda data events
- DynamoDB data events
- CloudTrail Insights
- read-only events
- write-only events
- event selector
- advanced event selector
- multi-region trail
- single-region trail
- log file validation
- S3 digest
- CloudWatch Logs delivery
- CloudTrail Lake
- event data store
- KMS key disabled
- log encryption
- log file prefix
- AWS service not logging
- troubleshooting
tags:
- cloudtrail
- governance
- troubleshoot
- missing-events
- audit
- compliance
- org-trail
- event-selectors
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Governance
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing why CloudTrail events are missing — a specific API call is not appearing in lookup-events, the S3 bucket is not receiving log files, an organisation trail is not logging a member account, data events (S3 / Lambda / DynamoDB) are absent despite the trail being IsLogging true, CloudTrail Insights is silent, log file validation digest is failing, CloudWatch Logs delivery is delayed, CloudTrail Lake query returns empty, a regional service is not logging, or KMS-disabled log encryption is blocking delivery. Use whenever the symptom is "events that should be in CloudTrail are not".
  when_not_to_use: Steady-state CloudTrail posture audits (use cloudtrail-org-trail-auditor), IAM policy authoring for the CloudTrail service role (use iam-least-privilege-advisor), CloudTrail Lake event-data-store provisioning (use cloudtrail-lake-operator), Security Hub finding triage (use securityhub-finding-troubleshooter), or CloudWatch Logs ingestion from non-CloudTrail sources. This skill diagnoses missing-events incidents; it does not audit steady-state configuration posture or provision new trails.
  activation_triggers:
  - CloudTrail missing events
  - CloudTrail events not appearing
  - CloudTrail trail not logging
  - CloudTrail IsLogging false
  - CloudTrail stop-logging
  - CloudTrail S3 bucket policy
  - CloudTrail bucket policy missing cloudtrail.amazonaws.com
  - CloudTrail data events missing
  - CloudTrail S3 data events
  - CloudTrail Lambda data events
  - CloudTrail management events
  - CloudTrail Insights not firing
  - CloudTrail read-only events
  - CloudTrail write-only events
  - CloudTrail event selector
  - CloudTrail multi-region trail
  - CloudTrail single-region
  - CloudTrail log file validation
  - CloudTrail digest
  - CloudTrail CloudWatch Logs delivery delay
  - CloudTrail Lake empty query
  - CloudTrail KMS key disabled
  - CloudTrail log encryption blocked
  - CloudTrail org trail not logging member
  - CloudTrail log file prefix
  - CloudTrail service not logging
  - troubleshoot CloudTrail missing events
  invocation_schema: 'Input: either (a) a symptom description (trail name, the missing event source or eventName, any error strings from the console), optionally paired with describe-trails / get-trail-status / get-event-selectors output, OR (b) a TrailName plus caller context (region, expected event) for live-account diagnosis. Output: a deterministic TARGET / VERDICT / ROOT_CAUSE / LAYER / EVIDENCE / REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {TRAIL_DISABLED, BUCKET_POLICY_BLOCKING, ORG_TRAIL_SHADOWS_MEMBER, DATA_EVENTS_NOT_ENABLED, EVENT_SELECTOR_READONLY, MULTI_REGION_SCOPE_GAP, LOG_FILE_VALIDATION_FAILED, CW_LOGS_DELIVERY_DELAYED, LAKE_EDS_QUERY_ISSUE, SERVICE_NOT_IN_REGION, KMS_KEY_DISABLED, LOG_FILE_PREFIX_ERROR, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"CloudTrail trail prod-org-trail shows IsLogging true but S3 GetObject events from account 222222222222 are not\nappearing in lookup-events for the last 24 hours.\"\nTrailName: prod-org-trail\nIsOrganizationTrails: true\nIsLogging: true\nRegions: multi-region (us-east-1 home)\nEventSelectors:\n  - ManagementEvents: Source = aws.amazonaws.com, ReadWriteType = All\n  - DataEvents: (none configured)\nExpectedEventSource: s3.amazonaws.com\nExpectedEventName: GetObject\nCallerAccount: 222222222222"
---

# CloudTrail Missing Events Troubleshooter

## Quick start

- **Symptom → layer map (the first plausible match drives the first
  probe):** `get-trail-status` returns `IsLogging: false` →
  TRAIL_DISABLED; `IsLogging: true` but S3 has no new log files →
  BUCKET_POLICY_BLOCKING or KMS_KEY_DISABLED; specific data-plane
  API (GetObject, InvokeFunction) missing →
  DATA_EVENTS_NOT_ENABLED; org trail logs management account but
  not a member → ORG_TRAIL_SHADOWS_MEMBER; only one region's
  events appear → MULTI_REGION_SCOPE_GAP; lookup-events shows
  events but CloudWatch Logs is empty → CW_LOGS_DELIVERY_DELAYED;
  CloudTrail Lake query returns empty → LAKE_EDS_QUERY_ISSUE;
  service not appearing at all → SERVICE_NOT_IN_REGION.
- **Always verify with a probe, never guess.** Each layer has a
  single command that proves or disproves it. A
  ROOT_CAUSE_IDENTIFIED verdict requires positive evidence — a
  failing probe that matches the symptom — not a process of
  elimination that "must be the bucket policy."
- **The three rules every senior CloudTrail engineer keeps in
  head:** (1) management events are default-on, but data events
  (S3/Lambda/DynamoDB data-plane) must be **explicitly enabled**
  via an event selector; (2) an organization trail **shadows**
  member-account trails — a member trail stops delivering as soon
  as the org trail is created in the management account; (3) the
  S3 bucket policy must **explicitly allow
  `cloudtrail.amazonaws.com`** the `s3:GetBucketAcl`,
  `s3:PutObject` (with the `s3:x-amz-acl: bucket-owner-full-control`
  condition), and `s3:ListBucket` actions, or no log files land.
- **`IsLogging: true` does NOT mean events are delivering.** A
  trail can report `IsLogging: true` while the S3 bucket policy
  silently rejects PutObject from the CloudTrail service principal.
  The managed service does not fail the trail on bucket-policy
  rejection — it keeps retrying. Always cross-reference
  `LatestDeliveryTime` against the wall clock.
- **INSUFFICIENT_DATA is acceptable.** Missing-events incidents
  frequently present with partial telemetry (no CloudTrail event
  for the CloudTrail config change itself, no S3 access logs). If
  a failing probe cannot be obtained, emit INSUFFICIENT_DATA with
  the specific missing inputs — do not declare a verdict on
  inference alone.

## Mindset

A "CloudTrail is missing events" incident is almost always a
configuration mismatch between what the operator expects the trail
to capture and what the event selectors actually select. The trail
is fine; the *selector scope* is wrong, the *bucket policy* is
blocking delivery, or the *org trail* is shadowing a member trail.
Senior CloudTrail engineers do not start by reading individual log
files — they start with `describe-trails`, `get-trail-status`,
`get-event-selectors`, and `get-bucket-policy`. Only once the trail
configuration is proven correct do they pivot to `lookup-events`
to verify specific events are landing.

Four behaviours separate a senior CloudTrail engineer from a
generalist: (1) management events are default-on but data events
(S3 GetObject, Lambda InvokeFunction, DynamoDB GetItem) are
**opt-in** — a trail with default event selectors captures ZERO
data-plane API calls; data events require an explicit event
selector and are billed at a higher rate; (2) organization trails
**shadow** member trails — when an org trail is created, CloudTrail
creates a read-only shadow trail in every member account, and any
pre-existing member trail STOPS DELIVERING as soon as the shadow
appears (events route to the org bucket); (3) the S3 bucket policy
is the **silent failure mode** — `IsLogging: true` does NOT mean
events are delivering, because CloudTrail retries silently on
bucket-policy rejection, so always cross-reference
`LatestDeliveryTime` against the wall clock; (4) CloudTrail Lake
event data stores have **independent selectors** from S3 trails —
configuring one does not configure the other.

## Quick reference — symptom triage table

| Symptom phrase / error | Layer | First probe |
|---|---|---|
| `get-trail-status` returns `IsLogging: false` | TRAIL_DISABLED | `aws cloudtrail get-trail-status --name <trail>`; `lookup-events` for `StopLogging` |
| `IsLogging: true` but no new S3 objects in last hour | BUCKET_POLICY_BLOCKING / KMS_KEY_DISABLED | `aws s3api get-bucket-policy`; `aws s3 ls s3://<bucket>/<prefix>/ --recursive | tail` |
| Specific data-plane API (GetObject, InvokeFunction) missing from lookup-events | DATA_EVENTS_NOT_ENABLED | `get-event-selectors`; check `DataEvents` array |
| ReadWriteType `ReadOnly` but expecting a write event | EVENT_SELECTOR_READONLY | `get-event-selectors`; check `ReadWriteType` |
| Trail exists in management account but member account events missing | ORG_TRAIL_SHADOWS_MEMBER | `describe-trails` in member; look for `IsOrganizationTrail: true` |
| Only `us-east-1` events in trail; other regions missing | MULTI_REGION_SCOPE_GAP | `describe-trails`; `IsMultiRegionTrail: false` |
| `LatestDigestDeliveryTime` hours old; `S3 validation failed` alarm | LOG_FILE_VALIDATION_FAILED | `get-trail-status`; S3 bucket digest object listing |
| `lookup-events` shows events but CloudWatch Logs is empty | CW_LOGS_DELIVERY_DELAYED | `get-trail-status`; CloudWatch Logs `LastEventTime` |
| CloudTrail Lake `start-query` returns empty | LAKE_EDS_QUERY_ISSUE | `aws cloudtrail list-event-data-stores`; `get-event-selectors` on the EDS |
| Specific AWS service events absent (e.g., a regional service) | SERVICE_NOT_IN_REGION | `lookup-events` with `--service` filter; AWS docs for regional availability |
| S3 prefix `logs/` configured but logs land in `cloudtrail/` | LOG_FILE_PREFIX_ERROR | `describe-trails`; `S3KeyPrefix` field |

## Pre-flight: trail state and gather-info gate

Before running symptom-specific probes, gather the canonical trail
state and short-circuit on trail-wide events that mimic per-API
missing-events.

```bash
# Trail configuration (S3BucketName, S3KeyPrefix, IsMultiRegionTrail,
# IsOrganizationTrail, KmsKeyId, CloudWatchLogsLogGroupArn)
aws cloudtrail describe-trails --trail-name-list <trail> --output json

# Trail delivery status (IsLogging, LatestDeliveryTime,
# LatestCloudWatchLogsDeliveryTime, LatestDigestDeliveryTime)
aws cloudtrail get-trail-status --name <trail> --output json

# Event selectors (ManagementEvents, DataEvents, ReadWriteType,
# ExcludeManagementEventSources, AdvancedEventSelectors)
aws cloudtrail get-event-selectors --trail-name <trail> --output json

# S3 bucket policy and KMS key state (if KmsKeyId is set)
aws s3api get-bucket-policy --bucket <bucket> --output json
aws kms describe-key --key-id <kms-key-id> --output json

# Recent lookup-events to confirm the specific missing API
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=<service>.amazonaws.com \
  --start-time $(date -d '-24 hours' +%s) --end-time $(date +%s) --output json
```

### Trail-state short-circuit

| Signal | Effect on diagnosis |
|---|---|
| `IsLogging: false` | Trail was stopped. Jump to TRAIL_DISABLED. |
| `IsLogging: true`, `LatestDeliveryTime` < 60 min ago | Trail is delivering to S3. Pivot to event-selector or org-trail diagnosis. |
| `IsLogging: true`, `LatestDeliveryTime` > 60 min old | Silent delivery failure. Jump to BUCKET_POLICY_BLOCKING or KMS_KEY_DISABLED. |
| `IsOrganizationTrail: true` in a member account | Shadow trail from the org trail; member trail may be shadowed. Jump to ORG_TRAIL_SHADOWS_MEMBER. |
| `IsMultiRegionTrail: false` | Trail captures only its home region. Jump to MULTI_REGION_SCOPE_GAP if events from other regions are expected. |
| `KmsKeyId: <arn>`, `KeyState: Disabled` | KMS key disabled; log encryption blocked. Jump to KMS_KEY_DISABLED. |
| `CloudWatchLogsLogGroupArn: null` | No CloudWatch Logs delivery configured. If operator expects CW Logs, that is the gap. |
| `IncludeGlobalServiceEvents: false` | IAM and STS global-service events (delivered from us-east-1) are excluded. |

If the input is malformed (missing TrailName, absent symptom, no
specific EventSource or EventName), emit:

```text
TARGET: <trail-name or unknown>
VERDICT: INSUFFICIENT_DATA
ROOT_CAUSE: UNKNOWN
REASON: Input is missing required context — at minimum a symptom
  description (the missing EventSource or EventName, observed
  gap), the TrailName, and the caller account / region for
  org-trail disambiguation.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the specific event
  they expect to see (EventSource and EventName, e.g.,
  s3.amazonaws.com:GetObject), (2) the TrailName, (3) the caller
  account (especially if it is a member account of an
  organization), and (4) the approximate time window of the
  expected event.
```

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based
on the observed symptom, then walk the layer-specific probes in
order. Each layer ends with either a positive root-cause
confirmation (failing probe that matches the symptom) or a pass
that moves to the next layer. **Never emit ROOT_CAUSE_IDENTIFIED
without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

- **`IsLogging: true` does not mean events are delivering.** The
  managed service does not fail the trail on bucket-policy rejection
  — it retries silently. Cross-reference `LatestDeliveryTime` against
  the wall clock. A trail with `IsLogging: true` and
  `LatestDeliveryTime: 6 hours ago` is failing.
- **Organization trails create shadow trails in every member
  account.** The shadow trail appears in `describe-trails` with
  `IsOrganizationTrail: true`; the member cannot modify it. Any
  pre-existing member trail STOPS DELIVERING as soon as the shadow
  appears — events route to the org bucket.
- **Management events are default-on; data events are opt-in.** S3
  GetObject, Lambda InvokeFunction, DynamoDB GetItem require an
  event selector with `DataEvents` explicitly configured.
- **Event selectors have `ReadWriteType: All` by default**, but the
  field can be `ReadOnly` or `WriteOnly`. A trail with `ReadOnly`
  will not capture `CreateBucket`, `PutObject`, `RunInstances`.
- **`IncludeGlobalServiceEvents` controls IAM, STS, and
  CloudFront.** Global services deliver events from us-east-1 only.
  `IncludeGlobalServiceEvents: false` excludes them even on a
  multi-region trail.
- **KMS key disabled blocks log encryption silently.** If the trail
  has `KmsKeyId: <arn>` and `KeyState: Disabled` or
  `PendingDeletion`, CloudTrail cannot encrypt log files and stops
  delivering. `IsLogging` reports `true`; `LatestDeliveryTime` is
  stale.
- **CloudTrail Lake EDS has independent selectors from S3 trails.**
  An operator who "sees events in S3 but not in Lake" has the Lake
  EDS configured with a narrower selector. They are two independent
  ingestion paths.
- **Not all AWS services log in all regions.** Some regional
  services do not emit CloudTrail events in every region where they
  operate. Cross-reference the AWS docs for the service-region
  combination.
- **S3 log file prefix errors are subtle.** The trail's `S3KeyPrefix`
  field controls the prefix. An operator listing
  `s3://bucket/cloudtrail/` when `S3KeyPrefix` is `logs/` will see
  "no logs" even though delivery is healthy.
- **CloudTrail log file validation digests deliver separately.**
  `LatestDigestDeliveryTime` is independent of
  `LatestDeliveryTime`. Stale digest delivery with healthy log
  delivery is a separate issue (usually bucket policy missing
  `s3:PutObject` for the digest prefix).

### Step 1: Symptom entry — pick the diagnostic branch

| Symptom | Branch |
|---|---|
| `get-trail-status` returns `IsLogging: false` | Step 2 — Trail disabled |
| `IsLogging: true` but no new S3 objects | Step 3 — Bucket policy / KMS |
| Specific data-plane API (GetObject, InvokeFunction) missing | Step 4 — Data events |
| Org trail logs management account but not member | Step 5 — Org trail shadows |
| Only one region's events appear | Step 6 — Multi-region scope |
| `ReadWriteType: ReadOnly` but expecting write events | Step 7 — Event selector |
| `lookup-events` shows events but CloudWatch Logs empty | Step 8 — CW Logs delivery |
| CloudTrail Lake query returns empty | Step 9 — Lake EDS |
| Specific AWS service events absent | Step 10 — Service not in region |
| S3 prefix mismatch | Step 11 — Log file prefix |
| None of the above | Step 12 — INSUFFICIENT_DATA |

### Step 2: Trail disabled — `IsLogging: false`

Symptom: `get-trail-status` returns `IsLogging: false`. The trail
was stopped via `stop-logging` (explicit), or never started after
IaC creation (CloudFormation / Terraform that created the trail
without the `start-logging` invocation).

```bash
aws cloudtrail get-trail-status --name <trail> --output json
# Look for: IsLogging: false, StopLoggingTime: <timestamp>

aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=StopLogging \
  --start-time $(date -d '-7 days' +%s) --end-time $(date +%s) \
  --output json
# Find WHO called StopLogging and when
```

If `IsLogging: false`, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: TRAIL_DISABLED`. Identify the caller from the StopLogging
CloudTrail event; remediating requires `start-logging`:

```bash
aws cloudtrail start-logging --name <trail>
```

IaC pitfall: CloudFormation `AWS::CloudTrail::Trail` does NOT
automatically start logging on creation. The IaC template must
either include the `IsLogging: true` property or invoke
`start-logging` as a custom resource. Terraform has the same
gotcha — the `aws_cloudtrail` resource starts logging by default
but can be stopped by setting `enable_logging = false`.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: TRAIL_DISABLED`.

### Step 3: Bucket policy or KMS blocking delivery

Symptom: `IsLogging: true` but `LatestDeliveryTime` is hours old;
no new S3 objects in the trail bucket.

```bash
aws cloudtrail get-trail-status --name <trail> --output json | \
  jq '{IsLogging, LatestDeliveryTime, TimeLoggingStarted, TimeLoggingStopped}'

aws s3api get-bucket-policy --bucket <bucket> --output json | \
  jq '.Policy'

aws s3 ls s3://<bucket>/<prefix>/AWSLogs/<account>/CloudTrail/ \
  --recursive | tail -10

aws kms describe-key --key-id <kms-key-id> --output json | \
  jq '.KeyMetadata.{KeyState, KeyManager, Enabled}'
```

#### 3a: Bucket policy missing cloudtrail.amazonaws.com principal

The bucket policy MUST include a statement allowing the
`cloudtrail.amazonaws.com` service principal to perform:
- `s3:GetBucketAcl` (CloudTrail checks the bucket ACL on every
  delivery)
- `s3:ListBucket` (CloudTrail lists the prefix to determine the
  next sequence number)
- `s3:PutObject` with the condition
  `s3:x-amz-acl: bucket-owner-full-control` (ensures the log file
  is owned by the bucket owner, not the CloudTrail service)

The canonical policy statement:

```json
{
  "Sid": "AWSCloudTrailAclCheck20150319",
  "Effect": "Allow",
  "Principal": {"Service": "cloudtrail.amazonaws.com"},
  "Action": "s3:GetBucketAcl",
  "Resource": "arn:aws:s3:::<bucket>"
},
{
  "Sid": "AWSCloudTrailWrite20150319",
  "Effect": "Allow",
  "Principal": {"Service": "cloudtrail.amazonaws.com"},
  "Action": "s3:PutObject",
  "Resource": "arn:aws:s3:::<bucket>/<prefix>/AWSLogs/<account>/CloudTrail/*",
  "Condition": {
    "StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}
  }
}
```

If the bucket policy is missing this statement, missing the
condition, scoped to the wrong account, or has an explicit Deny
that matches, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: BUCKET_POLICY_BLOCKING`.

For organization trails, the `Resource` ARN must include a `/*`
wildcard at the end (to cover all member accounts) or list the
`o-xxxxxxx` org ID:

```json
"Resource": "arn:aws:s3:::<bucket>/<prefix>/AWSLogs/o-xxxxxxx/*"
```

#### 3b: KMS key disabled

If the trail has `KmsKeyId: <arn>` and `KeyState: Disabled` or
`PendingDeletion`, CloudTrail cannot encrypt log files and stops
delivering. **ROOT_CAUSE_IDENTIFIED** with `LAYER: KMS_KEY_DISABLED`.

Fix: re-enable the key (`aws kms enable-key --key-id <id>`), or
remove the KmsKeyId from the trail
(`update-trail --name <trail> --kms-key-id ""` — disables SSE-KMS).

**Verdicts:** ROOT_CAUSE_IDENTIFIED,
`LAYER: BUCKET_POLICY_BLOCKING` or `KMS_KEY_DISABLED`.

### Step 4: Data events not enabled

Symptom: specific data-plane API calls (S3 GetObject, Lambda
InvokeFunction, DynamoDB GetItem) are missing from lookup-events,
but management-plane APIs are present.

```bash
aws cloudtrail get-event-selectors --trail-name <trail> --output json
# Look for: EventSelectors[].DataResources
# An empty DataEvents array means data events are NOT being captured
```

Data events require an event selector with `DataResources`
configured. The canonical configurations:

| Data source | Required event selector |
|---|---|
| S3 GetObject / PutObject / DeleteObject | `DataResources: [{ Type: "AWS::S3::Object", Values: ["arn:aws:s3:::<bucket>/"] }]` (trailing slash matters) |
| Lambda InvokeFunction | `DataResources: [{ Type: "AWS::Lambda::Function", Values: ["arn:aws:lambda"] }]` |
| DynamoDB GetItem / PutItem / DeleteItem | `DataResources: [{ Type: "AWS::DynamoDB::Stream", Values: ["arn:aws:dynamodb"] }]` (advanced event selector recommended) |

To enable S3 data events for a specific bucket:

```bash
aws cloudtrail put-event-selectors --trail-name <trail> \
  --event-selectors '[{
    "ReadWriteType": "All",
    "IncludeManagementEvents": true,
    "DataResources": [{
      "Type": "AWS::S3::Object",
      "Values": ["arn:aws:s3:::<bucket>/"]
    }]
  }]'
```

If the trail's event selector has no `DataResources` for the
expected data source, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: DATA_EVENTS_NOT_ENABLED`.

Note: data events are billed at a higher rate than management
events ($0.10 per 100,000 events vs. free for the first
copy of management events). Operators who "see the cost" may
have disabled data events intentionally — confirm with the operator
before re-enabling.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DATA_EVENTS_NOT_ENABLED`.

### Step 5: Org trail shadows member trail

Symptom: an organization trail in the management account captures
the management account's events but a member account's events are
missing, OR a member account's previously-working trail "suddenly
stopped delivering."

```bash
# In the member account
aws cloudtrail describe-trails --output json | \
  jq '.trailList[] | {Name, IsOrganizationTrail, S3BucketName}'

# Look for: IsOrganizationTrail: true
# This is the SHADOW TRAIL — created by CloudTrail when the org
# trail was created in the management account

# In the management account
aws organizations describe-organization --output json
aws cloudtrail describe-trails --output json | \
  jq '.trailList[] | select(.IsOrganizationTrail == true)'

# Verify the org trail's bucket policy covers member accounts
aws s3api get-bucket-policy --bucket <org-trail-bucket> --output json | \
  jq '.Policy'
# Look for: Resource ARN ending in /AWSLogs/o-<org-id>/* (covers members)
```

When an org trail is created, CloudTrail creates a shadow trail in
every member account. The shadow trail delivers events to the **org
trail's bucket**, not the member's bucket. Any pre-existing member
trail that delivered to the member's own bucket stops delivering
to that bucket — the events are now captured by the org trail.

Common patterns:

| Pattern | Cause |
|---|---|
| Member account `describe-trails` shows a trail with `IsOrganizationTrail: true` that the member did not create | Shadow trail from the org trail; member events go to the org bucket |
| Member's pre-existing trail still exists but stops delivering after the org trail was created | Org trail shadows the member trail; member events go to the org bucket |
| Org trail bucket policy scoped to the management account only | Bucket policy missing the org ID `o-xxxxxxx` in the Resource ARN; member events fail to deliver |
| Member left the org | Member's shadow trail is removed; member events no longer captured |

If the org trail shadows the member trail and the operator expects
events in the member's own bucket, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: ORG_TRAIL_SHADOWS_MEMBER`. Fix: either (a) accept that
events are in the org bucket (recommended for centralized audit),
or (b) keep the member trail AND have the org trail — both will
deliver, but the org trail delivers to the org bucket and the
member trail delivers to the member bucket.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: ORG_TRAIL_SHADOWS_MEMBER`.

### Step 6: Multi-region scope gap

Symptom: only events from one region appear in the trail; events
from other regions are missing.

```bash
aws cloudtrail describe-trails --trail-name-list <trail> --output json | \
  jq '.trailList[0].IsMultiRegionTrail'
# false = single-region trail; captures only its home region
```

If `IsMultiRegionTrail: false`, the trail captures only its home
region. Convert to multi-region:

```bash
aws cloudtrail update-trail --name <trail> --is-multi-region-trail
```

Note: a single-region trail in us-east-1 still captures global
service events (IAM, STS, CloudFront) if
`IncludeGlobalServiceEvents: true`. Operators who "see IAM events
but not EC2 events from us-west-2" have a single-region trail.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: MULTI_REGION_SCOPE_GAP`.

### Step 7: Event selector — read-only vs write-only

Symptom: specific management-plane events (CreateBucket, RunInstances,
PutObject) are missing; ReadOnly events (ListBuckets, DescribeInstances)
are present.

```bash
aws cloudtrail get-event-selectors --trail-name <trail> --output json | \
  jq '.EventSelectors[].ReadWriteType'
# ReadOnly = only ListXxx, GetXxx, DescribeXxx events
# WriteOnly = only CreateXxx, PutXxx, DeleteXxx events
# All = both (default)
```

If `ReadWriteType: ReadOnly`, write events are excluded. Convert to
`All`:

```bash
aws cloudtrail put-event-selectors --trail-name <trail> \
  --event-selectors '[{"ReadWriteType": "All", "IncludeManagementEvents": true}]'
```

If `ReadWriteType: WriteOnly`, read events are excluded — operators
debugging "where did this ListBuckets call come from" will not find
it.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: EVENT_SELECTOR_READONLY`.

### Step 8: CloudWatch Logs delivery delay

Symptom: `lookup-events` shows recent CloudTrail events but the
CloudWatch Logs log group configured on the trail is empty or
delayed beyond the 5-15 minute expected window.

```bash
aws cloudtrail get-trail-status --name <trail> --output json | \
  jq '{LatestDeliveryTime, LatestCloudWatchLogsDeliveryTime}'

aws logs describe-log-streams \
  --log-group-name <cw-log-group> \
  --order-by LastEventTime --descending --limit 5 --output json
```

CloudTrail delivers to CloudWatch Logs via a separate path from S3
delivery. `LatestCloudWatchLogsDeliveryTime` is independent of
`LatestDeliveryTime`. If CW Logs delivery lags beyond 15 minutes
while S3 delivery is healthy:

| Pattern | Cause |
|---|---|
| `LatestCloudWatchLogsDeliveryTime` stale, S3 delivery healthy | The CW Logs role ARN on the trail lacks `logs:CreateLogStream`, `logs:PutLogEvents`; or the log group was deleted |
| `LatestCloudWatchLogsDeliveryTime` recent but log group empty | The log group name on the trail points at the wrong log group |
| Sustained 5-15 minute lag | Normal during high-volume periods (CloudTrail batches); investigate only if lag > 15 min |

Fix: verify the CloudWatchLogsLogGroupArn and the
CloudWatchLogsRoleArn on the trail; ensure the role trusts
`cloudtrail.amazonaws.com` and has `logs:CreateLogStream`,
`logs:PutLogEvents` on the log group ARN.

**Verdict:** ROOT_CAUSE_IDENTIFIED,
`LAYER: CW_LOGS_DELIVERY_DELAYED`.

### Step 9: CloudTrail Lake event data store

Symptom: CloudTrail Lake `start-query` returns empty for an event
that is present in the S3 trail.

```bash
aws cloudtrail list-event-data-stores --output json
aws cloudtrail get-event-selectors --event-data-store <eds-id> --output json

# Run a query against the EDS
aws cloudtrail start-query --query-statement \
  "SELECT eventTime, eventSource, eventName, userIdentity.arn \
   FROM <eds-id> \
   WHERE eventTime > timestamp '2026-08-10 00:00:00' \
   AND eventSource = 's3.amazonaws.com' \
   AND eventName = 'GetObject'" --output json
```

Lake EDS has its own event selectors independent of any S3 trail.
If the EDS selector is narrower than the S3 trail's selector, the
EDS will not ingest events that the S3 trail captures.

Common Lake EDS issues:
- EDS configured with `eventCategory: Management` only; no data
  events.
- EDS scoped to a subset of accounts via advanced event selectors.
- EDS billing mode `PRICE-per-QUERY` with no query budget; queries
  are throttled.
- EDS in a different region than the events being queried (Lake is
  regional).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: LAKE_EDS_QUERY_ISSUE`.

### Step 10: AWS service not logging in region

Symptom: events from a specific AWS service are absent from
CloudTrail in a specific region.

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=<service>.amazonaws.com \
  --region <region> \
  --start-time $(date -d '-7 days' +%s) --end-time $(date +%s) \
  --output json
# If empty, the service may not log in this region
```

Not all AWS services emit CloudTrail events in every region. A
service that launched in us-east-1 may not log in newer regions
until the regional endpoint is fully supported. Cross-reference the
AWS CloudTrail documentation for the specific service-region
combination.

Common regional-logging gaps:
- New AWS services often log in us-east-1 first.
- Some services log only at the regional endpoint; cross-region
  calls may attribute the event to the home region of the resource.
- China regions and GovCloud have separate CloudTrail event
  sources.

**Verdict:** ROOT_CAUSE_IDENTIFIED,
`LAYER: SERVICE_NOT_IN_REGION`.

### Step 11: Log file prefix error

Symptom: `LatestDeliveryTime` is recent but the operator sees no
logs at the expected S3 prefix.

```bash
aws cloudtrail describe-trails --trail-name-list <trail> --output json | \
  jq '.trailList[0].S3KeyPrefix'
# This is the prefix under which log files land

aws s3 ls s3://<bucket>/<S3KeyPrefix>/AWSLogs/<account>/CloudTrail/ \
  --recursive | tail -10
```

If the operator is listing `s3://bucket/cloudtrail/` but the trail's
`S3KeyPrefix` is `logs/`, the logs are at
`s3://bucket/logs/AWSLogs/...` — not at `cloudtrail/`. Always read
`S3KeyPrefix` from `describe-trails` before concluding delivery is
broken.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: LOG_FILE_PREFIX_ERROR`.

### Step 12: INSUFFICIENT_DATA

If none of the above produced a positive root-cause match, OR a
probe requires operator input (live-account credentials, missing
trail config), emit INSUFFICIENT_DATA with the specific missing
pieces and the next probe to run once the info is available.

## Output format

```text
TARGET: <trail-name>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
ROOT_CAUSE: <one-sentence naming the failed configuration>
LAYER: <TRAIL_DISABLED | BUCKET_POLICY_BLOCKING | KMS_KEY_DISABLED |
        DATA_EVENTS_NOT_ENABLED | EVENT_SELECTOR_READONLY |
        ORG_TRAIL_SHADOWS_MEMBER | MULTI_REGION_SCOPE_GAP |
        LOG_FILE_VALIDATION_FAILED | CW_LOGS_DELIVERY_DELAYED |
        LAKE_EDS_QUERY_ISSUE | SERVICE_NOT_IN_REGION |
        LOG_FILE_PREFIX_ERROR | UNKNOWN>
EVIDENCE:
  - <observed symptom — the missing event or delivery gap>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <trail> in <region>. Proceed?
  (yes/no)"
```

### Worked example — data events not enabled

```text
TARGET: prod-org-trail
VERDICT: ROOT_CAUSE_IDENTIFIED
ROOT_CAUSE: Trail has IsLogging: true and management events are
  delivering, but the operator expects S3 GetObject events from
  account 222222222222 — and the trail's event selector has no
  DataResources configured for AWS::S3::Object. Data events are
  opt-in; the default event selector captures only management
  events.
LAYER: DATA_EVENTS_NOT_ENABLED
EVIDENCE:
  - Symptom: `lookup-events` for `s3.amazonaws.com:GetObject` in
    the last 24 hours returns zero results; management events
    (ListBuckets, CreateBucket) are present.
  - Probe: `get-event-selectors --trail-name prod-org-trail`
    returns `EventSelectors: [{ReadWriteType: All,
    IncludeManagementEvents: true}]` — no `DataResources` array.
    S3 data-plane events are not being captured.
  - Passing: `get-trail-status` returns `IsLogging: true`,
    `LatestDeliveryTime: 4 minutes ago` (trail is healthy);
    `describe-trails` returns `IsMultiRegionTrail: true` (no
    scope gap); bucket policy includes the
    `cloudtrail.amazonaws.com` principal with the correct
    condition (no delivery block).
REMEDIATION:
  1. Add S3 data events to the trail's event selector:
     aws cloudtrail put-event-selectors --trail-name prod-org-trail \
       --event-selectors '[{
         "ReadWriteType": "All",
         "IncludeManagementEvents": true,
         "DataResources": [{
           "Type": "AWS::S3::Object",
           "Values": ["arn:aws:s3:::"]
         }]
       }]'
     (ARN `arn:aws:s3:::` with trailing colon captures ALL buckets.
      Scope to a specific bucket: `arn:aws:s3:::<bucket>/`.)
  2. Verify with lookup-events 10-15 minutes after the change:
     aws cloudtrail lookup-events \
       --lookup-attributes AttributeKey=EventSource,AttributeValue=s3.amazonaws.com \
       --start-time $(date -d '-15 minutes' +%s) --end-time $(date +%s)
CONFIRM: Before updating the event selector, emit and await:
  "CONFIRM: About to enable S3 data events on prod-org-trail. Data
   events are billed at $0.10 per 100,000 events. Proceed? (yes/no)"
```

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom. A "process of elimination" diagnosis erodes
  operator trust.
- NEVER trust `IsLogging: true` alone. The managed service does
  not fail the trail on bucket-policy rejection — it retries
  silently. Always cross-reference `LatestDeliveryTime` against
  the wall clock.
- NEVER conclude "the trail is broken" without checking
  `get-event-selectors`. The most common missing-events cause is
  that the operator expects data events (GetObject, InvokeFunction)
  that the event selector was never configured to capture.
- NEVER recommend deleting a member trail without checking for an
  org trail. The org trail shadows member trails — deleting the
  member trail does NOT restore the pre-org-trail behaviour; the
  org trail still captures everything.
- NEVER modify the bucket policy to remove the
  `s3:x-amz-acl: bucket-owner-full-control` condition. The
  condition ensures log files are owned by the bucket owner;
  removing it causes the CloudTrail service account to own the
  objects, breaking downstream Athena / Lake Formation queries.
- NEVER re-enable data events without flagging the cost. Data
  events are billed at $0.10 per 100,000 events (vs. free for the
  first copy of management events). High-volume S3 buckets can
  generate millions of GetObject events per hour.
- NEVER convert a single-region trail to multi-region without
  confirming the S3 bucket policy covers all account IDs that
  will deliver. The default policy covers the trail's home
  account; multi-region trails deliver from every region.
- NEVER disable KMS encryption on a trail to fix a delivery
  issue without first verifying the KMS key state. Disabling
  SSE-KMS changes the security posture; the proper fix is to
  re-enable the key.
- NEVER assume CloudTrail Lake and S3 trails share selectors.
  They are independent ingestion paths. Configuring one does
  NOT configure the other.
- NEVER recommend `update-trail` to fix a delivery issue without
  confirming the change will not break existing dashboards.
  Updating `--kms-key-id` or `--s3-bucket-name` re-encrypts or
  re-routes all future log delivery; existing Athena tables and
  GuardDuty detectors that point at the old bucket break.
- NEVER expect CloudTrail events to appear instantly. The
  typical delivery window is 5-15 minutes for management events;
  data events can take longer. Investigate only if the gap is
  > 15 minutes.
- NEVER use `lookup-events` for high-volume queries.
  `lookup-events` paginates slowly and is rate-limited. For
  sustained queries, use Athena on the S3 bucket or CloudTrail
  Lake `start-query`.
- NEVER assume a service logs in every region. A handful of
  regional services do not emit CloudTrail events in every
  region where they operate. Cross-reference the AWS docs.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`start-logging`, `stop-logging`, `update-trail`,
  `put-event-selectors`, `put-insight-selectors`, `enable-kms-key`),
  emit and await operator approval.
- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`describe-trails`, `get-trail-status`,
  `get-event-selectors`, `lookup-events`, `get-bucket-policy`,
  `describe-key`). Do not perform state-changing operations as
  diagnostic probes.
- **`start-logging`** is safe and non-disruptive; the trail
  resumes delivery within ~5 minutes.
- **`stop-logging`** is disruptive; the trail stops capturing
  events immediately. Only the operator should decide to stop.
- **`update-trail`** changes the trail configuration and may
  break downstream consumers (Athena tables, GuardDuty detectors,
  SIEM integrations). Always confirm the downstream impact with
  the operator.
- **`put-event-selectors`** changes which events are captured.
  Enabling data events incurs cost ($0.10 per 100,000 events).
  Confirm the cost impact with the operator before enabling.
- **`enable-kms-key`** is safe; re-enables encryption for all
  services that depend on the key, including CloudTrail.
- **Bucket policy edits** affect every consumer of the bucket.
  Tighten policy gradually; never deny-by-default without
  confirming no other service depends on the bucket.

## Remediation guidance

### For TRAIL_DISABLED
1. Identify who called StopLogging via `lookup-events`.
2. Restart the trail: `aws cloudtrail start-logging --name <trail>`.
3. If IaC-created, ensure the IaC template includes
   `enable_logging = true` (Terraform) or the equivalent
   CloudFormation property to prevent recurrence.

### For BUCKET_POLICY_BLOCKING
1. Add the canonical CloudTrail bucket policy statement
   (`cloudtrail.amazonaws.com` principal,
   `s3:GetBucketAcl`, `s3:ListBucket`, `s3:PutObject` with
   `bucket-owner-full-control` condition).
2. For org trails, ensure the Resource ARN covers the org ID
   (`o-<org-id>/*`).
3. Verify with `aws s3 ls` that log files begin landing within
   ~15 minutes.

### For KMS_KEY_DISABLED
1. Re-enable the key: `aws kms enable-key --key-id <id>`.
2. If the key is `PendingDeletion`, the key cannot be re-enabled
  within the deletion window; migrate the trail to a new key via
  `update-trail --kms-key-id <new-arn>`.

### For DATA_EVENTS_NOT_ENABLED
1. Add the data-event selector for the expected data source
   (S3, Lambda, DynamoDB).
2. Confirm the cost impact with the operator before enabling.
3. Verify with `lookup-events` 10-15 minutes after the change.

### For ORG_TRAIL_SHADOWS_MEMBER
1. Accept that events are in the org trail bucket (recommended
   for centralized audit).
2. If member-local delivery is required, keep both trails — the
   org trail delivers to the org bucket and the member trail
   delivers to the member bucket.

### For MULTI_REGION_SCOPE_GAP
1. Convert to multi-region:
   `aws cloudtrail update-trail --name <trail> --is-multi-region-trail`.
2. Verify with `lookup-events --region <other-region>`.

### For EVENT_SELECTOR_READONLY
1. Convert `ReadWriteType` to `All`:
   `put-event-selectors --event-selectors '[{"ReadWriteType": "All", "IncludeManagementEvents": true}]'`.

### For CW_LOGS_DELIVERY_DELAYED
1. Verify `CloudWatchLogsRoleArn` on the trail.
2. Verify the role trusts `cloudtrail.amazonaws.com` and has
   `logs:CreateLogStream`, `logs:PutLogEvents` on the log group.
3. Verify the log group exists and was not deleted.

### For LAKE_EDS_QUERY_ISSUE
1. Verify the EDS event selectors match the events being queried.
2. Verify the EDS billing mode has query budget.
3. Verify the EDS region matches the events being queried.

### For SERVICE_NOT_IN_REGION
1. Cross-reference the AWS CloudTrail documentation for the
   service-region combination.
2. If the service logs in us-east-1 only, query
   `lookup-events --region us-east-1`.

### For LOG_FILE_PREFIX_ERROR
1. Read `S3KeyPrefix` from `describe-trails`.
2. List the correct prefix: `aws s3 ls s3://<bucket>/<S3KeyPrefix>/AWSLogs/<account>/CloudTrail/`.

## Domain

AWS CloudOps / Governance — CloudTrail Audit Logging, Event
Selector Configuration, Organization Trail Topology, S3 Bucket
Policy for CloudTrail Delivery, KMS-Encrypted Log Files,
CloudTrail Lake Event Data Stores, CloudWatch Logs Delivery,
Multi-Region Trail Scope, Log File Validation.

## AWS documentation

- **AWS CloudTrail User Guide** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/
- **CloudTrail event selectors** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-management-and-data-events-with-cloudtrail.html
- **Organization trails** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html
- **S3 bucket policy for CloudTrail** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/create-s3-bucket-policy-for-cloudtrail.html
- **CloudTrail Lake** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake.html
- **Log file validation** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-log-file-validation-cli.html
- **CloudTrail Insights** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-insights-events-with-cloudtrail.html
- **KMS-encrypted log files** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/encrypting-cloudtrail-log-files-with-aws-kms.html
- **CloudTrail supported services by region** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-supported-services.html
