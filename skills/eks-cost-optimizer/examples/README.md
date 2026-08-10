# Example usage: eks-cost-optimizer

A walkthrough showing the skill optimizing an overprovisioned EKS managed
node group, demonstrating the layered optimization framework (bin-packing
check, node group right-sizing, Karpenter evaluation, pricing-model
layering), and the staged migration with a CONFIRM gate.

## Input (user prompt)

> Our EKS production cluster has a managed node group that looks expensive.
> 4 x m5.2xlarge nodes running 8 pods each. CPU is around 12% average.
> Help me right-size it and capture the savings.

```text
Cluster: prod-cluster
Region: us-east-1
Node group: prod-general-purpose
Instance type: m5.2xlarge
Desired size: 4 nodes (min 3, max 10)
Capacity type: ON_DEMAND
Autoscaler: Cluster Autoscaler

Utilization (Container Insights, last 30 days):
  - node_cpu_utilization: avg=12%, max=20%
  - node_memory_utilization: avg=25%, max=35%
  - Average pods per node: 8 (allocatable capacity ~28 pods)

Bin-packing analysis (kubectl top):
  - Pod requests/usage ratio: 1.4x (healthy)
  - CPU requests per pod: 1000m, actual usage: 700m avg

Pricing: On-Demand (no Savings Plan)
Workload: mixed microservices (Java 17, Python, Go), multi-arch
Docker images available (arm64 manifest entries present).
```

## Skill output

```text
TARGET: prod-cluster/prod-general-purpose
VERDICT: OPPORTUNITY_FOUND
REASON: m5.2xlarge node group (4 nodes) at 12% CPU / 25% Memory over 30 days
  is overprovisioned. Bin-packing is healthy (1.4x ratio). Downsize to
  m7i.xlarge (Step 5), migrate to Karpenter for consolidation (Step 8),
  and commit a 3-year Compute Savings Plan on the reduced baseline (Step 9).
RECOMMENDATION:
  Current: m5.2xlarge x 4 nodes at On-Demand via Cluster Autoscaler
  Proposed: m7i.xlarge x 2 nodes at 3-year Compute Savings Plan via Karpenter
  Compute model: EC2 On-Demand → EC2 On-Demand (Karpenter-managed)
  Autoscaler: Cluster Autoscaler → Karpenter (consolidation enabled)
  Bin-packing action: none (ratio 1.4x is healthy)
  Graviton: consider after multi-arch build verification
  Confidence: HIGH — Container Insights reporting, healthy bin-packing,
    requests/usage ratio 1.4x.
ESTIMATED_SAVINGS:
  Monthly (right-size + bin-pack): $896.64  (m5.2xlarge $0.384/h x 4 →
    m7i.xlarge $0.192/h x 2; 730h x $1.152 delta)
  Monthly (Karpenter consolidation): $280.32  (estimated 30% further
    node reduction from consolidation vs Cluster Autoscaler)
  Monthly (pricing model): $112.22  (50% off m7i.xlarge On-Demand via
    3-yr Compute Savings Plan on 2 nodes)
  Annual total: $15,447.36
  Assumptions: 730h/month, us-east-1 pricing, Karpenter consolidation
    estimate is conservative (20-40% range).
MIGRATION_STEPS:
  1. Install Karpenter and create a NodePool with m7i.xlarge:
     helm install karpenter oci://public.ecr.aws/karpenter/karpenter \
       -n karpenter --create-namespace
     kubectl apply -f karpenter-nodepool.yaml
  2. Cordon the old node group gradually (one node at a time):
     kubectl cordon <node> && kubectl drain <node> --ignore-daemonsets
  3. Verify pods reschedule onto Karpenter nodes:
     kubectl get pods -o wide
  4. Delete the old node group once all pods are on Karpenter nodes:
     aws eks delete-nodegroup --cluster-name prod-cluster \
       --nodegroup-name prod-general-purpose
  5. Purchase a 3-year Compute Savings Plan for the m7i.xlarge baseline:
     aws savingsplans create-savings-plan --savings-plan-offering-id <id> \
       --commitment "<hourly-amount>"
CONFIRM: Before installing Karpenter and cordoning nodes, emit and await:
  "CONFIRM: About to install Karpenter on prod-cluster and cordon the
   prod-general-purpose node group. Proceed? (yes/no)"
  Do NOT execute until the operator confirms.
```

## What the skill caught that a generic assistant misses

1. **Bin-packing check before node right-sizing.** A generic assistant
   jumps straight to "downsize the nodes." The skill first checks the
   requests/usage ratio (1.4x — healthy) to confirm the low utilization is
   genuine, not an artifact of inflated requests masking real usage.

2. **Karpenter consolidation savings.** The skill identifies that moving
   from Cluster Autoscaler to Karpenter adds 20-40% savings on top of the
   instance-type downsize. A generic assistant recommends only the instance
   change.

3. **Pricing-model layering.** The skill stacks three savings layers:
   right-size (m5.2xlarge x4 → m7i.xlarge x2), Karpenter consolidation,
   and a 3-year Compute Savings Plan. A generic assistant captures only
   the rightsize.

4. **Gradual cordon safety.** The skill specifies one-node-at-a-time
   cordon-drain with verification between each step. A generic assistant
   recommends deleting the node group or scaling to 0 without a safe
   cutover plan.

5. **Savings Plan scope.** The skill notes that the Savings Plan covers
   EC2 nodes only (not Fargate) and commits to the reduced baseline after
   right-sizing — not the original spend.

## Slash-command invocation

```
/aws:optimize-eks-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our EKS production cluster for the Q3 FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: eks-cost-optimizer]` and hands off to
this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI + kubectl)

After remediating, validate the new node group's utilization:

```bash
# Confirm Karpenter is managing nodes
kubectl get nodes -l karpenter.sh/nodepool
kubectl get nodepools

# Monitor node utilization for 7 days post-change
aws cloudwatch get-metric-statistics \
  --namespace ContainerInsights \
  --metric-name node_cpu_utilization \
  --dimensions Name=ClusterName,Value=prod-cluster \
  --start-time $(date -d '-7 days' +%FT%TZ) \
  --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json

# Confirm Savings Plan coverage
aws ce get-savings-plans-coverage \
  --time-period Start=2026-08-01,End=2026-08-10 \
  --granularity DAILY
```

If node CPU > 80% or Memory > 85% sustained for 7 days, scale up the
Karpenter NodePool or adjust the minSize.

## Fleet-wide extension

For a multi-cluster EKS fleet:

1. Enable Container Insights on all clusters.
2. Run the skill per node group, sorted by estimated savings (largest first).
3. Batch remediation: max 3 node groups per batch, CONFIRM per batch.
4. After the right-sizing sweep, evaluate the steady-state EC2 spend and
   commit a 3-year Compute Savings Plan for the baseline.
5. Consolidate small clusters to reduce control-plane costs ($73/month each).
