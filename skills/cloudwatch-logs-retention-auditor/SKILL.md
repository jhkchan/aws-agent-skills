---
name: cloudwatch-logs-retention-auditor
description: >-
  Audits CloudWatch Logs log groups for Never-expire retention (silent
  infinite-cost accumulation), missing SSE-KMS customer-managed-key (CMK)
  encryption, excessive-retention × volume cost exposure, subscription
  filter fan-out (Lambda/Kinesis/Cross-account destination), missing
  metric filters, and absent CloudWatch Logs Anomaly Detectors. Emits a
  deterministic first-fail-wins verdict
  (NO_RETENTION | NO_ENCRYPTION | COST_RISK | CONFIG_GAP | OK) per log
  group with enumerated findings and CLI remediation. Use when reviewing
  CloudWatch Logs posture, auditing log group retention, validating KMS
  CMK encryption, hunting for runaway cost on Never-expire groups,
  checking metric-filter / anomaly-detector observability coverage, or
  hardening log-group posture before compliance review.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline config classification.
  Live-account audits use aws logs describe-log-groups,
  describe-metric-filters, describe-subscription-filters,
  describe-anomaly-detectors, and aws kms describe-key (AWS CLI v2, SSO
  or key-based credentials).
keywords:
  - CloudWatch Logs
  - log group retention
  - Never expire
  - retentionInDays
  - SSE-KMS
  - customer-managed key
  - kmsKeyId
  - metric filter
  - subscription filter
  - anomaly detector
  - CloudWatch Logs Insights
  - storedBytes
  - PutRetentionPolicy
  - AssociateKmsKey
  - PutMetricFilter
  - PutSubscriptionFilter
  - log cost audit
  - infinite retention
  - compliance retention
  - observability gap
tags: [cloudwatch-logs, management, retention, cost, kms-encryption, metric-filters, anomaly-detection, audit]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Management
  verdict_shape: "NO_RETENTION | NO_ENCRYPTION | COST_RISK | CONFIG_GAP | OK"
  when_to_use: >-
    Pre-compliance review of CloudWatch Logs log groups, Never-expire
    retention audits, KMS CMK encryption verification, runaway log cost
    investigations, metric-filter / anomaly-detector coverage audits, or
    hardening log-group posture before production cutover.
  activation_triggers:
    - "audit this CloudWatch Logs group"
    - "is my log group retention set"
    - "Never expire log group"
    - "check CloudWatch Logs cost"
    - "is CloudWatch Logs encrypted with KMS"
    - "are metric filters configured"
    - "is anomaly detection enabled"
    - "subscription filter audit"
    - "CloudWatch Logs compliance check"
    - "log group cost risk"
  invocation_schema: >-
    Input: either (a) describe-log-groups output (JSON or key-value
    summary) for one log group, optionally paired with
    describe-metric-filters, describe-subscription-filters, and
    describe-anomaly-detectors output, OR (b) a log-group name/ARN for
    live-account audit. Output: deterministic LOG_GROUP/VERDICT/REASON/
    FINDINGS/REMEDIATION block per log group, where VERDICT ∈
    {NO_RETENTION, NO_ENCRYPTION, COST_RISK, CONFIG_GAP, OK, ERROR}.
---

# CloudWatch Logs Retention & Cost Auditor

## Mindset

**One-line takeaway:** the verdict is the **first** failing dimension in
a strict first-fail-wins order — retention before encryption, encryption
before cost risk, cost risk before observability config gap. A log group
with `retentionInDays` absent (Never expire) fails the most fundamental
gate regardless of how well everything else is configured.

CloudWatch Logs is the default sink for application, Lambda, and
container logs. The pricing model is silent and additive — ingestion,
storage, and Insights queries bill continuously until you set a
retention. A log group left at the **default Never-expire retention** is
the single most common source of unexpected AWS bill surprises after
idle EC2 and untagged S3.

Three CloudWatch Logs behaviors shape every verdict:

- **`retentionInDays` absence means Never expire, NOT 0 or default-30.**
  `describe-log-groups` simply omits the field. A null-check (not a
  truthy-check) is required.
- **SSE at rest is on by default, but with a CloudWatch service-managed
  key, not a customer-managed KMS key (CMK).** Absence of `kmsKeyId`
  is NOT "unencrypted" — it is "no customer-controlled key." You cannot
  audit key usage via CloudTrail, cannot enforce key-policy guardrails,
  and cannot satisfy CMK-mandated compliance frameworks (FedRAMP,
  HIPAA-with-BAA-controls, SOC 2 Type II with CMK mandate).
- **`storedBytes` is a cumulative counter since log-group creation, not
  current storage.** A 3-year-old group with `storedBytes: 2 TB` may
  currently hold only 5 GB if retention is 30 days.

## Quick reference — verdict matrix

| Dimension checked | Fail verdict | Risk | Step |
|---|---|---|---|
| `retentionInDays` absent / null / 0 | **NO_RETENTION** | CRITICAL | 1 |
| `kmsKeyId` absent / null / empty | **NO_ENCRYPTION** | HIGH | 2 |
| Cost threshold crossed (see COST_RISK table below) | **COST_RISK** | HIGH | 3 |
| No metric filters AND/OR no anomaly detector | **CONFIG_GAP** | MEDIUM | 4 |
| All dimensions pass | **OK** | LOW | 5 |

The first matching row is the verdict — do NOT continue to lower rows
once one fires. Findings from later dimensions are still enumerated in
the FINDINGS block but cannot upgrade the verdict.

**COST_RISK thresholds (Step 3 — first matching row fires):**

| # | Condition | Why |
|---|---|---|
| 3a | `retentionInDays >= 3653` | API maximum (~10 years); almost no workload justifies this — usually a copy-paste from a "7-year" template rounded up. Fires regardless of volume. |
| 3b | `retentionInDays >= 731` AND `storedBytes >= 10 GB` | 2+ year retention on a non-trivial group; current storage cost is material. |
| 3c | `retentionInDays >= 365` AND `storedBytes >= 100 GB` | Year-plus retention on a high-volume group; storage + Insights query costs compound. |
| 3d | `retentionInDays >= 90` AND a Lambda subscription filter is active on the group | Lambda invocation cost on a high-volume group frequently exceeds the CloudWatch Logs storage charge — the filter is a cost multiplier. |

**Risk labels (used in FINDINGS):** CRITICAL = unbounded cost or
irrecoverable data loss; HIGH = bounded but material cost or auditability
gap; MEDIUM = observability gap, no cost/security impact; LOW = clean
posture. The verdict's risk is the risk of the first failing dimension.

**`storedBytes` fallback when `creationTime` is unavailable:** use
`storedBytes` directly as a worst-case upper bound (treat as current
storage). When `creationTime` IS available, estimate daily ingestion as
`storedBytes / ageInDays` and project current storage as
`(storedBytes / ageInDays) * retentionInDays` — typically 2-10x smaller
than the raw `storedBytes` reading.

**Critical NEVER summary** (full list in Anti-Patterns section):

- NEVER treat absence of `retentionInDays` as a default — it means Never
  expire (NO_RETENTION, CRITICAL).
- NEVER assume SSE-KMS CMK is in use because "CloudWatch Logs is
  encrypted at rest" — the default is a CloudWatch service-managed key,
  not a CMK. Absence of `kmsKeyId` is NO_ENCRYPTION (HIGH).
- NEVER classify a `retentionInDays`-absent group as NO_ENCRYPTION or
  COST_RISK — first-fail-wins terminates at NO_RETENTION regardless of
  what else is missing.

## Pre-flight: log group metadata gate

**Account-wide sweep note (pagination):** `aws logs describe-log-groups`
returns at most 50 per page; `describe-metric-filters`,
`describe-subscription-filters`, and `describe-anomaly-detectors` each
page independently at the same cap. Use `--starting-token` from the prior
`nextToken` to drain all pages — iterating only the first page silently
skips the long tail of stale Never-expire groups.

| Field | Value | Effect |
|---|---|---|
| `retentionInDays` | absent | **Never expire.** Highest-priority finding. Jump to Step 1. |
| `retentionInDays` | `1,3,5,7,14,30,60,90,120,150,180,365,400,545,731,1827,2192,2557,2922,3288,3653` | Valid values. Any other value is rejected at `PutRetentionPolicy` time — if observed, the snapshot is stale; re-fetch. |
| `kmsKeyId` | absent | **SSE with CloudWatch service-managed key** (still encrypted at rest, no CMK). NO_ENCRYPTION applies (Step 2). |
| `kmsKeyId` | ARN present | **SSE-KMS with CMK.** Verify region matches the log group region; cross-region CMK is rejected. |
| `storedBytes` | integer | **Cumulative counter since creation** — never decreases. Use `storedBytes / ageInDays` to estimate average daily ingestion. |
| Subscription filter count | `0,1,2` | Quota is **2 per group** (raised from 1 in 2020). A third `PutSubscriptionFilter` returns `LimitExceededException`; producers are not notified and silently drop the fan-out. |

**If input is unparseable** (invalid JSON, missing `logGroupName`,
truncated output), output:

```text
LOG_GROUP: <name-or-arn>
VERDICT: ERROR
REASON: Log group metadata is malformed — cannot classify. Missing field: <field>.
REMEDIATION: Re-fetch with `aws logs describe-log-groups --log-group-name-prefix <name> --output json` and re-audit.
```

## Process — Classification logic (first-fail-wins, in order)

### Step 0: Expert knowledge — non-obvious CloudWatch Logs behaviors

These behaviors change a verdict if ignored. Each is load-bearing:

- **`retentionInDays` absence is the default for new log groups.**
  Unlike S3 lifecycle rules or CloudTrail retention, CloudWatch Logs
  does NOT apply a default retention. New groups remain Never-expire
  until you explicitly call `PutRetentionPolicy`. Operators assume a
  "default sane retention" exists — it does not.

- **Retention changes apply only to NEW events.** Setting retention
  from Never to 30 days does NOT immediately delete existing logs.
  Existing events expire on the schedule they were originally written
  under; only events received AFTER the `PutRetentionPolicy` call are
  bound by the new retention. For incident response, shortening
  retention does not cleanse historical data — you must delete log
  streams or the log group itself.

- **SSE-KMS CMK is a paid feature with hidden cost.** Associating a
  CMK via `AssociateKmsKey` causes every `PutLogEvents` batch to
  trigger a `kms:GenerateDataKey` call. At $0.03 per 10,000 KMS
  requests, a high-volume group emitting 1,000 batches/sec accrues
  ~$8,000/month in KMS charges alone — frequently more than the
  CloudWatch Logs ingestion charge itself.

- **The default service-managed SSE is NOT `aws/logs` AWS-managed.**
  Unlike S3 (`aws/s3`) or EBS (`aws/ebs`), CloudWatch Logs does not
  expose an AWS-managed CMK in the customer account. The default is
  a CloudWatch-internal service key that never appears in
  `aws kms list-keys`. Therefore "no `kmsKeyId`" cannot be remediated
  by "switch to AWS-managed key" — the only CMK path is customer-
  managed.

- **Subscription filter quota is 2, not unlimited.** A common
  misconfiguration chains Logs → Lambda → Logs (cross-region) →
  Firehose → S3, where each hop consumes a slot. The third filter on
  the same source fails at `PutSubscriptionFilter` time, but producers
  continue writing logs unaware the fan-out is silently incomplete.

- **Metric filters do not backfill.** A filter processes only events
  received AFTER creation. Adding an "ERROR" counter today produces
  no historical baseline. Always pair with a CloudWatch Logs Anomaly
  Detector if retroactive signal is needed.

- **Metric filter pattern syntax is CloudSearch-style, not regex.**
  Complex patterns cost more per-GB to evaluate. The cheapest pattern
  is a literal token (`"ERROR"`); multi-field `[..., ...]` patterns
  with anchoring/alternation are most expensive. For high-volume
  groups, prefer two cheap filters over one complex filter.

- **Anomaly Detectors require a 2-week baseline.** A newly-created
  detector returns `Status: TRAINING` for ~14 days, during which it
  produces no findings. A less-than-2-week-old group has no meaningful
  anomaly detection even with a detector configured. Treat as
  CONFIG_GAP, not OK.

- **Cross-account subscription filters use a destination, not the
  filter itself.** The recipient account creates a
  `aws logs put-destination` + destination policy; the sender's filter
  targets the destination ARN. The destination policy IS the security
  boundary — a permissive policy allows any sender account to write
  to the recipient's Kinesis/Lambda. Always audit destination
  policies alongside subscription filters.

- **`describe-log-groups --log-group-name-prefix` is a PREFIX match,
  not a wildcard.** `/aws/lambda` matches `/aws/lambdaFoo` and
  `/aws/lambda-prod`. For exact-match, omit `--log-group-name-prefix`
  and pass `--log-group-name` (CLI v2 only).

- **`storedBytes` is monotonic.** Never decreases — not on retention
  expiry, not on `DeleteLogStream`. The only reset is `DeleteLogGroup`.

- **Insights queries bill per-GB-scanned, not per-query.** A
  `fields @timestamp, @message | filter level == "ERROR"` query on a
  100 GB group costs the same as a `stats count(*)` query — both scan
  the full time-range selection. Long retention + high volume =
  compounding query cost.

- **PutLogEvents batch limits: 1 MB and 10,000 events per batch.**
  Producers exceeding these limits receive
  `DataAlreadyAcceptedException` or throttling. Not a verdict driver,
  but high `storedBytes` growth with these errors suggests the
  producer needs better batching or stream sharding.

- **Log group KMS key region must match the log group region.**
  Multi-Region KMS keys are supported, but the in-region replica ARN
  must be referenced — the primary ARN from another region is
  rejected at `AssociateKmsKey` time.

- **Log group names cannot be renamed.** "Renaming" requires creating
  a new group, re-pointing the producer, and accepting that historical
  logs remain under the old name. A Never-expire group with a misnamed
  producer is doubly expensive — you cannot migrate cheaply.

- **Log group ARN suffix `:*` is required for resource-level IAM
  permissions.** `arn:aws:logs:<region>:<account>:log-group:<name>:*`
  matches stream-scoped actions (PutLogEvents, GetLogEvents,
  DeleteLogStream). Without `:*`, identity-based policies targeting
  the ARN will NOT match — the most common IAM policy error for
  CloudWatch Logs.

- **`AssociateKmsKey` is NOT retroactive.** When you associate a CMK
  on an existing log group, only events received AFTER the association
  are encrypted with the CMK. Existing events remain under the prior
  service-managed key — there is no re-encryption API. For
  compliance-mandated CMK coverage, you must rotate the underlying
  data (delete log streams after verifying CMK coverage is in place
  for new events) or migrate to a new CMK-associated group.

- **CloudFormation `AWS::Logs::LogGroup` without `RetentionInDays`
  creates a Never-expire group silently.** Unlike console-created
  groups (which at least surface the retention field), IaC templates
  that omit the property produce no warning — the stack succeeds and
  the group begins accumulating immediately. This is the dominant
  source of Never-expire groups in IaC-managed accounts. Always
  require `RetentionInDays` as a stack-level parameter or use a
  CloudFormation hook (rule `cloudwatch-logs-retention-set`) to fail
  the stack on omission.

- **`PutRetentionPolicy` is throttled at 5 requests/sec/account.**
  Bulk remediation across thousands of groups needs exponential
  backoff or the CLI returns `ThrottlingException`. The same cap
  applies to `AssociateKmsKey`, `PutMetricFilter`, and
  `PutSubscriptionFilter` — all control-plane mutations share the
  CloudWatch Logs account-level rate limit.

- **Lambda subscription filters without `DeadLetterConfig` silently
  drop failed invocations.** A Lambda fan-out that errors (exception,
  timeout, payload-too-large) is retried twice then dropped — without
  a DLQ, the drop has no metric and no alarm. For audit trails that
  must not lose events, always pair the subscription filter with a
  DeadLetterConfig (an SQS ARN); treat its absence as an additive
  finding when the subscription filter is on a security-relevant
  group.

- **CloudWatch Logs Anomaly Detectors bill per-detector-hour
  (~$0.15/detector/day, ~$4.50/detector/month at ONE_MIN frequency).**
  Adding a detector to every group in a 1,000-group account accrues
  ~$4,500/month in detector charges alone — sometimes more than the
  logs themselves. Reserve anomaly detectors for groups with
  operational or security signal, not for low-volume debug groups.

### Step 1: Never-expire retention (highest priority — silent infinite cost)

If `retentionInDays` is absent, null, or 0, the log group **never
expires**. Verdict: **NO_RETENTION** (CRITICAL).

- Storage accumulates at the Published-Log-Storage Per-GB-month rate
  indefinitely. A 10 GB/month ingestion group costs ~$50/month in
  storage after 1 year, ~$500/month after 2 years — unbounded.
- Most compliance frameworks (SOC 2, PCI-DSS v4, ISO 27001, FedRAMP)
  require **defined** retention. A Never-expire group is a control
  deficiency even when "we want to keep everything" — the absence of
  a documented decision is the finding.
- Remediation is `aws logs put-retention-policy --log-group-name
  <name> --retention-in-days <N>`. The CLI does NOT prompt.

**Why highest priority:** a Never-expire group with no CMK and no
metric filters is unambiguously NO_RETENTION (first-fail-wins). The
absence of retention is the loudest signal; encryption and observability
gaps compound but cannot override it.

### Step 2: SSE-KMS CMK encryption

If `kmsKeyId` is absent, null, or empty, the log group uses CloudWatch
service-managed encryption (SSE at rest is on, no CMK). Verdict:
**NO_ENCRYPTION** (HIGH).

- Without a CMK, you cannot audit key usage via CloudTrail
  `kms:Decrypt` events for log access.
- Most regulated workloads (FedRAMP, HIPAA BAA controls, SOC 2 Type
  II with CMK mandate, PCI-DSS v4 requirement 3.5) require a
  **customer-controlled** key for log data at rest.
- Remediation is `aws logs associate-kms-key --log-group-name <name>
  --kms-key-id <key-arn>`. The key policy MUST permit
  `logs.<region>.amazonaws.com` to call `kms:GenerateDataKey` and
  `kms:Decrypt` — without this, PutLogEvents/GetLogEvents fail with
  `AccessDeniedException`.

**Why HIGH not CRITICAL:** SSE at rest is on by default; the gap is
customer-controlled key auditability, not plaintext storage. CRITICAL is
reserved for active data-loss or infinite-cost vectors (NO_RETENTION).

### Step 3: Cost-risk retention × volume profile

If retention IS set AND a CMK IS associated, evaluate the retention ×
volume profile against the **COST_RISK thresholds** (table in the Quick
Reference above). The first matching row (3a → 3d) fires COST_RISK; do
not continue evaluating lower-priority rows once one fires.

**Required inputs:** `retentionInDays`, `storedBytes`, `creationTime`
(for the daily-ingestion estimate). If `creationTime` is missing, fall
back to treating `storedBytes` as current storage (worst-case upper
bound) — note the fallback in FINDINGS. If `storedBytes` is also
missing, the cost dimension cannot be classified and the verdict skips
to Step 4 with a `DATA_MISSING` note.

**Lambda subscription-filter cost caveat (Row 3d):** the threshold
fires only for Lambda destinations, NOT for Kinesis Data Streams or
Firehose — Kinesis/Firehose bill by ingestion shard / delivery stream,
not per-event invocation, so their cost profile does not multiply with
event volume the way Lambda does.

**Why below NO_ENCRYPTION:** cost risk is bounded (retention value caps
it); CMK absence is an unbounded auditability gap that scales with the
volume of regulated data flowing through the group.

### Step 4: Observability config gap

If retention, encryption, and cost profile are all OK, evaluate
observability coverage. **CONFIG_GAP** fires when ANY of these is true:

- **No metric filters** configured. Without metric filters, you cannot
  build CloudWatch alarms on log content (error rate, latency, auth-
  failure spikes). Baseline observability gap.
- **No CloudWatch Logs Anomaly Detector** on the group. Anomaly
  detectors catch unknown-unknowns (sudden pattern shifts) that fixed
  metric filters cannot.
- **Anomaly Detector exists but `Status: TRAINING` OR created < 14
  days ago.** A training detector produces no findings — treat as
  CONFIG_GAP with the training caveat in REMEDIATION.

**Why below COST_RISK:** a config gap does not cost money or expose
data — it leaves you blind to events the logs already recorded.

### Step 5: All dimensions pass — OK

If retention is set to a sane value, a CMK is associated, the cost
profile is reasonable, and at least one metric filter OR anomaly
detector is present, verdict: **OK**.

Note in FINDINGS which dimensions passed and any defense-in-depth
recommendations.

## Output format (per log group)

```text
LOG_GROUP: <name-or-arn>
VERDICT: NO_RETENTION | NO_ENCRYPTION | COST_RISK | CONFIG_GAP | OK
REASON: <1-2 sentences citing the first failing dimension and step number>
FINDINGS:
  - [CRITICAL] <finding description (Step N)>
  - [HIGH] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific CLI per finding, or "None required" if OK>
```

### Worked example — Never-expire with no CMK

```text
LOG_GROUP: /aws/lambda/prod-checkout-api
VERDICT: NO_RETENTION
REASON: retentionInDays is absent — the log group Never expires, accumulating
storage cost indefinitely (Step 1). kmsKeyId is also absent (Step 2 finding)
but first-fail-wins terminates at Step 1.
FINDINGS:
  - [CRITICAL] retentionInDays absent (Never expire) — unbounded storage cost
    and undefined retention for compliance (Step 1)
  - [HIGH] kmsKeyId absent — CloudWatch service-managed key only; no CMK
    auditability (Step 2, suppressed by first-fail-wins but reported)
  - [OK] logGroupArn includes ':*' suffix — resource-level IAM policies match
REMEDIATION:
  1. Set retention: aws logs put-retention-policy --log-group-name
     /aws/lambda/prod-checkout-api --retention-in-days 90.
  2. Associate CMK: aws logs associate-kms-key --log-group-name
     /aws/lambda/prod-checkout-api --kms-key-id
     arn:aws:kms:us-east-1:111111111111:key/abc-123. Ensure key policy
     permits logs.us-east-1.amazonaws.com to kms:GenerateDataKey + Decrypt.
```

### Worked example — malformed input (ERROR path)

When `describe-log-groups` output is truncated or missing required
fields, the audit cannot proceed deterministically. Emit ERROR and stop —
do NOT fabricate a verdict from partial data.

```text
LOG_GROUP: /aws/lambda/checkout-api
VERDICT: ERROR
REASON: Log group metadata is malformed — required field 'retentionInDays'
missing AND 'storedBytes' missing. Cannot classify retention (Step 1) or
cost-risk (Step 3) without one of these.
REMEDIATION: Re-fetch with `aws logs describe-log-groups --log-group-name
/aws/lambda/checkout-api --output json` and re-audit. If the field
genuinely is absent in fresh output, that absence IS the signal — apply
Step 1 (NO_RETENTION) once the data is confirmed.
```

## Edge-case handling

- **`retentionInDays: 0` literal.** The API never returns 0; absence is
  the Never-expire signal. If a snapshot shows `retentionInDays: 0`, the
  snapshot is hand-edited or stale — treat as NO_RETENTION and note.

- **AWS service-created log groups** (`/aws/lambda/<function>`,
  `/ecs/<cluster>/<task>`, `AWSChatBot/<account>`). AWS services
  auto-create these on first PutLogEvents with NO retention. They
  silently accumulate until audited. Apply the same Step 1 logic —
  origin does not exempt them.

- **OpenSearch subscription filter (formerly Elasticsearch).** The
  subscription-to-OpenSearch integration can bypass the 2-per-group
  quota rule in some legacy configurations — flag any group with > 2
  subscription filters as an anomaly.

- **`kmsKeyId` referencing a deleted key.** If the CMK is in
  `PendingDeletion` state, PutLogEvents fails immediately. Treat as
  NO_ENCRYPTION (effectively unusable) and note the deleted-key state.

- **Metric filter with pattern `""` (empty).** Matches every event —
  effectively a no-op that inflates metric count. Flag as a CONFIG_GAP
  sub-finding (filter exists but is non-functional).

- **Subscription filter on a Never-retention group.** Double cost driver
  (storage + Lambda invocation). First-fail-wins verdict is still
  NO_RETENTION; surface the Lambda fan-out as an additive HIGH finding.

- **Anomaly Detector in `TRAINING` status.** Treat the group as not-yet-
  observable for anomaly purposes — verdict CONFIG_GAP with REMEDIATION
  noting "wait 14 days for baseline".

## Anti-Patterns — NEVER

- NEVER treat absence of `retentionInDays` as "default 30 days" or
  "default retention". CloudWatch Logs has NO default retention —
  absence means Never expire, the highest-severity cost finding.

- NEVER classify a `retentionInDays`-absent group as NO_ENCRYPTION or
  COST_RISK. First-fail-wins: NO_RETENTION is the verdict. Encryption
  and cost findings may be enumerated in FINDINGS but cannot override.

- NEVER assume SSE-KMS is in use because "CloudWatch Logs is encrypted
  at rest." The default is a CloudWatch service-managed key, not a
  customer-managed CMK. The `kmsKeyId` field must be present for OK at
  Step 2; absence is NO_ENCRYPTION.

- NEVER confuse `storedBytes` with current storage. It is a cumulative
  counter since log-group creation that never decreases. Always pair
  with retention and age.

- NEVER recommend associating a CMK without noting the KMS-request
  cost impact. Every PutLogEvents batch triggers
  `kms:GenerateDataKey`. For high-volume groups this can cost more
  than the CloudWatch Logs ingestion itself.

- NEVER recommend `aws logs delete-log-group` as remediation for
  excessive storage. It destroys all historical logs irreversibly and
  the producer will recreate the group on the next PutLogEvents. The
  correct remediation is `PutRetentionPolicy` to a sane value;
  deletion is reserved for genuinely decommissioned groups.

- NEVER assume shortening retention immediately deletes historical
  events. Retention changes apply only to events received AFTER the
  PutRetentionPolicy call. If the goal is immediate data cleansing,
  you must delete log streams or the log group — both destructive.

- NEVER treat metric filters as retroactive. They process events
  received AFTER creation only. Pair with an anomaly detector if
  retroactive signal is needed (and accept the 2-week training delay).

- NEVER overlook the 2-subscription-filter-per-group quota. A third
  `PutSubscriptionFilter` fails with `LimitExceededException`. If you
  need 3+ destinations, aggregate via Kinesis Data Streams or Firehose.

- NEVER classify a group as OK if the only observability signal is an
  anomaly detector in `TRAINING` status. Treat as CONFIG_GAP until it
  has 14 days of baseline.

- NEVER recommend a CMK from another region. CloudWatch Logs requires
  an in-region key. For multi-Region keys, reference the in-region
  replica ARN.

- NEVER assume `--log-group-name-prefix` is an exact match. It is a
  prefix — `/aws/lambda` matches `/aws/lambdaFoo`. Use
  `--log-group-name` (no `prefix`) for exact match in CLI v2.

- NEVER skip paginating `describe-log-groups`,
  `describe-metric-filters`, `describe-subscription-filters`, or
  `describe-anomaly-detectors`. Each caps at 50 per page. Iterating
  only the first page silently misses the long-tail groups.

- NEVER audit a subscription filter without also auditing the
  destination policy (for cross-account destinations). The destination
  policy IS the security boundary.

- NEVER classify COST_RISK based on `retentionInDays` alone. Retention
  × volume is the cost function; a 3653-day retention on 1 MB is
  cheaper than 30-day retention on 1 TB. Always pair retention with
  `storedBytes` and `creationTime`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`PutRetentionPolicy`, `AssociateKmsKey`, `DeleteLogGroup`,
  `PutMetricFilter`, `PutSubscriptionFilter`, `DeleteMetricFilter`,
  `DeleteSubscriptionFilter`, `PutAnomalyDetector`), the auditor MUST
  emit:
  `CONFIRM: About to <action> on log group <name> in account
  <account>. This affects <consequence>. Proceed? (yes/no)`.
  Do NOT execute the CLI command until the operator confirms.
- **Back up filters before modification.** Capture
  `aws logs describe-metric-filters --log-group-name <name> --output json`
  and `aws logs describe-subscription-filters --log-group-name <name>
  --output json` BEFORE any change — filters are not versioned.
- **Verify retention value is in the allowed list** (1, 3, 5, 7, 14,
  30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 2192, 2557,
  2922, 3288, 3653). `PutRetentionPolicy` with any other value returns
  `InvalidParameterException` without changing state.
- **Verify CMK region and policy before `AssociateKmsKey`.** Region
  must match; key policy must permit `logs.<region>.amazonaws.com` to
  call `kms:GenerateDataKey` + `kms:Decrypt`. Without this, PutLogEvents
  and GetLogEvents fail immediately.
- **Confirm KMS-request cost tolerance** before CMK association.
  Estimate PutLogEvents batches/sec and project monthly KMS cost at
  $0.03 per 10,000 GenerateDataKey calls.
- **For `DeleteLogGroup`:** incident-response-only. Irreversible;
  deletes all streams and stored events; breaks producers until they
  recreate the group. Verify by checking CloudTrail for recent
  `PutLogEvents` before deletion.
- **For cross-account subscription filter changes:** audit the
  destination policy in the recipient account BEFORE modifying the
  sender's filter. Fixing the sender side does not close the boundary.
- **Prefer additive over destructive changes.** Add filters / detectors
  / alarms (do not break existing access). Removing a subscription
  filter or shortening retention can break downstream consumers —
  capture backup and coordinate with owners first.

## Remediation guidance

### For NO_RETENTION (Step 1)

1. Set retention matching the workload's compliance window:
   ```bash
   aws logs put-retention-policy --log-group-name <name> \
     --retention-in-days 90 --profile <p>
   ```
2. Choose the value by intent, not default:
   - 14-30 days for operational/debug logs (cheapest).
   - 90 days for application logs covering one quarter of incident review.
   - 365 days for security/compliance logs (SOC 2, ISO 27001 standard).
   - 731+ days only with documented regulatory requirement (PCI-DSS
     1-year, HIPAA 6-year, financial-services 7-year).
3. Verify: `aws logs describe-log-groups --log-group-name-prefix <name>
   --query 'logGroups[0].retentionInDays'`.
4. Note the legacy-events caveat: existing events expire on their
   original schedule, not immediately.

### For NO_ENCRYPTION (Step 2)

1. Identify an in-region CMK:
   ```bash
   aws kms describe-key --key-id <key-id> --profile <p>
   # Confirm Origin: AWS_KMS, KeyState: Enabled, KeyManager: CUSTOMER,
   # and the region in the ARN matches the log group region.
   ```
2. Attach a key policy permitting CloudWatch Logs:
   ```json
   {
     "Sid": "AllowCloudWatchLogs",
     "Effect": "Allow",
     "Principal": {"Service": "logs.<region>.amazonaws.com"},
     "Action": ["kms:GenerateDataKey", "kms:Decrypt"],
     "Resource": "*",
     "Condition": {
       "ArnLike": {"aws:SourceArn": "arn:aws:logs:<region>:<account>:log-group:*"},
       "StringEquals": {"aws:SourceAccount": "<account>"}
     }
   }
   ```
3. Associate the CMK:
   ```bash
   aws logs associate-kms-key --log-group-name <name> \
     --kms-key-id arn:aws:kms:<region>:<account>:key/<id> --profile <p>
   ```
4. Verify: `aws logs describe-log-groups --log-group-name-prefix <name>
   --query 'logGroups[0].kmsKeyId'`.
5. Project the KMS-request cost before committing at scale.

### For COST_RISK (Step 3)

1. Shorten retention to the minimum compliance window:
   ```bash
   aws logs put-retention-policy --log-group-name <name> \
     --retention-in-days 90 --profile <p>
   ```
2. For high-volume Lambda subscription filters: evaluate replacing
   synchronous Lambda fan-out with Kinesis Data Streams + enhanced
   fan-out, or move the consumer to a scheduled Logs Insights query
   on a data subset.
3. Archive cold logs to S3 (with S3 lifecycle to Glacier) before
   shortening retention if regulatory retention requires long-term
   storage but query frequency is low. Use a Firehose delivery stream
   with a CloudWatch Logs subscription filter.
4. Set a CloudWatch alarm on `IncomingBytes` to catch future surges:
   ```bash
   aws cloudwatch put-metric-alarm --alarm-name <name>-ingestion-spike \
     --metric-name IncomingBytes --namespace AWS/Logs \
     --statistic Sum --period 300 --threshold <bytes> \
     --comparison-operator GreaterThanThreshold --evaluation-periods 1 \
     --dimensions Name=LogGroupName,Value=<name>
   ```

### For CONFIG_GAP (Step 4)

1. Add at least one metric filter for the primary error signal:
   ```bash
   aws logs put-metric-filter --log-group-name <name> \
     --filter-name ErrorCount --filter-pattern '"ERROR"' \
     --metric-transformations metricName=ErrorCount,metricNamespace=LogMetrics,metricValue=1
   ```
2. Add a CloudWatch Logs Anomaly Detector:
   ```bash
   aws logs put-anomaly-detector --log-group-arn-list <arn> \
     --detector-name <name>-anomaly --eval-frequency ONE_MIN --profile <p>
   ```
3. Wait 14 days for baseline training. Findings begin only after the
   baseline is established.
4. Add an alarm on the anomaly detector:
   ```bash
   aws cloudwatch put-metric-alarm --alarm-name <name>-anomaly-alarm \
     --namespace AWS/Logs --metric-name <detector-name> \
     --dimensions Name=LogGroup,Value=<name> \
     --statistic Sum --period 60 --threshold 0 \
     --comparison-operator GreaterThanThreshold --evaluation-periods 1
   ```

### For OK

1. No remediation required for the current posture.
2. Defense-in-depth:
   - Add a second anomaly detector at `FIVE_MIN` for noisier groups.
   - Add a CloudWatch alarm on `IncomingBytes` for cost-spike detection.
   - Add a metric filter on `WARN` for early-warning signal.
   - For multi-account deployments, centralize logs via a cross-account
     subscription filter to a security-tooling account with a
     destination policy scoped via `aws:SourceAccount`.

## Domain

AWS CloudOps / Management & Governance — CloudWatch Logs cost, security,
and observability posture.
