# End-to-end usage scenario: ec2-reserved-capacity-optimizer

A walkthrough showing the skill optimizing a low-coverage EC2 fleet
with a coverage gap analysis and commitment recommendation. This
exercises Step 2 (COVERAGE_GAP), Step 4 (TERM_EVAL), and Step 5
(PAYMENT_EVAL).

## Input (user prompt)

> My EC2 fleet runs 50 m5.large instances 24/7 in us-east-1. Only 20
> are covered by 1-year Standard RIs (No Upfront) — coverage is 40%.
> RI utilization is 97%. The 90-day minimum count is 48 instances.
> Cost Explorer shows $3,504/month on on-demand for the uncovered 30.
> The fleet has been stable for 6 months, no migration planned.

## Skill output

```text
TARGET: EC2 fleet — m5.large, us-east-1, Linux (50 instances, 24/7)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: RI coverage is 40% (20 of 50 instances). The 90-day minimum
is 48 instances, meaning ~28 instances are committable steady-state
but running on-demand. RI utilization is 97% (well-sized existing
commitments). No migration planned, fleet stable 6 months — ideal
candidate for 3-year Standard RI.
RECOMMENDATION:
  1. COVERAGE_GAP: commit ~28 m5.large with 3-year Standard RIs (All
     Upfront) for the steady-state baseline. This raises coverage
     from 40% to ~96%.
  2. TERM_EVAL: choose 3-year over 1-year because the fleet has been
     stable for 6 months with no planned migration. 3-year Standard
     saves ~60% vs on-demand vs ~40% for 1-year.
  3. PAYMENT_EVAL: choose All Upfront over No Upfront for the 28 new
     RIs. Upfront cost is $7,784 (28 x $278). Breakeven is ~5 months.
     Additional 15% savings vs No Upfront.
  4. VEHICLE_EVAL: Standard RI is correct for this fleet because the
     instance type, family, AZ, and OS are fixed with no migration
     planned. Compute SP would give less discount (~54% vs 60%).
ESTIMATED_SAVINGS: ~$1,185/month ($14,220/year)
  - 28 instances x ($70.08 OD - $27.74 3yr Std All-Upfront) = $1,185/mo
ACTION_STEPS:
  1. Verify recommendation via Cost Explorer:
     aws ce get-reservation-purchase-recommendation \
       --service "Amazon Elastic Compute Cloud - Compute" \
       --term-in-years 3 --payment-option ALL_UPFRONT \
       --lookback-period 60 \
       --service-specification '{"EC2Specification":{"OfferingClass":"STANDARD"}}'
  2. Purchase 28 x m5.large Standard RIs (3yr, All Upfront) via
     the AWS Console or CLI:
     aws ec2 purchase-reserved-instances-offering \
       --reserved-instances-offering-id <offering-id> \
       --instance-count 28
  3. Set CloudWatch alarm for RI utilization < 80% to catch any
     fleet reduction that would waste the commitment.
  4. Monitor RI utilization for 14 days post-purchase; verify
     utilization > 90%.
```

## What the skill caught that a generic assistant misses

1. **The baseline-vs-peak distinction.** A generic assistant says "buy
   more RIs" but does not compute the committable baseline from the
   90-day minimum instance count. The skill identifies exactly 28
   instances (not all 30 on-demand) as committable, leaving 2 as
   headroom for fleet variation.

2. **The term justification.** A generic assistant says "3-year is
   cheaper" but does not validate the 90-day stability criterion. The
   skill confirms the fleet has been stable for 6 months with no
   planned migration — meeting the 90-day threshold for 3-year
   Standard RIs.

3. **The payment breakeven.** A generic assistant does not compute the
   upfront breakeven ($7,784 upfront, ~5 months to breakeven). The
   skill provides the exact upfront cost and breakeven timeline for
   finance approval.

4. **The vehicle comparison.** A generic assistant might recommend
   a Savings Plan without explaining why Standard RI is better for
   a fixed fleet. The skill compares Standard RI (60% discount) vs
   Compute SP (54%) and justifies the Standard RI choice based on the
   fleet's stability.

## Slash-command invocation

```
/aws:optimize-ec2-reserved-capacity
```

Or via the orchestrator:

```
/aws:pipeline
You: "50 m5.large fleet at 40% RI coverage, $3,504/month on-demand — optimise commitments"
```

The orchestrator emits `[Phase: Optimize | Skills routed:
ec2-reserved-capacity-optimizer]` and hands off to this skill for the
VERDICT.

## Live-account diagnostic flow (requires AWS CLI)

When the operator has AWS credentials:

```bash
# Check current RI inventory and utilization.
aws ec2 describe-reserved-instances \
  --filters Name=state,Values=active \
  --query 'ReservedInstances[*].{type:InstanceType,offering:OfferingType,duration:Duration,count:InstanceCount,start:Start}'

aws ce get-reservation-utilization \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY

# Get the purchase recommendation for the gap.
aws ce get-reservation-purchase-recommendation \
  --service "Amazon Elastic Compute Cloud - Compute" \
  --term-in-years 3 \
  --payment-option ALL_UPFRONT \
  --lookback-period 60 \
  --service-specification '{"EC2Specification":{"OfferingClass":"STANDARD"}}'

# Purchase the recommended RIs.
aws ec2 purchase-reserved-instances-offering \
  --reserved-instances-offering-id <offering-id> \
  --instance-count 28
```

The 40% coverage with 97% utilization on existing RIs confirms the
existing commitments are well-sized — the problem is under-commitment,
not over-commitment. The 90-day minimum of 48 instances gives a safe
commitment target of 46-48 RIs (48 existing + 28 new = covers the
baseline with 2-instance headroom).
