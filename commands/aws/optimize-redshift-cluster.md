---
description: Optimise Amazon Redshift cluster cost and performance — RA3 vs DC2 node-type selection, right-sizing via CloudWatch CPUUtilization and QueryQueueLength, workload management (WLM queues, Short Query Acceleration, Concurrency Scaling), storage optimisation (columnar compression, VACUUM, ANALYZE), pricing model (Reserved Nodes 1yr/3yr), Redshift Serverless (RPU base capacity), data sharing, materialized views, and Redshift ML.
nl_triggers:
  - "optimise Redshift cost"
  - "right-size Redshift cluster"
  - "RA3 vs DC2"
  - "Redshift Serverless migration"
  - "Redshift WLM tuning"
  - "Redshift Concurrency Scaling"
  - "Short Query Acceleration"
  - "Redshift Reserved Nodes"
  - "Redshift data sharing"
  - "Redshift materialized views"
  - "Redshift ML AUTO ON"
  - "Redshift columnar compression"
  - "VACUUM ANALYZE Redshift"
  - "Redshift data lake export"
  - "Redshift FinOps review"
  - "Redshift cluster optimization"
routes_to: redshift-cluster-optimizer
---

# /aws:optimize-redshift-cluster

Activate the `redshift-cluster-optimizer` skill and generate a cost and
performance optimisation plan for an Amazon Redshift cluster with
deterministic pre-checks, savings estimates, and the CONFIRM gate.

## What it does

Reads a cluster configuration plus CloudWatch metrics and applies the
priority-ordered optimisation dimension sequence:

1. Pre-flight cluster metadata gate — short-circuit `paused`/`modifying`
   states, Serverless vs provisioned detection, data sharing dependencies.
2. Node-type selection — RA3 managed storage vs DC2 local storage based
   on storage utilisation and compute patterns.
3. Right-sizing — CPUUtilization + QueryQueueLength analysis to determine
   node node count and size.
4. Pricing model — On-Demand vs Reserved Nodes (1yr/3yr) for provisioned;
   RPU base capacity evaluation for Serverless.
5. Workload management — WLM queue tuning, Short Query Acceleration,
   Concurrency Scaling cost-benefit analysis.
6. Storage optimisation — columnar compression (AZ64, Zstandard), VACUUM
   DELETE, ANALYZE, data lifecycle.
7. Advanced features — materialized views, Redshift ML, data sharing,
   data lake export.
8. Idle cluster detection — DatabaseConnections = 0 for 7+ days.

Emits a deterministic VERDICT per cluster:

```text
TARGET: <cluster-identifier or workgroup-name>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <recommendation and supporting data>
RECOMMENDATION:
  Current: <node-type> x <node-count> at <pricing-model>
  Proposed: <node-type> x <node-count> at <pricing-model>
  Dimensions: <applicable dimensions>
  Confidence: <HIGH/MEDIUM/LOW>
ESTIMATED_SAVINGS:
  Monthly (<dimension>): $<amount>
  Annual total: $<amount>
MIGRATION_STEPS:
  1. <CLI command>
  2. <verification step>
CONFIRM: <gate prompt>
```

## When to invoke

Paste a cluster configuration plus CloudWatch metrics, or just describe
the scenario and ask any of:

- "optimise our Redshift cluster cost"
- "should we move from DC2 to RA3?"
- "right-size our Redshift cluster"
- "is Redshift Serverless cheaper for our workload?"
- "should we enable Concurrency Scaling?"
- "how do we tune Redshift WLM queues?"
- "should we buy Reserved Nodes for Redshift?"

A bare cluster-id + any optimisation verb also routes here via the
orchestrator.

## Inputs

- Cluster configuration (`describe-clusters` JSON): node type, node
  count, status, storage, WLM config, data sharing state.
- CloudWatch metrics: CPUUtilization, QueryQueueLength,
  DatabaseConnections, ConcurrencyScalingClustersActive (30-day window).
- Pricing context: On-Demand, existing Reserved Nodes, Serverless RPU
  settings.
- Storage details: managed storage usage, compression status, VACUUM/
  ANALYZE history.

## Outputs

- One VERDICT block per cluster.
- ESTIMATED_SAVINGS with per-dimension arithmetic formulas.
- MIGRATION_STEPS with exact CLI commands.
- CONFIRM gate before any state-changing operation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for Redshift analytics workloads).
- `/aws:audit-redshift-cluster` for the security/compliance posture of
  the Redshift cluster before optimisation.
- `/aws:optimize-athena-query` for S3-based query cost optimisation
  (complement to Redshift for data lake workloads).
