# Savings Estimation and Effort Level — Cost Optimization Hub

Deep reference on the Hub's savings-estimation modes
(`AFTER_DISCOUNT` vs `BEFORE_DISCOUNT`), the annualization
convention used by the console, the look-back period setting,
the effort-level taxonomy (Low / Medium / High), quick-win
triage sequencing, and common reporting pitfalls. Loaded on
demand by the skill — kept out of the main SKILL.md body so
the optimization procedure stays scannable.

## Savings estimation modes

The Hub computes savings using one of two modes, configured via
`update-preferences --savings-estimation-mode`:

| Mode | What it factors in | When to use |
|---|---|---|
| `AFTER_DISCOUNT` | Net of RI/SP discounts (savings = On-Demand equivalent minus what you actually pay today) | Orgs with RIs/SPs — accurate net savings |
| `BEFORE_DISCOUNT` | On-Demand rates only (savings = list-price delta) | Orgs with no RIs/SPs, or for gross potential reporting |

```bash
aws cost-optimization-hub update-preferences \
  --savings-estimation-mode AFTER_DISCOUNT \
  --look-back-period-in-days 14
```

### The annualization convention

The Hub API returns `estimatedMonthlySavings` (USD/month). The
AWS console and the recommendation exports annualize this to
USD/year (`estimatedMonthlySavings * 12`) for display.

```text
Period        Source                    Example
────────────  ──────────────────────    ──────────
Monthly       API field directly        $4,820 / month
Annualized    Console / exports         $57,840 / year
Rate          estimatedSavingsRate      0.23 (23%)
```

**Critical:** when reporting, always label the period. A
common error is quoting the annualized number as monthly (or
vice versa). Pick one period per chart and label the axis.

### Look-back period

The Hub analyzes the trailing N days of utilization to produce
recommendations. Configure via `--look-back-period-in-days`.

| Look-back | Best for |
|---|---|
| 7 days | Volatile workloads with recent changes (faster signal, noisier) |
| 14 days (default) | Balanced — captures two weekly cycles |
| 30 days | Stable workloads, monthly seasonality (smoother, slower to react) |

For most production workloads, 14 days is correct. Use 7 days
for fast-moving workloads (e.g., Black Friday prep); use 30
days for steady-state services.

## Effort-level taxonomy

Every Hub recommendation carries an `effort` field with one of
three values. The field is canonical — do not second-guess it.

| Effort | Typical actions | Time-to-apply | Downtime | Risk |
|---|---|---|---|---|
| Low | EBS gp2 → gp3, S3 lifecycle, EIP release, terminate idle | <1 day | None | Minimal |
| Medium | EC2 instance type change, RDS right-size, Lambda memory tuning | 1-5 days | Brief (stop/start) | Low with pre-checks |
| High | Aurora cluster migrate, ECS restructure, ASG launch-template rev | 5+ days | Multi-step rollout | Medium — needs canary |

### Quick-win triage recipe

```text
Step 1: Pull all Low-effort recommendations
  aws cost-optimization-hub get-recommendations \
    --filter '{"effort":"Low"}' \
    --query 'items[*].{Resource:resourceArn,Savings:estimatedMonthlySavings,Action:action}' \
    --output table

Step 2: Sort by estimatedMonthlySavings descending
Step 3: Apply the top N (where N matches engineering capacity)
Step 4: Mark each APPLIED via update-recommendation-status
Step 5: Re-pull the next refresh (~24h) to confirm savings
        materialized in Cost Explorer
```

### Why effort level beats raw savings sort

A naive savings-sort puts a $5,000/month High-effort Aurora
migration ahead of a $1,500/month Low-effort EBS migration.
The Aurora migration takes weeks and consumes senior
engineering time; the EBS migration completes in an afternoon.
Quick wins compound: by the time the Aurora migration ships,
the EBS savings have been live for a month.

**Rule of thumb:** the first batch (Low effort, high savings)
typically delivers 60-80% of the total available savings for
<30% of the total effort.

## Per-recommendation savings anatomy

Each recommendation carries several savings-related fields:

```text
estimatedMonthlySavings     USD/month at current usage
estimatedSavingsRate        ratio (0..1) — savings as % of current spend
savingsEstimationMode       AFTER_DISCOUNT | BEFORE_DISCOUNT
```

The `estimatedSavingsRate` is useful for benchmarking: a 23%
rate is "save 23% of this resource's spend." Use it to compare
recommendations across services of different absolute cost.

### Recommendation source attribution

```bash
aws cost-optimization-hub get-recommendations \
  --query 'items[*].{Resource:resourceArn,Action:action,
    Source:recommendationSourceType,Savings:estimatedMonthlySavings}' \
  --output table
```

`recommendationSourceType` identifies the upstream service
(Compute Optimizer for EC2 / ASG / Lambda, native for EBS /
ECS / RDS / S3).

## Common reporting pitfalls

### Pitfall 1: mixing monthly and annualized in the same chart

Pick one period per report. Default for executive summaries:
annualized (yearly budget planning). Default for engineering
burn-down: monthly (sprint-level tracking).

### Pitfall 2: quoting BEFORE_DISCOUNT savings as net savings

`BEFORE_DISCOUNT` overstates savings for orgs with RIs/SPs. If
you have an RI covering 80% of an instance, the gross savings
of right-sizing that instance is much higher than the net
savings (because you are already paying the RI rate). Use
`AFTER_DISCOUNT` for net savings.

### Pitfall 3: ignoring the look-back window when comparing periods

A 7-day look-back produces different numbers than a 30-day
look-back for the same set of resources. When reporting
month-over-month, hold the look-back constant.

### Pitfall 4: forgetting that effort is per-recommendation, not per-resource

A single resource may have multiple recommendations (e.g., an
EC2 instance with both a right-size and a stop recommendation).
Each carries its own effort rating.

## Terraform example: configure preferences

```hcl
resource "aws_costoptimizationhub_enrollment_status" "this" {
  include_member_accounts = true
}

resource "aws_costoptimizationhub_preferences" "this" {
  savings_estimation_mode  = "AFTER_DISCOUNT"
  look_back_period_in_days = 14

  depends_on = [aws_costoptimizationhub_enrollment_status.this]
}
```

Terraform does not have native resources for individual
recommendation status updates; use a `null_resource` with
`local-exec` for batch status updates against the
`update-recommendation-status` API.
