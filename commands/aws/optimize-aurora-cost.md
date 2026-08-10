---
description: Optimises Amazon Aurora cluster costs across seven dimensions — instance-class right-sizing (writer vs readers independently), Aurora Serverless v2 ACU min/max tuning, Aurora I/O-Optimized storage tier (40-60% I/O savings for I/O-heavy workloads), storage and backtrack cleanup, Global Database DR-region replica right-sizing, Performance Insights waste-driving SQL detection, and Reserved Instance vs On-Demand evaluation. Emits OPTIMIZED, OPPORTUNITY_FOUND, or ALREADY_OPTIMAL per cluster with per-dimension savings and staged one-dimension-per-window migration.
nl_triggers:
  - "optimise Aurora cost"
  - "right-size Aurora instance"
  - "Aurora Serverless v2 ACU"
  - "Aurora I/O-Optimized"
  - "Aurora Standard vs I/O-Optimized"
  - "Aurora Reserved Instance"
  - "Aurora Global Database cost"
  - "Aurora backtrack cost"
  - "Aurora vs RDS cost"
  - "Aurora Limitless Database cost"
  - "Aurora reader replica sizing"
  - "Aurora storage optimization"
  - "Aurora Performance Insights waste"
  - "Aurora idle ACU"
  - "Aurora FinOps review"
  - "reduce Aurora bill"
  - "Aurora I/O charges too high"
  - "Aurora downsize recommendation"
  - "Aurora writer vs reader instance class"
routes_to: aurora-cost-optimizer
---

# /aws:optimize-aurora-cost

Activate the `aurora-cost-optimizer` skill and optimise Amazon Aurora
cluster cost across the seven dimensions.

## What it does

Reads cluster configuration (`describe-db-clusters`,
`describe-db-instances`, `describe-global-clusters`,
`describe-reserved-db-instances`, `describe-db-cluster-backtracks`),
Cost Explorer Aurora USAGE_TYPE line items
(`Aurora:InstanceUsage`, `Aurora:ServerlessUsage`,
`Aurora:StorageUsage`, `Aurora:IOUsage`, `Aurora:BackupUsage`,
`Aurora:ReplicaUsage`), CloudWatch CPUUtilization, and Performance
Insights top-SQL DBLoad — then applies the ordered optimisation logic:

1. **Pre-flight** — data sufficiency gate. If Cost Explorer access
   denied, emits NEED_MORE_INFO for the cost-quantification dimension.
2. **Cost classification** — identify top USAGE_TYPEs (I/O, Serverless,
   compute, storage, Global DB, backtrack).
3. **Instance right-sizing** — writer and reader CPU profiles drive
   independent class changes (writers rarely match readers).
4. **Serverless v2 ACU tuning** — drop MinCapacity to the SLA floor
   (saves `$0.12 × (Min−floor) × 730` per month).
5. **I/O-Optimized tier** — switch when I/O cost > storage price
   differential (break-even: 0.4M I/O per GB of storage per month).
6. **Storage / snapshot / backtrack cleanup** — 30/60/90-day retention;
   backtrack window reduction.
7. **Global Database DR** — right-size DR-region replicas independently.
8. **Performance Insights** — top-SQL > 30% of DBLoad drives a DBA
   ticket that, once fixed, may enable a further writer downsize.
9. **Reserved Instance** — 1-yr no-upfront RI on writer + primary
   readers for steady-state clusters (40% off On-Demand).
10. **Verdict** — OPPORTUNITY_FOUND, OPTIMIZED (post-remediation), or
    ALREADY_OPTIMAL.

Emits a deterministic optimisation block per cluster:

```text
TARGET: <cluster-identifier>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <instance-class, ACU, storage tier, I/O volume, pricing, ...>
  Proposed: <per-dimension list of changes>
  Confidence: <HIGH/MEDIUM/LOW>
ESTIMATED_SAVINGS:
  Monthly (right-sizing): $<amount>
  Monthly (ACU tuning): $<amount>
  Monthly (I/O-Optimized tier): $<amount>
  Monthly (storage/snapshot): $<amount>
  Monthly (Global DB): $<amount>
  Monthly (backtrack): $<amount>
  Monthly (RI/commit): $<amount>
  Annual total: $<amount>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a cluster configuration, billing line items, or Performance
Insights summary and ask any of:

- "why is our Aurora bill so high?"
- "should we switch to Aurora I/O-Optimized?"
- "is Aurora Serverless v2 ACU min too high?"
- "should we buy an Aurora Reserved Instance?"
- "are readers oversized relative to the writer?"
- "is backtrack storage costing us?"
- "does Global Database DR replica need a smaller instance?"
- "Aurora FinOps review"

A bare cluster identifier + any optimisation verb also routes here via
the orchestrator.

## Inputs

- **Cluster configuration:** DBClusterIdentifier, engine, instance
  classes (writer + readers), ServerlessV2ScalingConfiguration (min/max
  ACU), storage type, Multi-AZ, Global DB membership, backtrack config.
- **Cost Explorer:** 30-day USAGE_TYPE breakdown for Amazon Aurora
  service (InstanceUsage, ServerlessUsage, StorageUsage, IOUsage,
  BackupUsage, ReplicaUsage).
- **CloudWatch metrics:** CPUUtilization (avg / max) per instance over
  14-30 days; FreeableMemory; DatabaseConnections.
- **Performance Insights:** top-SQL DBLoad (avg active sessions by
  `db.sql` dimension).
- **Reserved Instances:** current RI inventory (offering class,
  duration, instance class, count).
- **Optional:** workload context (OLTP vs analytics, latency SLA,
  reader fan-out, DR requirements).

## Outputs

- One optimisation block per cluster.
- Per-dimension confidence with rationale.
- Per-dimension estimated monthly savings and annual total.
- Staged one-dimension-per-window migration plan with CLI commands.
- Rollback path (cluster snapshot before any change).
- A CONFIRM gate before any state-changing CLI.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 3 Optimize specialist for Amazon Aurora clusters).
- `/aws:optimize-rds-cost` for RDS for MySQL/PostgreSQL/Oracle/SQL
  Server cost optimisation (this skill is Aurora-specific).
- `/aws:operate-aurora-failover` for failover operations on the same
  cluster (cost optimisation is independent of failover).
- `/aws:audit-rds-instance` for configuration posture audits on Aurora
  instances (security exposure, encryption, deletion protection).
