---
description: Optimises DynamoDB table cost across seven dimensions — on-demand vs provisioned capacity mode crossover analysis (30% utilization break-even with write-heavy ratio adjustment), RCU/WCU sizing from CloudWatch ConsumedReadCapacityUnits and ConsumedWriteCapacityUnits, auto-scaling target utilization tuning (70% default vs 50-60% for headroom on bursty workloads), partition key design for even distribution (hot partition detection via CloudWatch consumed-vs-provisioned gap), GSI projection size optimization (ALL vs INCLUDE vs KEYS_ONLY, sparse index strategy), table class selection (Standard vs Standard-Infrequent Access for low-traffic tables), and TTL for data lifecycle cost reduction. DynamoDB Streams cost impact evaluated. Emits FURTHER_OPTIMIZATION_AVAILABLE, OPTIMIZED, or ALREADY_OPTIMAL per table.
nl_triggers:
  - "optimise DynamoDB cost"
  - "DynamoDB on-demand vs provisioned"
  - "DynamoDB RCU WCU sizing"
  - "DynamoDB auto-scaling target"
  - "DynamoDB hot partition"
  - "DynamoDB partition skew"
  - "DynamoDB GSI cost"
  - "DynamoDB sparse index"
  - "DynamoDB table class"
  - "DynamoDB Standard-Infrequent Access"
  - "DynamoDB TTL cost"
  - "DynamoDB Streams cost"
  - "DynamoDB adaptive capacity"
  - "DynamoDB FinOps review"
  - "reduce DynamoDB bill"
  - "DynamoDB capacity review"
  - "DynamoDB crossover analysis"
routes_to: dynamodb-capacity-optimizer
---

# /aws:optimize-dynamodb-capacity

Activate the `dynamodb-capacity-optimizer` skill and optimise DynamoDB
table cost across the seven-dimension analysis framework.

## What it does

Reads a table's configuration (`describe-table`, `describe-time-to-live`,
`describe-continuous-backups`, `describe-scaling-policies`), CloudWatch
consumed-capacity metrics (ConsumedReadCapacityUnits,
ConsumedWriteCapacityUnits, ThrottledRequests, SystemErrors over 14-30
days), and Cost Explorer DynamoDB usage breakdown — then applies the
ordered optimisation logic:

1. **Pre-flight** — data sufficiency gate. If consumed-capacity metrics
   absent or observation window < 14 days, emit NEED_MORE_INFO.
2. **Capacity mode crossover** — provisioned consumed < 30% → evaluate
   on-demand. Compute actual crossover with read/write ratio adjustment
   (write-heavy tables may stay provisioned even at <15%).
3. **RCU/WCU right-sizing** — consumed 30-60% of provisioned → reduce
   provisioned to ~140% of consumed with autoscaling headroom.
4. **Auto-scaling tuning** — target > 80% with ThrottledRequests > 0 →
   lower target to 60%. Min/max bounds: min ~p30, max ~p99 × 1.2.
5. **Partition key design** — ThrottledRequests > 0 with consumed <
   provisioned → hot partition. Redesign partition key or add suffix
   randomization.
6. **GSI optimization** — ALL projection → INCLUDE or KEYS_ONLY.
   Low-usage GSIs → evaluate dropping. Sparse index strategy for
   selective attributes.
7. **Table class** — avg consumed < 50 RCU/s and storage > 50 GB →
   Standard-Infrequent Access (60% storage savings).
8. **TTL and Streams** — high data churn without TTL → enable TTL.
   Streams with expensive Lambda consumers → evaluate necessity.
9. **Verdict** — FURTHER_OPTIMIZATION_AVAILABLE (any dimension has a
   recommendation), OPTIMIZED (applied and verified), or
   ALREADY_OPTIMAL (no change needed).

Emits a deterministic optimisation block per table:

```text
TARGET: <table-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <billing mode>, <RCU/WCU>, <GSIs>, <table class>, <TTL>, <Streams>
  Proposed: <billing mode>, <RCU/WCU>, <GSIs>, <table class>, <TTL>, <Streams>
  Confidence: <HIGH/MEDIUM/LOW>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a table configuration and ask any of:

- "should I switch to on-demand?"
- "are my RCU/WCU settings right?"
- "why am I getting throttled?"
- "is my GSI costing too much?"
- "should I enable TTL?"
- "is DynamoDB Streams worth the cost?"
- "should I use Standard-IA table class?"
- "DynamoDB FinOps review"

A bare table name + any optimise verb ("optimise this table",
"reduce DynamoDB cost") also routes here via the orchestrator.

## Inputs

- Table metadata: table name/ARN, region, BillingMode,
  ProvisionedThroughput, GlobalSecondaryIndexes (projection type, size),
  AutoScaling policies, TTL status, Streams configuration, TableClass.
- CloudWatch metrics (last 14-30 days): ConsumedReadCapacityUnits,
  ConsumedWriteCapacityUnits (avg/max/p99), ThrottledRequests,
  SystemErrors.
- Cost Explorer (optional): DynamoDB usage type breakdown.
- Workload context: read/write ratio, traffic variability (CV), latency
  SLA, data churn rate.

## Outputs

- One optimisation block per table.
- Confidence level with rationale (HIGH requires 14-30 day CloudWatch
  data).
- Estimated monthly and annual savings, with capacity + storage + GSI
  subtotals.
- Specific migration steps with CLI commands (update-table,
  register-scalable-target, put-scaling-policy, update-time-to-live).
- GSI swap plan (create new, verify, delete old) for projection changes.
- A CONFIRM gate before any state-changing CLI.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 3 Optimize specialist for DynamoDB tables).
- `/aws:optimize-aurora-cost` for Aurora cluster cost optimisation
  (sibling database optimize skill).
- `/aws:troubleshoot-dynamodb-throttling` for throttling troubleshooting
  without cost context (this skill covers throttling as part of the
  capacity optimization framework).
- `/aws:audit-dynamodb-table` for table security and configuration
  auditing (complements this cost-focused optimisation).
