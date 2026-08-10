---
description: Optimize EKS cluster costs — right-sizes managed node groups, evaluates Fargate vs EC2, assesses Spot node groups, compares Cluster Autoscaler vs Karpenter, finds bin-packing waste (requests vs limits), and layers pricing-model optimization with monthly savings estimates.
nl_triggers:
  - "optimize EKS cluster cost"
  - "right-size EKS node group"
  - "Fargate vs EC2 nodes"
  - "EKS Spot Instance node group"
  - "Karpenter vs Cluster Autoscaler"
  - "Karpenter consolidation savings"
  - "EKS bin-packing optimization"
  - "Kubernetes requests vs limits"
  - "EKS Compute Savings Plan"
  - "EKS FinOps savings"
  - "reduce EKS node spend"
  - "EKS Graviton node group"
  - "EKS Auto Mode cost"
  - "EKS node group downsize"
  - "Kubernetes cost optimization"
  - "EKS node right-sizing"
routes_to: eks-cost-optimizer
---

# /aws:optimize-eks-cost

Activate the `eks-cost-optimizer` skill and optimize EKS cluster costs
using the layered analysis framework.

## What it does

Reads a node group's utilization data (14-30 day Container Insights
metrics, kubectl top, node group configuration) plus optional bin-packing
data, then applies the ordered optimization logic:

1. **Pre-flight** — data sufficiency gate. If Container Insights metrics
   are absent, emits NEED_MORE_INFO (enable Container Insights, wait 14
   days).
2. **Bin-packing analysis** — requests-to-usage ratio. If ratio > 2x,
   fix requests first (VPA or manual tuning) before node right-sizing.
3. **Node group right-sizing** — CPU < 30% + Memory < 50% → downsize
   instance type or reduce desired count.
4. **Fargate vs EC2 evaluation** — breakeven calculation based on pod
   density, DaemonSet requirements, and workload pattern.
5. **Spot node group evaluation** — readiness checklist (PDB, NTH,
   multi-AZ, no stateful workloads). Up to 90% savings.
6. **Karpenter vs Cluster Autoscaler** — consolidation savings estimate
   (20-40% over Cluster Autoscaler).
7. **Pricing model optimization** — Compute Savings Plan for the EC2
   node baseline.
8. **Impact estimation** — monthly + annual savings per layer.
9. **Verdict** — OPPORTUNITY_FOUND (any dimension has a recommendation),
   OPTIMIZED (changes applied and verified), or ALREADY_OPTIMAL (no
   change recommended).

Emits a deterministic optimization block per node group or cluster:

```text
TARGET: <cluster-name/node-group-name>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <recommendation and supporting data>
RECOMMENDATION:
  Current: <instance-type x N nodes> at <pricing-model>
  Proposed: <instance-type x N nodes | Fargate | Spot> at <pricing-model>
  Compute model: <EC2 On-Demand | EC2 Spot | Fargate | mixed>
  Autoscaler: <Cluster Autoscaler | Karpenter | EKS Auto Mode>
  Bin-packing action: <reduce requests | VPA recommendation | none>
  Graviton: <yes/no/N/A>
  Confidence: <HIGH/MEDIUM/LOW>
ESTIMATED_SAVINGS:
  Monthly (right-size + bin-pack): $<amount>
  Monthly (compute model): $<amount>
  Monthly (pricing model): $<amount>
  Annual total: $<amount>
MIGRATION_STEPS:
  1. <action with CLI or kubectl command>
  2. <verification step>
```

## When to invoke

Paste a node group or cluster configuration plus utilization data and ask
any of:

- "right-size this EKS node group"
- "should I use Fargate or EC2 for this workload?"
- "can I move this workload to Spot?"
- "would Karpenter save me money?"
- "EKS fleet cost optimization review"
- "are my pod requests too high?"
- "EKS FinOps savings estimate"

A bare cluster/node-group name + any optimization verb also routes here
via the orchestrator.

## Inputs

- Node group metadata: cluster name, node group name, instance type(s),
  desired/min/max size, capacity type (ON_DEMAND/SPOT), autoscaler.
- Utilization metrics (14-30 days):
  - `node_cpu_utilization` (Container Insights)
  - `node_memory_utilization` (Container Insights)
  - `pod_cpu_utilization` (Container Insights)
  - `kubectl top nodes` / `kubectl describe node` (in-cluster signals)
- Bin-packing data (optional but recommended for downsizing):
  - Pod requests vs actual usage ratio
  - Pod density per node
  - VPA recommendations if available
- Optional: Fargate profile info, Spot readiness (PDB, NTH status),
  Karpenter/Cluster Autoscaler version, workload runtime info (for
  Graviton compatibility).

## Outputs

- One optimization block per node group or cluster.
- Confidence level with rationale.
- Estimated monthly and annual savings, broken down by optimization layer
  (right-size, bin-packing, Fargate/EC2, Spot, Karpenter, pricing model).
- Specific migration steps with CLI and kubectl commands.
- Rollback path (gradual cordon-drain) for production changes.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for EKS compute cost).
- `/aws:optimize-ec2-rightsizing` for EC2 instances outside EKS (standalone
  EC2 fleet right-sizing).
- `/aws:audit-eks-cluster` for the security/compliance posture of the EKS
  cluster before/after optimization.
