---
name: ec2-reserved-capacity-optimizer
description: 'Optimizes EC2 Reserved Instance and Savings Plans commitments across seven dimensions: RI utilization analysis (underused Standard or Convertible RIs), coverage gap detection (on-demand spend exposed to full price), Standard vs Convertible RI selection, 1-year vs 3-year term trade-offs, upfront vs no-upfront payment options, Savings Plans type choice (Compute SP vs EC2 Instance SP vs SageMaker SP), and Cost Explorer recommendation harvesting. Reads Cost Explorer RI/SP utilization, coverage reports, and EC2 fleet inventory. Emits FURTHER_OPTIMIZATION_AVAILABLE or OPTIMIZED with commitment adjustments, estimated savings, and utilization alerts. Use when reviewing RI portfolios, evaluating Savings Plans, planning a commitment strategy, or conducting a FinOps commitment review.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted Cost Explorer RI/SP utilization reports, coverage data, and EC2 fleet summaries. Live-account optimization uses aws ce get-reservation-utilization, aws ce get-reservation-coverage, aws ce get-savings-plans-utilization, aws ce get-savings-plans-coverage, aws ce get-cost-and-usage, aws ce get-reservation-purchase-recommendation, aws ec2...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimizing EC2 Reserved Instance portfolios, evaluating Savings Plans (Compute vs EC2 Instance vs SageMaker), analyzing RI utilization or coverage gaps, deciding Standard vs Convertible RIs, choosing 1-year vs 3-year commitment terms, evaluating upfront vs no-upfront payment options, selling unused RIs on the RI Marketplace, setting up RI/SP utilization alerts via CloudWatch or Budgets, normalizing an EC2 fleet for Savings Plans coverage, or conducting a FinOps commitment strategy review.
  when_not_to_use: EC2 instance right-sizing (use ec2-rightsizing-optimizer), Lambda cost optimization (use lambda-cost-optimizer), Fargate cost optimization (use fargate-cost-optimizer), EKS cost optimization (use eks-cost-optimizer), or Spot Instance strategy (use ec2-spot-strategy-optimizer). This skill focuses on commitment optimization (RIs and SPs), not workload architecture changes.
  activation_triggers: optimise Reserved Instances, RI utilization, RI coverage, Savings Plans optimization, Standard vs Convertible RI, 1-year vs 3-year commitment, upfront vs no upfront, Compute Savings Plans, EC2 Instance Savings Plans, RI marketplace sell, commitment management, FinOps commitment review, reduce EC2 commitment waste, RI underutilized, on-demand coverage gap
  invocation_schema: 'Input: either (a) a linked account or payer account with live Cost Explorer access, (b) pasted RI/SP utilization and coverage reports with EC2 fleet instance-type distribution, OR (c) a commitment decision question (e.g. "should I buy 3-year Standard RIs for m5.large?"). Output: a deterministic TARGET / VERDICT / REASON / RECOMMENDATION / ESTIMATED_SAVINGS / ACTION_STEPS block per commitment dimension, where VERDICT is one of {OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: EC2, Reserved Instances, Savings Plans, RI utilization, RI coverage, Standard RI, Convertible RI, commitment management, Cost Explorer, Compute Savings Plans, EC2 Instance Savings Plans, upfront payment, 1-year term, 3-year term, RI marketplace, FinOps, CloudWatch utilization alerts, Budgets
  tags: ec2, reserved-instances, savings-plans, compute, cost-optimization, finops, commitment-management, cost-explorer
---

# EC2 Reserved Capacity Optimizer

## Activation

Activate this skill when the user reports EC2 Reserved Instance or
Savings Plans cost concerns. Trigger phrases: "optimise Reserved
Instances", "RI utilization", "RI coverage", "Savings Plans
optimization", "Standard vs Convertible RI", "1-year vs 3-year
commitment", "upfront vs no upfront", "commitment management",
"FinOps commitment review", "reduce EC2 commitment waste".

## Mindset

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Quick reference — commitment vehicles

| Vehicle | Flexibility | Max discount (3yr) | Best for |
|---|---|---|---|
| Standard RI (3yr, All Upfront) | None — locked | ~72% | Steady-state, fixed instance type, 3yr horizon |
| Convertible RI (3yr, All Upfront) | Exchange within family+region | ~62% | Semi-stable, may change instance size/family |
| EC2 Instance SP (3yr, All Upfront) | Flexible across sizes+AZs in family | ~72% | Commit to a family but flexible on size |
| Compute SP (3yr, All Upfront) | Flexible across EC2+Fargate+Lambda | ~54% | Multi-service compute, highest flexibility |
| On-Demand | Full flexibility | 0% | Spiky, unpredictable, short-lived workloads |

## Quick navigation

| Section | Purpose |
|---|---|
| **Step 0** | Capture the commitment baseline (RI/SP inventory, fleet, spend) |
| **Step 1** | Classify the optimization category (A-G) |
| **Step 2** | COVERAGE_GAP: identify on-demand spend eligible for commitment |
| **Step 3** | UTILIZATION_GAP: identify underused RIs/SPs |
| **Step 4** | TERM_EVAL: 1-year vs 3-year trade-off analysis |
| **Step 5** | PAYMENT_EVAL: upfront vs no-upfront breakeven |
| **Step 6** | VEHICLE_EVAL: Standard RI vs Convertible RI vs SP |
| **Step 7** | Root-cause catalog (top patterns + canonical fixes) |
| **Step 8** | Verify the recommendation |
| **Step 9** | Decide VERDICT (OPTIMIZED / FURTHER_OPTIMIZATION_AVAILABLE) |

## STRICT output contract

```text
TARGET: <account/project/fleet> — <instance family or SP scope>
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE | OPTIMIZED
REASON: <summary of utilization, coverage, and commitment gaps>
RECOMMENDATION:
  1. <COVERAGE_GAP recommendation: what to commit and why>
  2. <UTILIZATION_GAP recommendation: what to exchange/sell/reduce>
  3. <TERM_EVAL recommendation: 1yr vs 3yr with rationale>
  4. <PAYMENT_EVAL recommendation: upfront vs no-upfront>
  5. <VEHICLE_EVAL recommendation: RI type or SP type>
ESTIMATED_SAVINGS: $<monthly savings> ($<annual savings>)
ACTION_STEPS:
  1. <specific step with AWS CLI or console action>
  2. <verification step>
  3. <rollback / hedging step>
```

## NEVER

- **NEVER** commit to a 3-year Standard RI for an instance type that
  has not run steadily for at least 90 days. Standard RIs cannot be
  exchanged or cancelled. If the workload changes, you pay for the RI
  regardless. Use a 1-year Convertible RI or Compute SP first, then
  upgrade to a 3-year Standard RI once the workload is confirmed
  stable.

- **NEVER** recommend a commitment without checking utilization of
  existing RIs first. Adding new RIs on top of underutilized ones
  compounds waste. Always audit current RI/SP utilization before
  recommending new commitments.

- **NEVER** recommend a Standard RI for workloads that may need
  instance-family migration (e.g., m5 to m6i, or x86 to Graviton).
  Standard RIs lock the family. Use a Compute SP (cross-family) or
  Convertible RI (exchangeable within family) instead.

- **NEVER** ignore the upfront cost in breakeven analysis. A 3-year
  all-upfront RI has the highest discount but requires full payment on
  day one. If the upfront capital is constrained, the no-upfront option
  may have a better effective rate when time-value of capital is
  considered.

- **NEVER** sell RIs on the RI Marketplace without verifying the
  remaining term and the pro-rated value. The Marketplace charges a
  12% service fee on the pro-rated remaining value. Selling a Standard
  RI with 30 days remaining loses money; selling with 18 months
  remaining may recover value if the workload has migrated.

- **NEVER** set utilization CloudWatch alarms at 100%. RIs have natural
  utilization dips during deployments, scaling events, and off-hours.
  Set alerts at 80% (investigate) and 60% (act — exchange or sell).
  A 100% threshold masks underutilization until it is too late.

## Process — Commitment optimization decision tree (apply in order)

### Step 0: Capture the commitment baseline

Gather these inputs. Each step below branches on which are available.

| Signal | Source | Why required |
|---|---|---|
| **RI inventory** | `aws ec2 describe-reserved-instances` | Active commitments, type, term, state |
| **SP inventory** | `aws savingsplans describe-savings-plans` | Active SPs, type, term, commitment |
| **RI utilization** | `aws ce get-reservation-utilization` | Are committed RIs being consumed? |
| **RI coverage** | `aws ce get-reservation-coverage` | Are running instances covered? |
| **SP utilization** | `aws ce get-savings-plans-utilization` | Are SP commitments being consumed? |
| **SP coverage** | `aws ce get-savings-plans-coverage` | Is compute spend covered by SP? |
| **EC2 fleet** | `aws ec2 describe-instances` | Instance type distribution, families, OS |
| **Cost data** | `aws ce get-cost-and-usage` | Baseline on-demand spend by service/usage |

If the user has not provided RI/SP data or fleet information, output:

```text
TARGET: <account or fleet>
VERDICT: NEED_MORE_INFO
REASON: Cannot optimize commitments without RI/SP utilization and
coverage data.
MISSING:
  - RI/SP utilization report (Cost Explorer, 30+ days)
  - RI/SP coverage report (Cost Explorer, 30+ days)
  - EC2 fleet instance-type distribution (describe-instances)
  - Monthly on-demand EC2 spend (Cost Explorer)
```

Moved verbatim to [references/commitment-analysis-commands.md](references/commitment-analysis-commands.md) - load on demand (see References below).

### Step 1: Identify the optimization category

| Category | Signal | Diagnostic step |
|---|---|---|
| **A. COVERAGE_GAP** | RI/SP coverage < 80% of steady-state hours | Step 2 |
| **B. UTILIZATION_GAP** | RI utilization < 90% or SP utilization < 95% | Step 3 |
| **C. TERM_EVAL** | 1-year commitments expiring; evaluate 3-year upgrade | Step 4 |
| **D. PAYMENT_EVAL** | No-upfront commitments; evaluate upfront breakeven | Step 5 |
| **E. VEHICLE_EVAL** | Standard RIs where Convertible or SP is better fit | Step 6 |
| **F. ALREADY_OPTIMAL** | Coverage > 90%, utilization > 95%, right vehicle/term | Verdict: OPTIMIZED |
| **G. MARKETPLACE_SELL** | Underused Standard RIs with > 6 months remaining | Step 3 |

**Apply B before A.** Fixing utilization gaps (excess commitments)
before coverage gaps (missing commitments) prevents compounding waste.
If you buy more RIs while existing ones are underutilized, the new RIs
will cannibalize the old ones.

### Step 2: COVERAGE_GAP — identify on-demand spend eligible for commitment

Coverage measures what fraction of running instance-hours is covered by
RIs or SPs. A coverage gap means you are paying on-demand for instances
that could be committed.

**Coverage assessment table:**

| RI/SP coverage | Status | Action |
|---|---|---|
| > 90% | Excellent | Maintain; monitor for fleet changes |
| 80-90% | Good | Consider committing the remaining steady-state baseline |
| 60-80% | Suboptimal | Significant on-demand spend; commit the steady-state portion |
| < 60% | Poor | Major coverage gap; prioritize commitment immediately |

**How to identify the committable baseline:**

1. Pull 90 days of hourly EC2 spend, grouped by instance family.
2. For each family, find the minimum instance count across all hours
   (this is the always-running baseline).
3. Commit to the baseline; leave the variable portion (scaling, spot)
   on on-demand or Spot.

```bash
# Get Cost Explorer RI purchase recommendation:
aws ce get-reservation-purchase-recommendation \
  --service "Amazon Elastic Compute Cloud - Compute" \
  --term-in-years 1 \
  --payment-option NO_UPFRONT \
  --lookback-period 60 \
  --service-specification '{"EC2Specification":{"OfferingClass":"STANDARD"}}'

# Get Savings Plans recommendation:
aws ce get-savings-plans-purchase-recommendation \
  --lookback-period 60 \
  --term-in-years 1 \
  --payment-option NO_UPFRONT
```

**Coverage gap example:**

A fleet of 50 m5.large instances runs 24/7. RI coverage is 40% (20
instances covered). The remaining 30 instances are on-demand. The
committable baseline is ~48 instances (the 90-day minimum count). A
gap of ~28 instances exists.

**Savings estimation (m5.large, us-east-1, Linux, 2026):**

| Pricing | Hourly | Monthly (730h) |
|---|---|---|
| On-Demand | $0.096 | $70.08 |
| 1yr Standard RI, No Upfront | $0.071 (~26% off) | $51.83 |
| 1yr Standard RI, All Upfront | $0.063 (~34% off) | $45.99 |
| 3yr Standard RI, No Upfront | $0.053 (~45% off) | $38.69 |
| 3yr Standard RI, All Upfront | $0.038 (~60% off) | $27.74 |
| 3yr Compute SP, All Upfront | $0.050 (~48% off) | $36.50 |

Covering 28 m5.large with 3yr Standard RI All Upfront saves ~$1,185/month
vs on-demand ($70.08 - $27.74 = $42.34/instance x 28).

### Step 3: UTILIZATION_GAP — identify underused RIs/SPs

Utilization measures whether committed dollars are actually consumed.
A utilization gap means you are paying for commitments that are not
used.

**Utilization assessment table:**

| RI/SP utilization | Status | Action |
|---|---|---|
| > 95% | Excellent | Well-sized commitment |
| 85-95% | Good | Minor over-commit; acceptable |
| 70-85% | Suboptimal | Over-committed; investigate fleet changes |
| < 70% | Poor | Significant waste; exchange (Convertible) or sell (Standard) |

**Diagnostic commands:**

```bash
# RI utilization by instance type (last 30 days):
aws ce get-reservation-utilization \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY \
  --group-by Type=DIMENSION,Key=INSTANCE_TYPE \
  --filter '{"Dimensions":{"Key":"Service","Values":["Amazon Elastic Compute Cloud - Compute"]}}'

# SP utilization detail:
aws ce get-savings-plans-utilization-detail \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --filter '{"Dimensions":{"Key":"SavingsPlanType","Values":["COMPUTE_SP"]}}'
```

**Utilization gap scenarios and fixes:**

| Scenario | Root cause | Fix |
|---|---|---|
| RI utilization dropped after instance migration (m5 to m6i) | Standard RI locked to m5; fleet moved to m6i | Sell on RI Marketplace; buy new commitment for m6i |
| RI utilization dropped after right-sizing (c5.xlarge to c5.large) | RI covers larger size than needed | If Convertible: exchange for smaller size. If Standard: sell |
| SP utilization < 80% | Committed $/hour too high for current spend | Let SP expire; recommit at lower rate |
| RI utilization < 70% after workload migration to Spot | Fleet moved to Spot; RI covers on-demand portion | Sell RIs; use Spot + smaller RI for baseline |

### Step 4: TERM_EVAL — 1-year vs 3-year trade-off

The longer the term, the deeper the discount — but the higher the
lock-in risk. The decision hinges on workload stability.

**Term decision matrix:**

| Workload characteristic | Recommended term | Rationale |
|---|---|---|
| Core infrastructure (databases, always-on API) | 3-year | Will not change; maximize discount |
| Stable service, uncertain instance type (may migrate to Graviton) | 3-year Convertible RI or Compute SP | Flexibility preserves the discount |
| Growing service, uncertain scale | 1-year | Re-evaluate annually |
| New service (< 90 days running) | No commitment yet | Use on-demand until baseline confirmed |
| Service likely to be deprecated | No commitment | Avoid lock-in on a dying service |

**Breakeven analysis (Standard RI, us-east-1, m5.large, Linux):**

| Term | Payment | Hourly | vs On-Demand savings | Breakeven |
|---|---|---|---|---|
| 1yr, No Upfront | $0.071 | 26% | Day 1 (no upfront) |
| 1yr, All Upfront | $336 upfront + $0/hour | 34% | ~6 months |
| 3yr, No Upfront | $0.053 | 45% | Day 1 (no upfront) |
| 3yr, All Upfront | $836 upfront + $0/hour | 60% | ~5 months |

The 3yr All Upfront is the cheapest but requires $836 upfront per RI.
The 3yr No Upfront has no upfront but a slightly higher hourly rate.
For predictable workloads, 3yr All Upfront maximizes savings.

### Step 5: PAYMENT_EVAL — upfront vs no-upfront breakeven

The payment option affects the effective discount. More upfront = more
discount but higher capital outlay.

**Payment option comparison (3yr Standard RI, m5.large):**

| Payment | Upfront cost | Monthly | Total 3yr cost | Discount vs OD |
|---|---|---|---|---|
| No Upfront | $0 | $38.69 | $1,392.84 | 45% |
| Partial Upfront | $418 | $19.35 | $1,114.80 | 55% |
| All Upfront | $836 | $0 | $836.00 | 60% |

**Decision rule:**
- If upfront capital is available and the workload is confirmed
  stable: All Upfront maximizes savings.
- If capital is constrained or budget is OpEx-only: No Upfront still
  yields 45% savings with zero upfront.
- Partial Upfront is a middle ground: 55% discount with manageable
  upfront.

### Step 6: VEHICLE_EVAL — Standard RI vs Convertible RI vs SP

| Factor | Standard RI | Convertible RI | Compute SP | EC2 Instance SP |
|---|---|---|---|---|
| Discount depth | Highest | High (~10% less than Standard) | Moderate | High (= Standard) |
| Instance family lock | Yes | Exchangeable within family | Flexible (any EC2/Fargate/Lambda) | Flexible within family sizes/AZs |
| AZ flexibility | Locked to AZ | Locked to AZ | Region-wide | Region-wide |
| OS flexibility | Locked to OS | Locked to OS | Any OS | Any OS within family |
| Best use case | Fixed workload, max discount | Semi-stable workload, hedge | Multi-service compute | Family commitment with size flexibility |

**Decision tree:**

1. Is the workload EC2-only, single instance family, stable 3yr? ->
   **Standard RI (3yr All Upfront)** for max discount.
2. Is the workload EC2-only, but may change instance size or migrate
   within the family? -> **EC2 Instance SP (3yr)** for family-level
   commitment with size/AZ flexibility.
3. Is the workload mixed (EC2 + Fargate + Lambda)? ->
   **Compute SP (3yr)** for cross-service flexibility.
4. Is the workload EC2-only but may migrate families (e.g., m5 to
   Graviton c7g)? -> **Compute SP** — Convertible RIs cannot cross
   families.
5. Is the workload semi-stable but uncertain? ->
   **Convertible RI (1yr)** — exchangeable if needs change.

### Step 7: Map to root-cause catalog

| # | Pattern | Category | Fix | Est. savings |
|---|---|---|---|---|
| 1 | RI coverage < 60%, steady-state 24/7 fleet | COVERAGE_GAP | Commit the baseline with 3yr RI/SP | 45-60% on committed portion |
| 2 | RI utilization < 70% after fleet migration | UTILIZATION_GAP | Sell Standard RI on Marketplace or exchange Convertible | 30-100% of wasted commitment |
| 3 | 1yr RIs on core databases with 3yr+ horizon | TERM_EVAL | Upgrade to 3yr at renewal | 15-25% additional discount |
| 4 | No-upfront RIs where capital is available | PAYMENT_EVAL | Switch to All-Upfront at renewal | 10-15% additional discount |
| 5 | Standard RIs on workloads migrating to Graviton | VEHICLE_EVAL | Switch to Compute SP at renewal | Preserves discount across family migration |
| 6 | No SP coverage on Fargate + Lambda compute | COVERAGE_GAP | Add Compute SP covering all services | 20-48% on committed portion |
| 7 | Over-committed SP ($/hr too high) | UTILIZATION_GAP | Let expire; recommit at lower rate | Eliminates waste |
| 8 | Convertible RI never exchanged despite fleet change | VEHICLE_EVAL | Exchange to current instance type | Restores utilization |

### Step 8: Verify the recommendation

- **For COVERAGE_GAP:** after purchasing the RI/SP, monitor utilization
  for 14 days. If utilization > 95%, the commitment is well-sized. If
  < 85%, the fleet changed — investigate before committing more.
- **For UTILIZATION_GAP:** after selling or exchanging, verify the
  remaining RIs/SPs have improved utilization. Check Cost Explorer
  coverage to ensure the sell/exchange did not open a new coverage gap.
- **For TERM_EVAL:** validate the 3-year commitment decision by
  confirming the workload has been steady-state for 90+ days and there
  are no planned migrations or deprecations.
- **For PAYMENT_EVAL:** confirm the upfront budget is approved before
  recommending All-Upfront. Document the breakeven timeline for
  finance.
- **For VEHICLE_EVAL:** after switching to SP, verify the SP
  utilization covers the expected services (EC2, Fargate, Lambda).

### Step 9: Decide — OPTIMIZED vs FURTHER_OPTIMIZATION_AVAILABLE

- **FURTHER_OPTIMIZATION_AVAILABLE.** At least one commitment dimension
  has a gap or suboptimal configuration. Output RECOMMENDATION and
  ESTIMATED_SAVINGS.
- **OPTIMIZED.** RI/SP coverage > 90%, utilization > 95%, the right
  commitment vehicle is selected for each workload segment, terms are
  matched to workload stability, and payment options are optimized.
  No further action needed.

## Expert heuristic — "3yr Standard for the bedrock, SP for the flexible layer, on-demand for the spike"

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Configuration dependency graph

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Utilization monitoring — CloudWatch and Budgets

Set proactive alerts to catch underutilization early.

Moved verbatim to [references/commitment-analysis-commands.md](references/commitment-analysis-commands.md) - load on demand (see References below).

**Alert thresholds:**

| Metric | Warning | Critical |
|---|---|---|
| RI utilization | < 80% (investigate) | < 60% (act: sell/exchange) |
| SP utilization | < 85% (investigate) | < 70% (act: recommit lower) |
| RI coverage | < 80% (investigate) | < 60% (act: commit more) |
| SP coverage | < 80% (investigate) | < 60% (act: commit more) |
| On-demand spend ratio | > 50% of EC2 spend (investigate) | > 70% (act: commit more) |

## RI Marketplace selling

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## References

See `references/ri-sp-pricing-matrix.md` for the full pricing reference
(Standard vs Convertible RI rates, Compute vs EC2 Instance SP rates,
1yr vs 3yr, all payment options, regional notes) and
`references/commitment-analysis-commands.md` for the canonical command
script for each optimization dimension.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Mindset, layering expert heuristic, configuration dependency graph, RI Marketplace selling checklist, and 2024-2026 features, moved verbatim from SKILL.md
- [references/commitment-analysis-commands.md](references/commitment-analysis-commands.md) — extended with the Step 0 baseline-pull CLI and the CloudWatch/Budget utilization-alert setup, moved verbatim from SKILL.md

## Domain

AWS CloudOps / EC2 Compute FinOps & Commitment Management.

## AWS documentation

- **EC2 Reserved Instances** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-reserved-instances.html
- **Reserved Instances pricing** — https://aws.amazon.com/ec2/pricing/reserved-instances/pricing/
- **Savings Plans** — https://docs.aws.amazon.com/savingsplans/latest/userguide/
- **Compute Savings Plans** — https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-compute.html
- **EC2 Instance Savings Plans** — https://docs.aws.amazon.com/savingsplans/latest/userguide/ec2-instance-savings-plans.html
- **Cost Explorer RI recommendations** — https://docs.aws.amazon.com/cost-management/latest/userguide/ce-ri.html
- **RI Marketplace** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-marketplace.html
- **Convertible RI exchange** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-convertible.html
