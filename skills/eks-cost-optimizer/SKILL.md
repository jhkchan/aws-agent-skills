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
  Right-sizing a node group without fixing inflated requests just shifts
  the waste to fewer, equally underutilized nodes.
- **Decision framework (apply in order):**
  - Bin-packing waste (requests >> usage) → reduce requests via VPA or
    manual tuning first (Step 6).
  - Node group right-sizing (CPU < 30% + Memory < 50% after request fix) →
    downsize instance type or reduce desired count (Step 5).
  - Fargate vs EC2 (Step 4): Fargate for sporadic/dev/low-density; EC2 for
    steady-state high-density.
  - Spot node groups (Step 7): up to 90% off for fault-tolerant, multi-AZ
    workloads with PDB + graceful drain.
  - Karpenter vs Cluster Autoscaler (Step 8): Karpenter consolidation saves
    20-40% over Cluster Autoscaler.
  - Pricing model (Step 9): Compute Savings Plan for the EC2 baseline.
- **Fargate is pay-per-pod, not pay-per-node.** A workload with 10 pods
  requesting 1 vCPU + 2 GB each on Fargate costs ~$360/month. The same 10
  pods on a single m5.large node cost ~$70/month. Fargate wins when pod
  density is low, the workload is sporadic, or you want zero node management.
  EC2 wins for steady-state, high-density scheduling.
- **The EKS control plane is a fixed cost ($0.10/hour = $73/month).**
  Right-sizing nodes does not reduce the control plane bill. Cluster
  consolidation (merging workloads into fewer clusters) is the only lever
  for control plane savings.

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
| **§ Quick start** | Decision framework order, Fargate vs EC2 rule of thumb, control plane cost | First read |
| **§ STRICT output contract** | Mandatory output block format | Before emitting any response |
| **§ Mindset** | Why bin-packing precedes node right-sizing, the Fargate breakeven, Spot safety model | Understanding the optimization philosophy |
| **§ Quick reference** | Verdict thresholds (OPPORTUNITY_FOUND/OPTIMIZED/ALREADY_OPTIMAL) | Classifying findings |
| **§ Pre-flight** | Data gate — Container Insights, kubectl top, CloudWatch requirements | Before any right-sizing decision |
| **§ Process** | Ordered optimization steps (0-10): bin-packing, node sizing, Fargate, Spot, Karpenter, pricing | Choosing recommendations |
| **§ Output format** | Worked examples (OPPORTUNITY_FOUND, ALREADY_OPTIMAL, NEED_MORE_INFO) | Formatting the response |
| **§ Expert heuristic** | Non-obvious EKS cost behaviours from operational experience | Review before complex decisions |
| **§ NEVER** | Anti-patterns that cause pod eviction, data loss, or false savings | Review before remediation |
| **§ Pre-flight safety** | Confirmation gate, PDB check, drain safety, batch limits | Before any state-changing CLI |

## Mindset

EKS cost optimization is a layered decision, not a single right-sizing call.
The cheapest configuration is the one where pods are densely packed onto
the fewest nodes that handle peak workload without scheduling pressure or
Spot-eviction risk. A node group downsize that triggers pending pods or
OOMKills costs more than it saves.

Four behaviours separate a senior Kubernetes FinOps engineer from a
generalist:

- **Bin-packing precedes node right-sizing.** If pods request 4 vCPU but
  use 0.5 vCPU, the node group appears fully scheduled (requests exhausted)
  while the nodes are actually 90% idle. Right-sizing the node group first
  produces pending pods because the scheduler still sees the inflated
  requests. Always fix requests (Step 6) before changing instance types or
  counts. This is the #1 cause of failed EKS right-sizing initiatives.
- **Fargate has a breakeven density, not a universal cost advantage.**
  Fargate charges per pod-second. Below ~3-4 steady pods per equivalent EC2
  node, Fargate is cheaper (no idle node waste). Above that density, EC2 is
  cheaper (amortize the node cost across many pods). The breakeven depends
  on pod size and instance type. Always compute the breakeven before
  recommending Fargate.
- **Spot savings require a safety contract, not just a launch config.** A
  Spot node group without a PodDisruptionBudget and a graceful drain
  mechanism (AWS Node Termination Handler or Karpenter's native disruption
  handling) will cause ungraceful pod terminations — data loss for stateful
  workloads, 502s for stateless services during traffic. The savings are
  real (up to 90%) but the safety contract is non-negotiable.
- **Karpenter consolidation is the single highest-leverage switch.** Moving
  from Cluster Autoscaler to Karpenter typically saves 20-40% through
  better bin-packing (Karpenter schedules pods directly onto the cheapest
  fitting instance, then consolidates underutilized nodes). This is often
  larger than any individual node right-sizing.

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

### Required data sources

```bash
# 1. Confirm Container Insights is enabled on the cluster
aws eks describe-cluster --name <cluster> --query 'cluster.logging' --output json

aws logs describe-metric-filters \
  --log-group-name /aws/containerinsights/<cluster>/performance \
  --output json

# 2. Pull 14-30 day node utilization from Container Insights
START=$(date -d '-30 days' +%FT%TZ)
END=$(date +%FT%TZ)

aws cloudwatch get-metric-statistics \
  --namespace ContainerInsights \
  --metric-name node_cpu_utilization \
  --dimensions Name=ClusterName,Value=<cluster> Name=NodeGroupName,Value=<ng> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum \
  --output json > node-cpu.json

aws cloudwatch get-metric-statistics \
  --namespace ContainerInsights \
  --metric-name node_memory_utilization \
  --dimensions Name=ClusterName,Value=<cluster> Name=NodeGroupName,Value=<ng> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum \
  --output json > node-mem.json

# 3. Pod-level utilization (the bin-packing signal)
aws cloudwatch get-metric-statistics \
  --namespace ContainerInsights \
  --metric-name pod_cpu_utilization \
  --dimensions Name=ClusterName,Value=<cluster> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum \
  --output json > pod-cpu.json

# 4. In-cluster signals (requires kubectl access)
kubectl top nodes --heapster-scheduler --sort-by=cpu
kubectl describe node <node> | grep -A 5 "Allocated resources"

# 5. Node group configuration
aws eks describe-nodegroup --cluster-name <cluster> --nodegroup-name <ng> \
  --output json
```

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| Container Insights not enabled (no `node_cpu_utilization` metric) | **NEED_MORE_INFO**: Enable Container Insights (`aws eks update-cluster-config --logging ...`), wait 14 days. Do NOT recommend a node downsize without utilization data. |
| Observation window < 14 days | **NEED_MORE_INFO**: workload may reflect atypical load (deploy week, scaling event). |
| kubectl access unavailable (offline plan) | Rely on Container Insights metrics alone. Mark bin-packing analysis as MEDIUM confidence without `kubectl describe node` allocatable data. |
| Node group `DesiredSize: 0` (scaled to zero) | Skip — no cost to optimize. Note in the fleet rollup. |
| Fargate profile present but 0 running Fargate pods | Fargate profile has no compute cost (Fargate charges per pod, not per profile). Note and skip. |
| Mixed instance types in node group (multi-type launch template) | Container Insights dimensions may not break down per instance type. Use `kubectl describe nodes` for per-node data. |

### Conflicting-data arbitration

When Container Insights and `kubectl top nodes` disagree, trust `kubectl
top nodes` (fresher, from the kubelet directly). When Container Insights
and CloudWatch `AWS/EC2` CPUUtilization disagree, trust Container Insights
(`node_cpu_utilization` accounts for kubelet overhead; `AWS/EC2`
`CPUUtilization` does not).

## Process — Optimization logic (apply in order)

### Step 0: Expert heuristic — non-obvious EKS cost behaviours

These behaviours route a recommendation away from the obvious choice. Each
is grounded in operational Kubernetes experience:

- **Pod `requests` is the scheduling currency, not `limits`.** The
  Kubernetes scheduler places pods based on `requests`, not `limits` and
  not actual usage. A node is "full" when the sum of pod `requests` equals
  the node's allocatable capacity — regardless of actual CPU/memory usage.
  This means a node at 10% actual CPU can still be "full" from the
  scheduler's perspective if pods have inflated requests. Always check the
  requests-to-usage ratio before right-sizing nodes.

- **Fargate does not support DaemonSets, privileged pods, or hostNetwork.**
  Workloads using node-local DaemonSets (Fluentd, Datadog agent, node-exporter,
  Istio CNI) cannot run on Fargate. Before recommending Fargate, verify
  none of the target pods require DaemonSet-based sidecars or privileged
  security context. This is the #1 Fargate migration blocker.

- **Fargate pricing is per-pod-per-second with a 1-minute minimum.**
  Fargate charges for the resources requested by the pod, not the resources
  used. A pod requesting 2 vCPU + 4 GB costs the same whether it uses 5%
  or 95% of those resources. Fargate does not benefit from "right-sizing
  the node" — it benefits from right-sizing the pod's own requests.

- **Spot Instance interruptions give a 2-minute warning via the Instance
  Metadata Service.** The AWS Node Termination Handler (NTH) or Karpenter's
  native disruption handler intercepts this warning, cordon-drains the node,
  and gracefully reschedules pods. Without NTH/Karpenter, the node is
  terminated hard and pods get the default `terminationGracePeriodSeconds`
  (30s) to shut down — insufficient for many workloads.

- **Karpenter consolidation has two modes: empty-node deletion and
  replace-with-cheaper.** "Delete" removes nodes with zero non-DaemonSet
  pods. "Replace" identifies nodes that could be replaced by a single
  cheaper/better-fit instance. Consolidation runs every ~10 seconds (v0.32+)
  and is the primary mechanism for the 20-40% savings over Cluster Autoscaler.

- **EKS Auto Mode (2024-2025) includes Karpenter-like auto-provisioning.**
  Auto Mode manages node creation/deletion automatically, including Spot
  support and consolidation. For new clusters, Auto Mode eliminates the need
  to install Karpenter separately. For existing clusters, evaluate Auto Mode
  vs a Karpenter upgrade.

- **Graviton (ARM) node groups require multi-arch container images.**
  Unlike EC2 right-sizing (where the AMI architecture is transparent to the
  application), EKS Graviton requires every pod's container image to have
  an arm64 manifest entry. Multi-arch images (built via `docker buildx`)
  work transparently. Single-arch x86 images will fail to schedule on
  Graviton nodes with `ImagePullBackOff` or runtime errors.

- **Managed node group updates are rolling and respect PDB.** Changing a
  node group's instance type or AMI triggers a rolling update. Each node is
  cordoned, drained, and replaced. If a PDB blocks drainage (too few
  replicas), the update stalls. Always verify PDB configuration before
  triggering a node group update.

- **Compute Savings Plans apply to the EC2 nodes, not Fargate.** Savings
  Plans commit to $X/hour of compute spend (any instance family, any region).
  EC2 nodes in EKS draw from the Savings Plan. Fargate spend is separate —
  Fargate does NOT draw from Compute Savings Plans (as of 2026). Do not
  claim Savings Plan savings on Fargate spend.

- **The cluster-autoscaler scales based on pending pods; Karpenter scales
  based on pending pods AND consolidation.** Cluster Autoscaler never
  removes a node unless it is completely empty. Karpenter proactively
  consolidates partially-utilized nodes. This is why Karpenter saves more
  in steady-state.

- **Cross-AZ traffic within a cluster is free; cross-AZ traffic between
  clusters or to other AWS services is not.** Node group right-sizing that
  changes AZ distribution may shift cross-AZ traffic patterns. Same-cluster,
  cross-AZ pod-to-pod traffic is free. Cross-AZ traffic to RDS, ElastiCache,
  or ALB is $0.01/GB each way.

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
     aws logs put-retention-policy --log-group-name \
       /aws/containerinsights/<cluster>/performance --retention-in-days 30
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
    capacity_type: .nodegroup.capacityType,   # ON_DEMAND | SPOT
    subnets: .nodegroup.subnets,
    ami_type: .nodegroup.amiType,
    disk_size: .nodegroup.diskSize
  }'
```

Compute current monthly node cost:
```
monthly_node_cost = instance_hourly * desired_size * 730
```

Add the control plane cost ($73/month) pro-rated if analyzing per-cluster.

### Step 3: Bin-packing analysis (Step 6 logic applied early)

Before right-sizing nodes, check whether pod `requests` are inflated
relative to actual usage:

```bash
# Per-pod requests vs usage (requires kubectl)
kubectl get pods --all-namespaces -o json | jq '
  .items[] | {
    pod: .metadata.name,
    ns: .metadata.namespace,
    cpu_request: .spec.containers[].resources.requests.cpu,
    mem_request: .spec.containers[].resources.requests.memory
  }'

# Actual usage (requires metrics-server)
kubectl top pods --all-namespaces
```

| Requests/usage ratio | Bin-packing verdict | Action |
|---|---|---|
| ratio < 1.5x | Healthy | Proceed to node right-sizing (Step 5) |
| ratio 1.5-3x | Moderate waste | Step 6 — reduce requests to p95 usage |
| ratio > 3x | Severe waste | Step 6 — reduce requests FIRST, then re-evaluate nodes |

If the ratio > 2x, the node right-sizing is blocked on bin-packing — the
nodes appear "full" from the scheduler's perspective (requests exhausted)
while actual usage is low. Fix requests first.

### Step 4: Fargate vs EC2 evaluation

Evaluate whether the workload should be on Fargate instead of EC2 nodes.

**Fargate is recommended when:**
- Pod density is low (< 3-4 steady pods per equivalent EC2 node).
- The workload is sporadic (dev/test, batch jobs with idle gaps).
- No DaemonSets, privileged pods, or hostNetwork are required.
- You want to eliminate node management overhead.

**EC2 is recommended when:**
- Steady-state with high pod density (> 6 pods/node).
- DaemonSets are in use (logging agents, monitoring, CNI).
- The workload needs specific instance features (GPU, NVMe, huge pages).
- Spot savings are a priority (Fargate Spot is available but less flexible).

**Fargate breakeven calculation:**
```
fargate_pod_hourly = (vCPU_request * $0.04048) + (GB_request * $0.004445)

ec2_node_hourly = <instance-type hourly rate>
ec2_pods_per_node = <pods that fit based on requests>

ec2_cost_per_pod = ec2_node_hourly / ec2_pods_per_node

if fargate_pod_hourly < ec2_cost_per_pod:
    Fargate is cheaper for this pod
else:
    EC2 is cheaper (amortize node across more pods)
```

**Fargate Spot** offers up to 75% savings on Fargate for interruptible
workloads (fault-tolerant, batch, dev/test).

### Step 5: Node group right-sizing (after bin-packing is fixed)

Apply the right-sizing decision after requests are tuned:

| Node utilization (30-day avg) | Action |
|---|---|
| CPU < 30% AND Memory < 50% | Downsize: reduce instance type by 1-2 sizes OR reduce desired count by 25-50%. |
| CPU > 70% OR Memory > 80% | Upsize: increase instance type or desired count. Pods may be pending. |
| 30-70% CPU, 50-80% Memory | Correctly sized. Proceed to Spot/pricing evaluation. |

**Downsize path (managed node group):**
- Option A: Create a new node group with the smaller instance type, drain
  the old group, shift traffic. Safer for production (zero-downtime).
- Option B: Update the existing node group's instance type (rolling update).
  Faster but causes rolling pod rescheduling.

**Graviton evaluation for node groups:**
- All pods must have multi-arch (arm64) container images.
- Java 11+, Python, Go, Node.js workloads typically compatible.
- C/C++, Rust with platform-specific binaries need recompilation.
- Graviton node types: m7g, c7g, r7g (up to 40% better price-performance).

### Step 6: Bin-packing optimization (requests adjustment)

Reduce pod `requests` to match actual p95 usage:

```bash
# Install VPA (Vertical Pod Autoscaler) in recommend mode
kubectl apply -f vpa-recommender.yaml

# Get VPA recommendations for a deployment
kubectl get vpa <vpa-name> -o json | jq '.status.recommendation'
```

| Resource | Recommendation rule |
|---|---|
| CPU request | Set to p95 CPU usage over 30 days. Round up to nearest 25m. |
| Memory request | Set to p99 memory usage over 30 days (memory is not compressible — OOMKill risk). Add 10-15% buffer. |
| CPU limit | Set to 2x request for burst workloads, or remove limit for latency-sensitive workloads (CPU is compressible). |
| Memory limit | Set equal to or slightly above request. A memory limit below request causes OOMKill. |

After adjusting requests, re-evaluate node utilization (Step 5). The node
group will appear less "full" from the scheduler's perspective, enabling a
downsize.

### Step 7: Spot node group evaluation

Evaluate whether the workload can run on Spot Instances (up to 90% savings).

**Spot readiness checklist (ALL must pass):**
1. Workload is stateless or can tolerate graceful shutdown (2-min warning).
2. PodDisruptionBudget is configured for all deployments (min available replicas).
3. Graceful drain mechanism is in place (AWS Node Termination Handler for
   Cluster Autoscaler; Karpenter handles disruptions natively).
4. Multi-AZ scheduling (topology spread constraints or anti-affinity) to
   avoid correlated Spot interruptions.
5. No stateful workloads (databases, queues) on Spot nodes — use persistent
   EC2 On-Demand nodes for stateful workloads.
6. Pod `terminationGracePeriodSeconds` is set appropriately (default 30s;
   increase for workloads that need graceful shutdown).

**Spot recommendation:**
- For Cluster Autoscaler: create a separate Spot node group alongside the
  On-Demand group. Use node selectors/tolerations to route fault-tolerant
  pods to Spot.
- For Karpenter: configure the Provisioner/NodePool with Spot capacity
  types and multiple instance type alternatives (Karpenter falls back to
  alternative types if one is reclaimed).

### Step 8: Cluster Autoscaler vs Karpenter evaluation

| Dimension | Cluster Autoscaler | Karpenter |
|---|---|---|
| Scaling trigger | Pending pods | Pending pods + consolidation |
| Node provisioning | Scales managed node groups | Provisions raw EC2 instances directly |
| Consolidation | Only removes empty nodes | Removes empty + replaces underutilized nodes with cheaper alternatives |
| Spot handling | Requires NTH for graceful drain | Native disruption handling |
| Instance flexibility | Constrained by node group config | Selects from a list of instance types automatically |
| Bin-packing | Relies on kube-scheduler | Bin-packs directly (considers all pending pods together) |
| Typical savings baseline | — | 20-40% over Cluster Autoscaler |
| Setup complexity | Lower (EKS add-on) | Higher (install + configure Provisioner/NodePool) |

**Recommendation:** If the cluster is running Cluster Autoscaler and has
underutilized nodes (nodes at < 40% CPU), migrating to Karpenter with
consolidation enabled is typically the highest-leverage single change.

**Karpenter migration steps:**
1. Install Karpenter via Helm.
2. Create a NodePool with instance type alternatives and consolidation
   enabled (`disruption.consolidationPolicy: WhenEmptyOrUnderutilized`).
3. Cordon the Cluster Autoscaler-managed node group gradually.
4. Karpenter provisions replacement nodes and consolidates.
5. Remove Cluster Autoscaler once all workloads are on Karpenter nodes.

### Step 9: Pricing model optimization

After utilization-based optimization, evaluate the pricing model for EC2 nodes:

| Node group pattern | Recommended model | Savings vs On-Demand |
|---|---|---|
| Steady-state On-Demand nodes (always-on baseline) | 3-year Compute Savings Plan | 50-72% |
| Variable nodes (auto-scaling) | 1-year Compute Savings Plan for the baseline + On-Demand for spikes | 30-40% |
| Spot-eligible burst nodes | Spot Instances | Up to 90% |
| Fargate pods | No Savings Plan (Fargate is not covered) | 0% (Fargate Spot for interruptible: up to 75%) |

**Commitment laddering:**
1. Identify the steady-state EC2 node baseline (min-size nodes that run 24/7).
2. Commit a 1-year Compute Savings Plan for this baseline.
3. Use Spot for fault-tolerant burst capacity.
4. Use On-Demand for unpredictable spikes above the Savings Plan commitment.

### Step 10: Impact estimation and final verdict

Compute the monthly savings for each recommendation layer:

```
Bin-packing savings = (freed node count * node_hourly * 730)
Fargate migration savings = (ec2_cost - fargate_pod_cost) * 730
Spot savings = (on_demand_hourly - spot_hourly) * node_count * 730
Karpenter savings = (pre_karpenter_node_count - post_karpenter_node_count) * node_hourly * 730
Savings Plan savings = committed_spend * discount_rate
```

Total savings = sum of applicable layers.

The verdict is the most-actionable finding across all dimensions:
- Any dimension with a concrete recommendation → **OPPORTUNITY_FOUND**.
- All dimensions pass + pricing optimized → **OPTIMIZED** or **ALREADY_OPTIMAL**.
- Data insufficient (Container Insights absent, window < 14 days) → **NEED_MORE_INFO**.

## Output format

See § STRICT output contract for the mandatory block. Worked examples below.

### Worked example — overprovisioned node group + bin-packing waste + Karpenter

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

### Worked example — Fargate migration for a low-density dev workload

```text
TARGET: dev-cluster/dev-nodegroup
VERDICT: OPPORTUNITY_FOUND
REASON: 3 On-Demand m5.large nodes ($210/month) running 6 dev pods that
  each need 0.5 vCPU + 1 GB. Pod density is 2 pods/node — well below the
  Fargate breakeven. No DaemonSets or privileged pods. Migrating to
  Fargate saves 55% and eliminates node management.
RECOMMENDATION:
  Current: m5.large x 3 nodes at On-Demand ($0.096/h each)
  Proposed: Fargate profile, 6 pods at 0.5 vCPU + 1 GB each
  Compute model: EC2 On-Demand → Fargate
  Autoscaler: N/A (Fargate auto-scales per pod)
  Bin-packing action: none (Fargate charges per pod request)
  Graviton: consider Fargate arm64 (20% cheaper per vCPU)
  Confidence: HIGH — no DaemonSets, no privileged pods, pod density 2/node.
ESTIMATED_SAVINGS:
  Monthly (right-size + bin-pack): $0
  Monthly (compute model): $116.12  (EC2: $0.096 x 3 x 730 = $210.24;
    Fargate: 6 pods x (0.5 x $0.04048 + 1 x $0.004445) x 730 = $94.12;
    savings: $210.24 - $94.12 = $116.12)
  Monthly (pricing model): $0 (Fargate not covered by Savings Plans)
  Annual total: $1,393.44
MIGRATION_STEPS:
  1. Create a Fargate profile for the dev namespace:
     aws eks create-fargate-profile --cluster-name dev-cluster \
       --fargate-profile-name dev-profile \
       --pod-execution-role-arn arn:aws:iam::<acct>:role/eks-fargate-pod-execution-role \
       --selectors namespaceName=dev \
       --subnets <subnet-ids> --security-groups <sg-ids>
  2. Verify no pods in the dev namespace use DaemonSets or privileged
     security context:
     kubectl get pods -n dev -o json | jq '.items[].spec.containers[].securityContext.privileged'
  3. Delete existing pods to trigger Fargate scheduling:
     kubectl delete pods -n dev --all
  4. Verify pods reschedule on Fargate:
     kubectl get pods -n dev -o wide | grep Fargate
  5. Scale the EC2 node group to 0 and delete after verification:
     aws eks update-nodegroup-config --cluster-name dev-cluster \
       --nodegroup-name dev-nodegroup --scaling-config desiredSize=0,minSize=0,maxSize=0
CONFIRM: Before creating the Fargate profile, emit and await operator
  approval.
```

### Worked example — already optimal

```text
TARGET: prod-cluster/prod-karpenter-spot
VERDICT: ALREADY_OPTIMAL
REASON: Karpenter-managed cluster with consolidation enabled, Spot capacity
  for fault-tolerant workloads, On-Demand baseline covered by a 3-year
  Compute Savings Plan. Pod requests tuned via VPA (ratio 1.3x). Node
  utilization 55% CPU / 62% Memory — healthy with headroom for traffic spikes.
RECOMMENDATION:
  Current: Karpenter with m7i.xlarge Spot + On-Demand mix, 3-yr Savings Plan
  Proposed: no change
  Compute model: mixed (Spot + On-Demand)
  Autoscaler: Karpenter (consolidation: WhenEmptyOrUnderutilized)
  Bin-packing action: none (VPA-managed, ratio 1.3x)
  Graviton: no (some workloads use x86 SIMD; revisit after multi-arch build)
  Confidence: HIGH — all dimensions optimized.
ESTIMATED_SAVINGS:
  Monthly (right-size + bin-pack): $0
  Monthly (compute model): $0
  Monthly (pricing model): $0
  Annual total: $0
MIGRATION_STEPS:
  - None required. Re-evaluate quarterly.
  - Monitor Spot interruption rate via CloudWatch (ClusterName dimension).
```

### Worked example — NEED_MORE_INFO (Container Insights absent)

```text
TARGET: staging-cluster/staging-ng
VERDICT: NEED_MORE_INFO
REASON: Container Insights is not enabled on staging-cluster. Without
  node_cpu_utilization and node_memory_utilization data, a node downsize
  is a guess.
RECOMMENDATION:
  Current: m5.xlarge x 3 nodes at On-Demand
  Proposed: pending data
  Confidence: LOW — no utilization data available.
ESTIMATED_SAVINGS:
  Monthly (right-size + bin-pack): $0 (cannot quantify)
  Monthly (compute model): pending
  Monthly (pricing model): pending
MIGRATION_STEPS:
  1. Enable Container Insights:
     aws eks update-cluster-config --name staging-cluster \
       --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
  2. Wait 14-30 days.
  3. Re-evaluate.
```

## Verdict semantics — reconciling the verdict_shape

The `verdict_shape` declares three primary verdicts. Two additional
data-gating verdicts appear in the workflow:

| Verdict | When to emit | Position in workflow |
|---|---|---|
| `OPPORTUNITY_FOUND` | At least one dimension (bin-packing, node size, Fargate, Spot, Karpenter, pricing) has a concrete, savings-bearing recommendation. | Primary — terminal for actionable findings. |
| `OPTIMIZED` | Changes applied and verified this session; metrics confirm the new configuration lands within healthy bands. | Primary — post-remediation only. |
| `ALREADY_OPTIMAL` | All dimensions optimized (Karpenter + Spot + Savings Plan + tight requests) AND utilization is healthy. | Primary — terminal for healthy findings. |
| `NEED_MORE_INFO` | Container Insights absent, observation window < 14 days, or kubectl access unavailable for bin-packing analysis. | Pre-decision — emit before any sizing recommendation. |
| `BLOCKED` | Spot readiness check failed (no PDB, stateful workload on Spot) and the ONLY recommendation was Spot. | Pre-decision — emit when the only savings path requires unmet safety prerequisites. |

**Rule:** never emit `OPPORTUNITY_FOUND` without first discharging every
`NEED_MORE_INFO` gate in Step 1.

## Expert heuristic — non-obvious EKS cost behaviours (consolidated)

| Heuristic | Impact on recommendation |
|---|---|
| Requests is the scheduling currency, not limits or usage | Always check requests/usage ratio before node right-sizing. Inflated requests mask the real node utilization. |
| Fargate does not support DaemonSets or privileged pods | Verify no DaemonSet dependencies before recommending Fargate. The #1 migration blocker. |
| Fargate charges per pod-request, not per pod-usage | Right-sizing the pod's own requests is the only Fargate lever. Node-level right-sizing does not apply. |
| Spot gives 2-min warning; NTH/Karpenter needed for graceful drain | Never recommend Spot without verifying PDB + drain mechanism. Hard termination causes data loss. |
| Karpenter consolidation deletes empty nodes AND replaces underutilized ones | Cluster Autoscaler only removes empty nodes. Karpenter's replace mode is the 20-40% savings source. |
| Graviton nodes need multi-arch container images | Verify arm64 manifest before recommending Graviton node groups. Single-arch x86 images fail on arm64. |
| Compute Savings Plans cover EC2 nodes, NOT Fargate | Never claim Savings Plan savings on Fargate spend. Fargate has no commitment-based discount (Fargate Spot除外). |
| Managed node group updates respect PDB | A PDB that blocks drainage stalls node group updates. Verify PDB before triggering updates. |
| Cross-AZ pod-to-pod traffic within a cluster is free | Node right-sizing that changes AZ distribution does not add intra-cluster transfer cost. Cross-AZ to RDS/ALB does. |
| EKS control plane is $0.10/hour ($73/month) fixed | Node right-sizing does not reduce control plane cost. Cluster consolidation is the only control-plane lever. |
| EKS Auto Mode (2024-2025) bundles Karpenter-like provisioning | For new clusters, Auto Mode eliminates separate Karpenter installation. Evaluate for existing clusters on upgrade. |
| cluster-autoscaler never consolidates partially-used nodes | If nodes are 30% utilized but not empty, Cluster Autoscaler keeps them. Karpenter consolidates them. |

## Anti-Patterns — NEVER

- NEVER recommend a node group downsize without first checking the pod
  requests-to-usage ratio. Inflated requests make nodes appear "full" from
  the scheduler's perspective while actual usage is low. Downsizing nodes
  with inflated requests produces pending pods.

- NEVER recommend Fargate without verifying no DaemonSets, privileged pods,
  or hostNetwork are in use. Fargate does not support these — the pods will
  fail to schedule. This is the #1 Fargate migration failure.

- NEVER recommend a Spot node group without verifying PodDisruptionBudget
  (PDB) and a graceful drain mechanism (NTH or Karpenter native). Without
  these, Spot interruptions cause hard pod termination and data loss for
  stateful workloads.

- NEVER recommend Spot for stateful workloads (databases, message queues,
  singleton services, or any pod with local state). Spot interruptions cause
  data loss. Use On-Demand or Fargate for stateful workloads.

- NEVER claim Compute Savings Plan savings on Fargate spend. Compute Savings
  Plans apply to EC2 instance spend only. Fargate has its own pricing model
  and is not covered by Savings Plans (as of 2026).

- NEVER recommend Graviton node groups without verifying every pod's
  container image has an arm64 manifest entry. Single-arch x86 images fail
  on Graviton nodes with `ImagePullBackOff` or runtime errors. Use
  `docker manifest inspect <image>` to verify multi-arch support.

- NEVER recommend a single instance type for a Spot node group or Karpenter
  NodePool. Spot capacity for a single type can be exhausted; always provide
  3+ alternative instance types of similar size so the scheduler/Karpenter
  can fall back.

- NEVER assume Cluster Autoscaler consolidation works. Cluster Autoscaler
  only removes completely empty nodes. If you see partially-utilized nodes
  that should be consolidated, the recommendation is Karpenter, not a
  Cluster Autoscaler config change.

- NEVER recommend Fargate for a high-density steady-state workload (> 6
  pods per equivalent EC2 node). Fargate's per-pod pricing exceeds EC2
  amortized cost at high density. Always compute the breakeven.

- NEVER set memory `limit` below `request`. A memory limit below the
  request causes OOMKill when the pod exceeds the limit — memory is not
  compressible. Set memory limit >= request.

- NEVER trigger a managed node group update (instance type or AMI change)
  during peak traffic. The rolling update cordons and drains nodes one at
  a time, causing brief capacity reduction. Schedule for off-peak hours.

- NEVER recommend Karpenter without configuring disruption budgets or
  consolidation rates for production. Aggressive consolidation (`WhenEmptyOrUnderutilized`)
  can cause rapid node churn if not rate-limited. Use
  `disruption.budgets` to control the pace.

- NEVER assume EKS Fargate pods have access to the same security group as
  EC2 nodes. Fargate pods use the Fargate profile's pod execution role and
  security groups. Verify network policies before migration.

- NEVER ignore the EKS control plane cost ($73/month) in fleet-wide
  analysis. A fleet of 10 small clusters pays $730/month in control plane
  costs alone. Cluster consolidation can save more than node right-sizing.

- NEVER recommend removing `requests` entirely. Some teams remove CPU
  requests to "improve bin-packing," but without requests, the scheduler
  cannot make placement decisions and nodes become oversubscribed. Always
  set requests to p95 usage.

- NEVER assume Container Insights CPU and `kubectl top nodes` will always
  agree. Container Insights may include kubelet/system overhead; `kubectl
  top` reflects cAdvisor data. Trust `kubectl top` for fresher data,
  Container Insights for historical trends.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-nodegroup-config`, `create-fargate-profile`, `delete-nodegroup`,
  `helm install karpenter`, `kubectl cordon/drain`, `create-savings-plan`),
  emit and await operator approval. Do NOT execute until the operator
  confirms.

- **Verify PDB before Spot migration.** Before adding a Spot node group or
  switching Karpenter to Spot capacity:
  `kubectl get pdb --all-namespaces` — confirm every deployment has a PDB
  with `minAvailable` or `maxUnavailable` set.

- **Verify multi-arch images before Graviton migration.**
  `docker manifest inspect <image>` — confirm the manifest list includes
  an arm64 entry for every pod image.

- **Verify no DaemonSet dependencies before Fargate migration.**
  `kubectl get ds --all-namespaces` — identify DaemonSets. Check if target
  pods depend on DaemonSet-provided sidecars (Istio CNI, Calico, logging).

- **Drain nodes one at a time during cutover.** Cordoning all nodes at
  once causes mass pod rescheduling and potential scheduling pressure.
  Cordon-drain one node, verify pods reschedule, then proceed to the next.

- **Batch limit for fleet-wide remediation.** Remediation across multiple
  node groups MUST follow: sort by savings, batch of at most 3 node groups,
  emit per-group MIGRATION_STEPS, single CONFIRM per batch, verify before
  the next batch. Do NOT auto-apply across the entire fleet.

- **Capture pre-state before changes.** Before modifying a node group:
  `aws eks describe-nodegroup --cluster-name <c> --nodegroup-name <ng> --output json > /tmp/<ng>-pre-$(date +%s).json`.

- **Verify Savings Plan coverage post-commitment.** Savings Plans take up
  to 1 hour to propagate. Verify with
  `aws ce get-savings-plans-coverage --time-period Start=2026-08-01,End=2026-08-05`.

## Recent AWS features (2024-2026)

- **EKS Auto Mode (2024-2025):** Managed compute auto-provisioning that
  bundles Karpenter-like node management. Auto Mode handles instance
  selection, Spot/On-Demand mix, and consolidation automatically. For new
  clusters, Auto Mode eliminates the need to install Karpenter separately.
  Existing clusters should evaluate Auto Mode vs a Karpenter upgrade.

- **Karpenter consolidation improvements (v0.32+, 2024-2025):** Disruption
  budgets (`disruption.budgets`) allow rate-limiting consolidation to
  control node churn in production. `WhenEmptyOrUnderutilized` is the
  recommended consolidation policy for steady-state clusters.

- **Graviton 4 (2024-2025):** Broad rollout across EKS-supported instance
  types. Graviton 4 nodes offer up to 30% better performance than Graviton
  3. Re-evaluate Graviton migration for workloads that were not
  Graviton-3-compatible.

- **Fargate pricing unchanged:** $0.04048/vCPU-hour + $0.004445/GB-hour
  (us-east-1). Fargate Spot remains up to 75% off for interruptible workloads.
  Fargate is still not covered by Compute Savings Plans (as of 2026).

- **Compute Savings Plans enhancements (2024):** More flexible commitment
  terms. Use for any EKS EC2 node baseline with uncertain workload growth.

- **EKS Container Insights with enhanced observability (2024-2025):**
  Beyond basic ContainerInsights metrics, the enhanced observability addon
  provides per-pod cost allocation via KubeCost integration. Recommended
  for FinOps-grade cluster analysis.

- **Spot Placement Score for EKS (2024-2025):** Predicts Spot capacity
  availability before provisioning Spot node groups. Check SPS for the
  target instance types to avoid recommending Spot where capacity is scarce.

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
