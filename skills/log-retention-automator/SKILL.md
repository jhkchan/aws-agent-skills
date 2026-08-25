---
name: log-retention-automator
description: Designs and implements CloudWatch Logs retention automation workflows. Maps tag-based retention policies (Environment=prod to 90d, dev to 7d), deploys EventBridge rules for auto-retention on CreateLogGroup, validates retention tier mapping against the 22 allowed values (1d/3d/5d/7d/14d/30d/60d/90d/120d/150d/180d/365d/400d/545d/731d/ 1096d/1827d/2192d/2557d/2922d/3288d/3653d), manages subscription filter cleanup and metric filter preservation during retention changes, enforces account-level default retention, configures S3 export via Kinesis Firehose for long-term archival, estimates cost per retention tier, and supports multi-account rollout via AWS Organizations. Emits AUTOMATION_DEPLOYED with deployment templates or REVIEW_REQUIRED with the specific gap. Use when automating log retention, building tag-driven retention policies, wiring CreateLogGroup EventBridge rules, or replacing never-expire log groups with S3 archival.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline workflow design. Live deployment uses aws logs put-retention-policy, describe-log-groups, delete-retention-policy, put-subscription-filter, delete-subscription-filter, describe-metric-filters, aws events put-rule, put-targets, aws firehose create-delivery-stream, describe-delivery-stream, and aws organizations list-accounts — AWS CLI v2, SSO or key-based credentials.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
  when_to_use: Automating CloudWatch Logs retention, building tag-driven retention policies, wiring EventBridge on CreateLogGroup for auto-retention, replacing never-expire log groups with S3 Firehose archival, auditing subscription/metric filter impact before retention changes, estimating log storage cost per tier, or enforcing retention across an Organizations account fleet.
  activation_triggers: automate log retention, tag-based retention policy, put-retention-policy, CreateLogGroup EventBridge, auto-retention new log groups, S3 Firehose log archival, never-expire replacement, subscription filter cleanup, metric filter preservation, account-level default retention, multi-account log retention, retention tier cost estimation
  invocation_schema: 'Input: either (a) a tag-to-retention mapping (e.g., Environment=prod to 90d, dev to 7d) plus target log groups, OR (b) a retention automation requirement ("auto-set retention on all new log groups", "archive expired logs to S3 before deletion"). Output: deterministic RETENTION block per policy — POLICY/TRIGGER/ARCHIVAL/ VERDICT — where VERDICT is AUTOMATION_DEPLOYED (templates ready) or REVIEW_REQUIRED (specific gap cited).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudWatch Logs, retention policy, put-retention-policy, EventBridge, CreateLogGroup, tag-based retention, log group automation, Kinesis Firehose, S3 archival, subscription filter, metric filter, CloudWatch Logs Insights, multi-account logging, AWS Organizations, retention tier, cost estimation, never-expire replacement, compliance logging, log lifecycle
  tags: cloudwatch-logs, retention, eventbridge, firehose, s3-archival, log-management, automate
---

# Log Retention Automator

## Mindset

**One-line takeaway:** CloudWatch Logs retention is per-log-group with
no account-level default — new log groups default to **Never Expire**
and silently accumulate cost until someone explicitly sets a policy.
The automation pipeline is **tag** (identify cohort) → **tier map**
(pick retention days) → **apply** (put-retention-policy) → **archive**
(Firehose-to-S3 for compliance logs before expiry) → **verify**
(describe-log-groups confirms retentionInDays is set).

> The three underlying facts (per-log-group retention, auto-retention on CreateLogGroup, Firehose-to-S3 for compliance) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
> Load them when designing a retention pipeline from scratch.

## Quick navigation

| You want to... | Go to |
|---|---|
| Map tags to retention tiers | Step 2 + Appendix A |
| Auto-apply retention on new log groups | Step 4 (EventBridge rule) |
| Replace Never Expire with S3 archival | Step 6 (Firehose pipeline) |
| Clean up subscription filters before retention | Step 5 |
| Preserve metric filters during retention change | Step 5 |
| Estimate cost per retention tier | Step 7 + Appendix B |
| Enforce account-level default retention | Step 8 |
| Roll out across Organizations accounts | Step 9 |
| Audit existing retention state | Step 10 |
| Avoid common automation pitfalls | Anti-Patterns |
| Recent features (Firehose Direct Put, Org-wide) | Recent AWS features |

## Critical rules at a glance (do NOT bury these)

1. **Retention is per-log-group. There is NO account-level default.**
   New log groups default to Never Expire. A 10-GB/day log group left
   at Never Expire for a year costs roughly $1,500 in storage alone
   ($0.03/GB/month). A fleet of 200 log groups without retention is a
   six-figure annual surprise.
2. **`put-retention-policy` is the ONLY API that sets retention.**
   It accepts one log group ARN and one integer (retentionInDays).
   There is no bulk API. To set retention across 500 log groups, you
   loop `put-retention-policy` 500 times (with rate limiting — the
   CloudWatch Logs API throttles at ~5-10 transactions/sec per account
   for put-retention-policy).
3. **The retention tier set is FINITE and NON-NEGOTIABLE.** Only these
   values are accepted: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365,
   400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653. A value
   like `45` or `100` produces `InvalidParameterException`. The tier
   map must round to the nearest allowed value.
4. **Shortening retention does NOT trigger immediate deletion of
   already-stored logs beyond the new window.** Logs older than the new
   retention are deleted asynchronously within the next service-side
   cycle (typically seconds to minutes). This is irreversible — the
   logs are gone. Always export to S3 first if compliance requires.
5. **Subscription filters and metric filters survive retention changes.**
   Retention controls data lifecycle, not ingestion or processing
   pipelines. But if you delete a log group (separate from retention),
   subscription and metric filters are destroyed with it. Know the
   difference.

## Pre-flight: data requirements

Designing a retention automation workflow requires these inputs:

| Input | Source | Why |
|---|---|---|
| All log groups + current retention | `describe-log-groups` | Baseline state — which groups are Never Expire |
| Tag schema on log groups | `list-tags-log-group` | Tag-based tier mapping |
| Subscription filters per group | `describe-subscription-filters` | Identify breaking-change risk |
| Metric filters per group | `describe-metric-filters` | Preservation list |
| CloudWatch Logs Insights saved queries | Account-level | Retention of saved query results |
| Monthly ingest volume per group | CloudWatch Metrics (`IncomingBytes`) | Cost estimation per tier |
| S3 bucket for archival (if applicable) | `s3 ls` | Firehose destination |
| KMS key for encryption (if applicable) | `kms describe-key` | Firehose + S3 encryption |
| Organizations account list (if multi-account) | `organizations list-accounts` | Rollout scope |

**If the input is malformed** (missing log group list, ambiguous tag
schema), emit:

```text
RETENTION: <reference>
LOG_GROUP: <name or "account-wide">
VERDICT: ERROR
REASON: Cannot design retention automation — log group inventory and tag-to-tier mapping are required.
GAP: Run describe-log-groups and list-tags-log-group, then supply the tag retention map.
```

## Process — Retention automation design (apply in order)

### Step 0: Expert knowledge — non-obvious CloudWatch Logs behaviors

> Step 0 deep-dive moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — eventual consistency, untagged service log groups, async bulk deletion, delete-retention-policy, filter limits, Firehose buffering, cross-account behavior.
> Load it before designing the automation.

### Step 1: Inventory the current state

> The inventory CLI (describe-log-groups queries, Never-Expire filter, tag lookup) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
> Load it before baselining an account.

Key observations to surface in the output:

- **Count of Never Expire groups** — the cost exposure.
- **Total storedBytes** — the volume at risk.
- **Tag coverage** — what percentage of groups have the tag the
  retention map depends on. Groups without the tag need a fallback
  (account-level default).

### Step 2: Build the tag-to-retention tier map

Map the tag value to one of the 22 allowed retention values:

| Tag value (Environment) | Desired retention | Allowed tier | Applied |
|---|---|---|---|
| prod | 90 days | 90 | 90 |
| staging | 30 days | 30 | 30 |
| dev | 7 days | 7 | 7 |
| sandbox | 1 day | 1 | 1 |
| compliance | 2557 days (7 years) | 2557 | 2557 |
| audit | 3653 days (10 years) | 3653 | 3653 |
| (untagged) | 14 days (account default) | 14 | 14 |

If a desired retention is not in the allowed set, round UP to the next
allowed tier (never down — rounding down deletes more data than
requested):

| Desired | Nearest allowed (round UP) | Reason |
|---|---|---|
| 2 | 3 | 1 is too short |
| 10 | 14 | 7 is too short |
| 45 | 60 | 30 is too short |
| 100 | 120 | 90 is too short |
| 200 | 365 | 180 is too short |
| 500 | 545 | 400 is too short |
| 800 | 1096 | 731 is too short |
| 1500 | 1827 | 1096 is too short |

The complete reference table is in **references/retention-tier-mapping.md**.

### Step 3: Apply retention to existing log groups

For each log group, look up the tag, resolve the tier, and apply:

```bash
aws logs put-retention-policy \
  --log-group-name /aws/lambda/my-function \
  --retention-in-days 90 \
  --region us-east-1
```

> The rate-limited batch-apply Python pattern moved verbatim to [references/worked-examples.md](references/worked-examples.md); the single-group CLI above stays canonical.
> Load it when applying retention across many log groups.

> The put-retention-policy error table (InvalidParameterException, ThrottlingException, ResourceNotFoundException, AccessDeniedException) moved verbatim to [references/error-handling.md](references/error-handling.md).
> Load it when apply calls fail.

### Step 4: Deploy EventBridge auto-retention on CreateLogGroup

This is the most critical automation — it catches new log groups at
creation time and applies retention before they accumulate data.

EventBridge rule pattern:

```bash
aws events put-rule \
  --name auto-retention-new-log-groups \
  --event-pattern '{
    "source": ["aws.logs"],
    "detail-type": ["AWS API Call via CloudTrail"],
    "detail": {
      "eventSource": ["logs.amazonaws.com"],
      "eventName": ["CreateLogGroup"]
    }
  }' \
  --region us-east-1
```

Target Lambda function (the retention applier):

```bash
aws events put-targets \
  --rule auto-retention-new-log-groups \
  --targets '[{
    "Id": "retention-applier-lambda",
    "Arn": "arn:aws:lambda:us-east-1:111111111111:function:auto-retention-applier",
    "DeadLetterConfig": {
      "Arn": "arn:aws:sqs:us-east-1:111111111111:retention-dlq"
    }
  }]' \
  --region us-east-1
```

> The auto-retention Lambda handler code moved verbatim to [references/worked-examples.md](references/worked-examples.md); the EventBridge rule and target CLI above stay canonical.
> Load it when deploying the CreateLogGroup automation.

**Critical timing note:** The `CreateLogGroup` API call creates the
group but tags may not be set in the same call. If the service creating
the log group tags it later (e.g., Lambda tags its own log groups
asynchronously), the Lambda may see no tags. Two strategies:

1. **Default-first:** Apply the account default retention immediately
   on CreateLogGroup. A second EventBridge rule on `TagResource` (or a
   60-second delay) re-evaluates and upgrades if tags warrant.
2. **Tag-aware with delay:** The Lambda sleeps 5 seconds, then checks
   tags. This risks a brief window where the group has no retention.

The recommended pattern is **default-first** — apply the account-level
default immediately, then upgrade via a tag-change rule.

### Step 5: Manage subscription and metric filters during retention changes

Changing retention does NOT affect subscription or metric filters.
Inventory them for audit:

```bash
aws logs describe-subscription-filters --log-group-name <name>
aws logs describe-metric-filters --log-group-name <name>
```

**Decommissioning a log group** (correct order): delete subscription
filters → delete metric filters → export to S3 if compliance requires →
set retention to 1 day (do NOT delete the group — let retention expire
naturally) → optionally delete after all data expires.

**Metric filter preservation:** metric filters powering CloudWatch
alarms survive retention changes — they evaluate at ingestion time.
Operators often confuse "retention shortened" with "metric filter
destroyed." Document this explicitly.

### Step 6: Configure S3 archival via Kinesis Firehose

For compliance logs that need retention beyond CloudWatch's maximum
(3653 days / 10 years) or where S3 storage is cheaper than CloudWatch
storage:

**Cost crossover point:** CloudWatch Logs storage costs $0.03/GB/month.
S3 Standard costs ~$0.023/GB/month but requires Firehose ($0.029/GB
delivered). For logs retained > 90 days, S3 archival is typically
cheaper. For logs retained < 90 days, CloudWatch is cheaper because
there is no Firehose delivery cost.

> The delivery-stream and subscription-filter CLI plus the Firehose design-decision table moved verbatim to [references/firehose-s3-export.md](references/firehose-s3-export.md).
> Load it when configuring S3 archival.

For the complete Firehose-to-S3 pipeline reference including IAM roles,
S3 lifecycle policies, and Athena table DDL, see
**references/firehose-s3-export.md**.

### Step 7: Cost estimation per retention tier

CloudWatch Logs costs: $0.50/GB ingestion (unavoidable), $0.03/GB-month
storage (controlled by retention), $0.005/GB Insights queries scanned,
$0.02/GB cross-account data transfer.

Formula: `Monthly storage = dailyIngestGB * retentionDays * $0.03`

Worked example (50 GB/month ingest):

| Retention | Stored GB | Monthly storage | Annual cost |
|---|---|---|---|
| Never Expire (1yr) | ~600 | $18.00 | $216 |
| 90 days | ~150 | $4.50 | $54 |
| 30 days | ~50 | $1.50 | $18 |
| 7 days | ~12 | $0.36 | $4.32 |
| S3 GZIP (1yr) | ~150 compressed | $3.45 | $41.40 |

S3 archival becomes cheaper at the ~90-day mark. See
**references/firehose-s3-export.md** for the full cost crossover analysis.

### Step 8: Enforce account-level default retention

Since CloudWatch Logs has no native account-level default, the
automation must enforce one via a combination of:

1. **EventBridge on CreateLogGroup** (Step 4) — applies the default to
   new groups.
2. **Scheduled Lambda sweep** — a daily EventBridge scheduled rule
   that scans for Never Expire groups and applies the default:

> The daily-sweep EventBridge rule and sweep-Lambda code moved verbatim to [references/worked-examples.md](references/worked-examples.md).
> Load it when enforcing the account-level default.

3. **CloudFormation StackSet** — for CloudFormation-managed log groups,
   always include `RetentionInDays` in the `AWS::Logs::LogGroup`
   resource. A CloudFormation linter rule (cfn-lint or cfn-nag) can
   flag log groups without `RetentionInDays`.

### Step 9: Multi-account rollout via AWS Organizations

For an Organizations fleet, the retention automation deploys as a
CloudFormation StackSet with `SERVICE_MANAGED` permission model. The
StackSet deploys the EventBridge rule, Lambda, IAM role, and DLQ to
each member account. A management-account sweep Lambda provides
centralized auditing via `organizations list-accounts` + cross-account
role assumption.

> The create-stack-set / create-stack-instances CLI moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
> Load it when rolling out across an Organizations fleet.

### Step 10: Audit and verify

After deploying retention automation, verify end-to-end:

> The end-to-end verification CLI (Never-Expire check, rule status, test log group, Firehose status, CloudTrail audit) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
> Load it after deploying the automation.

## Output format

```text
RETENTION: <reference>
LOG_GROUP: <name or "account-wide">
POLICY:
  - Tag map: <tag-key=value -> retention-days>
  - Tier: <which of the 22 allowed values>
  - Default: <account-level default retention-days>
TRIGGER:
  - Existing: MANUAL_SWEEP (describe + put loop)
  - New: EVENTBRIDGE CreateLogGroup -> Lambda
ARCHIVAL: <Firehose-to-S3 config, or "NONE — retention-only">
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet or YAML for the retention automation>
```

### Worked example — AUTOMATION_DEPLOYED, tag-based retention with archival

```text
RETENTION: prod-log-retention-baseline
LOG_GROUP: account-wide (200 groups)
POLICY:
  - Tag map: Environment=prod -> 90d, staging -> 30d, dev -> 7d, untagged -> 14d
  - Tier: 90/30/7/14 (all in allowed set)
  - Default: 14 days (account-level fallback)
TRIGGER:
  - Existing: Daily scheduled Lambda sweep (describe-log-groups + put-retention-policy)
  - New: EventBridge CreateLogGroup -> auto-retention-applier Lambda
ARCHIVAL: Firehose log-archive-prod -> S3 com-company-log-archive-prod (GZIP, 5MB/300s buffer)
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  # EventBridge rule
  aws events put-rule --name auto-retention-new-log-groups --event-pattern '{"source":["aws.logs"],"detail-type":["AWS API Call via CloudTrail"],"detail":{"eventSource":["logs.amazonaws.com"],"eventName":["CreateLogGroup"]}}'
  # Retention policy per group
  aws logs put-retention-policy --log-group-name <name> --retention-in-days 90
  # Firehose archival
  aws logs put-subscription-filter --log-group-name <name> --filter-name archive-to-firehose --filter-pattern "" --destination-arn arn:aws:firehose:us-east-1:111111111111:deliverystream/log-archive-prod
```

### Worked example — REVIEW_REQUIRED, missing tag schema

> This second worked example moved verbatim to [references/worked-examples.md](references/worked-examples.md); the AUTOMATION_DEPLOYED example above stays canonical.
> Load it when tag coverage is incomplete.

## Anti-Patterns — NEVER do these things

- NEVER leave log groups at Never Expire by default. Every log group
  without an explicit retention policy accumulates cost indefinitely.
  The single most impactful CloudWatch Logs cost optimization is
  setting retention on every group.

- NEVER round retention DOWN to the nearest allowed tier. If the
  desired retention is 45 days, the allowed tiers are 30 and 60. Round
  UP to 60. Rounding down to 30 deletes 15 days of data the operator
  expected to retain.

- NEVER deploy the EventBridge CreateLogGroup rule without a DLQ. If
  the retention Lambda fails (throttling, permissions, timeout), the
  CreateLogGroup event is lost and the group stays Never Expire. A DLQ
  captures the event for retry.

- NEVER delete a log group as a way to "reset" retention. Deleting a
  log group destroys all stored data, all subscription filters, all
  metric filters, and all associated CloudWatch alarms. Use
  `put-retention-policy` to control data lifecycle, not
  `delete-log-group`.

- NEVER assume tags are present on CreateLogGroup. Many AWS services
  create log groups without tags. The auto-retention Lambda must have
  a default fallback for untagged groups.

- NEVER forget that Firehose delivery has latency. The last buffer
  window before expiry may not flush to S3. Use a retention at least
  1 day longer than strictly needed when Firehose archival is in the
  pipeline.

- NEVER assume cross-account subscription filter destinations inherit
  source retention. The destination applies its own policy.

- NEVER omit the daily sweep Lambda. The EventBridge rule catches new
  groups, but existing Never Expire groups and uncommon creation paths
  may slip through.

- NEVER configure Firehose archival without S3 lifecycle policies.
  Transitioning to Glacier after 90 days ($0.0036/GB/month) and Deep
  Archive after 180 days ($0.00099/GB/month) reduces costs 10-20x.

- NEVER use `delete-retention-policy` to "reset" a group. This removes
  the retention policy entirely, causing unbounded growth. Use
  `put-retention-policy` with the new value instead.

- NEVER deploy multi-account retention automation without testing in
  a single account first. The StackSet propagates to ALL member
  accounts simultaneously.

- NEVER forget that `put-retention-policy` is throttled at ~5-10
  calls/sec. Batch-applied retention across 500 log groups without
  rate limiting produces `ThrottlingException` storms.

## Pre-flight safety checks (run before applying any retention CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit: `CONFIRM: About to <action> for log group <name> in account
  <account>. Logs older than <retention> will be permanently deleted.
  Proceed? (yes/no)`

- **Export to S3 before shortening retention on compliance logs.** Use
  `create-export-task` — the export is asynchronous and may take hours
  for large log groups.

- **Verify no active alarms depend on metric filters** on the target
  log group before shortening retention below the alarm evaluation
  window.

- **Test the EventBridge CreateLogGroup rule in a non-production
  account first.** Verify the Lambda fires and applies correct
  retention before promoting the StackSet.

- **Before multi-account rollout**, verify the Lambda execution role
  exists in every member account. Check stack instances after
  deployment for failures.

## Appendix A — Retention tier quick-reference

The 22 allowed values: `1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180,
365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653`.

Common tiers: dev=7, staging=14/30, prod=90, compliance=2557 (7yr)
or 3653 (10yr). Round UP to the nearest allowed value — never down.
For the full round-up mapping table and cost estimation worksheet,
see **references/retention-tier-mapping.md** and
**references/firehose-s3-export.md**.

## Recent AWS features (2024-2026)

> The 2024-2026 feature notes moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
> Load on demand when checking recent feature availability.

## Expert heuristic: the Never Expire trap

CloudWatch Logs is one of the few AWS services where the default
state is unbounded cost growth. Every log group created without an
explicit retention policy stays Never Expire indefinitely.

**The rule (non-negotiable):**

> EVERY log group in EVERY account MUST have an explicit retention
> policy. The EventBridge CreateLogGroup rule is mandatory. The daily
> sweep Lambda is the safety net.

**Why:** A single Lambda function generating 5 GB/day, left at Never
Expire for a year, costs $900 in storage. A microservices fleet can
easily reach 200+ Never Expire groups, costing $10,000+/year.

**Detection:** `describe-log-groups` filter for null retentionInDays;
AWS Config rule `log-group-retention-period-set`; Security Hub
finding CW.1; Cost Explorer CloudWatch Logs trend.

**Surface in output:** include `NEVER_EXPIRE_GROUPS: <count>` and
`COST_EXPOSURE: <$amount/month>`. If `NEVER_EXPIRE_GROUPS > 0`, do
NOT mark the deployment as complete.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — batch rate-limited apply script, auto-retention Lambda handler, daily-sweep Lambda, and the REVIEW_REQUIRED worked example.
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 non-obvious CloudWatch Logs behaviors, the Mindset deep-dive facts, multi-account StackSet CLI, and 2024-2026 feature notes.
- [references/error-handling.md](references/error-handling.md) — put-retention-policy error table (InvalidParameterException, ThrottlingException, ResourceNotFoundException, AccessDeniedException).
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — inventory CLI (describe-log-groups, tags) and the end-to-end post-deploy verification sequence.
- [references/firehose-s3-export.md](references/firehose-s3-export.md) — full Firehose-to-S3 pipeline (now also the delivery-stream and subscription-filter CLI plus the design-decision table).
- [references/retention-tier-mapping.md](references/retention-tier-mapping.md) — complete round-up mapping table and cost-estimation worksheet.

## Domain

AWS CloudOps / Management — CloudWatch Logs lifecycle automation.

## AWS documentation

- **CloudWatch Logs retention** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html#SettingLogRetention
- **CloudWatch Logs subscription filters** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/SubscriptionFilters.html
- **Kinesis Firehose** — https://docs.aws.amazon.com/firehose/latest/dev/what-is-this-service.html
- **EventBridge rules** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rules.html
- **AWS Config rule for log retention** — https://docs.aws.amazon.com/config/latest/developerguide/log-group-retention-period-set.html
