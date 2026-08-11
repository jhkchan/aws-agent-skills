---
name: eks-cost-optimizer
description: >-
  Optimizes EKS cluster costs via a layered analysis framework — right-sizes
  EC2 managed node groups from 14-30 day CloudWatch and Container Insights
  utilization, evaluates Fargate vs EC2 nodes (Fargate pay-per-pod at
  $0.04048/vCPU-hr + $0.004445/GB-hr; EC2 cheaper for steady-state dense
  scheduling), assesses Spot Instance node groups (up to 90% off, requires
  PodDisruptionBudget + graceful drain), compares Cluster Autoscaler vs
  Karpenter (consolidation, bin-packing, faster scale-up, 20-40% savings),
  finds bin-packing waste (requests vs limits gap, over-provisioned
  namespaces), and layers pricing-model optimization (Compute Savings Plans
  for the EC2 node baseline; control plane is fixed $73/month). Emits
  OPTIMIZED, OPPORTUNITY_FOUND with estimated monthly savings, or
  ALREADY_OPTIMAL. Use for EKS spend reviews, managed node group rightsizing,
  Karpenter evaluation, Fargate migration analysis, or FinOps Kubernetes plans.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline recommendation classification works from pasted Container
  Insights metrics and node group configurations. Live-account optimization
  uses aws eks describe-nodegroup, aws eks list-fargate-profiles, aws
  cloudwatch get-metric-statistics, aws ce get-cost-and-usage, aws ec2
  describe-instance-types, and aws ce get-savings-plans-coverage (AWS CLI v2,
  SSO or key-based credentials). kubectl top nodes / kubectl describe nodes
  for in-cluster signals.
keywords:
  - EKS
  - Kubernetes
  - cost optimization
  - managed node group
  - Fargate
  - Spot Instances
  - Karpenter
  - Cluster Autoscaler
  - bin-packing
  - PodDisruptionBudget
  - requests
  - limits
  - Container Insights
  - Compute Savings Plans
  - FinOps
  - node group right-sizing
  - EKS Auto Mode
  - consolidation
  - Graviton
  - Vertical Pod Autoscaler
tags: [eks, kubernetes, compute, cost-optimization, finops, fargate, karpenter, spot]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: Compute
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL"
  when_to_use: >-
    Right-sizing EKS managed node groups for cost, evaluating Fargate vs EC2
    for a workload, planning a Spot node group migration, comparing Cluster
    Autoscaler vs Karpenter, identifying bin-packing waste (requests vs limits
    gap), planning a Compute Savings Plan for EKS nodes, or building a
    monthly savings estimate for an EKS FinOps initiative.
  when_not_to_use: >-
    Auditing a single pod's resource requests (use VPA recommendations
    directly), troubleshooting a pod crash or OOMKill (use kubectl describe
    and application logs), EC2 instance rightsizing outside EKS (use
    ec2-rightsizing-optimizer), EKS security or RBAC audits (use the
    security audit skills), or EKS upgrade planning (use the deploy/operate
    skills). This skill focuses on cost-driven EKS optimization decisions.
  activation_triggers:
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
  invocation_schema: >-
    Input: either (a) an EKS cluster identifier + live-account context, (b)
    a managed node group configuration with utilization data, OR (c)
    Container Insights metrics (node CPU, node memory, pod CPU, pod memory)
    for one or more node groups with at least 14 days of observation. Output:
    a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/
    MIGRATION_STEPS block per node group or cluster, where VERDICT is one of
    {OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL} and RECOMMENDATION
    includes the target node type, compute model (EC2/Fargate/Spot), autoscaler
    strategy, and pricing model.
  invocation_example: |-
    # Minimal valid input (offline finding classification):
    Cluster: prod-cluster
    Region: us-east-1
    Node group: prod-general-purpose
    Instance type: m5.2xlarge
    Desired size: 4 nodes (min 3, max 10)
    Compute model: EC2 On-Demand managed node group
    Autoscaler: Cluster Autoscaler
    Utilization (Container Insights, last 30 days):
      - node_cpu_utilization: avg=12%, max=20%
      - node_memory_utilization: avg=25%, max=35%
      - Average pods per node: 8 (capacity ~30)
    Workload: mixed microservices (Java, Python, Go), multi-arch
    Docker images available.
    Emit the standard optimization block.
---

# EKS Cost Optimizer

## Quick start

- **Node utilization is the starting signal, not the final answer.** Low
  node CPU/memory tells you the node group is overprovisioned, but the root
  cause is usually the gap between pod `requests` and actual usage. Fix the
  requests first (Step 6 — bin-packing), then right-size the node group.
- **Decision framework (apply in order):**
  - Bin-packing waste (requests >> usage) → reduce requests first (Step 6).
  - Node group right-sizing (CPU < 30% + Memory < 50% after request fix) →
    downsize instance type or reduce desired count (Step 5).
  - Fargate vs EC2 (Step 4): Fargate for sporadic/dev/low-density; EC2 for
    steady-state high-density.
  - Spot node groups (Step 7): up to 90% off for fault-tolerant workloads.
  - Karpenter vs Cluster Autoscaler (Step 8): Karpenter saves 20-40%.
  - Pricing model (Step 9): Compute Savings Plan for the EC2 baseline.
- **Fargate is pay-per-pod, not pay-per-node.** 10 pods at 1 vCPU + 2 GB
  each on Fargate cost ~$360/month; the same 10 pods on one m5.large cost
  ~$70/month. Fargate wins at low density; EC2 wins for steady-state.
- **The EKS control plane is a fixed cost ($0.10/hour = $73/month).**
  Right-sizing nodes does not reduce the control plane bill. Cluster
  consolidation is the only lever for control plane savings.

## STRICT output contract

Every optimization response MUST emit this block per target (node group or
cluster). No prose before or after the block; the block is the entire
actionable output.

```text
TARGET: <cluster-name/node-group-name>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <instance-type x N nodes | Fargate profile> at <pricing-model>
  Proposed: <instance-type x N nodes | Fargate profile | Spot> at <pricing-model>
  Compute model: <EC2 On-Demand | EC2 Spot | Fargate | mixed>
  Autoscaler: <Cluster Autoscaler | Karpenter | EKS Auto Mode>
  Bin-packing action: <reduce requests | VPA recommendation | none>
  Graviton: <yes/no/N/A>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly (right-size + bin-pack): $<amount>
  Monthly (compute model): $<amount>
  Monthly (pricing model): $<amount>
  Annual total: $<amount>
  Assumptions: <730h/month, pricing region, etc.>
MIGRATION_STEPS:
  1. <specific action with CLI or kubectl command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <node-group> in <cluster>.
  Proceed? (yes/no)"
```

Do NOT omit any field. If a field is not applicable, write `N/A` with a
one-line reason. A missing ESTIMATED_SAVINGS block is a contract violation.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick start** | Decision framework order, Fargate vs EC2 rule of thumb | First read |
| **§ STRICT output contract** | Mandatory output block format | Before emitting any response |
| **§ Mindset** | Bin-packing precedes node right-sizing, Fargate breakeven, Spot safety | Understanding the philosophy |
| **§ Quick reference** | Verdict thresholds (OPPORTUNITY_FOUND/OPTIMIZED/ALREADY_OPTIMAL) | Classifying findings |
| **§ Pre-flight** | Data gate — Container Insights, kubectl top requirements | Before any right-sizing decision |
| **§ Process** | Ordered optimization steps (1-10): bin-packing, node sizing, Fargate, Spot, Karpenter, pricing | Choosing recommendations |
| **§ Output format** | Worked example (OPPORTUNITY_FOUND) | Formatting the response |
| **§ Expert heuristic** | Consolidated non-obvious EKS cost behaviours table | Review before complex decisions |
| **§ NEVER** | Top 5 anti-patterns that cause pod eviction, data loss, or false savings | Review before remediation |
| `references/` | CLI commands, extra worked examples, full NEVER list, detailed heuristics | Deep reference |

## Mindset

EKS cost optimization is a layered decision. Four behaviours separate a
senior Kubernetes FinOps engineer from a generalist:

- **Bin-packing precedes node right-sizing.** If pods request 4 vCPU but
  use 0.5 vCPU, nodes appear fully scheduled while actually 90% idle.
  Right-sizing nodes first produces pending pods. Always fix requests
  (Step 6) before changing instance types. #1 cause of failed EKS
  right-sizing.
- **Fargate has a breakeven density, not a universal advantage.** Below
  ~3-4 steady pods per equivalent EC2 node, Fargate is cheaper. Above that,
  EC2 amortizes cost across more pods. Always compute the breakeven.
- **Spot savings require a safety contract.** A Spot node group without
  PDB + graceful drain (NTH/Karpenter) causes data loss and 502s. The
  safety contract is non-negotiable.
- **Karpenter consolidation is the highest-leverage switch.** Moving from
  Cluster Autoscaler to Karpenter typically saves 20-40% through better
  bin-packing and consolidation of underutilized nodes.

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| Node CPU < 30% avg AND node Memory < 50% avg AND requests ~= usage | **OPPORTUNITY_FOUND** (downsize node group) | Step 5 — reduce instance size or desired count |
| Pod requests >> actual usage (requests/usage ratio > 2x) | **OPPORTUNITY_FOUND** (bin-packing) | Step 6 — reduce requests via VPA or manual tuning, then re-evaluate nodes |
| Sporadic/dev workload on steady EC2 nodes with low pod density (< 3 pods/node) | **OPPORTUNITY_FOUND** (Fargate migration) | Step 4 — migrate to Fargate profile |
| Steady-state, > 8 pods/node, fault-tolerant, no PDB gap | **OPPORTUNITY_FOUND** (Spot node group) | Step 7 — Spot node group or Karpenter Spot capacity |
| Cluster Autoscaler with empty/underutilized nodes | **OPPORTUNITY_FOUND** (Karpenter) | Step 8 — migrate to Karpenter for consolidation |
| EC2 nodes at On-Demand pricing for steady-state baseline | **OPPORTUNITY_FOUND** (pricing model) | Step 9 — Compute Savings Plan |
| Container Insights metrics absent (no observability) | **NEED_MORE_INFO** | Enable Container Insights, wait 14 days, re-evaluate |
| All dimensions optimized: Karpenter + Spot + Savings Plan + tight requests | **ALREADY_OPTIMAL** | None — continue monitoring |
| Post-remediation: changes applied and metrics confirm healthy utilization | **OPTIMIZED** | None — verification passed |

## Pre-flight: data gate (run before any right-sizing decision)

**Required data:** Container Insights node CPU/memory utilization (14-30
day window), pod-level usage for bin-packing analysis, node group
configuration, and (optionally) `kubectl top nodes` for real-time signals.
Key commands: `aws cloudwatch get-metric-statistics` for Container Insights
metrics, `kubectl top nodes` for live utilization, `kubectl describe node`
for allocatable resources.

Full CLI sequences for data gathering are in
`references/eks-cost-reference.md` → "Pre-flight data-gathering CLI commands".

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| Container Insights not enabled | **NEED_MORE_INFO**: Enable, wait 14 days. Do NOT recommend downsize without data. |
| Observation window < 14 days | **NEED_MORE_INFO**: may reflect atypical load. |
| kubectl access unavailable (offline plan) | Rely on Container Insights. Mark bin-packing analysis MEDIUM confidence. |
| Node group `DesiredSize: 0` (scaled to zero) | Skip — no cost to optimize. |
| Fargate profile present but 0 running Fargate pods | Fargate charges per pod, not per profile. Skip. |

### Conflicting-data arbitration

When Container Insights and `kubectl top nodes` disagree, trust `kubectl
top nodes` (fresher, from the kubelet). When Container Insights and
CloudWatch `AWS/EC2` CPUUtilization disagree, trust Container Insights
(`node_cpu_utilization` accounts for kubelet overhead).

## Process — Optimization logic (apply in order)

### Step 1: Validate input and data sufficiency

If Container Insights metrics (`node_cpu_utilization`,
`node_memory_utilization`) are absent, emit NEED_MORE_INFO:

```text
TARGET: <cluster/node-group>
VERDICT: NEED_MORE_INFO
REASON: Container Insights metrics are absent for this node group.
  Without node CPU + memory utilization data, a node downsize
  recommendation is a guess.
RECOMMENDATION:
  1. Enable Container Insights:
     aws eks update-cluster-config --name <cluster> \
       --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
  2. Verify metrics appear:
     aws cloudwatch list-metrics --namespace ContainerInsights \
       --metric-name node_cpu_utilization \
       --dimensions Name=ClusterName,Value=<cluster>
  3. Wait 14-30 days for representative data.
  4. Re-evaluate.
ESTIMATED_SAVINGS: $0 (cannot quantify without utilization data)
```

If the observation window < 14 days, emit NEED_MORE_INFO. Proceed only if
data sufficiency passes.

### Step 2: Node group inventory and current cost

Gather the node group configuration:

```bash
aws eks describe-nodegroup --cluster-name <cluster> --nodegroup-name <ng> \
  --output json | jq '{
    instance_types: .nodegroup.instanceTypes,
    desired: .nodegroup.scalingConfig.desiredSize,
    min: .nodegroup.scalingConfig.minSize,
    max: .nodegroup.scalingConfig.maxSize,
    capacity_type: .nodegroup.capacityType,
    ami_type: .nodegroup.amiType
  }'
```

Compute current monthly node cost: `monthly = instance_hourly *
desired_size * 730`. Add the control plane cost ($73/month) pro-rated if
analyzing per-cluster.

### Step 3: Bin-packing analysis (apply early)

Check whether pod `requests` are inflated relative to actual usage before
right-sizing nodes:

```bash
kubectl get pods --all-namespaces -o json | jq '.items[] | {
  pod: .metadata.name, cpu_request: .spec.containers[].resources.requests.cpu,
  mem_request: .spec.containers[].resources.requests.memory}'
kubectl top pods --all-namespaces
```

| Requests/usage ratio | Bin-packing verdict | Action |
|---|---|---|
| ratio < 1.5x | Healthy | Proceed to node right-sizing (Step 5) |
| ratio 1.5-3x | Moderate waste | Step 6 — reduce requests to p95 usage |
| ratio > 3x | Severe waste | Step 6 — reduce requests FIRST, then re-evaluate nodes |

If ratio > 2x, node right-sizing is blocked on bin-packing — fix requests
first. CLI commands in `references/eks-cost-reference.md`.

### Step 4: Fargate vs EC2 evaluation

**Fargate recommended when:** pod density < 3-4 per EC2 node, sporadic
workload, no DaemonSets/privileged pods, zero node management desired.

**EC2 recommended when:** steady-state with > 6 pods/node, DaemonSets in
use, specific instance features needed (GPU, NVMe), Spot savings priority.

**Fargate breakeven:**
```
fargate_pod_hourly = (vCPU_request * $0.04048) + (GB_request * $0.004445)
ec2_cost_per_pod = ec2_node_hourly / ec2_pods_per_node
# Fargate cheaper when fargate_pod_hourly < ec2_cost_per_pod
```
Fargate Spot offers up to 75% off for interruptible workloads.

### Step 5: Node group right-sizing (after bin-packing is fixed)

| Node utilization (30-day avg) | Action |
|---|---|
| CPU < 30% AND Memory < 50% | Downsize: reduce instance type by 1-2 sizes OR reduce desired count by 25-50%. |
| CPU > 70% OR Memory > 80% | Upsize: increase instance type or desired count. |
| 30-70% CPU, 50-80% Memory | Correctly sized. Proceed to Spot/pricing evaluation. |

**Downsize:** Option A — create new node group with smaller type, drain
old group, shift traffic (safer for production). Option B — update existing
group's instance type (faster, rolling rescheduling).

**Graviton:** requires multi-arch (arm64) container images. Types: m7g,
c7g, r7g (up to 40% better price-performance).

### Step 6: Bin-packing optimization (requests adjustment)

Reduce pod `requests` to match actual p95/p99 usage.

| Resource | Recommendation rule |
|---|---|
| CPU request | p95 CPU usage over 30 days. Round up to nearest 25m. |
| Memory request | p99 memory usage + 10-15% buffer (OOMKill risk). |
| CPU limit | 2x request for burst workloads, or remove for latency-sensitive. |
| Memory limit | >= request. A limit below request causes OOMKill. |

After adjusting requests, re-evaluate node utilization (Step 5).

### Step 7: Spot node group evaluation

**Spot readiness checklist (ALL must pass):**
1. Workload is stateless or tolerates graceful shutdown (2-min warning).
2. PodDisruptionBudget configured for all deployments:
   `kubectl get pdb --all-namespaces` — confirm `minAvailable` or
   `maxUnavailable` set on every deployment.
3. Graceful drain mechanism (NTH for Cluster Autoscaler; Karpenter native
   disruption handling).
4. Multi-AZ scheduling (topology spread constraints or anti-affinity) to
   avoid correlated Spot interruptions.
5. No stateful workloads (databases, queues) on Spot nodes — use
   persistent EC2 On-Demand for stateful workloads.
6. `terminationGracePeriodSeconds` set appropriately (default 30s; increase
   for workloads needing graceful shutdown).

**Recommendation:** Cluster Autoscaler → separate Spot node group + On-Demand
group with selectors/tolerations. Karpenter → NodePool with Spot capacity
and 3+ instance type alternatives.

### Step 8: Cluster Autoscaler vs Karpenter evaluation

| Dimension | Cluster Autoscaler | Karpenter |
|---|---|---|
| Scaling trigger | Pending pods | Pending pods + consolidation |
| Consolidation | Only removes empty nodes | Removes empty + replaces underutilized nodes |
| Spot handling | Requires NTH | Native disruption handling |
| Instance flexibility | Constrained by node group config | Selects from instance type list automatically |
| Typical savings | — | 20-40% over Cluster Autoscaler |

**Recommendation:** If running Cluster Autoscaler with underutilized nodes
(< 40% CPU), migrating to Karpenter with consolidation enabled is typically
the highest-leverage single change.

**Karpenter migration steps:**
1. Install Karpenter via Helm.
2. Create a NodePool with instance type alternatives and consolidation
   enabled (`disruption.consolidationPolicy: WhenEmptyOrUnderutilized`).
3. Cordon the Cluster Autoscaler-managed node group gradually.
4. Karpenter provisions replacement nodes and consolidates.
5. Remove Cluster Autoscaler once all workloads are on Karpenter nodes.

### Step 9: Pricing model optimization

| Node group pattern | Recommended model | Savings vs On-Demand |
|---|---|---|
| Steady-state On-Demand baseline | 3-year Compute Savings Plan | 50-72% |
| Variable nodes (auto-scaling) | 1-yr CSP for baseline + On-Demand for spikes | 30-40% |
| Spot-eligible burst nodes | Spot Instances | Up to 90% |
| Fargate pods | No Savings Plan (not covered) | 0% (Fargate Spot: up to 75%) |

**Commitment laddering:** commit a 1-3 year CSP for the steady-state EC2
baseline, use Spot for fault-tolerant burst, On-Demand for unpredictable spikes.

### Step 10: Impact estimation and final verdict

```
Bin-packing savings = freed_node_count * node_hourly * 730
Fargate migration savings = (ec2_cost - fargate_pod_cost) * 730
Spot savings = (on_demand_hourly - spot_hourly) * node_count * 730
Karpenter savings = (pre_nodes - post_nodes) * node_hourly * 730
Savings Plan savings = committed_spend * discount_rate
```

Verdict: any dimension with a concrete recommendation → **OPPORTUNITY_FOUND**.
All dimensions pass + pricing optimized → **OPTIMIZED** or **ALREADY_OPTIMAL**.
Data insufficient → **NEED_MORE_INFO**.

## Output format

See § STRICT output contract for the mandatory block. Worked example below.
Additional examples (Fargate migration, already optimal, NEED_MORE_INFO) in
`references/eks-cost-reference.md`.

### Worked example — overprovisioned node group + bin-packing + Karpenter

```text
TARGET: prod-cluster/prod-general-purpose
VERDICT: OPPORTUNITY_FOUND
REASON: m5.2xlarge node group (4 nodes) at 12% CPU / 25% Memory over 30 days
  is overprovisioned. Root cause: pod requests inflated 4x vs actual usage.
  Fix requests (Step 6), downsize to m7i.xlarge (Step 5), migrate to
  Karpenter for consolidation (Step 8), and commit a 3-year Compute Savings
  Plan on the reduced baseline (Step 9).
RECOMMENDATION:
  Current: m5.2xlarge x 4 nodes at On-Demand via Cluster Autoscaler
  Proposed: m7i.xlarge x 2 nodes at 3-year Compute Savings Plan via Karpenter
  Compute model: EC2 On-Demand → EC2 On-Demand (Karpenter-managed)
  Autoscaler: Cluster Autoscaler → Karpenter (consolidation enabled)
  Bin-packing action: reduce CPU requests from 4000m to 1000m per pod via VPA
  Graviton: N/A (some pods lack arm64 images; revisit after multi-arch build)
  Confidence: HIGH — Container Insights reporting, kubectl top confirms low
    usage, requests/usage ratio 4.2x (severe waste).
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
  1. Deploy VPA in recommend mode and review recommendations for top-20
     pods by request/usage gap:
     kubectl get vpa -n prod --output json | jq '.items[].status.recommendation'
  2. Apply reduced CPU requests (4000m → 1000m) to deployments:
     kubectl patch deployment <name> -n prod --type json \
       -p '[{"op":"replace","path":"/spec/template/spec/containers/0/resources/requests/cpu","value":"1000m"}]'
  3. Install Karpenter and create a NodePool with m7i.xlarge as the
     primary instance type and consolidation enabled:
     helm install karpenter oci://public.ecr.aws/karpenter/karpenter \
       -n karpenter --create-namespace
     kubectl apply -f karpenter-nodepool.yaml
  4. Cordon the old Cluster Autoscaler node group gradually (one node at
     a time) and verify pods reschedule onto Karpenter nodes:
     kubectl cordon <node> && kubectl drain <node> --ignore-daemonsets
  5. Once all pods are on Karpenter nodes, delete the old node group:
     aws eks delete-nodegroup --cluster-name prod-cluster \
       --nodegroup-name prod-general-purpose
  6. Purchase a 3-year Compute Savings Plan for the m7i.xlarge baseline:
     aws savingsplans create-savings-plan --savings-plan-offering-id <id> \
       --commitment "<hourly-amount>"
CONFIRM: Before installing Karpenter and cordoning nodes, emit and await:
  "CONFIRM: About to install Karpenter on prod-cluster and cordon the
   prod-general-purpose node group. Pods will reschedule with brief
   scheduling delays. Proceed? (yes/no)"
  Do NOT execute until the operator confirms.
```

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `OPPORTUNITY_FOUND` | At least one dimension has a concrete, savings-bearing recommendation. |
| `OPTIMIZED` | Changes applied and verified this session; metrics confirm healthy bands. |
| `ALREADY_OPTIMAL` | All dimensions optimized (Karpenter + Spot + Savings Plan + tight requests). |
| `NEED_MORE_INFO` | Container Insights absent or observation window < 14 days. Emit before any sizing recommendation. |
| `BLOCKED` | Spot readiness check failed and the ONLY recommendation was Spot. |

**Rule:** never emit `OPPORTUNITY_FOUND` without first discharging every
`NEED_MORE_INFO` gate in Step 1.

## Expert heuristic — consolidated

| Heuristic | Impact on recommendation |
|---|---|
| Requests is the scheduling currency, not limits or usage | Check requests/usage ratio before node right-sizing. Inflated requests mask real utilization. |
| Fargate does not support DaemonSets or privileged pods | Verify no DaemonSet dependencies before recommending Fargate. #1 migration blocker. |
| Fargate charges per pod-request, not per pod-usage | Right-sizing the pod's own requests is the only Fargate lever. |
| Spot gives 2-min warning; NTH/Karpenter needed for graceful drain | Never recommend Spot without verifying PDB + drain mechanism. |
| Karpenter consolidation deletes empty nodes AND replaces underutilized ones | Cluster Autoscaler only removes empty nodes. Replace mode is the 20-40% savings source. |
| Graviton nodes need multi-arch container images | Verify arm64 manifest before recommending. Single-arch x86 fails on arm64. |
| Compute Savings Plans cover EC2 nodes, NOT Fargate | Never claim Savings Plan savings on Fargate spend. |
| Managed node group updates respect PDB | A PDB that blocks drainage stalls node group updates. |
| Cross-AZ pod-to-pod traffic within a cluster is free | Right-sizing that changes AZ distribution does not add intra-cluster transfer cost. |
| EKS control plane is $0.10/hour ($73/month) fixed | Node right-sizing does not reduce control plane cost. |
| EKS Auto Mode bundles Karpenter-like provisioning | For new clusters, Auto Mode eliminates separate Karpenter installation. |
| cluster-autoscaler never consolidates partially-used nodes | If nodes are 30% utilized but not empty, recommend Karpenter. |

## NEVER (top 5 — full list in references)

- NEVER recommend a node group downsize without first checking the pod
  requests-to-usage ratio. Inflated requests produce pending pods.
- NEVER recommend Fargate without verifying no DaemonSets, privileged pods,
  or hostNetwork are in use. #1 Fargate migration failure.
- NEVER recommend Spot without verifying PDB and graceful drain (NTH or
  Karpenter). Without these, Spot interruptions cause data loss.
- NEVER claim Compute Savings Plan savings on Fargate spend. CSPs apply to
  EC2 instance spend only.
- NEVER recommend a single instance type for a Spot node group or Karpenter
  NodePool. Always provide 3+ alternative instance types.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE** before any state-changing operation.
- **Verify PDB before Spot migration:** `kubectl get pdb --all-namespaces`.
- **Verify multi-arch images before Graviton:** `docker manifest inspect <image>`.
- **Verify no DaemonSet dependencies before Fargate:** `kubectl get ds --all-namespaces`.
- **Drain nodes one at a time** during cutover.
- **Batch limit:** max 3 node groups per batch, single CONFIRM, verify before next.
- **Capture pre-state:** snapshot `describe-nodegroup` output before changes.

Full detail in `references/eks-cost-reference.md` → "Pre-flight safety checks".

## Recent AWS features (2024-2026)

- **EKS Auto Mode (2024-2025):** Managed compute auto-provisioning that
  bundles Karpenter-like node management. Auto Mode handles instance
  selection, Spot/On-Demand mix, and consolidation automatically. For new
  clusters, Auto Mode eliminates the need to install Karpenter separately.

- **Karpenter consolidation improvements (v0.32+, 2024-2025):** Disruption
  budgets (`disruption.budgets`) allow rate-limiting consolidation to
  control node churn in production. `WhenEmptyOrUnderutilized` is the
  recommended consolidation policy for steady-state clusters.

- **Graviton 4 (2024-2025):** Broad rollout across EKS-supported instance
  types. Graviton 4 nodes offer up to 30% better performance than Graviton 3.

- **Fargate pricing unchanged:** $0.04048/vCPU-hour + $0.004445/GB-hour
  (us-east-1). Fargate Spot remains up to 75% off. Still not covered by
  Compute Savings Plans (as of 2026).

- **Compute Savings Plans enhancements (2024):** More flexible commitment
  terms. Use for any EKS EC2 node baseline with uncertain workload growth.

- **EKS Container Insights enhanced observability (2024-2025):** Per-pod
  cost allocation via KubeCost integration. Recommended for FinOps-grade
  cluster analysis.

- **Spot Placement Score for EKS (2024-2025):** Predicts Spot capacity
  availability before provisioning Spot node groups.

## Domain

AWS CloudOps / EKS Kubernetes Compute Cost Optimization & FinOps.

## AWS documentation

- **Amazon EKS User Guide** — https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html
- **EKS Pricing** — https://aws.amazon.com/eks/pricing/
- **AWS Fargate Pricing** — https://aws.amazon.com/fargate/pricing/
- **EKS Managed Node Groups** — https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html
- **Karpenter** — https://karpenter.sh/
- **Container Insights** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html
- **EKS Auto Mode** — https://docs.aws.amazon.com/eks/latest/userguide/auto-mode.html
- **Spot Instances for EKS** — https://docs.aws.amazon.com/eks/latest/userguide/spot.html
- **PodDisruptionBudgets** — https://kubernetes.io/docs/tasks/run-application/configure-pdb/
- **AWS CLI EKS reference** — https://docs.aws.amazon.com/cli/latest/reference/eks/
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
