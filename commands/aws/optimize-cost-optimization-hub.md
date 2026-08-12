---
description: Optimizes AWS Cost Optimization Hub deployment and recommendation workflows with production-grade defaults — multi-account payer enrollment, AFTER_DISCOUNT savings mode, effort-level quick-win triage, Compute Optimizer integration, implementation-status tracking, and CloudWatch alerting. Emits an OPTIMIZED / FURTHER_OPTIMIZATION_AVAILABLE checklist with verification commands.
nl_triggers:
  - "cost optimization hub"
  - "cost optimization recommendation"
  - "enable cost optimization hub"
  - "right-size ec2"
  - "idle resource recommendation"
  - "ri sp coverage gap"
  - "savings estimate"
  - "effort level quick win"
  - "multi-account cost optimization"
  - "update recommendation status"
  - "compute optimizer integration"
  - "finops recommendations"
routes_to: cost-optimization-hub-optimizer
---

# /aws:optimize-cost-optimization-hub

Activate the `cost-optimization-hub-optimizer` skill and
optimize AWS Cost Optimization Hub deployment with
production-grade defaults.

## What it does

The skill walks the optimization procedure and emits an
OPTIMIZED / FURTHER_OPTIMIZATION_AVAILABLE checklist:

1. Enrollment (enable the hub)
2. Recommendation types (right-size, idle, RI/SP coverage gap)
3. Resource-level recommendations & filters
4. Savings estimate (annualized vs monthly labeling)
5. Effort level (Low / Medium / High for quick wins)
6. Multi-account via Organizations Payer
7. Integration with Compute Optimizer
8. Implementation tracking (Applied / Pending / Ignored)
9. Daily refresh cadence
10. CloudWatch alerts for recommendation counts
11. Cost allocation tag requirements
12. Recent features (RDS/Aurora right-size, ECS/Fargate)

## When to use

- You need to enable Cost Optimization Hub.
- You want to triage Low-effort quick wins.
- You are rolling out multi-account via the Organizations
  Payer.
- You need to verify Compute Optimizer is enrolled.
- You are tracking implementation status toward OPTIMIZED.
- You want CloudWatch alerts on new recommendations.
- You need to audit cost allocation tag activation.

## When NOT to use

- **AWS Cost Explorer forecasting** — use the
  ce-cost-anomaly-auditor skill.
- **AWS Budgets alerts** — use the budget skills.
- **Compute Optimizer standalone administration** — the Hub
  consumes CO findings but does not own CO's configuration.
- **Per-service optimization** (S3 lifecycle, NAT Gateway) —
  use the service-specific skills; the Hub aggregates but does
  not replace them.

## How to invoke

### Slash command

```
/aws:optimize-cost-optimization-hub
```

Then provide: payer account ID, member-account inclusion,
savings estimation mode (`AFTER_DISCOUNT` / `BEFORE_DISCOUNT`),
look-back period, quick-win threshold, tags.

### Natural language

Any of these routes to the same skill:

- "enable cost optimization hub across my org"
- "list low-effort cost optimization quick wins"
- "verify compute optimizer is feeding the hub"
- "track cost optimization recommendation status"
- "set up cloudwatch alerts for new cost optimization recommendations"

### CLI routing

```bash
node cli/bin/cli.js route "enable cost optimization hub"
```

## Pipeline integration

This skill operates in **Phase 2 (Optimize)** of the CloudOps
pipeline, in the **FinOps** family. The orchestrator routes to
it when the user wants to enable, triage, or track Cost
Optimization Hub recommendations. The output checklist feeds
into downstream FinOps pipelines and budget skills.

## Example

```
You: /aws:optimize-cost-optimization-hub

     Enable the Hub for org payer 123456789012
     with 14 member accounts. Use AFTER_DISCOUNT,
     14-day look-back. List Low-effort quick wins
     above $50/month. Compute Optimizer is ACTIVE.

Skill:
  COST_OPTIMIZATION_HUB: ACTIVE (Multi — Payer 123456789012,
                                   14 members linked)
  VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
  CHECKLIST:
    [✓] Enrollment status: ACTIVE
    [✓] Compute Optimizer enrolled: ACTIVE
    [✓] Savings estimation mode: AFTER_DISCOUNT
    [✗] Quick-win queue (Low effort, savings > $50/mo):
         23 recommendations, $1,910/mo ($22,920 annualized)
  VERIFICATION_COMMANDS:
    aws cost-optimization-hub get-enrollment-status
    aws cost-optimization-hub get-recommendations --filter '{"effort":"Low"}' --output table
    aws compute-optimizer get-enrollment-status
```

## References

- Skill definition: `skills/cost-optimization-hub-optimizer/SKILL.md`
- Savings and effort guide: `skills/cost-optimization-hub-optimizer/references/savings-and-effort.md`
- Multi-account and alerts guide: `skills/cost-optimization-hub-optimizer/references/multi-account-and-alerts.md`
- Eval suite: `skills/cost-optimization-hub-optimizer/evals/evals.json`
