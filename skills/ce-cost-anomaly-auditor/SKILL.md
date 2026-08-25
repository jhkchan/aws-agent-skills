---
name: ce-cost-anomaly-auditor
description: Audits AWS Cost Explorer (CE) anomaly-detection subscriptions, Savings Plan/RI coverage gaps, idle-resource detection readiness, and report- subscription cadence. Emits a deterministic FinOps verdict (NO_ANOMALY_SUB | LOW_RI_COVERAGE | CONFIG_GAP | OK) per account with enumerated findings and specific CLI remediation. Use when reviewing Cost Anomaly Detection (CAD) wiring, checking RI/SP commitment coverage on steady-state compute, validating anomaly subscription threshold and frequency calibration, auditing idle-resource detection readiness (CUR resource-ID gating), or hardening spend-visibility posture before a billing review.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline CE-document classification. Live-account audits use aws ce list-cost-anomaly-monitors, aws ce get-anomaly-subscriptions, aws ce get-reservation-coverage, aws ce get-savings-plans-coverage, and aws ce get-anomalies (AWS CLI v2, SSO or key-based credentials). All CE/CAD API endpoints are region-pinned to us-east-1.
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: FinOps
  verdict_shape: NO_ANOMALY_SUB | LOW_RI_COVERAGE | CONFIG_GAP | OK
  when_to_use: Reviewing Cost Anomaly Detection wiring before a billing review, checking that CAD subscriptions deliver on an IMMEDIATE cadence, auditing RI/SP coverage on a steady-state compute fleet, validating that the anomaly threshold is calibrated to spend (not the $100 default), or confirming that idle-resource detection has the CUR resource-ID foundation it needs.
  activation_triggers: audit Cost Anomaly Detection, check my anomaly subscription, is CAD wired correctly, RI coverage gap, Savings Plan coverage, anomaly threshold too high, idle resource detection, IMMEDIATE vs DAILY monitor, cost spike alerting, commitment gap, on-demand leak
  invocation_schema: 'Input: either (a) a CE/CAD inventory (anomaly monitors, anomaly subscriptions, RI/SP coverage percentages, CUR config, account spend profile), OR (b) an account-id for live-account audit. Output: deterministic ACCOUNT/VERDICT/REASON/FINDINGS/REMEDIATION block per account, where VERDICT is one of NO_ANOMALY_SUB, LOW_RI_COVERAGE, CONFIG_GAP, OK, or ERROR (CE not enabled).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Cost Explorer, Cost Anomaly Detection, CAD, anomaly subscription, RI coverage, Savings Plan coverage, idle resource, report subscription, IMMEDIATE monitor, DAILY monitor, threshold calibration, FinOps, commitment gap, on-demand leak, spend visibility, ce list-cost-anomaly-monitors, ce get-anomaly-subscriptions, free tier anomaly
  tags: cost-explorer, finops, anomaly-detection, ri-coverage, savings-plans, idle-resources, audit
---

# CE Cost Anomaly Auditor

## Mindset

**One-line takeaway:** detection without a subscription is silent, and a
subscription with the wrong frequency or threshold is decorative. Three
CE behaviours are easy to misjudge: **subscription Frequency is NOT
detection cadence** (an IMMEDIATE monitor paired with a WEEKLY
subscription detects in minutes but reports in days), **coverage % is
measured over eligible compute spend not total spend** (Lambda has no RIs;
a 90% aggregate can hide a 0% long tail), and **idle detection via CE is
gated on CUR resource IDs** (without CUR v2 the API stops at SERVICE
level and resource-level $0 detection is impossible).

Cost Explorer (CE) is the visibility layer; Cost Anomaly Detection (CAD)
is its ML spike detector. Three failure modes dominate:

- **No subscription** — zero monitors, or monitors with zero
  subscriptions. CAD either never runs or runs but never notifies. The
  account is blind to spikes from a runaway resource, compromised
  credential, or data-transfer surge.
- **Miscalibrated subscription** — the subscription exists but its
  `Threshold` is the $100 default on a free-tier account, or its
  `Frequency` is WEEKLY on an IMMEDIATE monitor. Alerts either never fire
  or arrive too late to act.
- **Commitment gap** — steady-state compute runs with low RI/SP coverage.
  On-demand spend leaks that a commitment would offset. CE coverage
  metrics surface this; CAD does not.

**Scope boundary:** `billing-account-auditor` checks whether CAD is
ENABLED (zero monitors = NO_ANOMALY_DETECTION). THIS skill goes deeper —
it audits CAD configuration quality, RI/SP commitment coverage, and
idle-resource detection readiness.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| Zero CAD monitors, OR monitors but zero subscriptions | **NO_ANOMALY_SUB** | 1 |
| Steady-state eligible compute spend (>$1k/mo) with RI coverage < 40% AND SP coverage < 40% | **LOW_RI_COVERAGE** | 2 |
| IMMEDIATE monitor paired with WEEKLY/DAILY subscription | **CONFIG_GAP** | 3a |
| Subscription Threshold = $100 default on account with spend < $2k/mo (or free-tier) | **CONFIG_GAP** | 3b |
| Only DAILY monitors (no IMMEDIATE) on account > $5k/mo | **CONFIG_GAP** | 3c |
| No CUR v2 with resource IDs — idle-resource detection impossible via CE | **CONFIG_GAP** | 3d |
| Single DIMENSIONAL monitor with no org/linked-account breadth | **CONFIG_GAP** | 3e |
| All dimensions healthy | **OK** | 4 |

Steps apply in order; the first triggering step sets the verdict, later
additive findings are still enumerated. Precedence:
NO_ANOMALY_SUB > LOW_RI_COVERAGE > CONFIG_GAP > OK.

**Severity/risk per verdict:** NO_ANOMALY_SUB = **HIGH** (total cost-spike
blind spot), LOW_RI_COVERAGE = **MEDIUM** (on-demand leak on steady-state
compute), CONFIG_GAP = **MEDIUM** (FREQUENCY_MISMATCH, THRESHOLD_MISALIGNED,
NO_IMMEDIATE_MONITOR) or **LOW** (NO_RESOURCE_LEVEL_COSTS, NARROW_SCOPE),
OK = **LOW**.

## Pre-flight: Cost Explorer enablement gate

Confirm CE is enabled (one-way root/admin console operation). If CE is
not enabled, CAD, RI/SP coverage APIs, and cost-and-usage queries all
fail. All CE/CAD API endpoints are region-pinned to `us-east-1` — always
pass `--region us-east-1`. A call without the flag may default to the
workload region and return empty results (false NO_ANOMALY_SUB).

**Pagination:** `ce list-cost-anomaly-monitors` and
`ce get-anomaly-subscriptions` paginate via `--next-page-token`; drain to
completion. Coverage APIs take a `--time-period` — use a trailing 7-day
window minimum (single-day coverage is noisy from hourly fluctuation).

**Live pre-flight (skip if offline):** confirm caller has `ce:List*`,
`ce:Get*` read perms; a read-only auditor without `ce:*` read silently
skips every dimension. For orgs, run coverage queries grouped by
`LINKED_ACCOUNT` to expose per-member long tail.

**If CE is not enabled** → VERDICT: ERROR, reason "Cost Explorer not
enabled — CE/CAD APIs unavailable. Enable CE in the console (root/admin,
one-way) before re-auditing."

**If inventory is malformed** (invalid JSON, missing `MonitorArn`) →
VERDICT: ERROR, reason "CE/CAD inventory not valid — cannot classify."
Re-fetch with `aws ce list-cost-anomaly-monitors --region us-east-1`.

**Expected input shape (CE/CAD inventory for offline audit):**

```yaml
Account id: <12-digit account>
Cost Explorer: enabled | not enabled
Account spend profile: $<amount>/month (<workload type>)
Cost Anomaly Detection monitors:
  - MonitorArn: arn:aws:ce::<account>:anomalyMonitor/<name>
    MonitorName: <name>
    MonitorType: IMMEDIATE | DAILY
Cost Anomaly Detection subscriptions:
  - SubscriptionArn: arn:aws:ce::<account>:anomalySubscription/<name>
    Threshold: <dollars>
    Frequency: IMMEDIATE | DAILY | WEEKLY
    MonitorArn: <linked monitor arn>
    Subscribers: [{Address: <email>, Type: EMAIL}]
RI coverage (7-day avg): <%> (over $<eligible spend>)
SP coverage (7-day avg): <%> (over $<eligible spend>)
CUR v2 with IncludeResourceIDs: enabled | NOT configured
Free-tier: yes | no
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious CE/CAD behaviours

These change a verdict if ignored:

- **Subscription Frequency is NOT detection cadence.** Monitor
  `MonitorType` (DAILY vs IMMEDIATE) controls WHEN anomalies are
  detected; subscription `Frequency` (IMMEDIATE/DAILY/WEEKLY) controls
  WHEN notifications are SENT. An IMMEDIATE monitor detects in ~5 min on
  new line items; a WEEKLY subscription delivers a digest 7 days later.
  This is the most misjudged CAD pairing — flag the mismatch as
  CONFIG_GAP; the monitor is working, the subscription is the bottleneck.

- **IMMEDIATE monitors evaluate on new line items, not the daily total.**
  IMMEDIATE fires on the FIRST anomalous charge in the near-real-time
  billing feed. DAILY averages the day; a single-resource spike diluted
  across 200 instances may not trip the daily threshold. For any account
  > $5k/mo, an IMMEDIATE monitor is mandatory — DAILY-only is CONFIG_GAP.

- **CAD ML needs ~10 days of history.** A new monitor on a new account
  over-alerts for ~10 days (no baseline). This is NORMAL, not a config
  gap. Conversely, an account > 10 days old with zero anomalies EVER is
  suspicious (threshold too high or monitor misconfigured).

- **Anomaly Feedback trains the model.** Each anomaly accepts feedback
  (`YES`/`NO`/`PLANNED`) — the ONLY tuning mechanism beyond the
  threshold. An account where feedback is never given has a stale,
  over-alerting model. Flag absent feedback as informational, not a
  verdict driver.

- **Threshold default is $100 and is almost always wrong.** The default
  `Threshold` is $100 above expected spend. On a free-tier/low-spend
  account (< $2k/mo), a $90 runaway is invisible until it crosses $100.
  On a high-spend account (>$50k/mo), $100 generates noise. Calibrate:
  threshold ≈ 5-10% of monthly spend, floored at $10-20. The $100
  default on a free-tier account defeats CAD's purpose.

- **RI coverage and SP coverage are SEPARATE; neither equals utilization.**
  Coverage = how much USAGE was commitment-offset (the on-demand leak to
  close). Utilization = how much COMMITMENT was consumed (over-buy
  waste). This skill audits COVERAGE. A workload can have 95% utilization
  (used your RIs fully) and 20% coverage (bought too few). Always query
  BOTH `get-reservation-coverage` AND `get-savings-plans-coverage`.

- **Coverage % is over ELIGIBLE compute spend, not total spend.** EC2,
  RDS, Redshift, DynamoDB (provisioned), ElastiCache support RIs. Compute
  SPs apply to EC2/Fargate/Lambda. Lambda has NO RIs (SP only). S3 and
  most SaaS have NEITHER. "60% RI coverage" on an account that is 80% S3
  is over the 20% compute slice — always interpret against eligible base.

- **Aggregate coverage masks the long tail.** Org-level 85% RI coverage
  can hide a member/region at 0%. Break down by `LINKED_ACCOUNT` and
  `REGION` for orgs before declaring coverage OK. The 0% member is the
  FinOps leak.

- **Idle detection via CE is GATED on CUR v2 with resource IDs.** CE
  `get-cost-and-usage` reaches RESOURCE granularity ONLY if CUR v2 with
  `IncludeResourceIDs=true` is configured and Athena-integrated. Without
  CUR, CE stops at SERVICE granularity — resource-level $0 detection is
  impossible. This is the boundary with `cur-cost-usage-report-auditor`.

- **$0 on-demand is NOT idle.** A running RI/SP-covered instance shows $0
  on-demand — it is commitment-covered, not idle. Free-tier credits do
  the same. Correlate CE $0 with service API state (`ec2
  describe-instances` State) and CloudWatch (CPUUtilization < 1% for 14
  days) before declaring idle. CE $0 is a SIGNAL, not a verdict.

- **CE data lag is 8-24h.** A trailing 14-day idle window MUST query days
  4-18 (skip the recent 72h of incomplete data) to avoid false-negatives.

- **Free-tier exhaustion is an anomaly CAD SHOULD catch — if calibrated.**
  When free-tier credits exhaust, on-demand charges appear suddenly. CAD
  flags this correctly, but a $100 threshold on a free-tier account means
  the exhaustion signal must exceed $100 — the leak is large by then.

### Step 1: CAD subscription gate (NO_ANOMALY_SUB — highest priority)

- **Zero monitors** → **NO_ANOMALY_SUB** (HIGH). No ML detection. Any cost
  spike goes undetected. CAD is free — there is no cost reason to skip it.
- **Monitors exist but zero subscriptions** → **NO_ANOMALY_SUB** (HIGH).
  CAD detects anomalies but nobody receives notifications. The CAD
  equivalent of a decorative budget — detection without delivery.

NO_ANOMALY_SUB short-circuits the verdict but does NOT skip enumeration
of additive findings (low RI coverage is still reported in FINDINGS).

### Step 2: RI/SP coverage (LOW_RI_COVERAGE)

Query `ce get-reservation-coverage` and `ce get-savings-plans-coverage`
over a trailing 7-day window against ELIGIBLE compute spend:

- **Eligible monthly compute spend > $1,000 AND RI coverage < 40% AND SP
  coverage < 40%** → **LOW_RI_COVERAGE** (MEDIUM). The account runs
  enough steady-state compute that a commitment would offset material
  on-demand spend, but coverage is below the functional threshold. Mature
  FinOps targets 70-90% on steady-state fleets.
- **Eligible spend < $1,000/mo** → coverage is informational, NOT a
  verdict driver. A small or spiky workload may legitimately have low
  coverage. Do NOT emit LOW_RI_COVERAGE.
- **RI >= 40% OR SP >= 40%** → OK for this dimension. Note the gap to
  70-90% target as informational.

Break down by `LINKED_ACCOUNT`/`REGION` for orgs — if ANY member/region
is 0% on an account at 40%+, emit an additive [MEDIUM] finding (long-tail
leak) even if the aggregate passes.

### Step 3: Configuration quality (CONFIG_GAP)

Five sub-checks; the FIRST triggering sub-check sets CONFIG_GAP if no
higher verdict applies:

**3a — Frequency mismatch.** An IMMEDIATE monitor linked to a WEEKLY
subscription detects in minutes, reports in 7 days. CONFIG_GAP
(FREQUENCY_MISMATCH, MEDIUM).

**3b — Threshold miscalibration.** Threshold = $100 default on account
with spend < $2k/mo (or free-tier). Sub-threshold spikes (the highest-
risk window) are invisible. CONFIG_GAP (THRESHOLD_MISALIGNED, MEDIUM).
Recommended: 5-10% of monthly spend, floor $10-20.

**3c — DAILY-only monitors.** Every monitor is DAILY, no IMMEDIATE, on an
account > $5k/mo. Sub-day runaway spikes are invisible until the daily
average trips. CONFIG_GAP (NO_IMMEDIATE_MONITOR, MEDIUM).

**3d — Idle-detection gating.** No CUR v2 with `IncludeResourceIDs` —
resource-level idle detection impossible via CE. CONFIG_GAP
(NO_RESOURCE_LEVEL_COSTS, LOW). Pair with `cur-cost-usage-report-auditor`.

**3e — Narrow monitor scope.** Only one DIMENSIONAL monitor on a single
SERVICE (no org breadth, no LINKED_ACCOUNT coverage for orgs). Spikes in
uncovered services/members are invisible. CONFIG_GAP (NARROW_SCOPE, LOW).

### Step 4: Aggregation — worst finding wins

```text
verdict = max(cad_subscription_verdict, coverage_verdict, config_gap_verdict)
```
Precedence: NO_ANOMALY_SUB > LOW_RI_COVERAGE > CONFIG_GAP > OK. ERROR is
reserved for CE-not-enabled or malformed input. If no findings, verdict
is **OK**.

## Output format (per account)

```text
ACCOUNT: <account-id>
VERDICT: NO_ANOMALY_SUB | LOW_RI_COVERAGE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the triggering step and worst finding>
FINDINGS:
  - [MEDIUM] <finding description (Step N)>
  - [LOW] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — IMMEDIATE monitor, WEEKLY subscription, low RI coverage

```text
ACCOUNT: 111111111111
VERDICT: LOW_RI_COVERAGE
REASON: Account runs $18k/mo eligible EC2 spend with 22% RI / 12% SP coverage
(Step 2). Additionally the IMMEDIATE monitor is paired with a WEEKLY
subscription (Step 3a) and the $100 threshold is miscalibrated for $20k/mo
(Step 3b).
FINDINGS:
  - [MEDIUM] LOW_RI_COVERAGE: 22% RI / 12% SP on $18k/mo eligible compute (Step 2)
  - [MEDIUM] FREQUENCY_MISMATCH: IMMEDIATE monitor linked to WEEKLY subscription (Step 3a)
  - [MEDIUM] THRESHOLD_MISALIGNED: $100 threshold on $20k/mo spend (Step 3b)
  - [OK] CUR v2 with IncludeResourceIDs configured — idle detection ready
REMEDIATION:
  1. MEDIUM — Run commitment analysis (ce get-reservation-utilization +
     get-savings-plans-utilization). Target 70-90% on the steady-state base.
  2. MEDIUM — aws ce update-anomaly-subscription --subscription-arn <arn>
     --frequency IMMEDIATE --region us-east-1.
  3. MEDIUM — aws ce update-anomaly-subscription --subscription-arn <arn>
     --threshold 1000 --region us-east-1.
```

## Edge-case handling

- **Partially malformed monitor.** Classify valid monitors; emit ERROR
  note for the malformed one: "Monitor <arn> malformed — skipped." Do NOT
  fail the entire account on one bad monitor.
- **RI budget mistaken for coverage.** A Budgets RI_COVERAGE budget is a
  threshold on a metric, NOT actual coverage. Query
  `ce get-reservation-coverage` for ground truth.
- **New account (< 10 days).** CAD ML has no baseline; over-alerting is
  NORMAL — do NOT flag. Coverage queries may return empty — informational.
- **Lambda-only compute (no EC2).** Lambda has NO RIs. RI coverage is 0%
  by design. Evaluate SP coverage independently; do NOT emit
  LOW_RI_COVERAGE on RI alone if SP is adequate.
- **CUR present but not Athena-integrated.** Resource-level CE queries
  need CUR v2 + Athena. Treat as CONFIG_GAP (Step 3d) — remediation
  includes Athena setup.
- **Org member relying on payer CAD.** Acceptable IF payer monitors cover
  the member (DIMENSIONAL on LINKED_ACCOUNT). A payer monitor filtering
  to only the payer account is a blind spot for members.

## Anti-Patterns — NEVER

- NEVER classify zero CAD monitors as CONFIG_GAP. Zero monitors is
  NO_ANOMALY_SUB — a total cost-spike blind spot. Softening to CONFIG_GAP
  underweights the risk.
- NEVER treat subscription Frequency as detection cadence. An IMMEDIATE
  monitor detects in minutes; the subscription controls notification
  delivery. IMMEDIATE monitor + WEEKLY subscription is CONFIG_GAP because
  the OPERATOR learns of the spike a week late.
- NEVER leave the $100 threshold default on a free-tier/low-spend account.
  The default defeats CAD: sub-$100 runaway resources (the highest-risk
  window) are invisible. Calibrate to 5-10% of monthly spend, floor $10-20.
- NEVER conflate RI coverage with RI utilization. Coverage = USAGE offset
  (leak to close); utilization = COMMITMENT consumed (over-buy waste).
  This skill audits COVERAGE. Flagging low utilization here is a category
  error.
- NEVER interpret $0 on-demand as idle. RI/SP coverage and free-tier
  credits zero out on-demand on RUNNING instances. CE $0 is a SIGNAL
  requiring correlation with service API state and CloudWatch before an
  idle verdict.
- NEVER attempt resource-level idle detection without CUR v2 + resource
  IDs. CE stops at SERVICE granularity without CUR. Querying RESOURCE
  granularity without CUR returns empty — a false "all idle" or "no data."
- NEVER query a 14-day idle window ending today. CE data lags 8-24h
  (longer at month-end). Query days 4-18 (skip the recent 72h).
- NEVER omit `--region us-east-1` on CE/CAD calls. The endpoint is
  us-east-1 regardless of workload region; a missing flag returns empty
  results (false NO_ANOMALY_SUB).
- NEVER evaluate coverage at org aggregate only. An 85% org-level can hide
  a member/region at 0%. Break down by LINKED_ACCOUNT and REGION — the 0%
  long tail is the leak.
- NEVER flag a new account's CAD over-alerting as a finding. CAD ML needs
  ~10 days to build a baseline; over-alerting is NORMAL. Flagging it
  erodes trust in real findings.
- NEVER recommend RIs/SPs on a spiky/scale-to-zero workload without a
  commitment analysis. LOW_RI_COVERAGE means "run a commitment analysis,"
  not "buy RIs now."

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before Create/Update/Delete on CAD
  monitors/subscriptions or RI/SP purchases, emit: `CONFIRM: About to
  <action> in account <account>. Proceed? (yes/no)`
- Confirm caller has `ce:Create*`, `ce:Update*` for CAD remediation;
  RI/SP purchases need `savingsplans:CreateSavingsPlan` or RI marketplace
  perms. Surface gaps BEFORE the operator approves.
- Before updating a subscription, capture current config: `aws ce
  get-anomaly-subscriptions --monitor-arn <arn> --region us-east-1 >
  /tmp/<monitor>-sub-backup-$(date +%s).json`.
- Threshold changes take effect immediately but the ML model does NOT
  re-evaluate historical anomalies — only future charges. Note this.
- Before recommending RIs/SPs, ALWAYS pair with utilization analysis.
  This skill flags the COVERAGE gap; the commitment decision needs
  utilization context.
- Prefer additive changes (add an IMMEDIATE monitor, add a calibrated
  subscription) over destructive ones.

## Remediation guidance

**Ordering principle:** prefer additive changes. Add a calibrated
subscription before deleting the miscalibrated one; add an IMMEDIATE
monitor before retiring the DAILY one.

### For NO_ANOMALY_SUB — no monitors or no subscriptions

1. Create an org-wide IMMEDIATE monitor + subscription:
   ```bash
   aws ce create-anomaly-monitor --region us-east-1 --profile <p> \
     --monitor '{"MonitorName":"org-immediate","MonitorType":"IMMEDIATE","MonitorSpecification":{}}'
   aws ce create-anomaly-subscription --region us-east-1 --profile <p> \
     --subscription '{"SubscriptionName":"finops-immediate","Threshold":50,"Frequency":"IMMEDIATE","MonitorArn":"<arn>","Subscribers":[{"Address":"finops@corp.com","Type":"EMAIL"}]}'
   ```
   Set Threshold to ~5-10% of monthly spend (floor $10-20 for low-spend).

### For LOW_RI_COVERAGE — commitment gap

1. Run commitment analysis:
   ```bash
   aws ce get-reservation-utilization --region us-east-1 --profile <p> \
     --time-period Start=$(date -u -d '-7 days' +%F),End=$(date -u +%F) --granularity DAILY
   aws ce get-savings-plans-utilization --region us-east-1 --profile <p> \
     --time-period Start=$(date -u -d '-7 days' +%F),End=$(date -u +%F) --granularity DAILY
   ```
2. Target 70-90% on the steady-state EC2/Fargate base. Prefer Compute SPs
   for flexibility over Standard RIs for workloads with instance churn.
3. Do NOT purchase commitments on spiky/scale-to-zero workloads.

### For CONFIG_GAP — frequency mismatch (3a)

```bash
aws ce update-anomaly-subscription --region us-east-1 --profile <p> \
  --subscription-arn <arn> --frequency IMMEDIATE
```

### For CONFIG_GAP — threshold miscalibration (3b)

```bash
aws ce update-anomaly-subscription --region us-east-1 --profile <p> \
  --subscription-arn <arn> --threshold <5-10%-of-monthly-spend>
```

### For CONFIG_GAP — DAILY-only monitors (3c)

```bash
aws ce create-anomaly-monitor --region us-east-1 --profile <p> \
  --monitor '{"MonitorName":"immediate-spike","MonitorType":"IMMEDIATE","MonitorSpecification":{}}'
```

### For CONFIG_GAP — no CUR resource IDs (3d)

Route to `cur-cost-usage-report-auditor` to configure CUR v2 with
`IncludeResourceIDs=true` + Athena. CE resource-level queries become
available up to 24h after CUR setup.

### For CONFIG_GAP — narrow scope (3e)

Add a DIMENSIONAL monitor on LINKED_ACCOUNT for org member coverage, or
broaden the SERVICE list.

### For OK

1. No remediation required.
2. Recommend periodic anomaly feedback review (train the ML model).
3. Recommend quarterly coverage re-assessment as workload mix changes.

## Deep reference: threshold rationale and sources

Each threshold in this skill is grounded in a specific AWS behaviour or
FinOps benchmark, not arbitrary:

- **40% coverage floor (Step 2).** Below 40%, the commitment strategy is
  functionally absent — a steady-state fleet paying > 60% on-demand is
  leaking material spend. 40% is the floor where RI/SP commitment ROI
  turns positive (the break-even between commitment overhead and on-demand
  discount). Mature FinOps programs target 70-90% on steady-state fleets
  (per AWS Cost Optimization guidance). Below $1k/mo eligible spend,
  commitment administrative overhead exceeds the discount, so the gate is
  skipped.

- **$100 threshold default (Step 3b).** This is the literal AWS default
  for `ce create-anomaly-subscription --threshold` (confirmed via the CE
  API). On a free-tier account, a $90/day runaway resource is invisible
  for days; on a $50k/mo account, $100 fires on normal daily fluctuation.
  The 5-10% of monthly spend calibration (floor $10-20) matches the
  threshold to the account's Cost Explorer noise floor.

- **$5k/mo IMMEDIATE monitor gate (Step 3c).** Below $5k/mo, a full day
  of runaway charges ($50-200) is recoverable and within a DAILY monitor's
  24h detection window. Above $5k/mo, a single day of EC2 runaway can
  exceed $500-1000 — only an IMMEDIATE monitor (5-min evaluation on new
  line items in the near-real-time billing feed) catches it before
  material loss. The IMMEDIATE monitor evaluates on each new line item,
  not the daily total (per the CE anomaly-detection evaluation model).

- **7-day coverage lookback (Pre-flight).** Single-day coverage is noisy
  from hourly workload fluctuation and Spot instance churn. 7 days smooths
  the signal while staying recent enough to reflect current commitment
  posture. CE `get-reservation-coverage` accepts DAILY granularity; a
  7-day `--time-period` returns 7 data points to average.

- **CAD ML 10-day baseline (Step 0).** Per AWS Cost Anomaly Detection
  documentation, the ML model trains on ~10 days of historical usage data
  to build a spend baseline. Before that window, it has no comparison
  point and over-alerts. This is documented behaviour, not a
  misconfiguration.

## Recent AWS features (2024-2026)

- **Improved anomaly detection ML model (2024-2025):** Cost Anomaly Detection upgraded its detection model with more granular dimension support and reduced false-positive rates. Auditors should re-evaluate subscription thresholds after model upgrades — the old thresholds may produce different alert patterns with the new model.
- **Daily vs hourly anomaly evaluation:** CAD now supports hourly evaluation cadence for more responsive detection. Auditors should verify that critical accounts use hourly cadence rather than daily, as the skill recommends.

## Domain

AWS CloudOps / FinOps Cost Visibility & Commitment Strategy.

## AWS documentation

- **AWS Cost Anomaly Detection User Guide** — https://docs.aws.amazon.com/cost-management/latest/userguide/anomaly-detection.html
- **AWS Cost Management Security** — https://docs.aws.amazon.com/cost-management/latest/userguide/security.html
- **Cost Explorer API Reference** — https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_cost-explorer.html
- **AWS CLI Command Reference (ce)** — https://docs.aws.amazon.com/cli/latest/reference/ce/
