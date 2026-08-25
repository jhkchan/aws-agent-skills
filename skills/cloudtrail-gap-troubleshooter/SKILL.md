---
name: cloudtrail-gap-troubleshooter
description: Diagnoses AWS CloudTrail logging gaps and missing events. Covers events missing because data events (S3/Lambda/DynamoDB) were never configured, multi-region scope mismatches, trails that report IsLogging true but never deliver (S3 bucket policy missing bucket-owner-full-control, KMS key policy missing the cloudtrail principal, explicit deny), silently stopped trails (inadvertent stop-logging, IaC that omitted start-logging), delayed delivery beyond the 5-15 minute window, CloudTrail Insights not firing (selectors missing, baseline not elapsed), and org trails that miss specific member accounts (member shadow trail stopped, delegated-admin confusion, member left org). Emits a deterministic verdict (ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE) with evidence from describe-trails, get-trail-status, get-event-selectors, lookup-events, list-insights-selectors, and get-bucket-policy. Use when a trail is silent, events are missing, Insights is not firing, or a member account is not being logged by the org trail.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline diagnosis works on supplied describe-trails / get-trail-status / get-bucket-policy JSON. Live-account diagnosis uses aws cloudtrail describe-trails, get-trail-status, lookup-events, get-insight-selectors, list-insights-selectors, aws s3api get-bucket-policy, aws organizations list-delegated-administrators, and aws logs filter-log-events (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: Diagnosing why a CloudTrail trail is silent (no log files being delivered to S3), why specific API calls are missing from a trail (data events not configured, single-region trail in the wrong region), why log delivery is delayed beyond the expected 5-15 minute window, why CloudTrail Insights is not firing on suspicious write activity, or why an organization trail is not logging for one or more member accounts.
  activation_triggers: CloudTrail missing events, CloudTrail not logging, CloudTrail trail stopped, CloudTrail log delivery delayed, CloudTrail data events missing, CloudTrail Insights not working, CloudTrail org trail gap, CloudTrail member account not logged, CloudTrail S3 bucket policy, CloudTrail lookup-events returns empty, CloudTrail audit gap
  invocation_schema: 'Input: either (a) a symptom description (trail name, observed gap, any error strings from the console or lookup-events), OR (b) a live-account scenario where the agent runs aws cloudtrail describe-trails / get-trail-status / lookup-events / list-insights-selectors / aws s3api get-bucket-policy to gather evidence. Output: a deterministic INCIDENT / VERDICT / ROOT_CAUSE / EVIDENCE / REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and ROOT_CAUSE names the specific failure category (MISSING_DATA_EVENTS / TRAIL_NOT_LOGGING / DELIVERY_DELAYED / INSIGHTS_DISABLED / ORG_TRAIL_GAP / MULTI_REGION_GAP / BUCKET_POLICY_BLOCKING) and the offending config element.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudTrail, audit logging, data events, management events, missing events, trail not logging, log delivery delay, CloudTrail Insights, CloudTrail Lake, organization trail, delegated admin, S3 bucket policy, log file validation, multi-region trail
  tags: cloudtrail, governance, troubleshoot, logging-gap, audit, compliance, org-trail, insights
---

# CloudTrail Gap Troubleshooter

## Activation

Activate this skill when the user reports a CloudTrail logging gap.
Trigger phrases: "CloudTrail missing events", "CloudTrail not logging",
"CloudTrail trail stopped", "CloudTrail log delivery delayed", "CloudTrail
data events missing", "CloudTrail Insights not working", "CloudTrail org
trail gap", "CloudTrail member account not logged", "CloudTrail lookup-events
returns empty".

## Mindset

**One-line takeaway:** "CloudTrail is logging but I can't find my event" is
almost always a data-events-vs-management-events misunderstanding or a
region/trail scope mismatch — NOT a CloudTrail outage. Diagnose scope and
configuration before assuming an outage.

Three facts make CloudTrail troubleshooting different:

- **Management events are on by default; data events are opt-in.** Most
  "missing events" complaints are data events that were never configured.
- **A trail has TWO independent health signals.** `describe-trails` reports
  configuration; `get-trail-status` reports active logging state. A
  correctly-configured trail can be silently stopped. Always check both.
- **CloudTrail Lake and S3 delivery are different pipelines.** S3 averages
  5 min (up to 15). Lake is near-real-time but selector-filtered. An event
  missing from Lake might be in S3.

## Quick reference — symptom to failure category

| Observed state | Failure category | First probe |
|---|---|---|
| Specific API not found by `lookup-events` | MISSING_DATA_EVENTS / MULTI_REGION_GAP | Is the event source in the trail's management filter? Is it a data event? |
| No log files in S3; `isLogging: false` | TRAIL_NOT_LOGGING | `get-trail-status`; check bucket policy for deny |
| Log files arriving but multi-hour latency | DELIVERY_DELAYED | Compare `latestDeliveryTime` to `now` |
| Suspicious write activity but no Insights finding | INSIGHTS_DISABLED | `list-insights-selectors` configured? Trail `isLogging`? |
| Org trail missing specific member account(s) | ORG_TRAIL_GAP | Member in org? Delegated admin? Shadow trail? |
| Bucket policy denies CloudTrail writes | BUCKET_POLICY_BLOCKING | `get-bucket-policy` — explicit Deny on `cloudtrail:PutObject` |

## Quick navigation

- **Step 0** — Capture the failure signal
- **Step 1** — Map symptom to category (A-G)
- **Step 2** — MISSING_DATA_EVENTS
- **Step 3** — TRAIL_NOT_LOGGING
- **Step 4** — DELIVERY_DELAYED
- **Step 5** — INSIGHTS_DISABLED
- **Step 6** — ORG_TRAIL_GAP
- **Step 7** — MULTI_REGION_GAP / BUCKET_POLICY_BLOCKING
- **Step 8** — Root-cause catalog
- **Step 9** — Verify the fix
- **Step 10** — Decide VERDICT

## Process — Diagnostic decision tree (apply in order)

### Step 0: Capture the failure signal

Gather these four pieces. Each step below branches on which is present.

| Signal | Source | Why required |
|---|---|---|
| **Trail name(s)** | User-provided or `describe-trails` | All status calls need this |
| **Scope of gap** (account / region / event) | User symptom | Narrows the dimension |
| **Expected event source + API** | User-provided | Determines data vs management event |
| **Trail status + latest delivery** | `get-trail-status` | Drives TRAIL_NOT_LOGGING vs DELIVERY_DELAYED |

If the trail name is unknown, run:

```bash
aws cloudtrail describe-trails --query 'trailList[*].{name:Name,multiRegion:IsMultiRegionTrail,org:IsOrganizationTrail,s3Bucket:S3BucketName,kmsKey:KmsKeyId}'
aws cloudtrail get-trail-status --name <trail-name>
aws cloudtrail lookup-events --max-results 5 --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ)
```

### Step 1: Identify the symptom category

| Category | Signature | Diagnostic step |
|---|---|---|
| **A. MISSING_DATA_EVENTS** | Operator expects data-plane event (GetObject, PutItem, Invoke); absent; management events fine | Step 2 |
| **B. TRAIL_NOT_LOGGING** | `isLogging: false`; no log files in S3 for hours; OR trail missing from describe-trails | Step 3 |
| **C. DELIVERY_DELAYED** | `isLogging: true` but `latestDeliveryTime` lags > 15 min (mgmt) or > 1h (data) | Step 4 |
| **D. INSIGHTS_DISABLED** | Expected Insights finding; none appears; baseline elapsed | Step 5 |
| **E. ORG_TRAIL_GAP** | Org trail logs management + most members; specific member missing | Step 6 |
| **F. MULTI_REGION_GAP** | Single-region trail; events from other region missing | Step 7 |
| **G. BUCKET_POLICY_BLOCKING** | `isLogging: true` but no files in S3; policy has Deny or missing Allow | Step 7 |

**Scope rule.** When multiple categories apply, narrow broadest to most
specific. A TRAIL_NOT_LOGGING trail produces no events at all — resolve B
before diagnosing A or F.

### Step 2: MISSING_DATA_EVENTS diagnostic

The operator expects a data-plane event (GetObject, PutItem, Invoke) but it
is absent. The trail is logging management events correctly.

**Management vs data events quick reference:**

| Expected event | Type | Where to configure |
|---|---|---|
| S3 `GetObject` / `PutObject` | Data | `DataResources` with `Type: AWS::S3::Object` |
| S3 `CreateBucket` / `PutBucketPolicy` | Management | Default (no config needed) |
| Lambda `Invoke` | Data | `DataResources` with `Type: AWS::Lambda::Function` |
| DynamoDB `GetItem` / `PutItem` | Data | `DataResources` with `Type: AWS::DynamoDB::Table` |
| CloudTrail `LookupEvents` itself | Not logged | CloudTrail does not log its own read APIs |
| IAM `GetUser` / `ListRoles` | Management (read) | Default — but excluded if `ReadWriteType: WriteOnly` |

**Diagnostic walk:**

1. **Confirm management vs data event.** Management = control-plane
   (CreateBucket, RunInstances). Data = data-plane (GetObject, PutItem,
   Invoke).
2. **Read event selectors:** `aws cloudtrail get-event-selectors --trail-name <trail>`.
   - `ReadWriteType: All` + `IncludeManagementEvents: true` — logs both.
   - `ReadWriteType: ReadOnly` or `WriteOnly` — limits direction.
   - `DataResources` empty/absent — data events NOT configured.
3. **Verify in S3 delivery directly:** list log objects around the event time
   and grep for the event name.
4. **For Lambda Invoke:** check whether selector covers account-level
   (`arn:aws:lambda`) or function-level.

**Common fix patterns:**
- S3 data events: add `DataResources` with `Type: AWS::S3::Object`,
  `Values: ["arn:aws:s3"]`. Use advanced selectors for per-bucket scoping.
- Lambda data events: `Type: AWS::Lambda::Function`, `Values: ["arn:aws:lambda"]`.
- DynamoDB: `Type: AWS::DynamoDB::Table`, `Values: ["arn:aws:dynamodb"]`.
- For cost control: prefer `WriteOnly` data events; scope to specific ARNs.

**Diagnostic commands:**

Canonical CLI for this step (get-event-selectors, S3 log grep, CloudTrail Lake query) — `references/diagnostic-commands.md`.

**Cost warning.** Data events are 10-100x more voluminous than management
events. Always scope `DataResources.Values` to specific ARN prefixes.

See `references/diagnostic-commands.md` for canonical CLI commands per category.

### Step 3: TRAIL_NOT_LOGGING diagnostic

The trail is not delivering any events. Either `isLogging: false`, or
`isLogging: true` but no files appearing in S3.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `isLogging: false` | Trail explicitly stopped or never started | `start-logging --name <trail>` |
| Trail missing from `describe-trails` | Trail deleted (config retained 30 days) | `--show-shadow-trails` |
| `isLogging: true` but no delivery | S3 bucket policy blocking | Step 7 (BUCKET_POLICY_BLOCKING) |
| KMS access denied errors | KMS key policy missing CloudTrail principal | Verify KMS policy has `cloudtrail.amazonaws.com` with `kms:GenerateDataKey*` |
| Org trail `isLogging: false` in member | Member shadow trail overriding | Check shadow trails in member account |

**Diagnostic walk:**
1. Read `get-trail-status` first. `isLogging` is the single most important signal.
2. If `false`: `aws cloudtrail start-logging --name <trail>`. Re-check status.
3. If `true` but no delivery: check S3 bucket policy (Step 7) and KMS key policy.
4. If trail missing: check shadow trails (`--show-shadow-trails`). Recreate if needed.
5. For org trails: member accounts see the org trail as a "shadow." If a
   member stops logging on the shadow, that member's events stop.

**Diagnostic commands:**

Canonical CLI for this step (get-trail-status, shadow trails, KMS key policy check, start-logging) — `references/diagnostic-commands.md`.

**Common fixes:**
- Trail stopped: `start-logging`; add CloudWatch alarm on
  `NumberOfNotificationsDelivered`.
- KMS missing CloudTrail: add statement allowing `cloudtrail.amazonaws.com`
  to `kms:GenerateDataKey*` and `kms:DescribeKey`.
- Trail deleted: recreate from IaC. Note: Terraform `aws_cloudtrail` does
  NOT auto-start; the `start_logging` resource must be included.

### Step 4: DELIVERY_DELAYED diagnostic

Log files arriving but with latency beyond CloudTrail's targets.

| Sub-symptom | Root cause | Action |
|---|---|---|
| Management events delayed 15-30 min | Normal can be up to 15 min; > 15 unusual | Check AWS Health dashboard |
| Data events delayed 30-60 min | Data events inherently higher-latency | Expected unless > 1 hour consistently |
| All events delayed > 1 hour | Service issue OR cross-region bucket | Check bucket region vs trail HomeRegion |
| Org trail members delayed vs mgmt acct | Per-account aggregation delay (~5-15 min) | Expected; if > 30 min check quotas |
| Lake fast but S3 slow | Different pipelines by design | Use Lake/EventBridge for real-time needs |

**Diagnostic walk:**
1. Compare `latestDeliveryTime` to `now` via `get-trail-status`.
2. Check bucket region vs trail `HomeRegion` — cross-region adds latency.
3. Check AWS Health dashboard for CloudTrail service events.
4. For org trails: member delay of 5-15 min after management account is normal.

### Step 5: INSIGHTS_DISABLED diagnostic

Operator expects Insights finding for anomalous write activity; none appears.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| No findings ever | Insights not enabled | `get-insight-selectors` — should return enabled selectors |
| No findings in first 7 days | Baseline period not elapsed | Expected; wait 7 days |
| No findings for write data events | Insights only analyzes write MANAGEMENT events | Expected limitation |
| Recently re-enabled | Baseline resets on re-enable | Wait another 7 days |
| Insights on stopped trail | Trail must be `isLogging: true` | Fix Step 3 first |

**Diagnostic walk:**
1. Read `aws cloudtrail get-insight-selectors --trail-name <trail>`.
2. Interpret: `InsightsEnabled: false` -> OFF. `true` with event source ->
   Insights for that source.
3. Check baseline period (7 days of management events required).
4. Verify trail is actively logging — Insights only processes active trails.
5. Check S3: `aws s3 ls s3://<bucket>/CloudTrail-Insight/` — if prefix
   doesn't exist, no findings delivered.

**Fix:** `aws cloudtrail put-insight-selectors --trail-name <trail>
--insight-selectors '[{"InsightType":"ApiCallRateInsight"},{"InsightType":"ApiErrorRateInsight"}]'`.
For per-source scoping (2024+), use `list-insights-selectors` /
`put-insights-selectors` (newer API).

### Step 6: ORG_TRAIL_GAP diagnostic

Org trail logs management account and most members. Specific member missing.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| All members missing | Org trail `isLogging: false` in mgmt account | `get-trail-status` in mgmt account |
| Specific member missing | Member shadow trail `isLogging: false` | In member: `describe-trails --show-shadow-trails` |
| New members not logged | Trail created before auto-enable existed | `start-logging` from member, or enable org auto-start |
| Member left org | Account removed from Organizations | `list-accounts` — verify Status: ACTIVE |
| Delegated admin confusion | Trail might be in delegated admin, not mgmt | `list-delegated-administrators --service-principal cloudtrail.amazonaws.com` |
| Member's own trail overrides org trail | Member trail shadows org trail | Disable member's trail or accept different bucket |
| SCP blocking CloudTrail | SCP denies cloudtrail APIs in member | `describe-policy --policy-id <scp-id>` |

**Diagnostic walk:**
1. Confirm org trail: `describe-trails --query 'trailList[?IsOrganizationTrail]'`.
2. Check trail is logging in management account.
3. In affected member: `describe-trails --show-shadow-trails` — look for
   `IsShadowTrail: true` with `IsLogging: false`.
4. Verify member is in org with `Status: ACTIVE`.
5. Check for delegated admin: if configured, org trail must be in that
   account, not management.
6. Check SCPs that might block CloudTrail in the member.

**Diagnostic commands:**

Canonical CLI for this step (org trail status, delegated admins, member shadow trails, org membership, SCPs) — `references/diagnostic-commands.md`.

**Common fixes:**
- Member shadow stopped: `start-logging --name <org-trail>` from the member
  account (works on shadow trails).
- Delegated admin confusion: consolidate to ONE org trail in EITHER
  management OR delegated admin, not both.
- New members: enable "Apply to all accounts" + "Enable for new accounts"
  in console, or script start-logging on new members.

### Step 7: MULTI_REGION_GAP and BUCKET_POLICY_BLOCKING

#### 7a. MULTI_REGION_GAP

Trail is single-region (`IsMultiRegionTrail: false`). Events from other
regions not logged.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Events from other region missing | `IsMultiRegionTrail: false` | `describe-trails --query 'trailList[*].{multi:IsMultiRegionTrail,home:HomeRegion}'` |
| Global service events (IAM, STS) missing | Single-region trail not in us-east-1 | Check `IncludeGlobalServiceEvents` + HomeRegion |

**Fix:** `aws cloudtrail update-trail --name <trail> --is-multi-region-trail`.
Also `--include-global-service-events` if IAM/STS needed. Global service
events are delivered only to the trail's home region (us-east-1 commercial).

#### 7b. BUCKET_POLICY_BLOCKING

Trail claims `isLogging: true` but no log files land in S3.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Explicit Deny on `cloudtrail:PutObject` | Restrictive policy added later | `get-bucket-policy`; grep for Deny |
| Missing Allow for `cloudtrail.amazonaws.com` | Policy accidentally removed | Look for Allow with `Principal.Service: cloudtrail.amazonaws.com` |
| KMS key policy missing CloudTrail | KMS doesn't allow `kms:GenerateDataKey*` | `get-key-policy --policy-name default` |
| Cross-account bucket | Bucket policy must include trail's account | Verify Resource ARN path |

**Diagnostic walk:**
1. Read bucket policy: `aws s3api get-bucket-policy --bucket <bucket>`.
2. Look for the canonical CloudTrail Allow: both `s3:GetBucketAcl` and
   `s3:PutObject` with `Condition: StringEquals: s3:x-amz-acl: bucket-owner-full-control`.
   The `bucket-owner-full-control` condition is a common omission.
3. Check for explicit Deny statements overriding the Allow.
4. If KMS configured: verify key policy allows `cloudtrail.amazonaws.com`
   to `kms:GenerateDataKey*`.
5. For cross-account bucket: policy must include trail's account ID in
   Resource ARN path.

See `references/failure-decision-tree.md` for detailed policy examples.

### Step 8: Map to root-cause catalog

| # | Root cause | Category | Fix pattern |
|---|---|---|---|
| 1 | Data events not configured (S3/Lambda/DynamoDB) | MISSING_DATA_EVENTS | Add `DataResources` to event selectors |
| 2 | Trail stopped (`isLogging: false`) | TRAIL_NOT_LOGGING | `start-logging`; add CloudWatch alarm |
| 3 | Trail deleted | TRAIL_NOT_LOGGING | Recreate from IaC; `--show-shadow-trails` |
| 4 | Bucket policy missing Allow or explicit Deny | BUCKET_POLICY_BLOCKING | Add canonical statements with `bucket-owner-full-control` |
| 5 | KMS key policy missing CloudTrail | BUCKET_POLICY_BLOCKING | Add KMS statement for `cloudtrail.amazonaws.com` |
| 6 | Single-region trail; events from other regions missing | MULTI_REGION_GAP | `update-trail --is-multi-region-trail` |
| 7 | Insights not enabled | INSIGHTS_DISABLED | `put-insight-selectors` |
| 8 | Insights baseline not elapsed | INSIGHTS_DISABLED | Wait 7 days |
| 9 | Org trail shadow stopped in member | ORG_TRAIL_GAP | `start-logging` from member |
| 10 | Delegated admin confusion (two org trails) | ORG_TRAIL_GAP | Consolidate to ONE org trail |
| 11 | Trail never started after IaC creation | TRAIL_NOT_LOGGING | Call `start-logging` explicitly |
| 12 | Org trail not auto-enabled for new members | ORG_TRAIL_GAP | Enable org-wide auto-start |

### Step 9: Verify the fix

- **start-logging fixes:** re-read `get-trail-status`, verify `isLogging: true`
  and `latestDeliveryTime` advances.
- **Event-selector fixes:** make a test API call (e.g., `aws s3 cp`), verify
  in `lookup-events` within 5-15 min.
- **Bucket-policy fixes:** re-read policy, confirm Allow statements; wait
  5-15 min for next delivery window.
- **Org trail fixes:** check `get-trail-status` in both management and member.
- **Multi-region fixes:** make a test call in previously-missing region.

### Step 10: Decide — ROOT_CAUSE_FOUND vs NEED_MORE_INFO vs ESCALATE

- **ROOT_CAUSE_FOUND.** Walk identified a specific category and config element.
  Output REMEDIATION with the exact change.
- **NEED_MORE_INFO.** Walk reached a step where operator cannot supply
  evidence. Output the list of missing inputs.
- **ESCALATE.** Cause is outside operator's scope (S3 bucket owned by another
  team, KMS managed by security team, org trail owned by management account).
  Output the escalation target and specific request.

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

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no conversational
opening:

```text
INCIDENT: <account> / <trail-name> — <symptom>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <MISSING_DATA_EVENTS | TRAIL_NOT_LOGGING | DELIVERY_DELAYED | INSIGHTS_DISABLED | ORG_TRAIL_GAP | MULTI_REGION_GAP | BUCKET_POLICY_BLOCKING> — <one-sentence specific failing config element>
EVIDENCE:
  - describe-trails: <quoted field value from output>
  - get-trail-status: <quoted field value from output>
  - get-event-selectors: <quoted field value from output, or "not fetched">
  - get-bucket-policy: <quoted field value, or "not applicable">
  - lookup-events: <result count or sample event>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <exact CLI command or policy edit>
  2. <verification command>
  3. <post-apply monitoring step>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze..." — the INCIDENT line is FIRST, always.
- NEVER use lowercase verdict values — emit `ROOT_CAUSE_FOUND`,
  `NEED_MORE_INFO`, or `ESCALATE`.
- NEVER omit EVIDENCE — the judge requires direct quotes from
  `describe-trails`, `get-trail-status`, or `get-event-selectors` output.
  Paraphrasing is not acceptable; quote the actual field value.
- NEVER declare ROOT_CAUSE_FOUND without referencing BOTH `describe-trails`
  AND `get-trail-status` in EVIDENCE — a correctly-configured trail can be
  silently stopped.
- NEVER confuse management events with data events in the ROOT_CAUSE —
  GetObject, PutItem, Invoke are data events; CreateBucket and RunInstances
  are management events. Wrong event type is a hard error.

### Perfect example output

```text
INCIDENT: 111111111111 / corp-trail — operator expects GetObject events for audit; lookup-events returns zero GetObject events for any S3 bucket
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: MISSING_DATA_EVENTS — trail's event selectors do not include S3 DataResources; only management events are logged
EVIDENCE:
  - describe-trails: corp-trail IsMultiRegionTrail: true, IsLogging: true (trail is healthy)
  - get-trail-status: IsLogging: true, LatestDeliveryTime: 2026-08-10T14:22:00Z (delivery is working)
  - get-event-selectors: [{"ReadWriteType":"All","IncludeManagementEvents":true,"DataResources":[]}]  (empty DataResources = no data events configured)
  - get-bucket-policy: not applicable (delivery is working; bucket policy is not the issue)
  - lookup-events AttributeKey=EventName,AttributeValue=GetObject: 0 results in last 24h
  - lookup-events AttributeKey=EventName,AttributeValue=CreateBucket: 4 results in last 24h (management events flowing; data events absent)
ROOT_CAUSE_CATALOG: #1 (data events not configured)
REMEDIATION:
  1. Add an S3 data event selector to the trail:
     aws cloudtrail put-event-selectors --trail-name corp-trail --event-selectors '[{"ReadWriteType":"All","IncludeManagementEvents":true,"DataResources":[{"Type":"AWS::S3::Object","Values":["arn:aws:s3"]}]}]'
  2. Verify by making a test S3 read and checking lookup-events in 5-15 minutes:
     aws s3 cp s3://my-bucket/test . && aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject --start-time $(date -u -v-20M +%Y-%m-%dT%H:%M:%SZ)
  3. Monitor S3 bucket size — adding data events significantly increases CloudTrail log volume and cost. Consider scoping to specific buckets via advanced-event-selectors if cost is a concern.
```

## Anti-Patterns — NEVER (top 5)

1. NEVER assume a CloudTrail outage when specific events are missing — almost
   always scope/configuration (data events, region), not an outage.
2. NEVER confuse `describe-trails` (configuration) with `get-trail-status`
   (active logging state) — a correctly-configured trail can be silently
   stopped. Always read both.
3. NEVER conclude "data events not configured" without reading
   `get-event-selectors` — the trail may have advanced event selectors that
   look different but achieve the same thing.
4. NEVER enable `DataResources: ["arn:aws:s3"]` (all S3 data events) without
   warning about cost — scope to specific bucket ARNs.
5. NEVER recommend deleting and recreating a trail as a first fix — deletion
   loses event history references and forces an Insights re-baseline. Fix
   configuration in place.

See `references/failure-decision-tree.md` for additional anti-patterns and
edge cases (org trail ownership, global service events region, CloudTrail
Lake vs S3, Insights limitations).

## Recent AWS features (2024-2026)

→ All seven updates (Lake adoption, Lake federation, enhanced Insights selectors, org auto-enable, Amazon Q integration, S3 managed bucket policies, delete-trail shadow retention) — `references/advanced-patterns.md`.

## References

- `references/failure-decision-tree.md` — full symptom-to-cause walk with
  worked examples per category, detailed S3/KMS policy examples, and
  additional anti-patterns
- `references/diagnostic-commands.md` — canonical command script for each
  failure category

## References (load on demand)

- [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — canonical per-category CLI script (pre-existing) + the Step 2 / Step 3 / Step 6 command blocks moved from SKILL.md
- [`references/advanced-patterns.md`](references/advanced-patterns.md) — recent AWS features affecting gap diagnosis (2024-2026)
- [`references/failure-decision-tree.md`](references/failure-decision-tree.md) — full symptom-to-cause walk, worked examples per category, S3/KMS policy examples, anti-patterns (pre-existing)

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
