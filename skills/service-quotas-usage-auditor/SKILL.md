---
name: service-quotas-usage-auditor
description: >-
  Audits AWS Service Quotas — quota utilization per service, approaching
  limits (>=80%), CloudWatch alarm coverage on AWS/Usage metrics, applied
  vs default quota drift, adjustable quotas stuck at default with rising
  usage, denied or stale quota increase requests, and non-trackable quotas
  lacking a UsageMetric. Emits a deterministic verdict
  (APPROACHING_LIMIT | NO_ALARM | CONFIG_GAP | OK) per quota with
  enumerated findings and CLI remediation. Use when reviewing quota
  utilization, checking for approaching service limits, auditing quota
  increase request history, or validating CloudWatch alarm coverage.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline quota-snapshot classification.
  Live-account audits use aws service-quotas list-service-quotas,
  get-service-quota, get-aws-default-service-quota,
  list-requested-service-quota-change-history, and aws cloudwatch
  describe-alarbs-for-metric (AWS CLI v2, SSO or key-based credentials).
keywords:
  - Service Quotas
  - quota utilization
  - approaching limit
  - AWS/Usage
  - CloudWatch alarm
  - quota increase
  - applied quota
  - default quota
  - Adjustable
  - UsageMetric
  - quota code
  - service limits
  - Trusted Advisor
  - quota monitoring
  - quota remediation
tags: [service-quotas, management, quota, limits, cloudwatch, monitoring, audit]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Management
  verdict_shape: "APPROACHING_LIMIT | NO_ALARM | CONFIG_GAP | OK"
  when_to_use: >-
    Auditing AWS Service Quotas utilization, CloudWatch alarm coverage on
    AWS/Usage metrics, and quota increase request history.
  activation_triggers:
    - "audit service quotas"
    - "check quota utilization"
    - "approaching service limit"
    - "quota increase request"
    - "cloudwatch alarm on quota"
    - "service limits audit"
  invocation_schema: >-
    Input: either (a) a Service Quotas snapshot (quota code, service code,
    applied value, default value, UsageMetric, utilization, increase
    request history, CloudWatch alarm state), OR (b) a service-code for
    live-account audit via aws service-quotas list-service-quotas.
    Output: deterministic QUOTA/VERDICT/REASON/UTILIZATION/FINDINGS/
    REMEDIATION block per quota, where VERDICT is one of APPROACHING_LIMIT,
    NO_ALARM, CONFIG_GAP, OK (or ERROR for malformed input).
---

# Service Quotas Usage Auditor

## Mindset

**One-line takeaway:** the verdict is the **worst** finding across all
dimensions, and three Service Quotas behaviors are easy to misjudge —
**applied vs default** (list-service-quotas returns the APPLIED value,
not the AWS default), **UsageMetric presence** (quotas without a metric
block CANNOT be auto-monitored via CloudWatch), and **request status
lifecycle** (a PENDING increase has not taken effect — the applied quota
is still the old value until APPROVED).

A quota is the hard ceiling on a specific AWS resource or API rate.
Exhausting one is a **silent outage**: API calls return
`ThrottlingException` or `LimitExceededException` with no remediation
window. Unlike a misconfigured policy (fixable by editing text), a quota
that blocks operations can stall an entire deployment pipeline while a
support case grinds through the approval process.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| Utilization >= 80% of applied quota (inclusive: exactly 80% counts) | **APPROACHING_LIMIT** | 1 |
| `Adjustable: false` AND utilization >= 50% | **CONFIG_GAP** | 2b |
| Increase request DENIED/NOT_APPROVED AND utilization >= 50% | **CONFIG_GAP** | 2c |
| At AWS default, `Adjustable: true`, utilization >= 50%, request history completely empty | **CONFIG_GAP** | 2d |
| No `UsageMetric` block defined | **CONFIG_GAP** | 2a |
| Has `UsageMetric`, utilization < 80%, no CloudWatch alarm | **NO_ALARM** | 3 |
| Utilization < 50%, alarm in place or N/A | **OK** | 4 |

See the ordered steps below for edge cases. Deep Service Quotas +
CloudWatch integration details are in the
[Deep reference](#deep-reference-service-quotas--cloudwatch-internals)
section at the end.

## Pre-flight: quota metadata gate (run before classification)

Before evaluating utilization, classify the quota metadata itself.
Several attributes **short-circuit** the audit — misclassifying them
produces false positives.

| Attribute | Value | Effect on audit |
|---|---|---|
| `UsageMetric` | absent | **No CloudWatch metric exists.** Cannot auto-monitor utilization. This is a CONFIG_GAP (Step 2a) regardless of current utilization — you are flying blind. |
| `UsageMetric` | present | Proceed — utilization is auto-trackable via `AWS/Usage`. |
| `Adjustable` | `false` | **Hard limit.** Cannot request an increase via `request-service-quota-increase`. If utilization >= 50%, the only remediation is architectural (distribute load, use a different service, reduce usage). Flag as CONFIG_GAP (Step 2b). |
| `Adjustable` | `true` | Quota is increasable. Proceed to check increase request history. |
| `GlobalQuota` | `true` | **Account-wide quota** (e.g., IAM users, S3 buckets). Applies across all regions. An increase applies globally. |
| `GlobalQuota` | `false` | **Regional quota** (e.g., VPCs per region, EC2 vCPUs per region). An increase in us-east-1 does NOT apply to eu-west-1 — request per-region. |
| `Unit` | `Gigabytes`, `Mbps`, etc. | **Unit mismatch risk.** Never compare a utilization value in one unit against a quota in another. A quota of "100 Gigabytes" at "50 Count" usage is a data error. |
| Applied == Default | — | Quota has never been increased. Not inherently bad, but combined with utilization >= 50% and `Adjustable: true`, it signals that no proactive capacity management has occurred (Step 2d). |
| Applied > Default | — | An increase was APPROVED at some point — active capacity management. This is a positive signal. |

**Multi-service / account-wide sweep note (pagination):** when auditing
every quota for a service, `aws service-quotas list-service-quotas
--service-code <code>` returns at most 100 per page. Use
`--starting-token` from the prior `NextToken` to page through all
quotas. The same applies to
`list-requested-service-quota-change-history`. Always drain the
paginator to completion — the long tail often contains the quota that
matters.

**Malformed input handling.** If the quota snapshot is missing the
applied value, missing quota code, has a utilization value not
parseable as a number, or has a unit mismatch between utilization and
quota, output an ERROR block and refuse classification. Do NOT guess
the utilization percentage — a wrong percentage produces a wrong
verdict. Output:

```text
QUOTA: <quota-code or name>
VERDICT: ERROR
REASON: Quota snapshot is incomplete or malformed — cannot classify.
REMEDIATION: Retrieve the canonical data with `aws service-quotas
get-service-quota --service-code <code> --quota-code <code> --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious Service Quotas behaviors

These behaviors are easy to misjudge without operational Service Quotas
experience. Each changes a verdict if ignored:

- **`list-service-quotas` returns the APPLIED value, not the default.**
  The `Value` field in the response is the currently-effective quota,
  which may include an approved increase. To see the AWS default, call
  `get-aws-default-service-quota`. Many operators compare utilization
  against the default and produce false negatives — the applied quota
  may already be higher, giving more headroom than expected. Always
  compute utilization as `currentUsage / appliedValue`.

- **Not all quotas emit CloudWatch metrics.** Only quotas with a
  `UsageMetric` block have a corresponding `AWS/Usage` metric. Quotas
  without it (some IAM quotas, some Route 53 quotas, many
  Organizations quotas) have NO programmatic utilization signal — you
  must enumerate live resources and compare manually. This is a
  CONFIG_GAP (Step 2a) because there is no way to alarm before
  exhaustion.

- **The `AWS/Usage` CloudWatch namespace requires exact dimensions.**
  The `UsageMetric` block specifies `MetricNamespace` (always
  `AWS/Usage`), `MetricName` (usually `ResourceCount`), `Dimensions`
  (Service, Resource, Type, and sometimes a Class or other dimension),
  and `StatisticType` (`Sum` or `Maximum`). An alarm created with the
  wrong dimension values silently monitors nothing — `DescribeAlarms`
  returns the alarm as OK while the actual metric has no data points.
  Always copy dimensions verbatim from the `UsageMetric` block.

- **`GlobalQuota` determines region scope.** A `GlobalQuota: true`
  quota (e.g., S3 buckets per account) applies account-wide; an increase
  is global. A `GlobalQuota: false` quota (e.g., VPCs per region) is
  per-region — an increase in us-east-1 does NOT apply to eu-west-1.
  Cross-referencing a regional quota across regions requires querying
  each region independently.

- **Applied quota != requested quota.** A PENDING increase request has
  NOT changed the applied quota. The applied value remains the old
  number until the request transitions to APPROVED. Computing
  utilization against the requested (future) value masks the current
  risk. Always use the current `Value` from `get-service-quota`, not the
  `DesiredValue` from a pending request.

- **Request status lifecycle:** `PENDING` -> `CASE_OPENED` ->
  (`APPROVED` | `DENIED` | `NOT_APPROVED` | `CASE_CLOSED`). APPROVED
  increases the applied quota (may take minutes to propagate). DENIED
  and NOT_APPROVED do not change the quota. A CASE_OPENED status means
  AWS support is reviewing — this can take days for large increases.

- **`Adjustable: false` quotas are architectural constraints.** You
  cannot request an increase — the limit is fixed by AWS. The only
  remediation is to restructure: distribute across accounts (if
  GlobalQuota) or regions (if regional), reduce usage, or switch to a
  different service. Do NOT suggest `request-service-quota-increase` —
  it returns `ValidationException`.

- **`AWS/Usage` metrics publish with a 5-15 minute ingestion delay.**
  A CloudWatch alarm set at exactly 80% of the applied quota may fire
  AFTER actual usage has already crossed 100% — by the time the alarm
  triggers and pages on-call, new resource creation is already failing
  with `LimitExceededException`. Set alarm thresholds at 70-75% of
  the applied quota to create a real remediation window, not at the
  same 80% line used for the audit verdict.

- **`list-service-quotas` does NOT return current utilization.** The
  API returns only quota metadata and the applied value — there is no
  `CurrentUsage` field. You must separately call `aws cloudwatch
  get-metric-statistics` on the `AWS/Usage` metric and divide by the
  applied value to compute utilization. Automation that assumes
  `list-service-quotas` includes a usage number silently produces 0%
  for every quota — every verdict comes back OK.

- **The Service Quotas API itself is rate-limited.** The
  `list-service-quotas` and `list-requested-service-quota-change-history`
  endpoints share a per-account throttle (approximately 10-20 TPS).
  Bulk-auditing every quota for every service in a single loop will
  hit `ThrottlingException`. Implement exponential backoff and batch
  by service-code with a 0.5s delay between services.

- **Large increase requests auto-route to support cases.** Even for
  `Adjustable: true` quotas, requests beyond a service-specific
  multiplier (often 2x-10x the current value) are NOT auto-approved.
  AWS converts them to a support case (status transitions to
  CASE_OPENED) that can take 2-5 business days. This means a quota at
  85% with a freshly-submitted 2x request will NOT be relieved before
  exhaustion — plan capacity increases when utilization crosses 50%,
  not 80%.

- **Pending increase requests have their own quota.** There is a limit
  on the number of concurrent PENDING requests per account. If you hit
  this, you must withdraw old requests (`--request-id`) before
  submitting new ones.

- **`QuotaCode` (e.g., `L-1212C26A`) is the stable identifier.**
  `QuotaName` can change between API versions or be renamed by the
  service team. Always track and reference quotas by `QuotaCode` in
  automation, dashboards, and remediation scripts.

- **Service Quotas is replacing Trusted Advisor service-limit checks.**
  Trusted Advisor's service-limit checks cover only a subset of quotas
  and are deprecated for accounts with Business/Enterprise support. The
  modern approach is Service Quotas + CloudWatch alarms on `AWS/Usage`.
  Do NOT rely on Trusted Advisor as the sole utilization signal.

- **Utilization can spike instantly.** A quota at 30% utilization can
  jump to 100% in seconds if an Auto Scaling group adds instances, a
  Lambda function fan-outs, or a misconfigured deploy creates resources.
  This is why a CloudWatch alarm is recommended even for quotas with
  moderate utilization — the alarm is for the spike, not the trend.

### Step 1: Utilization threshold — APPROACHING_LIMIT

Compute utilization: `utilization_pct = (currentUsage / appliedValue) * 100`.

If `utilization_pct >= 80`, the verdict is **APPROACHING_LIMIT**. This is
the highest-priority finding regardless of alarm state, UsageMetric
presence, or increase request status. The operational risk of imminent
exhaustion dominates all monitoring and structural concerns.

**Boundary rule (critical):** the threshold is **inclusive** — `>= 80%`
means a quota at exactly 80.0% utilization IS APPROACHING_LIMIT, not OK.
For example, 40/50 VPCs (exactly 80%) is APPROACHING_LIMIT. Models and
operators frequently misread `>=` as `>` (strictly greater than);
this is the single most common classification error. When in doubt, a
quota at the exact boundary has no headroom for even one additional
resource — treat it as approaching.

- At exactly 80%: no headroom remains for growth. APPROACHING_LIMIT.
- At 80-89%: immediate action required. Request an increase if
  adjustable, or reduce usage.
- At 90-100%: critical — any new resource creation or API burst may
  fail with `LimitExceededException`.
- At > 100%: the quota has been exceeded. AWS may allow brief overages
  for some quotas but will block new operations imminently.

If a PENDING increase request exists, note it in FINDINGS but do NOT
downgrade the verdict — the applied quota has not changed yet.

If an APPROVED increase exists that has not yet propagated (applied
value still shows old number), note the expected new value in FINDINGS.

### Step 2: Structural config gap — CONFIG_GAP

If Step 1 did not match (utilization < 80%), check for structural issues
in this order:

**(a) No UsageMetric defined.** The quota cannot be auto-monitored via
CloudWatch. This is a CONFIG_GAP regardless of utilization — you have no
programmatic signal to detect exhaustion. The remediation is to track
manually (enumerate live resources and compare against the applied value
on a schedule) or use AWS Config rules.

**(b) `Adjustable: false` AND utilization >= 50%.** The quota is a hard
limit that cannot be increased, and utilization is high enough to be a
future risk. This is a CONFIG_GAP because there is no increase path —
the remediation is architectural.

**(c) Increase request DENIED or NOT_APPROVED AND utilization >= 50%.**
A previous increase attempt was rejected and utilization is moderate-to-high.
The team has not addressed the underlying capacity issue. This is a
CONFIG_GAP — either restructure usage or open a support case with
justification.

**(d) At AWS default, `Adjustable: true`, utilization >= 50%, AND the
increase request history is completely empty (zero entries of ANY
status — no PENDING, no APPROVED, no DENIED, no NOT_APPROVED).**
The quota has never been increased and no request has ever been
submitted, but utilization is high enough to warrant proactive action.

**Disambiguation (critical for D8):** Step 2d matches ONLY when the
request history list is truly empty. If there is ANY entry in the
history — even a PENDING request or a DENIED request — Step 2d does
NOT apply. A PENDING request means the team is actively seeking an
increase (skip to Step 3). A DENIED request is handled by Step 2c.
Only a completely empty history combined with utilization >= 50% at
the AWS default value triggers this CONFIG_GAP.

If none of (a)-(d) match, proceed to Step 3.

### Step 3: Alarm coverage — NO_ALARM

If the quota has a `UsageMetric` (auto-trackable), utilization is < 80%,
and Step 2 found no structural issues, check for a CloudWatch alarm.

If NO CloudWatch alarm is configured on the `AWS/Usage` metric for this
quota, the verdict is **NO_ALARM**. The quota is trackable but no
alerting exists — a sudden utilization spike would go undetected until
operations fail.

Verification: `aws cloudwatch describe-alarms --metric-name <MetricName>
--namespace AWS/Usage --dimensions <dims from UsageMetric>`. An alarm
is considered to exist ONLY when ALL of these conditions are met:
(1) `MetricName` matches the `UsageMetric.MetricName` value, (2) every
dimension from the `UsageMetric.Dimensions` list appears in the alarm
with the same name AND value, and (3) the alarm `Threshold` is at or
below the applied quota value — an alarm threshold of 999999 for a
quota of 50 is effectively disabled and should be treated as NO_ALARM.
An empty `describe-alarms` response or any dimension mismatch means
NO_ALARM.

Note: this step is only reached if Step 2 did not match. A quota at
default with 60% utilization is CONFIG_GAP (Step 2d), not NO_ALARM — the
structural issue (should have requested an increase) takes precedence
over the monitoring gap (no alarm).

### Step 4: OK

If none of Steps 1-3 matched, the verdict is **OK**:
- Utilization is below 80% (no approaching-limit risk).
- No structural issues (Step 2 clean).
- Either a CloudWatch alarm is configured, or the quota is low-risk
  (low utilization, not adjustable, no metric).

No remediation required. Recommend periodic re-audit as usage grows.

### Step 5: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all findings, where
APPROACHING_LIMIT > CONFIG_GAP > NO_ALARM > OK:

```text
verdict = max(utilization_severity, config_gap_severity, alarm_severity)
```

If no findings (all dimensions clean), the verdict is **OK**.

**Creative audit extensions:** The four verdicts cover the standard
audit dimensions. You MAY add supplementary FINDINGS lines for
quota-specific risks the standard steps do not capture (e.g., a
quota shared across instance types where one type is near exhaustion,
or a quota whose growth rate has accelerated in the past 30 days).
Keep the VERDICT to the four standard values — additional context
goes in FINDINGS, not in new verdict labels.

## Output format (per quota)

```text
QUOTA: <quota-code> (<quota-name>)
SERVICE: <service-code>
VERDICT: APPROACHING_LIMIT | NO_ALARM | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
UTILIZATION: <current>/<applied> (<pct>%) [default: <default>] [unit: <unit>]
FINDINGS:
  - [APPROACHING_LIMIT] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific CLI per finding, or "None required" if OK>
```

### Worked example — approaching limit with denied increase

```text
QUOTA: L-1212C26A (Running On-Demand Standard instances)
SERVICE: ec2
VERDICT: APPROACHING_LIMIT
REASON: Utilization is at 85% of the applied quota (850/1000 vCPUs).
A prior increase request to 2000 vCPUs was DENIED — the applied value
remains 1000 (Step 1).
UTILIZATION: 850/1000 (85%) [default: 1000] [unit: vCPUs]
FINDINGS:
  - [APPROACHING_LIMIT] 850/1000 vCPUs (85%) — any new instance launch may fail (Step 1)
  - [CONFIG_GAP] Increase request to 2000 DENIED on 2025-06-15 — no alternative capacity plan in place (Step 2c)
REMEDIATION:
  1. Open an AWS support case with workload justification for a vCPU increase.
  2. Switch non-critical workloads to Spot Instances (separate quota).
  3. Distribute across regions — the us-east-1 quota does not apply to us-west-2.
```

## Anti-Patterns — NEVER

- NEVER compute utilization against the AWS default value instead of the
  applied value. `list-service-quotas` returns the APPLIED value (which
  may include approved increases). Using the default inflates utilization
  and produces false-positive APPROACHING_LIMIT verdicts.

- NEVER assume all quotas have a CloudWatch metric. Quotas without a
  `UsageMetric` block CANNOT be auto-monitored. There is no
  `AWS/Usage` metric to alarm on — the only option is manual resource
  enumeration. Treating "no alarm" as NO_ALARM for a non-trackable quota
  is a category error; it is CONFIG_GAP (Step 2a).

- NEVER treat a PENDING increase request as if it has taken effect. The
  applied quota remains the old value until the request transitions to
  APPROVED. Computing utilization against the requested future value
  masks the current risk. Always use `get-service-quota` for the
  authoritative applied value.

- NEVER suggest `request-service-quota-increase` on an
  `Adjustable: false` quota. It returns `ValidationException`. These are
  hard limits — the only remediation is architectural (redistribute,
  reduce, or switch services).

- NEVER create a CloudWatch alarm on `AWS/Usage` without copying the
  exact dimensions from the `UsageMetric` block. Wrong dimension values
  produce an alarm that monitors nothing — `DescribeAlarms` shows OK
  while the actual metric has no data. Copy `Service`, `Resource`,
  `Type`, and any `Class` dimension verbatim.

- NEVER assume a regional quota increase applies across regions. A VPC
  quota increase in us-east-1 does NOT apply to eu-west-1. Each region
  has independent quotas for non-global quotas. Request increases
  per-region.

- NEVER use `QuotaName` as a stable identifier in automation.
  `QuotaName` can be renamed by the service team; `QuotaCode` (e.g.,
  `L-1212C26A`) is the stable identifier. Scripts that key on
  `QuotaName` break silently when AWS renames a quota.

- NEVER compare utilization across different `Unit` values. A quota of
  "100 Gigabytes" and usage of "50 Count" is a data error, not 50%
  utilization. Verify the unit before computing the ratio.

- NEVER classify a quota at exactly 80.0% utilization as OK, NO_ALARM, or
  CONFIG_GAP. The `>= 80%` threshold is **inclusive** — 40/50 (exactly
  80%) IS APPROACHING_LIMIT. The most common classification error is
  treating the boundary as exclusive (`> 80%`). If utilization computes
  to exactly 80.0%, the verdict MUST be APPROACHING_LIMIT, not OK.

- NEVER ignore the 50% threshold for CONFIG_GAP. A quota at 55%
  utilization that is adjustable, at default, and has no increase request
  is a CONFIG_GAP — the team should have acted proactively. Waiting until
  80% to flag it (where it becomes APPROACHING_LIMIT) leaves no
  remediation window.

- NEVER recommend deleting resources as the only remediation for an
  APPROACHING_LIMIT quota. First check if the quota is adjustable and
  submit an increase request. Resource cleanup is a complement, not a
  substitute — the underlying capacity ceiling remains.

- NEVER rely on Trusted Advisor service-limit checks as the sole
  utilization signal. Trusted Advisor covers only a subset of quotas and
  is deprecated for Business/Enterprise support tiers. The modern
  approach is Service Quotas + CloudWatch alarms on `AWS/Usage`.

- NEVER drain only the first page of `list-service-quotas` (100 per
  page). The quota you need may be on page 2. Always iterate
  `--starting-token` to completion.

- NEVER exceed the concurrent pending-request quota. Each account has
  a fixed limit on simultaneous PENDING increase requests per region
  (typically 4 per region per service). When this limit is full,
  `request-service-quota-increase` fails with `QuotaExceededException`
  even though the target quota has ample headroom. Before submitting a
  new request, check for stale PENDING entries via
  `list-requested-service-quota-change-history --status PENDING` and
  contact AWS support to withdraw expired ones — there is no public API
  to programmatically close a pending request.

- NEVER classify a quota with `UsageMetric` present, an alarm configured,
  low utilization, and no structural issues as anything other than OK.
  Over-classifying clean quotas erodes trust in the audit.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`request-service-quota-increase`, closing a request), the auditor
  MUST emit:
  `CONFIRM: About to request a quota increase for <quota-code> on
  <service-code> from <current> to <desired>. This opens a request that
  may require AWS support review. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.
- Before requesting an increase, verify the quota is `Adjustable: true`.
  A request on a non-adjustable quota returns `ValidationException`.
- Before requesting an increase, verify `--desired-value` is strictly
  greater than the current applied value (`get-service-quota`). Equal or
  lower values are rejected.
- Check for existing PENDING requests on the same quota to avoid
  duplicates: `aws service-quotas
  list-requested-service-quota-change-history-by-quota --service-code
  <code> --quota-code <code --status PENDING`.
- Before creating a CloudWatch alarm, verify the `UsageMetric` dimensions
  by querying the metric first:
  `aws cloudwatch get-metric-statistics --namespace AWS/Usage --metric-name
  <MetricName> --dimensions <dims> --start-time <iso> --end-time <iso>
  --period 300 --statistics <StatisticType>`. No data points = wrong
  dimensions.
- For regional quotas, confirm the correct `--region` is set on every
  CLI call. A quota increase in the wrong region is a waste of a request
  slot and cannot be transferred.

## Remediation guidance

### For APPROACHING_LIMIT

1. If `Adjustable: true`, request an increase immediately:
   `aws service-quotas request-service-quota-increase --service-code
   <code> --quota-code <code> --desired-value <value>`
   Use a desired value with at least 50% headroom above current usage
   (e.g., if at 850/1000, request 1500-2000).
2. If a PENDING request already exists, note the expected resolution
   time. Do NOT submit a duplicate — it wastes a request slot.
3. If `Adjustable: false`, reduce usage immediately: terminate
   non-critical resources, switch to Spot/alternative instance types,
   redistribute across accounts or regions.
4. Create or verify a CloudWatch alarm at 80% and 90% thresholds.

### For CONFIG_GAP

- **No UsageMetric (Step 2a):** set up a scheduled audit (EventBridge +
  Lambda) that enumerates live resources and compares against the
  applied quota. There is no CloudWatch metric to alarm on.
- **Adjustable: false (Step 2b):** document the architectural constraint
  and plan capacity around it. Consider multi-account or multi-region
  distribution.
- **Denied increase (Step 2c):** open an AWS support case with
  workload justification. Reduce usage in the interim.
- **At default, no request (Step 2d):** submit a proactive increase
  request. Even if current usage is moderate, growth will eventually
  exhaust the default.

### For NO_ALARM

Create a CloudWatch alarm on the `AWS/Usage` metric:
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "quota-<quota-code>-80pct" \
  --namespace AWS/Usage \
  --metric-name <MetricName from UsageMetric> \
  --dimensions <dims from UsageMetric> \
  --statistic <StatisticType from UsageMetric> \
  --period 300 \
  --threshold <applied * 0.8> \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions <sns-topic-arn>
```

### For OK

No remediation required. Recommend:
- Periodic re-audit as usage grows (monthly or per-deploy).
- Verify the CloudWatch alarm threshold is still appropriate if the
  applied quota changes.
- For regional quotas, audit each region where the workload operates.

## Reference: AWS/Usage metric structure

The `UsageMetric` block maps to a CloudWatch metric in `AWS/Usage`:

| Field | Typical value | Notes |
|---|---|---|
| `MetricNamespace` | `AWS/Usage` | Always this value. |
| `MetricName` | `ResourceCount` | Sometimes `ResourceLimit` or service-specific. |
| `Dimensions` | `Service`, `Resource`, `Type`, optionally `Class` | Copy verbatim — wrong values produce a silent alarm. |
| `StatisticType` | `Sum` or `Maximum` | `Sum` for cumulative resources; `Maximum` for peak-based quotas. |

**Organizations note:** the management account can view member-account
quotas via `list-service-quotas --account-id <id>` but CANNOT submit
increase requests on their behalf — each member account must submit
its own request.

## Recent AWS features (2024-2026)

- **Organization-level quota management (2024-2025):** Service Quotas now supports viewing and requesting quota increases across all accounts in an Organization from the management account. Auditors should verify that the management account has visibility into member-account quota utilization and that organization-level quota requests are tracked.
- **Additional trackable quotas (2024):** More AWS services now expose `UsageMetric` data for Service Quotas tracking. Auditors should re-check quotas that were previously non-trackable — many have been updated with CloudWatch metrics.
- **Quota increase request automation:** Enhanced API support for programmatic quota increase requests. No new audit-surface fields, but auditors should verify that automated quota requests have approval workflows (not auto-approved without review).

## Domain

AWS CloudOps / Service Quotas Capacity Management & Monitoring.

## AWS documentation

- **Service documentation** — https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html
- **Security** — https://docs.aws.amazon.com/servicequotas/latest/userguide/security.html
- **API reference** — https://docs.aws.amazon.com/servicequotas/2019-06-24/apireference/
- **CLI reference** — https://docs.aws.amazon.com/cli/latest/reference/service-quotas/
