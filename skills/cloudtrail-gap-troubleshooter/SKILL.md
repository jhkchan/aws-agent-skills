---
name: cloudtrail-gap-troubleshooter
description: Diagnoses AWS CloudTrail logging gaps and missing events — events missing from a trail (data events vs management events, multi-region trail misconfiguration), a trail not logging at all (stopped
  trail, S3 bucket policy not allowing CloudTrail write, trail inadvertently deleted), log delivery delayed beyond the expected 5-15 minute window (CloudTrail Lake vs S3 delivery differences, org trail
  aggregation lag), CloudTrail Insights not detecting anomalies (Insights disabled, no dedicated S3 prefix, baseline period not yet elapsed), and cross-account / organization trails not logging for member
  accounts (delegated admin misconfiguration, member-account bucket policy). Emits a deterministic verdict (ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE) with the specific failure category and evidence
  from describe-trails / get-trail-status / lookup-events / list-insights-selectors / get-bucket-policy. Use when a CloudTrail trail is silent, events are missing from CloudTrail Lake or the S3 delivery,
  Insights is not.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline diagnosis works on supplied describe-trails / get-trail-status / get-bucket-policy JSON. Live-account
  diagnosis uses aws cloudtrail describe-trails, get-trail-status, lookup-events, get-insight-selectors, list-insights-selectors, aws s3api get-bucket-policy, aws organizations list-delegated-administrators,
  and aws logs filter-log-events (AWS CLI v2, SSO or key-based credentials).
keywords:
- CloudTrail
- audit logging
- data events
- management events
- missing events
- trail not logging
- log delivery delay
- CloudTrail Insights
- CloudTrail Lake
- organization trail
- delegated admin
- S3 bucket policy
- log file validation
- multi-region trail
tags:
- cloudtrail
- governance
- troubleshoot
- logging-gap
- audit
- compliance
- org-trail
- insights
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
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: Diagnosing why a CloudTrail trail is silent (no log files being delivered to S3), why specific API calls are missing from a trail (data events not configured, single-region trail in the wrong
    region), why log delivery is delayed beyond the expected 5-15 minute window, why CloudTrail Insights is not firing on suspicious write activity, or why an organization trail is not logging for one or
    more member accounts.
  activation_triggers:
  - CloudTrail missing events
  - CloudTrail not logging
  - CloudTrail trail stopped
  - CloudTrail log delivery delayed
  - CloudTrail data events missing
  - CloudTrail Insights not working
  - CloudTrail org trail gap
  - CloudTrail member account not logged
  - CloudTrail S3 bucket policy
  - CloudTrail lookup-events returns empty
  - CloudTrail audit gap
  invocation_schema: 'Input: either (a) a symptom description (trail name, observed gap, any error strings from the console or lookup-events), OR (b) a live-account scenario where the agent runs aws cloudtrail
    describe-trails / get-trail-status / lookup-events / list-insights-selectors / aws s3api get-bucket-policy to gather evidence. Output: a deterministic INCIDENT / VERDICT / ROOT_CAUSE / EVIDENCE / REMEDIATION
    block where VERDICT ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and ROOT_CAUSE names the specific failure category (MISSING_DATA_EVENTS / TRAIL_NOT_LOGGING / DELIVERY_DELAYED / INSIGHTS_DISABLED
    / ORG_TRAIL_GAP / MULTI_REGION_GAP / BUCKET_POLICY_BLOCKING) and the offending config element.'
---

# CloudTrail Gap Troubleshooter

## Activation

Activate this skill when the user reports a CloudTrail logging gap.
Trigger phrases: "CloudTrail missing events", "CloudTrail not
logging", "CloudTrail trail stopped", "CloudTrail log delivery
delayed", "CloudTrail data events missing", "CloudTrail Insights not
working", "CloudTrail org trail gap", "CloudTrail member account not
logged", "CloudTrail lookup-events returns empty".

## Mindset

**One-line takeaway:** "CloudTrail is logging but I can't find my
event" is almost always a data-events-vs-management-events
misunderstanding or a region/trail scope mismatch — NOT a CloudTrail
outage. Diagnose scope and configuration before assuming an outage.

Three facts make CloudTrail troubleshooting different from generic
service debugging:

- **Management events are on by default; data events are opt-in.**
  Management events log control-plane operations (CreateBucket,
  RunInstances, PutObject* NOT included). Data events log data-plane
  operations (GetObject, PutItem, Invoke). Most "missing events"
  complaints are data events that were never configured. The trail is
  working as designed; the operator's expectation is wrong.
- **A trail has TWO independent health signals.** `describe-trails`
  reports configuration (isMultiRegionTrail, isOrganizationTrail,
  includeGlobalServiceEvents, logFileValidationEnabled). It does NOT
  report whether the trail is actively logging — that comes from
  `get-trail-status` (isLogging, latestCloudWatchLogsDeliveryTime,
  latestDeliveryTime, latestDigestResultTime). Both must be consulted.
  A correctly-configured trail can be silently stopped.
- **CloudTrail Lake and CloudTrail S3 delivery are different
  pipelines with different latency.** S3 delivery averages 5 minutes
  but can take up to 15 minutes for management events (longer for
  data events). CloudTrail Lake ingestion is near-real-time (seconds
  to a few minutes) but only surfaces events that match the event
  data store's selector. A "missing event in Lake" might just not
  match the selector, while the same event IS in the S3 delivery.

## Quick reference — symptom to failure category

| Observed state | Failure category | First probe |
|---|---|---|
| Specific API call not found by `lookup-events` | MISSING_DATA_EVENTS / MULTI_REGION_GAP | Is the event source in the trail's management event filter? Is the trail multi-region? Is it a data event? |
| No log files delivered to S3 for hours; `get-trail-status` `isLogging: false` | TRAIL_NOT_LOGGING | `get-trail-status`; check S3 bucket policy for `cloudtrail:PutObject` deny |
| Log files arriving but with multi-hour latency | DELIVERY_DELAYED | Compare `latestDeliveryTime` to `now`; check org trail aggregation |
| Suspicious write activity but no Insights finding | INSIGHTS_DISABLED | `list-insights-selectors` — are Insights selectors configured? Is the trail `isLogging`? |
| Org trail missing events from specific member account(s) | ORG_TRAIL_GAP | Is the member account in the org? Is there a delegated admin? Is there a member-account S3 bucket with a conflicting trail? |
| S3 bucket policy denies CloudTrail writes | BUCKET_POLICY_BLOCKING | `aws s3api get-bucket-policy` — look for an explicit Deny on `cloudtrail:PutObject` or a missing Allow |

See the ordered steps below for the full diagnostic walk.

## Quick navigation

- **Step 0** — Capture the failure signal (trail name, account scope,
  expected vs observed event).
- **Step 1** — Map the symptom to a category letter (A-G).
- **Step 2** — MISSING_DATA_EVENTS diagnostic.
- **Step 3** — TRAIL_NOT_LOGGING diagnostic.
- **Step 4** — DELIVERY_DELAYED diagnostic.
- **Step 5** — INSIGHTS_DISABLED diagnostic.
- **Step 6** — ORG_TRAIL_GAP diagnostic.
- **Step 7** — MULTI_REGION_GAP / BUCKET_POLICY_BLOCKING diagnostic.
- **Step 8** — Root-cause catalog (top patterns + canonical fixes).
- **Step 9** — Verify the fix.
- **Step 10** — Decide VERDICT (ROOT_CAUSE_FOUND / NEED_MORE_INFO / ESCALATE).

## Process — Diagnostic decision tree (apply in order)

### Step 0: Capture the failure signal

Gather these four pieces. Each step below branches on which is present.

| Signal | Source | Why required |
|---|---|---|
| **Trail name(s)** | User-provided or `aws cloudtrail describe-trails` | All describe-trails/get-trail-status calls need this |
| **Scope of the gap** (account / region / event) | User-provided symptom | Narrows from "events missing" to a specific dimension |
| **Expected event source + API** | User-provided | Determines data-events vs management-events |
| **Trail status + latest delivery time** | `aws cloudtrail get-trail-status --name <trail>` | Drives the TRAIL_NOT_LOGGING vs DELIVERY_DELAYED split |

If the user has not provided the trail name, output:

```text
INCIDENT: <account> — <symptom>
VERDICT: NEED_MORE_INFO
REASON: Cannot diagnose without the trail name. Identify the trail
with: aws cloudtrail describe-trails --query 'trailList[*].
  {name:Name,multiRegion:IsMultiRegionTrail,org:IsOrganizationTrail,
  logging:''}
MISSING:
  - Trail name (or region if you suspect a single-region trail)
  - Expected event source and API name (e.g., s3.amazonaws.com GetObject)
  - Time window for the missing event
```

If the user reports "CloudTrail is broken" but does not know which
trail or which event, ask for the account ID and region. Then run:

```bash
aws cloudtrail describe-trails --query 'trailList[*].{name:Name,multiRegion:IsMultiRegionTrail,org:IsOrganizationTrail,s3Bucket:S3BucketName,kmsKey:KmsKeyId}'

# Status per trail (one call per trail):
aws cloudtrail get-trail-status --name <trail-name>

# Recent events to confirm whether ANY events are flowing:
aws cloudtrail lookup-events --max-results 5 --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ)
```

### Step 1: Identify the symptom category

Map the observed state to one of seven categories. Each category has a
different diagnostic walk in Steps 2-7.

| Category | Signature | Diagnostic step |
|---|---|---|
| **A. MISSING_DATA_EVENTS** | Operator expects a data-plane event (GetObject, PutItem, Invoke) in lookup-events or S3 delivery; not present; trail is logging management events fine | Step 2 |
| **B. TRAIL_NOT_LOGGING** | `get-trail-status` returns `isLogging: false`; no log files in S3 for hours; OR trail is missing entirely from describe-trails | Step 3 |
| **C. DELIVERY_DELAYED** | `isLogging: true` but `latestDeliveryTime` lags `now` by > 15 min (management) or > 1h (data events) | Step 4 |
| **D. INSIGHTS_DISABLED** | Operator expects an Insights finding for anomalous write activity; none appears; baseline period elapsed | Step 5 |
| **E. ORG_TRAIL_GAP** | Org trail logs management account and most members; specific member account's events are missing | Step 6 |
| **F. MULTI_REGION_GAP** | Trail is single-region; operator expects events from a different region (e.g., `us-west-2` events missing on a `us-east-1` single-region trail) | Step 7 |
| **G. BUCKET_POLICY_BLOCKING** | Trail claims `isLogging: true` but no log files land in S3; bucket policy has an explicit Deny on `cloudtrail:PutObject` or a missing Allow | Step 7 |

**Scope rule.** When multiple categories apply, narrow from broadest
to most specific. A TRAIL_NOT_LOGGING trail produces no events at all;
resolve B before diagnosing A or F. ORG_TRAIL_GAP only applies if the
trail is `IsOrganizationTrail: true`.

### Step 2: MISSING_DATA_EVENTS diagnostic

The operator expects a data-plane event (S3 GetObject/PutObject,
DynamoDB GetItem/PutItem, Lambda Invoke) in CloudTrail but it is
absent. The trail is logging management events correctly.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| S3 GetObject / PutObject missing | S3 data events not configured on the trail (default is off) | `aws cloudtrail get-event-selectors --trail-name <trail>`; look for `ReadWriteType: All` or `DataResources` covering `arn:aws:s3:::` |
| Lambda Invoke missing | Lambda data events not configured | `get-event-selectors`; look for `DataResources` with `Type: AWS::Lambda::Function` OR `IncludeManagementEvents: true` + advanced event selectors for Lambda |
| DynamoDB GetItem / PutItem missing | DynamoDB data events not configured | `get-event-selectors`; look for `DataResources` with `Type: AWS::DynamoDB::Table` |
| All data events missing | Trail has only management event selectors (default) | Same as above — no `DataResources` entries |
| Some S3 buckets logged, others not | Event selector has a specific bucket prefix; other buckets excluded | Check the `DataResources.Values` list — only the listed ARN prefixes are logged |
| Data event selector present but event still missing | CloudWatch metric filter or Lake ingestion has its own filter | Verify directly in S3 delivery (`aws s3 ls s3://<bucket>/AWSLogs/<account>/CloudTrail/<region>/YYYY/MM/DD/`) |
| Management event is missing (not data) | Trail has advanced event selectors that exclude the event source | `get-event-selectors` — check for `ExcludeManagementEventSources` |

**Diagnostic walk:**

1. **Confirm whether the missing event is a management event or a data
   event.** Management events (default) log control-plane operations:
   CreateBucket, RunInstances, CreateUser, AttachRolePolicy. Data
   events log data-plane operations: GetObject, PutItem, Invoke.
   Quick reference:
   - S3 — CreateBucket / PutBucketPolicy = management. GetObject /
     PutObject / DeleteObject = data.
   - Lambda — CreateFunction / UpdateFunctionCode = management.
     Invoke = data.
   - DynamoDB — CreateTable = management. GetItem / PutItem /
     Query = data.
2. **Read the trail's event selectors:**
   `aws cloudtrail get-event-selectors --trail-name <trail>`.
3. **Interpret the selectors:**
   - `ReadWriteType: All` + `IncludeManagementEvents: true` — logs
     both management and data events (for the resources in
     `DataResources`).
   - `ReadWriteType: ReadOnly` or `WriteOnly` — limits to one
     direction; a missing read event might just be filtered.
   - `DataResources` empty / absent — data events are NOT configured.
4. **Verify by directly listing the S3 log objects** around the event
   time:
   `aws s3 ls s3://<bucket>/AWSLogs/<account>/CloudTrail/<region>/<YYYY>/<MM>/<DD>/`
   and grep the JSON.gz files for the expected event name.
5. **For Lambda Invoke specifically:** Lambda data events can be
   configured at the function level (only specific functions) or at
   the account level (all functions). The selector `Values` list
   controls this; `arn:aws:lambda` logs all functions in the region.

**Diagnostic commands:**

```bash
# Read the trail's event selectors:
aws cloudtrail get-event-selectors --trail-name <trail>

# Read advanced event selectors (mutually exclusive with basic):
aws cloudtrail get-insight-selectors --trail-name <trail>
# (advanced event selectors are returned by get-event-selectors when
# the trail uses advanced mode)

# Search the S3 log delivery directly for the expected event:
aws s3api list-objects-v2 \
  --bucket <bucket> \
  --prefix "AWSLogs/<account>/CloudTrail/<region>/$(date -u +%Y/%m/%d)/" \
  --query 'Contents[*].Key' --output text | tr '\t' '\n' | tail -10

# Download a specific log and grep (local tools):
aws s3 cp s3://<bucket>/<key> - | gzip -d | jq '.Records[] | select(.eventName=="GetObject")'

# Or use CloudTrail Lake to query across all regions/accounts:
aws cloudtrail query --query-statement "SELECT eventName, eventTime, userIdentity.arn FROM <eds-id> WHERE eventName='GetObject' AND eventTime > '2026-08-09T00:00:00Z'"
```

**Common fix patterns:**

- **S3 data events not configured:** add a basic event selector with
  `ReadWriteType: All` and a `DataResources` entry for
  `arn:aws:s3`. Or use advanced event selectors for granular control
  (per-bucket, read-only vs write-only).
- **Lambda data events:** same pattern. `DataResources` with
  `Type: AWS::Lambda::Function`, `Values: ["arn:aws:lambda"]`.
- **DynamoDB data events:** `DataResources` with
  `Type: AWS::DynamoDB::Table`, `Values: ["arn:aws:dynamodb"]`.
- **Too noisy?** Use advanced event selectors to limit to specific
  buckets / tables / functions, or to log only `WriteOnly` data
  events (recommended for cost control).

**Cost warning.** Data events generate significantly more log volume
than management events. S3 data events on a busy bucket can multiply
CloudTrail costs 10-100x. Always scope `DataResources` to specific
buckets / tables / functions where possible, and prefer `WriteOnly`
for data events unless you have a specific audit need for reads.

### Step 3: TRAIL_NOT_LOGGING diagnostic

The trail is not delivering any events. Either `get-trail-status`
reports `isLogging: false`, or `isLogging: true` but no log files are
appearing in S3.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `get-trail-status` returns `isLogging: false` | Trail was explicitly stopped (via `stop-logging`) or never started after creation | `aws cloudtrail start-logging --name <trail>`; verify status flips |
| `get-trail-status` returns `isLogging: false`, `latestDeliveryAttemptSucceeded` empty | Trail was created but logging was never started (this happens if CloudTrail was created via IaC without the start-logging call) | Same fix: `start-logging --name <trail>` |
| Trail missing entirely from `describe-trails` | Trail was deleted (CloudTrail retains trail config for 30 days; `lookup-events` still works for events already delivered) | CloudTrail → Trails in console; check `describe-trails` with `--show-shadow-trails` to see deleted trails |
| `isLogging: true` but `latestDeliveryTime` lagging hours / empty | S3 bucket policy blocking CloudTrail writes | Step 7 (BUCKET_POLICY_BLOCKING) |
| `isLogging: true` but KMS access denied errors in CloudTrail event history | KMS key policy does not allow CloudTrail to `kms:GenerateDataKey` | Verify KMS key policy includes `cloudtrail.amazonaws.com` as Principal with `kms:GenerateDataKey*` and `kms:DescribeKey` |
| CloudTrail event history shows events but S3 delivery has none since a recent change | Trail was recreated or modified; new trail has a new `LogFilePrefix` or bucket; old logs remain in old prefix | Compare `S3BucketName` and `S3KeyPrefix` before and after the change |
| Organization trail `isLogging: false` in member account | Org trail is being overridden by a member-account trail (a member account can stop logging on an org trail) | In the member account: `describe-trails --query 'trailList[*].{name:Name,isOrg:IsOrganizationTrail,logging:''}`; check for shadow trails |

**Diagnostic walk:**

1. **Read `get-trail-status` first.** The `isLogging` flag is the
   single most important signal. `false` means the trail is stopped;
   `true` means it is attempting to deliver (delivery may still fail
   due to bucket policy or KMS).
2. **If `isLogging: false`:** restart logging:
   `aws cloudtrail start-logging --name <trail>`. Then re-check status.
3. **If `isLogging: true` but no delivery:** check the S3 bucket
   policy (Step 7), the KMS key policy, and the bucket's region (must
   match or be a supported cross-region setup).
4. **If `describe-trails` does not list the trail:** check shadow
   trails (`--show-shadow-trails`) — CloudTrail retains deleted trail
   configuration for 30 days. Recreate the trail if needed.
5. **For org trails:** the management account owns the org trail.
   Member accounts see it as a "shadow" trail. If a member account
   stops logging on the shadow, that member's events stop being
   delivered to the org trail's S3 bucket. Re-start logging from
   the management account or the delegated admin.

**Diagnostic commands:**

```bash
# Trail status (the canonical health signal):
aws cloudtrail get-trail-status --name <trail>

# Trail configuration:
aws cloudtrail describe-trails --trail-name-list <trail> \
  --query 'trailList[0].{name:Name,multiRegion:IsMultiRegionTrail,org:IsOrganizationTrail,s3:S3BucketName,prefix:S3KeyPrefix,kms:KmsKeyId,validation:LogFileValidationEnabled}'

# If the trail is missing, look for shadow (deleted) trails:
aws cloudtrail describe-trails --show-shadow-trails \
  --query 'trailList[*].{name:Name,shadow:IsShadowTrail,logging:IsLogging,region:HomeRegion}'

# Verify the bucket policy allows CloudTrail write:
aws s3api get-bucket-policy --bucket <bucket> --query Policy --output text | jq '.Statement[] | select(.Principal.Service=="cloudtrail.amazonaws.com" or .Principal.Service=="{" .Service="cloudtrail.amazonaws.com" "}")'

# Verify KMS key policy (if KMSKeyId is set):
aws kms get-key-policy --key-id <key-id> --policy-name default \
  --query Policy --output text | jq '.Statement[] | select(.Principal.Service=="cloudtrail.amazonaws.com")'

# Restart logging if stopped:
aws cloudtrail start-logging --name <trail>
```

**Common fix patterns:**

- **Trail stopped:** `aws cloudtrail start-logging --name <trail>`.
  Add a CloudWatch alarm on `NumberOfNotificationsDelivered` metric
  to alert when the trail stops delivering.
- **Bucket policy blocking:** see Step 7.
- **KMS key policy missing CloudTrail:** add a statement allowing
  `cloudtrail.amazonaws.com` to `kms:GenerateDataKey*` and
  `kms:DescribeKey` on the key ARN, with `StringEquals` on
  `kms:ViaService` if you want to scope by region.
- **Trail deleted:** recreate from infrastructure-as-code. If you
  don't have IaC, recreate manually from the console or CLI with the
  same S3 bucket, KMS key, and event selectors.

### Step 4: DELIVERY_DELAYED diagnostic

Log files are arriving in S3 but with multi-minute or multi-hour
latency beyond CloudTrail's documented delivery targets.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Management events delayed 15-30 min, all accounts | CloudTrail S3 delivery averages 5 min but can be up to 15 min in normal operation; > 15 min is unusual | Compare `latestDeliveryTime` to `now`; check AWS Health dashboard for CloudTrail service events |
| Data events delayed 30-60 min | Data event delivery is inherently higher-latency than management events due to volume | Expected; not a defect unless > 1 hour consistently |
| All events delayed > 1 hour | CloudTrail service issue OR S3 bucket in a different region with high cross-region latency | Check `S3BucketName` region vs trail region |
| Org trail events from member accounts delayed vs management account | Org trail aggregation introduces a per-account delay; member account events land in the org bucket ~5-15 min after the management account's events for the same window | Expected; if > 30 min, check for org trail quota issues |
| CloudTrail Lake shows events immediately but S3 delivery lags | Different pipelines — Lake is near-real-time, S3 is batched every ~5 min | Not a defect; if you need real-time, use Lake or EventBridge |
| One trail delayed, another fine in the same account | The delayed trail writes to a bucket in a different region or with KMS that is rate-limited | Compare trail configs; check KMS key CloudWatch metrics for throttle |

**Diagnostic walk:**

1. **Compare `latestDeliveryTime` to `now`:**
   `aws cloudtrail get-trail-status --name <trail>` — the
   `latestDeliveryTime` field shows the last successful S3 write.
2. **Check the S3 bucket region** vs the trail's home region:
   `aws s3api get-bucket-location --bucket <bucket>` vs
   `describe-trails[].HomeRegion`. A bucket in a different region
   adds cross-region replication latency.
3. **Check the AWS Health dashboard** for CloudTrail service events
   in the affected region.
4. **For org trails:** verify the management account's trail is
   delivering on time; member account events follow by ~5-15 min.
5. **If Lake is fast and S3 is slow:** this is by design. If you
   need real-time alerting, route through EventBridge instead of S3.

**Diagnostic commands:**

```bash
aws cloudtrail get-trail-status --name <trail> \
  --query '{isLogging:IsLogging,latestDelivery:LatestDeliveryTime,latestDigest:LatestDigestDeliveryTime,latestCWL:LatestCloudWatchLogsDeliveryTime,started:StartLoggingTime,stopped:StopLoggingTime}'

# Bucket region:
aws s3api get-bucket-location --bucket <bucket>

# Trail region:
aws cloudtrail describe-trails --trail-name-list <trail> \
  --query 'trailList[0].HomeRegion'

# If you have an org trail, check management-account delivery time vs
# member account; member delays of 5-15 min are normal.
aws cloudtrail lookup-events --start-time $(date -u -v-30M +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) --max-results 5 \
  --query 'Events[*].{time:EventTime,source:CloudTrailEvent}'

# For org trail aggregation issues, check org-wide trail:
aws cloudtrail describe-trails --query 'trailList[?IsOrganizationTrail].{name:Name,s3:S3BucketName,isLogging:IsLogging}'
```

**Common fix patterns:**

- **Bucket in a different region:** move the bucket to the trail's
  home region, OR accept the latency.
- **CloudTrail service issue:** no operator fix; monitor the AWS
  Health dashboard. Open a support ticket if the issue persists
  beyond 1 hour.
- **Org trail aggregation lag:** expected; not a defect.
- **Lake vs S3 mismatch:** use Lake for real-time needs; S3 for
  long-term archive.

### Step 5: INSIGHTS_DISABLED diagnostic

The operator expects a CloudTrail Insights finding for anomalous write
management activity (e.g., spike in `PutBucketPolicy` or
`AttachRolePolicy` calls). No finding appears.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| No Insights findings ever | Insights not enabled on the trail | `aws cloudtrail get-insight-selectors --trail-name <trail>` — should return `InsightsEnabled: true` with at least one selector |
| Insights enabled but no findings for the first 7 days of a new trail | Insights requires a baseline period (~7 days of management events) before it can detect anomalies | Expected; wait for baseline to complete |
| Insights enabled but no findings for write data events | Insights only supports write MANAGEMENT events by default; data events are not analyzed for anomalies | Expected limitation; no current fix |
| Insights was enabled recently after being disabled | Re-enabling Insights resets the baseline; another 7-day baseline period is required | Expected; wait |
| Insights S3 prefix missing or misconfigured | Insights findings are delivered to `<prefix>/CloudTrail-Insight/<account>/...`; if the bucket policy restricts the prefix, findings cannot be written | Verify the bucket policy allows writes to the CloudTrail-Insight prefix |
| Insights configured on a stopped trail | Insights requires the trail to be `IsLogging: true` | Restart logging (Step 3) |

**Diagnostic walk:**

1. **Read the Insights selectors:**
   `aws cloudtrail get-insight-selectors --trail-name <trail>`.
2. **Interpret the response:**
   - `InsightsEnabled: false` → Insights is OFF. Enable it.
   - `InsightsEnabled: true` with `EventSource: "s3.amazonaws.com"`
     `EventType: "AwsApiCall"` → Insights for S3 API write anomalies.
   - `InsightsEnabled: true` with `EventSource: "iam.amazonaws.com"`
     → Insights for IAM API write anomalies.
3. **Check whether the baseline period has elapsed.** Insights
   requires ~7 days of management events to establish a baseline. If
   the trail was created less than 7 days ago, or Insights was just
   enabled, no findings will appear.
4. **Verify the trail is logging** — Insights only processes events
   from an actively logging trail. If `get-trail-status` shows
   `isLogging: false`, fix Step 3 first.
5. **Check the S3 bucket for Insights findings** directly:
   `aws s3 ls s3://<bucket>/CloudTrail-Insight/` — if the prefix
   does not exist, no findings have been delivered.

**Diagnostic commands:**

```bash
aws cloudtrail get-insight-selectors --trail-name <trail>
# Expected: {"InsightSelectors":[{"InsightType":"ApiCallRateInsight"},{"InsightType":"ApiErrorRateInsight"}]}

aws cloudtrail list-insights-selectors --trail-name <trail>
# (newer API; returns per-event-source selectors if configured)

# Verify the trail is logging (Insights requires active logging):
aws cloudtrail get-trail-status --name <trail> --query 'IsLogging'

# Check for Insights findings in S3:
aws s3 ls s3://<bucket>/CloudTrail-Insight/ --recursive | head

# Or query Insights findings via Lake (if integrated):
aws cloudtrail query --query-statement "SELECT eventID, eventName, eventTime FROM <eds-id> WHERE eventType='AwsInsightInsight'"
```

**Common fix patterns:**

- **Insights not enabled:**
  `aws cloudtrail put-insight-selectors --trail-name <trail>
  --insight-selectors '[{"InsightType":"ApiCallRateInsight"},{"InsightType":"ApiErrorRateInsight"}]'`.
- **Baseline period not elapsed:** wait 7 days; document this in
  onboarding runbooks so operators do not file false "Insights broken"
  tickets.
- **Need Insights for specific event sources:** use
  `list-insights-selectors` API (2024+) to configure per-source
  selectors like `iam.amazonaws.com` for IAM write anomalies.
- **Insights bucket prefix:** CloudTrail writes Insights findings to
  `<S3KeyPrefix>/CloudTrail-Insight/`. The bucket policy must allow
  `cloudtrail:PutObject` on this prefix.

### Step 6: ORG_TRAIL_GAP diagnostic

The organization trail logs the management account and most member
accounts. Specific member account events are missing.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| All member accounts missing | Org trail is `IsLogging: false` in the management account | `get-trail-status` in the management account |
| Specific member account missing, others fine | Member account has a SHADOW trail that is `IsLogging: false`; a member can stop logging on an org trail | In the member account: `describe-trails`; look for `IsShadowTrail: true` and stop it from overriding |
| New member accounts not being logged | Member account is enrolled in the org but the org trail was created before auto-enable; the new account needs logging started manually | `aws cloudtrail start-logging --name <org-trail>` from the member account, OR enable org-wide auto-start via Organizations |
| Member account not in the org | Account was removed from Organizations; the org trail no longer covers it | `aws organizations list-accounts` — verify the account is ACTIVE |
| Delegated admin account configured but trail is in management account | Confusion about which account owns the org trail; the trail must be in the management account OR a delegated admin account — not both | Check both accounts for `IsOrganizationTrail: true`; only one should own it |
| Member account has its own trail that overrides the org trail | Member account's own trail shadows the org trail; the org trail stops logging in that member | Disable the member account's own trail OR accept that the member's events go to the member's bucket instead of the org bucket |
| Service control policy (SCP) blocking CloudTrail in a member | An SCP denies `cloudtrail:PutEventSelectors` or related APIs in the member; CloudTrail cannot configure logging | `aws organizations describe-policy --policy-id <scp-id>`; check for CloudTrail denies |

**Diagnostic walk:**

1. **Confirm the trail is an org trail:**
   `describe-trails --query 'trailList[?IsOrganizationTrail]'`.
2. **Check the trail is logging in the management account:**
   `aws cloudtrail get-trail-status --name <trail>` (run with
   management-account credentials).
3. **For the affected member account:** switch credentials to the
   member account and run `describe-trails --show-shadow-trails`.
   Look for the org trail as a shadow trail (`IsShadowTrail: true`).
   If the shadow is `IsLogging: false`, the member is overriding the
   org trail's logging state.
4. **Verify the member account is still in the org:**
   `aws organizations list-accounts --query 'Accounts[?Id==<member-acct-id>].Status'`.
   Status must be `ACTIVE`. A `SUSPENDED` account stops logging.
5. **Check for a delegated admin:**
   `aws organizations list-delegated-administrators --service-principal cloudtrail.amazonaws.com`.
   If a delegated admin is configured, the org trail must be in that
   account, not the management account. Confusion here leads to two
   org trails (one in each), and one of them silently stops.
6. **Check for SCPs** that might block CloudTrail in the member
   account.

**Diagnostic commands:**

```bash
# Management account:
aws cloudtrail describe-trails --query 'trailList[?IsOrganizationTrail].{name:Name,isLogging:IsLogging,s3:S3BucketName,homeRegion:HomeRegion}'
aws cloudtrail get-trail-status --name <org-trail>

# Delegated admin check:
aws organizations list-delegated-administrators \
  --service-principal cloudtrail.amazonaws.com \
  --query 'DelegatedAdministrators[*].{id:Id,name:AccountName,email:EmailAddress}'

# Member account (use member-account profile):
aws cloudtrail describe-trails --show-shadow-trails \
  --query 'trailList[*].{name:Name,shadow:IsShadowTrail,logging:IsLogging,isOrg:IsOrganizationTrail}'
aws cloudtrail get-trail-status --name <org-trail>

# Verify member account is in the org and ACTIVE:
aws organizations list-accounts --query 'Accounts[?Id==`<member-acct-id>`].{id:Id,status:Status,name:Name}'

# Check SCPs applied to the member account's OU:
aws organizations list-policies-for-target --target-id <member-or-ou-id> \
  --filter SERVICE_CONTROL_POLICY
```

**Common fix patterns:**

- **Org trail stopped in management account:** restart via
  `aws cloudtrail start-logging --name <org-trail>` with management
  account credentials.
- **Member shadow trail stopped:** in the member account, run
  `aws cloudtrail start-logging --name <org-trail-name>` to re-align
  with the org. (Yes — start-logging works on a shadow trail in the
  member account.)
- **Delegated admin confusion:** consolidate to ONE org trail in
  EITHER the management account OR the delegated admin. Not both.
- **New member not auto-enabled:** enable Organizations-aware trail
  management via the management account's CloudTrail console
  ("Apply trail to all accounts in the organization" + "Enable for
  new accounts"). Or script `start-logging` on each new member.
- **SCP blocking CloudTrail:** add an exception to the SCP for
  `cloudtrail:*` from the CloudTrail service principal.

### Step 7: MULTI_REGION_GAP and BUCKET_POLICY_BLOCKING diagnostics

Two remaining categories share this step because they both appear as
"events missing" or "no delivery."

### 7a. MULTI_REGION_GAP

The trail is single-region (`IsMultiRegionTrail: false`). Events from
other regions are not logged.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Events from `us-west-2` missing; trail in `us-east-1` only | Trail is single-region; `IsMultiRegionTrail: false` | `describe-trails --query 'trailList[*].{name:Name,multi:IsMultiRegionTrail,home:HomeRegion}'` |
| Global service events (IAM, STS) missing | `IncludeGlobalServiceEvents: false`, OR trail is single-region and global events are not being delivered | `describe-trails --query 'trailList[*].IncludeGlobalServiceEvents'` |
| Trail is multi-region but events from one region still missing | CloudTrail service issue in that specific region | Check AWS Health dashboard; `lookup-events --region <region>` |

**Diagnostic commands:**

```bash
aws cloudtrail describe-trails --trail-name-list <trail> \
  --query 'trailList[0].{multi:IsMultiRegionTrail,globalEvents:IncludeGlobalServiceEvents,home:HomeRegion}'

# Search a specific region directly:
aws cloudtrail lookup-events --region us-west-2 \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
  --max-results 5
```

**Fix:**

- Convert to a multi-region trail:
  `aws cloudtrail update-trail --name <trail> --is-multi-region-trail`.
  Also `--include-global-service-events` if IAM/STS events are needed.
- Global service events (IAM, STS, Route 53) are logged only in the
  region where CloudTrail considers them "global" (us-east-1 for
  commercial, us-gov-west-1 for GovCloud). A single-region trail in
  any other region will not capture them.

### 7b. BUCKET_POLICY_BLOCKING

The trail claims `isLogging: true` but no log files land in S3.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Bucket policy has explicit `Deny` on `cloudtrail:PutObject` | A restrictive bucket policy added later blocks CloudTrail | `aws s3api get-bucket-policy --bucket <bucket>`; grep for `cloudtrail:PutObject` in Deny statements |
| Bucket policy missing the Allow for `cloudtrail.amazonaws.com` | Trail was created before the bucket policy was finalized; or the policy was accidentally removed | Same — look for an Allow statement with `Principal.Service: cloudtrail.amazonaws.com` |
| KMS key policy missing CloudTrail | KMS key policy does not allow `cloudtrail.amazonaws.com` to `kms:GenerateDataKey*` | `aws kms get-key-policy --key-id <key-id> --policy-name default` |
| Bucket in a different account | Cross-account bucket policy requires the CloudTrail account to be listed in the bucket policy's `Principal` | Verify the bucket's account vs the trail's account; bucket policy must allow the trail's account |

**Diagnostic walk:**

1. **Read the bucket policy:**
   `aws s3api get-bucket-policy --bucket <bucket> --query Policy --output text`.
2. **Look for the canonical CloudTrail Allow statement:**
   ```json
   {
     "Effect": "Allow",
     "Principal": {"Service": "cloudtrail.amazonaws.com"},
     "Action": "s3:GetBucketAcl",
     "Resource": "arn:aws:s3:::<bucket>"
   },
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
   Both statements are required. The `bucket-owner-full-control`
   condition is a common omission that breaks delivery.
3. **Check for explicit Deny statements** that override the Allow.
4. **If KMS is configured:** verify the KMS key policy has a
   statement allowing `cloudtrail.amazonaws.com` to
   `kms:GenerateDataKey*` and `kms:DescribeKey`.
5. **For cross-account bucket:** the bucket's account must have the
   Allow with the trail's account ID in the `Resource` ARN path.

**Diagnostic commands:**

```bash
# Read the bucket policy:
aws s3api get-bucket-policy --bucket <bucket> --query Policy --output text | jq .

# Verify CloudTrail Allow statements:
aws s3api get-bucket-policy --bucket <bucket> --query Policy --output text \
  | jq '.Statement[] | select(.Principal.Service=="cloudtrail.amazonaws.com" or (.Principal.Service // "" | tostring | contains("cloudtrail")))'

# Verify KMS key policy (if KMSKeyId is set on the trail):
aws kms get-key-policy --key-id <key-id> --policy-name default --query Policy --output text \
  | jq '.Statement[] | select(.Principal.Service=="cloudtrail.amazonaws.com")'

# Check the most recent log file delivery:
aws s3 ls s3://<bucket>/AWSLogs/<account>/CloudTrail/ --recursive \
  | sort | tail -5
```

**Common fix patterns:**

- **Missing Allow:** add the canonical CloudTrail statements (AWS
  docs: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/create-s3-bucket-policy-for-cloudtrail.html).
- **Explicit Deny:** remove the Deny or scope it to not apply to the
  CloudTrail prefix.
- **Missing `bucket-owner-full-control` ACL condition:** add it to
  the PutObject Allow statement. Without it, CloudTrail writes objects
  owned by the CloudTrail service principal, not the bucket owner —
  the bucket owner cannot read or delete the logs.
- **Cross-account bucket:** the bucket policy must include the trail's
  account ID in the Resource ARN path, e.g.,
  `arn:aws:s3:::<bucket>/AWSLogs/<trail-account-id>/CloudTrail/*`.
- **KMS key policy missing CloudTrail:** add a statement allowing
  `cloudtrail.amazonaws.com` to `kms:GenerateDataKey*` on the key ARN,
  with `StringEquals` on `kms:ViaService` if you want to scope by region.

### Step 8: Map to root-cause catalog

After the walk identifies the category, cross-reference with this
catalog.

| # | Root cause | Category | Fix pattern |
|---|---|---|---|
| 1 | Data events not configured (S3 / Lambda / DynamoDB) | MISSING_DATA_EVENTS | Add `DataResources` to the event selectors; scope by ARN prefix |
| 2 | Trail stopped (`isLogging: false`) | TRAIL_NOT_LOGGING | `aws cloudtrail start-logging --name <trail>`; add a CloudWatch alarm |
| 3 | Trail deleted | TRAIL_NOT_LOGGING | Recreate from IaC; `--show-shadow-trails` shows the old config |
| 4 | S3 bucket policy missing CloudTrail Allow or explicit Deny | BUCKET_POLICY_BLOCKING | Add the canonical CloudTrail Allow statements with `bucket-owner-full-control` condition |
| 5 | KMS key policy missing CloudTrail principal | BUCKET_POLICY_BLOCKING | Add KMS statement allowing `cloudtrail.amazonaws.com` `kms:GenerateDataKey*` |
| 6 | Single-region trail; events from other regions missing | MULTI_REGION_GAP | `update-trail --is-multi-region-trail` + `--include-global-service-events` |
| 7 | Insights not enabled | INSIGHTS_DISABLED | `put-insight-selectors` with `ApiCallRateInsight` + `ApiErrorRateInsight` |
| 8 | Insights baseline period not elapsed | INSIGHTS_DISABLED | Wait 7 days after enabling; document in onboarding |
| 9 | Org trail shadow stopped in member account | ORG_TRAIL_GAP | In the member account: `start-logging --name <org-trail>` |
| 10 | Delegated admin confusion (two org trails) | ORG_TRAIL_GAP | Consolidate to ONE org trail in either management OR delegated admin |
| 11 | Trail never started after creation (IaC) | TRAIL_NOT_LOGGING | Call `start-logging` explicitly; add to IaC (Terraform `aws_cloudtrail` does NOT auto-start; the `start_logging` resource must be included) |
| 12 | Org trail not auto-enabled for new members | ORG_TRAIL_GAP | Enable "Apply to all accounts" + "Enable for new accounts" in the CloudTrail console, or script start-logging on new members |

### Step 9: Verify the fix

Before declaring ROOT_CAUSE_FOUND, validate the proposed fix:

- **For start-logging fixes:** re-read `get-trail-status` and verify
  `isLogging: true` and `latestDeliveryTime` advances.
- **For event-selector fixes:** make a test API call (e.g.,
  `aws s3 cp /tmp/test s3://<bucket>/cloudtrail-test/`) and verify
  it appears in `lookup-events` within 5-15 minutes.
- **For bucket-policy fixes:** re-read the bucket policy and confirm
  the Allow statements are present; then wait 5-15 min for the next
  delivery window.
- **For org trail fixes:** check `get-trail-status` in both the
  management account and the affected member account.
- **For multi-region fixes:** make a test call in a previously-missing
  region and verify via `lookup-events --region <region>`.

### Step 10: Decide — ROOT_CAUSE_FOUND vs NEED_MORE_INFO vs ESCALATE

- **ROOT_CAUSE_FOUND.** The walk identified a specific category and a
  specific configuration element (event selector, bucket policy
  statement, trail status, Insights selector, org trail ownership).
  Output REMEDIATION with the exact change.
- **NEED_MORE_INFO.** The walk reached a step where the operator
  cannot supply evidence (e.g., bucket policy access requires
  s3:GetBucketPolicy which the operator does not have). Output the
  list of missing inputs.
- **ESCALATE.** The walk identifies a cause outside the operator's
  scope: the S3 bucket is owned by another team, the KMS key is
  managed by the security team, the org trail is owned by the
  management account and the operator only has member-account
  credentials. Output the escalation target and the specific request.

## Output format

```text
INCIDENT: <account> / <trail-name> — <symptom>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <category name> — <specific failing config element>
EVIDENCE:
  - describe-trails: <field>
  - get-trail-status: <field>
  - get-event-selectors: <field>
  - get-bucket-policy: <field>
  - lookup-events: <result count or sample>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <specific config change with field name>
  2. <verification command>
  3. <post-apply monitoring>
```

### Worked example — S3 data events not configured

```text
INCIDENT: 111111111111 / corp-trail — operator expects GetObject events
for audit; lookup-events returns zero GetObject events for any S3 bucket
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: MISSING_DATA_EVENTS — trail's event selectors do not
include S3 DataResources; only management events are logged
EVIDENCE:
  - describe-trails: corp-trail IsMultiRegionTrail: true,
    IsLogging: true (trail is healthy)
  - get-trail-status: IsLogging: true, LatestDeliveryTime: 2026-08-10T...
    (delivery is working)
  - get-event-selectors: [
      {"ReadWriteType":"All","IncludeManagementEvents":true,
       "DataResources":[]}
    ]
    (empty DataResources = no data events)
  - lookup-events --lookup-attributes AttributeKey=EventName,
    AttributeValue=GetObject: 0 results in last 24h
  - lookup-events --lookup-attributes AttributeKey=EventName,
    AttributeValue=CreateBucket: 4 results in last 24h
    (management events flowing; data events absent)
ROOT_CAUSE_CATALOG: #1 (data events not configured)
REMEDIATION:
  1. Add an S3 data event selector to the trail:
     aws cloudtrail put-event-selectors --trail-name corp-trail \
       --event-selectors '[{"ReadWriteType":"All","IncludeManagementEvents":true,"DataResources":[{"Type":"AWS::S3::Object","Values":["arn:aws:s3"]}]}]'
     Note: for advanced per-bucket scoping, use
     --advanced-event-selectors instead.
  2. Verify by making a test S3 read and checking lookup-events in
     5-15 minutes:
     aws s3 cp s3://my-bucket/test . && \
     aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject --start-time $(date -u -v-20M +%Y-%m-%dT%H:%M:%SZ)
  3. Monitor S3 bucket size — adding data events significantly
     increases CloudTrail log volume and cost. Consider scoping to
     specific buckets via advanced-event-selectors if cost is a
     concern.
```

## Expert heuristic — "Data events vs management events"

The single most common "missing events" complaint is a data event
that was never configured. Memorize this distinction:

- **Management events** (default, always on unless excluded) log
  control-plane operations: `CreateBucket`, `RunInstances`,
  `CreateUser`, `AttachRolePolicy`, `PutBucketPolicy`. These are
  operations that CREATE or MODIFY AWS resources.
- **Data events** (opt-in via event selectors) log data-plane
  operations: `GetObject`, `PutObject`, `DeleteObject` (S3);
  `GetItem`, `PutItem`, `Query` (DynamoDB); `Invoke` (Lambda). These
  are operations that READ or WRITE data inside an already-created
  resource.

Quick lookup table for common "missing event" complaints:

| Expected event | Type | Where to configure |
|---|---|---|
| S3 `GetObject` / `PutObject` | Data | `DataResources` with `Type: AWS::S3::Object` |
| S3 `CreateBucket` / `PutBucketPolicy` | Management | Default (no config needed) |
| Lambda `Invoke` | Data | `DataResources` with `Type: AWS::Lambda::Function` |
| Lambda `CreateFunction` | Management | Default |
| DynamoDB `GetItem` / `PutItem` | Data | `DataResources` with `Type: AWS::DynamoDB::Table` |
| DynamoDB `CreateTable` | Management | Default |
| CloudTrail `LookupEvents` itself | Not logged | CloudTrail does not log its own read APIs (lookup-events is a CloudTrail read) |
| IAM `GetUser` / `ListRoles` | Management (read) | Default — but only if `ReadWriteType: All`; if `WriteOnly`, reads are excluded |

When in doubt, run:
`aws cloudtrail get-event-selectors --trail-name <trail>` and check
whether `DataResources` has any entries. If it is empty, no data
events are being logged — full stop.

**Cost warning.** Data events are 10-100x more voluminous than
management events. Enabling S3 data events on a busy bucket can
multiply CloudTrail costs significantly. Always scope
`DataResources.Values` to specific bucket ARN prefixes
(`arn:aws:s3:::audit-bucket/`) rather than the catch-all
`arn:aws:s3` unless you genuinely need all S3 data events.

## Anti-Patterns — NEVER

- **NEVER** assume a CloudTrail outage when specific events are
  missing. CloudTrail outages are rare and account-wide. Specific
  events missing almost always means scope/configuration (data
  events, region, multi-region), not an outage.

- **NEVER** confuse `describe-trails` with `get-trail-status`.
  `describe-trails` reports configuration; `get-trail-status` reports
  active logging state. A correctly-configured trail can be silently
  stopped. Always read both.

- **NEVER** conclude "data events are not configured" without
  reading `get-event-selectors`. The trail may have advanced event
  selectors that look different from basic selectors but achieve the
  same thing. Always read the actual selector output.

- **NEVER** enable `DataResources: ["arn:aws:s3"]` (all S3 data
  events) without warning the operator about cost. A busy bucket can
  generate millions of events per day. Scope to specific buckets.

- **NEVER** declare ROOT_CAUSE_FOUND without checking the trail's
  `isLogging` state. A stopped trail produces zero events regardless
  of event-selector configuration.

- **NEVER** recommend deleting and recreating a CloudTrail trail as
  a first fix. Deletion loses the trail's event history references
  and forces a re-baseline for Insights. Fix the configuration
  in place.

- **NEVER** assume the org trail is in the management account. With
  delegated administrators, the org trail may be in the delegated
  admin account. Check both before concluding the trail is missing.

- **NEVER** assume `IncludeGlobalServiceEvents: true` captures IAM
  events in all regions. Global service events are delivered only to
  the trail's home region (us-east-1 commercial) for global services.
  A single-region trail in eu-west-1 will not capture them.

- **NEVER** confuse CloudTrail Lake with CloudTrail S3 delivery.
  Lake is near-real-time and selector-filtered; S3 is batched every
  ~5 minutes. An event missing from Lake might be filtered by the
  event data store's selector, while present in S3.

- **NEVER** assume Insights is broken because no findings appear in
  the first 7 days. Insights requires a 7-day baseline to establish
  normal patterns. Document this in onboarding.

- **NEVER** expect Insights to detect anomalous data events. Insights
  analyzes write management events by default. Data event anomalies
  require specific configuration and are limited.

- **NEVER** recommend disabling `LogFileValidationEnabled` to "fix"
  delivery issues. Log file validation (digest files) is a security
  feature; disabling it does not fix any delivery problem.

- **NEVER** assume the S3 bucket policy is correct because the trail
  was created via the console. Console-created trails get the
  canonical policy automatically, but a later bucket policy edit can
  break it. Always re-read the current policy.

- **NEVER** declare ROOT_CAUSE_FOUND for an org trail gap without
  verifying the member account is still in the org (`Status: ACTIVE`).
  A suspended or removed member stops being logged by design.

- **NEVER** forget that CloudTrail does not log its own read APIs
  (`LookupEvents`, `GetTrailStatus`). If the operator expects to see
  their own troubleshooting API calls, that expectation is wrong.

- **NEVER** conclude "Insights is broken" without verifying the
  trail is actively logging. Insights only processes events from an
  `isLogging: true` trail.

- **NEVER** assume a cross-region S3 bucket is unsupported. CloudTrail
  supports cross-region delivery, but with added latency and a KMS
  key in the trail's region (not the bucket's region). Misdiagnosing
  the KMS region leads to broken encryption.

- **NEVER** recommend restarting logging on an org trail from a
  member account without first verifying the shadow trail's status.
  The member can start logging on a shadow, but only the management
  account (or delegated admin) owns the trail configuration.

## Remediation guidance

### For MISSING_DATA_EVENTS

1. Read `get-event-selectors --trail-name <trail>`.
2. Identify which service's data events are missing (S3 / Lambda /
   DynamoDB).
3. Add a `DataResources` entry for the relevant ARN prefix. Use
   advanced event selectors for per-resource or read/write scoping.
4. Verify with a test API call and `lookup-events` (5-15 min latency).
5. Monitor cost — data events increase CloudTrail charges
   significantly.

### For TRAIL_NOT_LOGGING

1. Read `get-trail-status --name <trail>`.
2. If `isLogging: false`: `aws cloudtrail start-logging --name <trail>`.
3. If the trail is missing from `describe-trails`: check shadow trails
   (`--show-shadow-trails`); recreate if needed.
4. If `isLogging: true` but no delivery: see BUCKET_POLICY_BLOCKING.
5. Add a CloudWatch alarm on `NumberOfNotificationsDelivered` to
   catch future silent stops.

### For DELIVERY_DELAYED

1. Compare `latestDeliveryTime` to `now`.
2. Check bucket region vs trail home region.
3. Check AWS Health dashboard for CloudTrail service issues.
4. For org trails, expect 5-15 min member-account aggregation delay.
5. Use CloudTrail Lake for real-time needs; S3 for archive.

### For INSIGHTS_DISABLED

1. Read `get-insight-selectors --trail-name <trail>`.
2. If no selectors: enable with `put-insight-selectors`.
3. Wait 7 days for baseline to establish.
4. Verify the trail is actively logging.
5. For per-source scoping (2024+), use `list-insights-selectors` /
   `put-insights-selectors` (note: newer API).

### For ORG_TRAIL_GAP

1. In the management account (or delegated admin), verify the org
   trail exists and is logging.
2. In the affected member account, check for shadow trail and its
   `isLogging` state.
3. Verify the member is in the org with `Status: ACTIVE`.
4. Check for conflicting member-account trails that override the org
   trail.
5. Consolidate to ONE org trail in either management OR delegated
   admin, not both.

### For MULTI_REGION_GAP

1. Read `describe-trails` and check `IsMultiRegionTrail`.
2. If false: `aws cloudtrail update-trail --name <trail>
   --is-multi-region-trail`.
3. Also `--include-global-service-events` if IAM/STS events are
   needed.
4. Verify by making a test call in a previously-missing region.

### For BUCKET_POLICY_BLOCKING

1. Read `aws s3api get-bucket-policy --bucket <bucket>`.
2. Verify the canonical CloudTrail Allow statements are present
   (GetBucketAcl + PutObject with `bucket-owner-full-control`).
3. Check for explicit Deny statements that override.
4. If KMS is configured: verify the KMS key policy allows
   `cloudtrail.amazonaws.com` to `kms:GenerateDataKey*`.
5. For cross-account bucket: verify the bucket policy includes the
   trail's account ID in the Resource ARN path.

## Recent AWS features (2024-2026)

- **CloudTrail Lake (2022 GA, widely adopted 2024-2026):** CloudTrail
  Lake is a managed event data store that supports SQL queries and
  near-real-time ingestion. Troubleshoot Lake gaps by checking the
  event data store's selector (`aws cloudtrail list-event-data-stores`
  + `get-event-data-store`) — the selector determines which events
  land in Lake, independent of the S3 delivery configuration.
- **CloudTrail Lake federation (2024):** Lake can be federated to
  external analytics (Athena, OpenSearch). Federation failures
  present as "events in Lake but not in Athena" — check the
  federation role and Athena workgroup.
- **Enhanced Insights selectors (2024):** The new
  `list-insights-selectors` / `put-insights-selectors` APIs allow
  per-event-source Insights configuration (e.g., Insights for
  `iam.amazonaws.com` only). The legacy `get-insight-selectors` /
  `put-insight-selectors` APIs still work but only toggle global
  Insights on/off.
- **CloudTrail Organizations auto-enable (2024-2025):** New member
  accounts can now auto-receive the org trail without manual
  `start-logging`. Verify the "Enable for new accounts" toggle in the
  CloudTrail console or via Organizations APIs.
- **CloudTrail Lake integration with Amazon Q (2025):** Q can query
  CloudTrail Lake in natural language. Troubleshoot by verifying the
  Q service role has `cloudtrail:StartQuery` on the event data store.
- **S3 managed bucket policies for CloudTrail (2024):** When you
  create a trail via the console on a bucket in your account, the
  console auto-applies the canonical CloudTrail bucket policy. IaC
  (Terraform / CloudFormation) does NOT — you must include the
  policy explicitly.
- **CloudTrail delete-trail retention (2024):** Deleted trails remain
  as shadow trails for 30 days. `describe-trails --show-shadow-trails`
  surfaces them. Events already delivered remain in S3.

## References

See `references/failure-decision-tree.md` for the full symptom-to-cause
walk with worked examples per category, and `references/diagnostic-
commands.md` for the canonical command script for each failure category.

## Domain

AWS CloudOps / Governance, Audit Logging & Compliance.

## AWS documentation

- **AWS CloudTrail User Guide** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-user-guide.html
- **CloudTrail troubleshooting** — https://repost.aws/knowledge-center/cloudtrail-troubleshooting
- **CloudTrail data events** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-data-events-with-cloudtrail.html
- **CloudTrail Insights** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-insights-events-with-cloudtrail.html
- **CloudTrail organization trails** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html
- **CloudTrail S3 bucket policy** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/create-s3-bucket-policy-for-cloudtrail.html
- **CloudTrail Lake** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake.html
- **CloudTrail supported services** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-unsupported-aws-services.html
- **Terraform aws_cloudtrail** — https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudtrail
