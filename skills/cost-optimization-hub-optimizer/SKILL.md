---
name: cost-optimization-hub-optimizer
description: >-
  Optimizes AWS Cost Optimization Hub deployment and recommendation
  workflows with production defaults: account/region enablement
  (update-enrollment-status), recommendation types (right-size,
  idle resource, RI/SP coverage gap), resource-level
  recommendations (get-recommendations), savings estimate
  per recommendation (estimatedMonthlySavings annualized),
  effort level (Low/Medium/High for quick-win prioritization),
  recommendation filters (resource type, region, account,
  action), multi-account via Organizations Payer enrollment,
  integration with Compute Optimizer (right-size source),
  implementation tracking (Applied / Pending / Ignored via
  update-recommendation-status), daily refresh cadence,
  CloudWatch metrics for recommendation-count alerts
  (CostOptimizationHub > ResourceCount), and cost allocation
  tag requirements. Emits an OPTIMIZED /
  FURTHER_OPTIMIZATION_AVAILABLE checklist with verification
  commands. Triggers: cost optimization hub, cost optimization
  recommendation, right-size ec2, idle resource recommendation,
  ri sp coverage gap, savings estimate, effort level quick win,
  multi-account cost optimization, update recommendation
  status, cost optimization hub enable.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor,
  Windsurf, Codex, Gemini). For live deployment: AWS CLI v2
  with cost-optimization-hub:* permissions, organizations:
  ListAccounts for multi-account, and ce:.* for Cost Explorer
  cross-reference. Works with Terraform
  aws_costoptimizationhub_enrollment_status /
  aws_costoptimizationhub_preferences resources.
keywords:
  - aws
  - cost optimization hub
  - finops
  - optimize
  - right-size
  - idle resource
  - ri sp coverage
  - savings estimate
  - effort level
  - quick win
  - multi-account
  - compute optimizer
  - recommendation tracking
  - cost allocation tags
  - cloudwatch alert
tags:
  - aws
  - cost-optimization-hub
  - finops
  - optimize
  - right-size
  - idle-resource
  - ri-sp-coverage
  - savings-estimate
  - effort-level
  - multi-account
  - compute-optimizer
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: FinOps
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - cost-optimization-hub
    - finops
    - optimize
    - right-size
    - idle-resource
    - ri-sp-coverage
    - savings-estimate
    - effort-level
    - multi-account
    - compute-optimizer
  dependencies:
    - aws-orchestrator
  keywords:
    - cost optimization hub
    - cost optimization recommendation
    - right-size ec2
    - idle resource recommendation
    - ri sp coverage gap
    - savings estimate
    - effort level quick win
    - multi-account cost optimization
    - update recommendation status
    - cost optimization hub enable
  when_to_use: >-
    Invoke when the user wants to enable AWS Cost Optimization
    Hub, list or filter recommendations (right-size, idle
    resource, RI/SP coverage gap), estimate savings per
    recommendation, prioritize quick wins by effort level,
    roll out multi-account via the Organizations Payer, track
    implementation status (Applied / Pending / Ignored), set
    up CloudWatch alerts for new recommendations, or audit cost
    allocation tag hygiene. Do NOT invoke for AWS Cost Explorer
    forecasting (use the ce-cost-anomaly-auditor skill), AWS
    Budgets alerts (use the budget skills), or Compute
    Optimizer standalone administration (Cost Optimization Hub
    consumes Compute Optimizer but does not own its
    configuration).
---

# Cost Optimization Hub Optimizer

An AWS CloudOps agent skill that optimizes AWS Cost Optimization
Hub deployments and recommendation workflows with correct
defaults. The skill walks the operator through enrollment
enablement, recommendation types and filtering, savings
estimation (annualized), effort-level prioritization for quick
wins, multi-account roll-out via the Organizations Payer,
integration with Compute Optimizer, implementation-status
tracking, the daily refresh cadence, CloudWatch alerting for
recommendation counts, and cost allocation tag hygiene;
captures the optimization posture; explains why each default
matters; and emits an OPTIMIZED or FURTHER_OPTIMIZATION_AVAILABLE
checklist with copy-pasteable verification commands.

## Activation keywords

cost optimization hub, cost optimization recommendation,
right-size EC2, idle resource recommendation, RI/SP coverage
gap, savings estimate, effort level quick win, multi-account
cost optimization, update recommendation status, cost
optimization hub enable.

## STRICT output contract

When this skill is invoked with a Cost Optimization Hub request
(enable the hub, list recommendations, estimate savings,
prioritize quick wins, track implementation, set up alerts, or
audit cost allocation tags), the agent MUST respond with the
checklist defined in the "Output format" section using the
literal all-caps labels `COST_OPTIMIZATION_HUB:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block
as the first lines of the response. This contract is what
assertion-based evals and downstream FinOps pipelines rely on;
deviating from the literal labels breaks automation silently.

The verdict is `OPTIMIZED` when there are no pending
recommendations with positive estimated savings (all are
Applied or Ignored with documented rationale). The verdict is
`FURTHER_OPTIMIZATION_AVAILABLE` when at least one
recommendation with positive estimated savings is in a Pending
or non-terminal state. Both verdicts MUST NOT appear together.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before optimization |
| Step 1 — Enrollment (enable the hub) | Activation |
| Step 2 — Recommendation types | What the hub finds |
| Step 3 — Resource-level recommendations & filters | Filtering |
| Step 4 — Savings estimate (annualized) | Quantification |
| Step 5 — Effort level (Low/Medium/High) | Prioritization |
| Step 6 — Multi-account via Organizations Payer | Rollout |
| Step 7 — Integration with Compute Optimizer | Right-size source |
| Step 8 — Implementation tracking (Applied/Pending/Ignored) | Workflow |
| Step 9 — Daily refresh cadence | Timing |
| Step 10 — CloudWatch alerts for recommendation counts | Monitoring |
| Step 11 — Cost allocation tag requirements | Hygiene |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/savings-and-effort.md | Savings + effort detail |
| references/multi-account-and-alerts.md | Multi-account + alerting detail |

## Mindset

**One-line takeaway:** Cost Optimization Hub aggregates
recommendations across EC2, EBS, Lambda, ECS, Fargate, ASG, and
more — each with an annualized savings estimate and an effort
level. The verdict reflects whether anything remains on the
table; effort level lets you cherry-pick quick wins first;
multi-account roll-out is one call from the Organizations
Payer.

Four misconceptions dominate Cost Optimization Hub misdesign at
activation time:

- **"Cost Optimization Hub is the same as Cost Explorer."** It
  is NOT. Cost Explorer (CE) shows past spend and forecasts;
  Cost Optimization Hub produces ACTIONABLE resource-level
  recommendations with savings estimates. CE answers "where did
  the money go"; the Hub answers "what should I change to spend
  less next month."

- **"Savings estimates are monthly."** They are NOT in the way
  most operators expect. The Hub's `estimatedMonthlySavings` is
  a monthly figure, but the console and recommendation exports
  annualize it (`estimatedMonthlySavings * 12`) for display.
  Always clarify which period you are quoting — annualized
  numbers drive more action but can mislead if labeled wrong.

- **"The Hub covers every AWS service."** It does NOT. The Hub
  aggregates a specific list (EC2, EBS, Lambda, ECS, Fargate,
  ASG, EC2 Auto Scaling, RDS, Aurora, and a growing set of
  others). Services not on the list produce no Hub
  recommendations — use service-specific skills (e.g., S3
  lifecycle, NAT Gateway optimization) for those.

- **"You must apply recommendations one by one."** You do NOT
  need to apply each manually. The Hub's
  `update-recommendation-status` API marks recommendations as
  Applied, Pending, or Ignored in bulk, and the Hub tracks the
  aggregate. Status is for tracking and reporting — it does not
  perform the optimization. The actual optimization still runs
  via the underlying service (EC2 right-size, Lambda memory,
  etc.).

## Configuration dependency graph (novel heuristic)

Cost Optimization Hub deployment is NOT a single enable call.
The hub must be enrolled; member accounts must be linked via
the Organizations Payer for multi-account visibility; Compute
Optimizer must be enabled for right-size recommendations; cost
allocation tags must be activated for accurate resource-level
attribution; CloudWatch alarms require the Hub namespace.

| Configuration | Hard dependencies (API error without) | Silent failure | Enables downstream |
|---|---|---|---|
| Enrollment (update-enrollment-status ACTIVE) | cost-optimization-hub:UpdateEnrollmentStatus | recommendations are computed but NOT returned until ACTIVE | hub live |
| Multi-account (Organizations Payer) | payer account is the org management account; member accounts linked | single-account enrollment sees only the payer — child accounts are invisible until linked | org-wide recommendations |
| Compute Optimizer enabled | servicecatalog:EnableAWSDefaultServiceRole + compute-optimizer:UpdateEnrollmentStatus | without Compute Optimizer, the Hub's right-size recommendations are EMPTY (it consumes CO findings) | EC2 / ASG / Lambda right-size recommendations |
| Recommendation refresh (daily) | enrollment ACTIVE; runs ~24h cycle | new resources take up to 24h to appear in recommendations | up-to-date recommendations |
| Cost allocation tags activated | ce:UpdateCostAllocationTagsStatus — user-defined tags activated in CE | without activated tags, recommendations still flow but resource-level filtering by tag returns no matches | tag-based filtering and grouping |
| CloudWatch Hub namespace | enrollment ACTIVE; CostOptimizationHub namespace flows automatically | namespace is publish-only on the Hub side — no setup needed beyond enrollment | CloudWatch alarms on recommendation counts |
| Recommendation status tracking | cost-optimization-hub:UpdateRecommendationStatus | status is metadata only — it does NOT apply the optimization | implementation tracking |

**The Compute-Optimizer-enabled row is the one a baseline model
misses.** The Hub consumes Compute Optimizer findings for
right-size recommendations. If Compute Optimizer is not
enrolled, the Hub returns zero right-size recommendations even
though EC2 instances may be massively over-provisioned. The
procedure below forces an explicit check.

## Expert heuristic: the Hub is an aggregator, not a sensor

A baseline model says "enable the Hub and you get
recommendations." The correct heuristic recognizes that the Hub
AGGREGATES findings from upstream services.

```text
Cost Optimization Hub recommendation sources:
  EC2 right-size   ← Compute Optimizer (must be enrolled)
  ASG right-size   ← Compute Optimizer (must be enrolled)
  Lambda right-size ← Compute Optimizer (must be enrolled)
  EBS right-size   ← native (EBS volume metrics)
  ECS/Fargate      ← native (ECS service metrics)
  RDS/Aurora       ← native (RDS DB instance metrics)
  Idle resources   ← native (usage metrics across services)
  RI/SP coverage   ← native (consolidated billing + usage)

If ANY upstream source is missing, that recommendation type
returns empty. Always verify Compute Optimizer enrollment
alongside the Hub.
```

**Key implication:** enable Compute Optimizer in every region
where you run compute, before expecting the Hub to find right-
size opportunities.

## Expert heuristic: effort level drives quick-win sequencing

A baseline model sorts recommendations by savings. The correct
heuristic recognizes that effort level gates the work.

```text
Effort levels (Hub-provided per recommendation):
  Low    — apply in <1 day, no downtime (e.g., EBS gp2 → gp3)
  Medium — apply in 1-5 days, brief downtime or pre-checks
           (e.g., EC2 instance type change with stop/start)
  High   — apply in 5+ days, multi-step rollout
           (e.g., migrate Aurora cluster, restructure ECS)

Quick-win triage:
  1. Filter: effort=Low AND estimatedMonthlySavings > threshold
  2. Sort: by estimatedMonthlySavings desc
  3. Apply this batch first; expect ~70-80% of total savings
     from <30% of the effort.

ALWAYS start with Low-effort high-savings. The Hub's effort
field is canonical — do not guess.
```

**Key implication:** the effort-level filter is the single
highest-leverage dimension for FinOps teams with limited
engineering bandwidth.

## Expert heuristic: savings are annualized in the console

A baseline model quotes "you'll save $X" without the period.
The correct heuristic always labels the period.

```text
Hub API field: estimatedMonthlySavings (USD/month)
Console display: estimatedMonthlySavings × 12 (USD/year)

Annualized quotes are correct for budget conversations
(annual planning). Monthly quotes are correct for
month-over-month burn-rate conversations.

NEVER mix the two in the same report. Pick one and label it.
Default for executive summaries: annualized. Default for
engineering burn-down: monthly.
```

## Prerequisites (verify before optimization)

Before emitting optimization commands, verify these
prerequisites. If any are missing, the verdict is
**FURTHER_OPTIMIZATION_AVAILABLE** with the specific gap cited.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Hub enrollment ACTIVE | Recommendations not returned until ACTIVE | `aws cost-optimization-hub get-enrollment-status` returns `ACTIVE` |
| Caller is the Organizations Payer (for multi-account) | Multi-account visibility only from the payer | `aws organizations describe-organization` master account ID == caller |
| Compute Optimizer enrolled | Right-size recommendations are EMPTY without it | `aws compute-optimizer get-enrollment-status` returns `ACTIVE` |
| Cost allocation tags activated | Required for accurate resource-level grouping | `aws ce list-cost-allocation-tags` shows user tags as `Active` |
| CloudTrail org trail active (recommended) | Without it, recommendation application cannot be audited | `aws cloudtrail describe-trails` shows an Organization trail |
| Member accounts linked | Without linkage, child-account resources invisible | `aws organizations list-accounts` count matches Hub account list |
| Recommendation refresh within 24h | Stale recommendations drive bad decisions | `aws cost-optimization-hub get-recommendation-summary` `lastRefresh` within 24h |

If any prerequisite is missing, output
`VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` and cite the specific
gap.

## Step 1 — Enrollment (enable the hub)

```bash
# Check current status
aws cost-optimization-hub get-enrollment-status

# Enable (ACTIVE). Use --no-include-member-accounts for
# single-account; omit for multi-account via Organizations Payer.
aws cost-optimization-hub update-enrollment-status \
  --status ACTIVE \
  --include-member-accounts

# Configure recommendation preferences (which resources to include)
aws cost-optimization-hub update-preferences \
  --savings-estimation-mode AFTER_DISCOUNT \
  --look-back-period-in-days 14
```

`AFTER_DISCOUNT` factors in RI/SP discounts; `BEFORE_DISCOUNT`
uses On-Demand rates. Use `AFTER_DISCOUNT` for accurate net
savings when you have RIs/SPs.

## Step 2 — Recommendation types

| Type | Source | What it finds | Typical savings |
|---|---|---|---|
| Right-size (EC2 / ASG / Lambda) | Compute Optimizer | Over-provisioned instances, functions with wrong memory | 10-40% on compute |
| EBS volume right-size | Native EBS | gp2 → gp3, oversized volumes, unattached volumes | 20-50% on EBS |
| ECS / Fargate right-size | Native ECS | Oversized task definitions, Fargate vs EC2 tradeoff | 15-30% on ECS |
| Idle resource | Native (usage) | ELBs with no targets, EIPs unattached, idle RDS | 100% of idle |
| RI / SP coverage gap | Native (billing + usage) | On-Demand spend that could be covered by RI/SP | 20-40% on covered spend |
| S3 storage class | Native S3 | Standard → Intelligent-Tiering / Glacier | 30-60% on S3 |
| Aurora / RDS right-size | Native RDS | Oversized instances, storage right-size | 15-30% on RDS |

**Each recommendation includes:** resource ARN, current config,
recommended config, `estimatedMonthlySavings`, `effort`, and
`action` (e.g., `Rightsize`, `Stop`, `Terminate`, `Migrate`).

## Step 3 — Resource-level recommendations & filters

```bash
# List all recommendations (paginated)
aws cost-optimization-hub get-recommendations \
  --query 'items[*].{Resource:resourceArn,Action:action,Savings:estimatedMonthlySavings,Effort:effort}' \
  --output table

# Filter by resource type
aws cost-optimization-hub get-recommendations \
  --filter '{"resourceType":"EC2_INSTANCE"}' \
  --output table

# Filter by region
aws cost-optimization-hub get-recommendations \
  --filter '{"region":"us-east-1"}'

# Filter by account (multi-account payer)
aws cost-optimization-hub get-recommendations \
  --filter '{"accountId":"111122223311"}'

# Filter by action
aws cost-optimization-hub get-recommendations \
  --filter '{"action":"Rightsize"}'

# Filter by effort (quick wins)
aws cost-optimization-hub get-recommendations \
  --filter '{"effort":"Low"}'
```

Filters COMBINE with AND when chained. Use the `--filter`
argument with a JSON object of multiple keys.

## Step 4 — Savings estimate (annualized)

```bash
# Aggregate summary
aws cost-optimization-hub get-recommendation-summary

# Estimated monthly savings total
# (output: estimatedMonthlySavings)
# Annualized = estimatedMonthlySavings * 12
```

| Field | Period | Use for |
|---|---|---|
| `estimatedMonthlySavings` | monthly | Burn-rate tracking, month-over-month reporting |
| `estimatedMonthlySavings * 12` | annual | Executive summaries, budget planning |
| `estimatedSavingsRate` (ratio) | % | Benchmarking (e.g., "save 23% of compute spend") |

Always label the period when reporting. The Hub API returns
monthly; the console annualizes. Do NOT mix.

## Step 5 — Effort level (Low/Medium/High)

| Effort | Typical action | Examples | Recommended first? |
|---|---|---|---|
| Low | One-shot, no downtime | EBS gp2 → gp3, S3 lifecycle, EIP release | YES — quick wins |
| Medium | Brief downtime or pre-checks | EC2 instance type change, RDS right-size | After Low batch |
| High | Multi-step rollout | Aurora cluster migrate, ECS restructure | Quarterly planning |

**Quick-win query:**

```bash
aws cost-optimization-hub get-recommendations \
  --filter '{"effort":"Low"}' \
  --query 'items[*].{Resource:resourceArn,Savings:estimatedMonthlySavings,Action:action}' \
  --output table
```

Sort by `estimatedMonthlySavings` descending for the canonical
quick-win queue.

## Step 6 — Multi-account via Organizations Payer

Multi-account visibility is anchored at the Organizations
Payer (the management account). Enable on the payer with
`--include-member-accounts`:

```bash
# From the Payer (management) account
aws cost-optimization-hub update-enrollment-status \
  --status ACTIVE \
  --include-member-accounts

# Verify all member accounts are linked
aws cost-optimization-hub get-enrollment-statuses \
  --query 'items[*].{Account:accountId,Status:status}' \
  --output table
```

**Common pitfalls:**

- Member accounts that opted OUT of the org are invisible.
- Linked accounts that joined the org AFTER enablement may
  take up to 24h to appear.
- The Payer itself is always enrolled; member accounts inherit
  enrollment.

## Step 7 — Integration with Compute Optimizer

Compute Optimizer (CO) is the upstream source for right-size
recommendations on EC2, ASG, and Lambda. Without CO enrolled,
the Hub returns ZERO right-size recommendations.

```bash
# Check CO enrollment
aws compute-optimizer get-enrollment-status

# Enable CO (if not already)
aws compute-optimizer update-enrollment-status \
  --status Active \
  --include-member-accounts

# CO recommendations feed the Hub after the next refresh cycle
```

CO enrollment takes up to 12h to surface its first findings;
the Hub refreshes daily. Plan for a 24-36h lag between
enabling CO and seeing right-size recommendations in the Hub.

## Step 8 — Implementation tracking (Applied / Pending / Ignored)

The Hub tracks each recommendation's lifecycle status. Updating
status is for tracking only — it does NOT apply the
optimization.

```bash
# Mark a single recommendation Applied
aws cost-optimization-hub update-recommendation-status \
  --recommendation-id <id> \
  --status APPLIED

# Mark a batch Ignored (with reason via the resource tag)
aws cost-optimization-hub batch-update-recommendation-status \
  --request '{"recommendationIds":["id1","id2"],"status":"IGNORED"}'

# List by status
aws cost-optimization-hub get-recommendations \
  --filter '{"implementationStatus":"PENDING"}'
```

| Status | Meaning |
|---|---|
| PENDING | Default; not yet acted on |
| APPLIED | Optimization applied manually or automatically |
| IGNORED | Deliberately not applying (document rationale) |

**The verdict rule:** OPTIMIZED requires that NO recommendation
with positive estimated savings is PENDING. All must be APPLIED
or IGNORED with documented rationale.

## Step 9 — Daily refresh cadence

The Hub refreshes approximately every 24 hours. New resources
appear in recommendations within one cycle. There is no
manual refresh trigger.

```bash
# Last refresh timestamp
aws cost-optimization-hub get-recommendation-summary \
  --query 'lastRefresh'
```

For fresh findings, wait for the next cycle. Do NOT trigger
changes and expect same-day recommendations — the Hub lags by
up to 24h.

## Step 10 — CloudWatch alerts for recommendation counts

The Hub publishes metrics to the `CostOptimizationHub` namespace.
Use CloudWatch to alert on changes in recommendation counts or
estimated savings.

```bash
# Create a CloudWatch alarm for new high-savings recommendations
aws cloudwatch put-metric-alarm \
  --alarm-name "CostOptHub-HighSavings-Recommendations" \
  --namespace CostOptimizationHub \
  --metric-name ResourceCount \
  --statistic Sum \
  --period 86400 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:111122223311:finops-alerts"
```

Common alarm shapes:

| Alarm | Trigger | Use case |
|---|---|---|
| New recommendation count > 0 | Daily fresh findings | Triage queue |
| Total estimated savings drop > 25% | Sustained progress | Celebrate / verify |
| Total estimated savings rise > 25% | Regression / new waste | Investigate |
| Pending recommendation count > 50 | Backlog growth | Engineering capacity check |

## Step 11 — Cost allocation tag requirements

Cost allocation tags drive resource-level grouping in the Hub.
Without activated user-defined tags, the Hub cannot group by
your taxonomy.

```bash
# List all cost allocation tags and their status
aws ce list-cost-allocation-tags \
  --query 'CostAllocationTags[?Status==`Active`].TagKey' \
  --output table

# Activate a user-defined tag
aws ce update-cost-allocation-tags-status \
  --status ACTIVE \
  --tag-keys Environment,Owner,CostCenter
```

Tag activation takes up to 24h to flow through billing →
CUR → Hub. Plan tag-driven rollouts accordingly.

**Common pitfalls:**

- `aws:createdBy` and other AWS-generated tags are active by
  default; user-defined tags must be activated explicitly.
- Tag values are case-sensitive in CE grouping.
- Tags applied today take ~24h to appear in Hub
  recommendations.

## Step 12 — Recent features

**Recent AWS features (2023-2026):**

- **Aurora and RDS right-size recommendations (2023-2024):**
  The Hub added native RDS/Aurora right-sizing, sourced from
  RDS CloudWatch metrics. No additional enrollment needed.
- **ECS and Fargate right-size (2023-2024):** Task-definition
  CPU/memory recommendations for ECS services and Fargate
  tasks. Effort level is High for Fargate → EC2 migrations.
- **Resource-level granularity expansion (2024-2025):** The
  Hub added per-resource ARN linkage to Compute Optimizer
  findings, simplifying downstream automation.
- **`AFTER_DISCOUNT` savings estimation (2024-2025):** New
  preference to factor in RI/SP discounts for accurate net
  savings. Default for most enterprises.
- **Implementation Status API (2024-2025):**
  `batch-update-recommendation-status` and per-account
  implementation rollups added to support CI/CD-style
  FinOps pipelines.
- **CloudWatch native namespace (2024-2025):** The
  `CostOptimizationHub` CloudWatch namespace is now published
  automatically on enrollment — no manual metric-stream
  setup needed.
- **Multi-account enrollment controls (2025-2026):** Per-
  member-account opt-out for sensitive workloads (e.g.,
  regulated environments where the payer should not see
  resource-level detail).

## NEVER do these things

1. **NEVER confuse the Hub with Cost Explorer.** CE shows
   spend; the Hub produces actionable recommendations. They
   are complementary, not interchangeable.

2. **NEVER quote savings without labeling the period.**
   `estimatedMonthlySavings` is monthly; the console
   annualizes. Pick one and label it.

3. **NEVER assume Compute Optimizer is enrolled.** The Hub's
   right-size recommendations are EMPTY without it. Always
   verify CO enrollment alongside the Hub.

4. **NEVER expect same-day recommendations after a change.**
   The Hub refreshes approximately every 24h. Plan for the
   lag; do not trigger a change and expect instant feedback.

5. **NEVER rely on `update-recommendation-status` to APPLY the
   optimization.** Status is tracking metadata only. The
   actual optimization runs via the underlying service (EC2
   stop/start, Lambda memory update, etc.).

6. **NEVER assume cost allocation tags are active by default.**
   User-defined tags require explicit activation via
   `ce:UpdateCostAllocationTagsStatus`. Without activation,
   tag-based filtering returns no matches.

7. **NEVER enroll the Hub from a member account for org-wide
   visibility.** Multi-account visibility is anchored at the
   Organizations Payer. Member-account enrollment sees only
   the member.

8. **NEVER mark a recommendation IGNORED without documenting
   why.** Future operators will not know whether it was
   inapplicable, deferred, or rejected. Use the resource tag
   or a comment field to record rationale.

9. **NEVER mix `BEFORE_DISCOUNT` and `AFTER_DISCOUNT` savings
   in the same report.** Pick one mode (prefer
   `AFTER_DISCOUNT` for RI/SP holders) and label every chart.

10. **NEVER expect CloudWatch alarms on the Hub namespace
    without enrollment.** The `CostOptimizationHub` namespace
    flows only when the hub is ACTIVE. Verify enrollment
    before alarm creation.

## Output format

```text
COST_OPTIMIZATION_HUB: <enrollment-status> (<account-scope>) — last refresh <timestamp>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
CHECKLIST:
  [✓|✗] Enrollment status: ACTIVE | INACTIVE
  [✓|✗] Account scope: Single | Multi (Payer <account-id>, <N> members linked)
  [✓|✗] Compute Optimizer enrolled: ACTIVE | INACTIVE (right-size recs will be empty)
  [✓|✗] Savings estimation mode: AFTER_DISCOUNT | BEFORE_DISCOUNT
  [✓|✗] Look-back period: <N> days
  [✓|✗] Total estimated savings: $<monthly> / month ($<annualized> annualized)
  [✓|✗] Recommendation count: <total> (Applied: <N>, Pending: <N>, Ignored: <N>)
  [✓|✗] Quick-win queue (Low effort, savings > $<threshold>): <N> recommendations, $<monthly>/mo
  [✓|✗] Cost allocation tags: <N> active (Environment, Owner, CostCenter, ...)
  [✓|✗] CloudWatch alarms: <N> configured on CostOptimizationHub namespace
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws cost-optimization-hub get-enrollment-status
  aws cost-optimization-hub get-recommendation-summary
  aws cost-optimization-hub get-recommendations --filter '{"effort":"Low"}' --output table
  aws compute-optimizer get-enrollment-status
```

### Worked example — quick-win triage in a multi-account org

```text
COST_OPTIMIZATION_HUB: ACTIVE (Multi — Payer 123456789012, 14 members linked) — last refresh 2026-08-11T03:14Z
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
CHECKLIST:
  [✓] Enrollment status: ACTIVE
  [✓] Account scope: Multi (Payer 123456789012, 14 members linked)
  [✓] Compute Optimizer enrolled: ACTIVE
  [✓] Savings estimation mode: AFTER_DISCOUNT
  [✓] Look-back period: 14 days
  [✗] Total estimated savings: $4,820 / month ($57,840 annualized)
  [✗] Recommendation count: 87 (Applied: 12, Pending: 71, Ignored: 4)
  [✗] Quick-win queue (Low effort, savings > $50): 23 recommendations, $1,910/mo
  [✓] Cost allocation tags: 3 active (Environment, Owner, CostCenter)
  [✓] CloudWatch alarms: 2 configured (NewRecommendations, SavingsRegression)
  [✓] Tags: Owner=finops, Cadence=weekly
VERIFICATION_COMMANDS:
  aws cost-optimization-hub get-enrollment-status
  aws cost-optimization-hub get-recommendation-summary
  aws cost-optimization-hub get-recommendations --filter '{"effort":"Low"}' --output table
  aws compute-optimizer get-enrollment-status
```

## Error handling

### Hub returns zero recommendations

- Either (a) enrollment is INACTIVE (verify with
  `get-enrollment-status`), (b) Compute Optimizer is not
  enrolled for right-size types (verify with
  `compute-optimizer get-enrollment-status`), or (c) the
  daily refresh has not yet run since enrollment (wait 24h).

### Multi-account payer sees only the payer account

- `--include-member-accounts` was not set at
  `update-enrollment-status` time. Re-issue with the flag, or
  verify each member is in `ACTIVE` status via
  `get-enrollment-statuses`.

### Savings estimates differ from Cost Explorer

- The Hub and CE use different methodologies. The Hub uses
  resource-level right-sizing logic; CE uses aggregate
  forecasting. Discrepancies are expected and not bugs.
  Report Hub numbers for resource-level optimization, CE for
  forecasting.

### Cost allocation tag filter returns empty

- The tag is not activated. Activate via
  `ce update-cost-allocation-tags-status --status ACTIVE
  --tag-keys <key>`. Activation takes up to 24h to flow
  through billing → CUR → Hub.

### CloudWatch namespace missing

- The Hub must be ACTIVE for the `CostOptimizationHub`
  namespace to publish. Verify enrollment, then wait up to
  24h for the first metric publish.

## Domain

AWS CloudOps / FinOps — Cost Optimization Hub Administration,
Recommendation Triage, Multi-Account Roll-out, and Quick-Win
Implementation Tracking.

## AWS documentation

- **Cost Optimization Hub** — https://docs.aws.amazon.com/cost-management/latest/userguide/cothub.html
- **Recommendations** — https://docs.aws.amazon.com/cost-management/latest/userguide/recommendations.html
- **Enrollment** — https://docs.aws.amazon.com/cost-management/latest/userguide/enrollment.html
- **Multi-account** — https://docs.aws.amazon.com/cost-management/latest/userguide/multi-account.html
- **Compute Optimizer** — https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is.html
- **Cost allocation tags** — https://docs.aws.amazon.com/cost-management/latest/userguide/alloc-tags.html
- **CloudWatch Hub metrics** — https://docs.aws.amazon.com/cost-management/latest/userguide/monitoring-cloudwatch.html
- **Implementation tracking** — https://docs.aws.amazon.com/cost-management/latest/userguide/implementation-status.html
- **Effort levels** — https://docs.aws.amazon.com/cost-management/latest/userguide/recommendations.html#effort
- **Savings estimation modes** — https://docs.aws.amazon.com/cost-management/latest/userguide/preferences.html
