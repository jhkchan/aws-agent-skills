# Advanced Patterns (load on demand) — Compute Optimizer Findings Auditor

Expert edge-case catalog, the deep Compute Optimizer internals reference, and 2024-2026 feature changes, moved verbatim from SKILL.md.


---

## Expert edge cases — non-obvious Compute Optimizer behaviors (moved from SKILL.md)

These behaviors change classification if ignored:

- **Memory inference without CWAgent.** Compute Optimizer cannot see actual
  memory usage unless the CloudWatch Agent is installed. Without it, the
  Memory metric is absent from `utilizationMetrics` and memory utilization is
  inferred from the instance type's specs. An `Overprovisioned` finding based
  on CPU-only data may be a false positive — the instance could be
  memory-bound. This is the #1 source of unreliable findings.

- **performanceRisk scale is 1-5, not 0-1.** Each recommendation option
  includes a `performanceRisk` integer (1 = very safe, 5 = very risky). The
  cheapest option often carries the highest risk. Risk 1-2 is safe to act on;
  Risk 3 is acceptable with monitoring; Risk 4-5 requires load testing before
  acting. Treat Risk ≥ 4 as LOW confidence (Step 3).

- **30-hour continuous data requirement.** Compute Optimizer needs at least
  30 hours of continuous utilization data to produce a finding. A frequently
  stopped/started instance may not accumulate enough continuous data,
  producing no finding or a misleading one from partial data. Check the
  number of utilization metric data points as a proxy for data completeness.

- **Lambda memory increase can REDUCE total cost.** For Lambda functions,
  increasing memory also increases CPU allocation, which can reduce
  execution time. Since Lambda bills on `memory × duration`, a faster
  function may cost LESS even with more memory. An `Underprovisioned` Lambda
  finding that recommends more memory may show a negative savingsOpportunity
  (cost increase on paper) but actually reduce real cost through faster
  execution. Always cross-reference `projectedUtilizationMetrics` with the
  function's billed duration.

- **gp2 → gp3 EBS recommendations are price-driven, not utilization-driven.**
  Compute Optimizer frequently recommends migrating `gp2` volumes to `gp3`
  because gp3 has a lower baseline price ($0.08/GB vs $0.10/GB) — not because
  the volume is misconfigured. A gp2 volume at 80% IOPS utilization may still
  get an `Overprovisioned` finding simply because gp3 is cheaper. Treat gp2
  → gp3 recommendations as cost optimizations, not performance issues.

- **ASG recommendations are launch-template level.** Changing an Auto Scaling
  Group recommendation requires updating the launch template AND rolling
  existing instances — this is a higher-effort change than a standalone
  instance right-size. Old instances continue running on the old type until
  terminated and replaced. Flag ASG findings as higher-effort remediation.

- **Savings opportunity can be negligible.** Even with an `Overprovisioned`
  finding, the `estimatedMonthlySavings` may be $0 or near-zero (e.g.,
  t3.nano → t3.micro saves pennies). Do not treat all `Overprovisioned`
  findings as equally urgent. Use savings magnitude to prioritise.

- **External metrics integration raises confidence.** Compute Optimizer
  supports external metrics (Datadog, Dynatrace, Instana) via the AWS
  Marketplace. When external metrics are configured, findings include richer
  data (application-level metrics, not just infrastructure). A finding with
  external metrics data is HIGHER confidence than one with CloudWatch-only
  data.

- **Enhanced infrastructure metrics for EC2 bare-metal / metal instance
  types.** Some instance types (`.metal`, certain 7th-gen types) require
  enhanced infrastructure metrics enrollment to produce full findings.
  Without it, these instances may show no finding despite being
  overprovisioned.

- **Compute Optimizer does not analyse Spot Instance pricing.** A Spot
  Instance with an `Overprovisioned` finding still represents waste, but the
  savings opportunity assumes On-Demand pricing. The actual savings from
  right-sizing a Spot Instance are smaller because Spot is already
  discounted up to 90%.

- **Finding reasons drive remediation path.** `CPUOverprovisioned` vs
  `NetworkBandwidthOverprovisioned` lead to different remediation. CPU-
  based findings are safe to right-size by reducing vCPU. Network-based
  findings may need a different instance family (e.g., from `m5` to `t3`
  with burst networking) rather than simply a smaller size. Always extract
  `findingReasons` and cite the specific reason in remediation.

- **ECS/Fargate recommendations require separate enrollment.** ECS service
  recommendations on Fargate need the Compute Optimizer ECS enrollment
  (distinct from the base EC2/EBS/Lambda enrollment). An account enrolled
  for EC2 may not be enrolled for ECS — check before expecting ECS findings.

- **Recommendation options are ranked by savings, not by safety.** The first
  recommendation option (index 0) is the cheapest, not the safest. Always
  check `performanceRisk` on each option. The safest option may be at index
  1 or 2 with slightly lower savings.

## Deep reference: Compute Optimizer internals (moved from SKILL.md)

### Analysis window and data sources

Compute Optimizer analyses the trailing **30 days** of CloudWatch metrics.
The minimum data threshold is **30 hours of continuous** utilization within
that window. Resources that do not accumulate 30 hours (frequently stopped
instances, rarely invoked Lambda functions) receive no finding.

For EC2, the data sources are:
- **CPU** — always available from CloudWatch (`AWS/EC2` namespace,
  `CPUUtilization`).
- **Memory** — only available when CloudWatch Agent is installed
  (`CWAgent` namespace, `mem_used_percent`). Without CWAgent, Memory is
  inferred from instance type specifications.
- **Network** — always available (`NetworkIn`, `NetworkOut`).
- **Disk** — available for instance-store volumes (`DiskReadOps`,
  `DiskWriteOps`). EBS-attached volumes are analysed separately via the EBS
  recommendations API.

### Recommendation option ranking

Recommendation options are ranked by `savingsOpportunity`
(highest savings first), NOT by safety. The `performanceRisk` field (1-5)
is the safety indicator — it is independent of ranking. Always evaluate
both fields: an option with high savings but performanceRisk 5 is not
actionable.

### Finding refresh cycle

Compute Optimizer refreshes findings approximately every **24 hours**. The
`lastRefreshTimestamp` on each finding indicates when it was last
recomputed. A finding with a stale timestamp (> 30 days) may indicate:
(1) the resource was stopped or terminated, (2) Compute Optimizer lost
access to CloudWatch data, or (3) enrollment was paused. Always verify
resource state before acting on a stale finding.

### EBS volume type migration matrix

| From | To | Performance impact | Cost impact |
|---|---|---|---|
| gp2 | gp3 | Baseline 3,000 IOPS / 125 MiB/s (vs gp2's size-scaled IOPS). Purchase provisioned IOPS to match. | Cheaper per GB; may need provisioned IOPS for parity. |
| io1 | gp3 | gp3 caps at 16,000 IOPS; io1 supports up to 64,000. High-IOPS workloads may lose performance. | Significantly cheaper. |
| st1 | gp3 | gp3 is SSD (random I/O); st1 is HDD (sequential). Random-I/O workloads improve, sequential may not. | More expensive per GB but better random I/O. |

### Lambda memory-cost relationship

Lambda allocates CPU proportional to memory (approximately 1 vCPU per
1,769 MB). Increasing memory increases CPU, which can reduce duration. The
optimal memory setting minimises `memory × duration` (total cost). Compute
Optimizer's Lambda recommendations model this trade-off, but always verify
with `aws lambda get-function` and CloudWatch Duration metrics
post-change.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **EBS volume recommendations (2024):** Compute Optimizer now provides right-sizing recommendations for EBS volumes (gp2 to gp3, io1 to io2, size adjustments). Auditors should include EBS findings in the cost-optimization review alongside EC2 and Lambda.
- **Enhanced finding filters and trade-off analysis (2024-2025):** Compute Optimizer now supports filtering by workload metadata and trade-off analysis between cost and performance risk. Auditors should verify that the finding confidence and performance-risk thresholds are appropriate before acting on recommendations.
- **ECS service recommendations (2024):** Compute Optimizer now provides right-sizing recommendations for ECS services (CPU and memory task-size optimization). Auditors should include ECS task-definition findings in the optimization review.
