# EKS Cost Optimization Reference

Load this reference when analyzing or planning EKS cost optimization. Contains
pricing tables, Fargate breakeven formulas, Karpenter vs Cluster Autoscaler
comparison, and Spot safety checklists.

## EKS pricing components (2026, us-east-1)

| Component | Cost | Notes |
|---|---|---|
| EKS control plane | $0.10/hour ($73/month) | Per cluster, fixed. Not reduced by node right-sizing. |
| EC2 managed node group nodes | EC2 instance hourly rate | Standard EC2 pricing; Spot up to 90% off. |
| Fargate (per pod) | $0.04048/vCPU-hr + $0.004445/GB-hr | Per pod, per second, 1-min minimum. |
| Fargate Spot | Up to 75% off Fargate | For interruptible workloads. |
| Load balancers | ALB/NLB pricing | Not covered by this skill. |
| Data transfer | Cross-AZ $0.01/GB each way | Intra-cluster cross-AZ pod-to-pod is free. |

## Fargate breakeven calculator

```
# Inputs
pod_vcpu = 1         # vCPU requested by the pod
pod_mem_gb = 2       # GB requested by the pod
pod_count = 10       # number of pods

ec2_instance = "m5.large"
ec2_hourly = 0.096   # us-east-1 On-Demand
pods_per_node = 10   # how many pods fit on one m5.large

# Fargate cost
fargate_per_pod_hour = (pod_vcpu * 0.04048) + (pod_mem_gb * 0.004445)
fargate_monthly = fargate_per_pod_hour * pod_count * 730

# EC2 cost
ec2_nodes_needed = ceil(pod_count / pods_per_node)
ec2_monthly = ec2_hourly * ec2_nodes_needed * 730

# Verdict
if fargate_monthly < ec2_monthly:
    print("Fargate cheaper: $" + str(fargate_monthly) + " vs $" + str(ec2_monthly))
else:
    print("EC2 cheaper: $" + str(ec2_monthly) + " vs $" + str(fargate_monthly))
```

### Breakeven reference table (steady-state, On-Demand)

| Pod size (vCPU + GB) | Pods to break even vs m5.large | Fargate monthly/pod | EC2 monthly/pod (at 10 pods/node) |
|---|---|---|---|
| 0.25 vCPU + 0.5 GB | ~38 pods | $10.25 | $7.01 (at 10 pods/node) |
| 0.5 vCPU + 1 GB | ~19 pods | $17.18 | $7.01 |
| 1 vCPU + 2 GB | ~10 pods | $34.36 | $7.01 |
| 2 vCPU + 4 GB | ~5 pods | $68.72 | $14.02 (at 5 pods/node) |
| 4 vCPU + 8 GB | ~2 pods | $137.44 | $35.04 (at 2 pods/node) |

**Rule of thumb:** Below 3-4 steady pods per equivalent EC2 node, Fargate
is typically cheaper. Above that density, EC2 is cheaper.

## Karpenter vs Cluster Autoscaler — detailed comparison

| Dimension | Cluster Autoscaler | Karpenter |
|---|---|---|
| Architecture | Scales ASG / managed node group desired size | Provisions EC2 instances directly (no ASG) |
| Scaling trigger | Pending pods | Pending pods + consolidation |
| Consolidation — empty nodes | Yes (scales down when nodes are empty) | Yes |
| Consolidation — partially used | No (keeps nodes with any non-DaemonSet pod) | Yes (replaces with cheaper/better-fit instance) |
| Consolidation cadence | N/A | Every ~10 seconds (v0.32+) |
| Instance selection | Fixed per node group config | Dynamic — selects from a list of instance types |
| Spot handling | Requires AWS Node Termination Handler | Native disruption handling |
| Spot fallback | Manual (multiple node groups) | Automatic (tries next instance type) |
| Bin-packing | Relies on kube-scheduler (one pod at a time) | Considers all pending pods together |
| Typical savings vs CA baseline | — | 20-40% |
| Setup complexity | Lower (EKS managed add-on) | Higher (Helm install + NodePool/NodeClaim config) |
| Disruption budgets | N/A | `disruption.budgets` for rate-limiting |
| EKS Auto Mode | No | Yes (Auto Mode bundles Karpenter) |

## Spot Instance safety checklist

Before recommending a Spot node group or Karpenter Spot capacity, verify
ALL of the following:

1. **PodDisruptionBudget** is configured for every deployment:
   ```bash
   kubectl get pdb --all-namespaces
   ```
   Each PDB must have `minAvailable` or `maxUnavailable` set. Without a PDB,
   Spot drain can evict all replicas simultaneously.

2. **Graceful drain mechanism** is installed:
   - For Cluster Autoscaler: AWS Node Termination Handler (NTH) via Helm.
   - For Karpenter: native disruption handling (no extra install needed).

3. **terminationGracePeriodSeconds** is set appropriately:
   ```yaml
   spec:
     terminationGracePeriodSeconds: 60  # default is 30; increase for slow shutdown
   ```

4. **Multi-AZ scheduling** to avoid correlated Spot interruptions:
   ```yaml
   topologySpreadConstraints:
     - maxSkew: 1
       topologyKey: topology.kubernetes.io/zone
       whenUnsatisfiable: ScheduleAnyway
   ```

5. **Multiple instance type alternatives** (3+) so the scheduler/Karpenter
   can fall back when one Spot type is exhausted:
   ```yaml
   # Karpenter NodePool
   requirements:
     - key: karpenter.k8s.aws/instance-family
       operator: In
       values: ["m5", "m6i", "m7i"]  # 3+ families
   ```

6. **No stateful workloads** on Spot nodes. Verify with:
   ```bash
   kubectl get pods --all-namespaces -o json | \
     jq '.items[] | select(.spec.affinity.nodeAffinity.requiredDuringSchedulingIgnoredDuringExecution.nodeSelectorTerms[0].matchExpressions[0].values[] | test("spot")) | select(.metadata.annotations."example.com/stateful" == "true")'
   ```

## Bin-packing optimization reference

### Requests tuning formula

```
CPU request    = p95(CPU usage over 30 days)    # round up to nearest 25m
Memory request = p99(Memory usage over 30 days)  # add 10-15% buffer (OOMKill risk)
CPU limit      = 2 * CPU request                 # or remove for latency-sensitive workloads
Memory limit   = Memory request                  # or slightly above
```

### VPA (Vertical Pod Autoscaler) setup

```bash
# Install VPA recommender
git clone https://github.com/kubernetes/autoscaler.git
cd autoscaler/vertical-pod-autoscaler
./vpa-up.sh

# Create a VPA in recommendation mode
cat <<EOF | kubectl apply -f -
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
  namespace: prod
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"   # recommendation only; apply manually
EOF

# View recommendations
kubectl get vpa my-app-vpa -n prod -o jsonpath='{.status.recommendation}'
```

### Common requests/limits pitfalls

| Pitfall | Effect | Fix |
|---|---|---|
| CPU request too high (e.g., 4000m, using 500m) | Nodes appear full; scheduler rejects pods; cluster over-provisions | Set request to p95 usage |
| Memory request too low | OOMKill under memory pressure | Set request to p99 + 15% buffer |
| CPU limit set, request not set | Scheduler uses default request; nodes oversubscribed | Always set request explicitly |
| Memory limit < request | Immediate OOMKill when pod exceeds limit | Set limit >= request |
| No requests at all | Scheduler cannot place pods; QoS class becomes BestEffort | Always set requests |

## Graviton node group migration checklist

1. **Verify multi-arch images:**
   ```bash
   docker manifest inspect <image:tag> | jq '.manifests[].platform.architecture'
   # Must include "arm64"
   ```

2. **Verify workload compatibility:**
   - JVM (Java 11+): full support.
   - Python: pure-Python works; C-extension packages need arm64 wheels.
   - Go: pure-Go works; CGO with x86 assembly needs recompile.
   - Node.js: works; native addons (.node) need arm64 builds.
   - C/C++/Rust: recompile for aarch64.

3. **Create a Graviton node group:**
   ```bash
   aws eks create-nodegroup \
     --cluster-name <cluster> \
     --nodegroup-name graviton-ng \
     --instance-types m7g.large \
     --ami-type AL2023_ARM_64 \
     --node-role <node-role-arn> \
     --subnets <subnet-ids> \
     --scaling-config minSize=2,desiredSize=2,maxSize=10
   ```

4. **Cordon x86 nodes gradually; verify pods reschedule on Graviton.**

## Cost estimation formulas

### EC2 node group monthly cost
```
monthly = instance_hourly * desired_size * 730
```

### Fargate monthly cost (per pod)
```
monthly_per_pod = (vCPU_request * 0.04048 + memory_GB_request * 0.004445) * 730
monthly_total = monthly_per_pod * pod_count
```

### Spot savings
```
spot_hourly = on_demand_hourly * (1 - spot_discount)
# Spot discount is typically 60-90% depending on instance type and AZ
```

### Karpenter consolidation savings estimate
```
savings = (pre_karpenter_nodes - post_karpenter_nodes) * avg_node_hourly * 730
# Conservative: 20% node reduction; Aggressive: 40% node reduction
```

### Savings Plan savings (EC2 nodes only)
```
savings = committed_hourly_spend * discount_rate * 730
# 1-yr Compute SP: ~30% off; 3-yr Compute SP: ~50% off
```

## Instance type quick reference (EKS common, 2026)

| Instance type | vCPU | Memory | On-Demand $/hr | Spot est. $/hr | Graviton equiv. |
|---|---|---|---|---|---|
| m5.large | 2 | 8 GB | $0.096 | $0.029 | m7g.large |
| m5.xlarge | 4 | 16 GB | $0.192 | $0.058 | m7g.xlarge |
| m5.2xlarge | 8 | 32 GB | $0.384 | $0.115 | m7g.2xlarge |
| m6i.large | 2 | 8 GB | $0.096 | $0.029 | m7g.large |
| m6i.xlarge | 4 | 16 GB | $0.192 | $0.058 | m7g.xlarge |
| m7i.large | 2 | 8 GB | $0.096 | $0.029 | m7g.large |
| m7i.xlarge | 4 | 16 GB | $0.192 | $0.058 | m7g.xlarge |
| m7g.large (Graviton) | 2 | 8 GB | $0.077 | $0.023 | — |
| m7g.xlarge (Graviton) | 4 | 16 GB | $0.154 | $0.046 | — |
| c6i.large | 2 | 4 GB | $0.085 | $0.026 | c7g.large |
| c7g.large (Graviton) | 2 | 4 GB | $0.068 | $0.020 | — |
| r6i.large | 2 | 16 GB | $0.126 | $0.038 | r7g.large |
| r7g.large (Graviton) | 2 | 16 GB | $0.101 | $0.030 | — |

Prices are approximate us-east-1 rates as of 2026. Always verify with
`aws ec2 describe-spot-price-history` for current Spot prices.

## Pre-flight data-gathering CLI commands

```bash
# 1. Confirm Container Insights is enabled
aws eks describe-cluster --name <cluster> --query 'cluster.logging' --output json
aws logs describe-metric-filters \
  --log-group-name /aws/containerinsights/<cluster>/performance --output json

# 2. Pull 14-30 day node utilization
START=$(date -d '-30 days' +%FT%TZ)
END=$(date +%FT%TZ)
aws cloudwatch get-metric-statistics \
  --namespace ContainerInsights --metric-name node_cpu_utilization \
  --dimensions Name=ClusterName,Value=<cluster> Name=NodeGroupName,Value=<ng> \
  --start-time $START --end-time $END --period 3600 --statistics Average,Maximum \
  --output json > node-cpu.json
aws cloudwatch get-metric-statistics \
  --namespace ContainerInsights --metric-name node_memory_utilization \
  --dimensions Name=ClusterName,Value=<cluster> Name=NodeGroupName,Value=<ng> \
  --start-time $START --end-time $END --period 3600 --statistics Average,Maximum \
  --output json > node-mem.json

# 3. Pod-level utilization (bin-packing signal)
aws cloudwatch get-metric-statistics \
  --namespace ContainerInsights --metric-name pod_cpu_utilization \
  --dimensions Name=ClusterName,Value=<cluster> \
  --start-time $START --end-time $END --period 3600 --statistics Average,Maximum \
  --output json > pod-cpu.json

# 4. In-cluster signals
kubectl top nodes --heapster-scheduler --sort-by=cpu
kubectl describe node <node> | grep -A 5 "Allocated resources"

# 5. Node group config
aws eks describe-nodegroup --cluster-name <cluster> --nodegroup-name <ng> --output json

# 6. Per-pod requests vs usage
kubectl get pods --all-namespaces -o json | jq '.items[] | {
  pod: .metadata.name, ns: .metadata.namespace,
  cpu_request: .spec.containers[].resources.requests.cpu,
  mem_request: .spec.containers[].resources.requests.memory}'
kubectl top pods --all-namespaces

# 7. VPA recommendations
kubectl apply -f vpa-recommender.yaml
kubectl get vpa <vpa-name> -o json | jq '.status.recommendation'

# 8. Capture pre-state before changes
aws eks describe-nodegroup --cluster-name <c> --nodegroup-name <ng> \
  --output json > /tmp/<ng>-pre-$(date +%s).json
```

## Detailed expert heuristics (non-obvious EKS cost behaviours)

- **Pod `requests` is the scheduling currency, not `limits`.** The scheduler
  places pods based on `requests`, not `limits` and not actual usage. A node at
  10% actual CPU can still be "full" if pods have inflated requests.
- **Fargate does not support DaemonSets, privileged pods, or hostNetwork.**
  Verify no DaemonSet dependencies before recommending Fargate.
- **Fargate pricing is per-pod-per-second with a 1-minute minimum.** A pod
  requesting 2 vCPU + 4 GB costs the same at 5% or 95% usage.
- **Spot gives a 2-minute warning.** NTH or Karpenter intercepts and
  cordon-drains. Without them, pods get 30s default grace period.
- **Karpenter consolidation: delete + replace.** Delete removes empty nodes;
  replace swaps underutilized nodes for cheaper alternatives. Runs every ~10s.
- **EKS Auto Mode (2024-2025) bundles Karpenter-like provisioning.** New
  clusters: Auto Mode eliminates separate Karpenter install.
- **Graviton requires multi-arch images.** Single-arch x86 images fail with
  `ImagePullBackOff` on arm64 nodes. Verify via `docker manifest inspect`.
- **Managed node group updates respect PDB.** A PDB that blocks drainage
  stalls the update.
- **Compute Savings Plans cover EC2 nodes, NOT Fargate.** Never claim Savings
  Plan savings on Fargate spend.
- **Cluster Autoscaler never consolidates partially-used nodes.** Karpenter
  does — this is the 20-40% savings source.
- **Cross-AZ pod-to-pod traffic within a cluster is free.** Cross-AZ to
  RDS/ElastiCache/ALB is $0.01/GB each way.

## Additional worked examples

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
CONFIRM: Before creating the Fargate profile, emit and await operator approval.
```

### Worked example — already optimal

```text
TARGET: prod-cluster/prod-karpenter-spot
VERDICT: ALREADY_OPTIMAL
REASON: Karpenter-managed cluster with consolidation enabled, Spot capacity
  for fault-tolerant workloads, On-Demand baseline covered by a 3-year
  Compute Savings Plan. Pod requests tuned via VPA (ratio 1.3x). Node
  utilization 55% CPU / 62% Memory — healthy with headroom.
RECOMMENDATION:
  Current: Karpenter with m7i.xlarge Spot + On-Demand mix, 3-yr Savings Plan
  Proposed: no change
  Confidence: HIGH — all dimensions optimized.
ESTIMATED_SAVINGS:
  Monthly: $0 (all layers)
  Annual total: $0
MIGRATION_STEPS:
  - None required. Re-evaluate quarterly.
  - Monitor Spot interruption rate via CloudWatch.
```

### Worked example — NEED_MORE_INFO (Container Insights absent)

```text
TARGET: staging-cluster/staging-ng
VERDICT: NEED_MORE_INFO
REASON: Container Insights is not enabled on staging-cluster.
RECOMMENDATION:
  Current: m5.xlarge x 3 nodes at On-Demand
  Proposed: pending data
  Confidence: LOW — no utilization data available.
ESTIMATED_SAVINGS: $0 (cannot quantify)
MIGRATION_STEPS:
  1. Enable Container Insights:
     aws eks update-cluster-config --name staging-cluster \
       --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
  2. Wait 14-30 days.
  3. Re-evaluate.
```

## Full NEVER list (anti-patterns)

- NEVER recommend a node group downsize without first checking the pod
  requests-to-usage ratio. Inflated requests make nodes appear "full" while
  actual usage is low.
- NEVER recommend Fargate without verifying no DaemonSets, privileged pods,
  or hostNetwork are in use.
- NEVER recommend a Spot node group without verifying PodDisruptionBudget
  (PDB) and a graceful drain mechanism (NTH or Karpenter native).
- NEVER recommend Spot for stateful workloads (databases, message queues,
  singleton services, or any pod with local state).
- NEVER claim Compute Savings Plan savings on Fargate spend. CSPs apply to
  EC2 instance spend only.
- NEVER recommend Graviton node groups without verifying every pod's
  container image has an arm64 manifest entry.
- NEVER recommend a single instance type for a Spot node group or Karpenter
  NodePool. Always provide 3+ alternative instance types.
- NEVER assume Cluster Autoscaler consolidates partially-utilized nodes.
  Only Karpenter does this.
- NEVER recommend Fargate for a high-density steady-state workload (> 6
  pods per equivalent EC2 node). Always compute the breakeven.
- NEVER set memory `limit` below `request`. Memory limit < request causes
  OOMKill.
- NEVER trigger a managed node group update during peak traffic. Schedule
  for off-peak hours.
- NEVER recommend Karpenter without configuring disruption budgets for
  production. Use `disruption.budgets` to control the pace.
- NEVER assume EKS Fargate pods have access to the same security group as
  EC2 nodes. Fargate pods use the Fargate profile's pod execution role.
- NEVER ignore the EKS control plane cost ($73/month) in fleet-wide
  analysis. A fleet of 10 small clusters pays $730/month in control planes.
- NEVER recommend removing `requests` entirely. Without requests, the
  scheduler cannot make placement decisions.
- NEVER assume Container Insights CPU and `kubectl top nodes` will always
  agree. Trust `kubectl top` for fresher data, Container Insights for
  historical trends.

## Pre-flight safety checks (full detail)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval.
- **Verify PDB before Spot migration:**
  `kubectl get pdb --all-namespaces` — confirm every deployment has a PDB.
- **Verify multi-arch images before Graviton migration:**
  `docker manifest inspect <image>` — confirm arm64 entry exists.
- **Verify no DaemonSet dependencies before Fargate migration:**
  `kubectl get ds --all-namespaces` — check target pods.
- **Drain nodes one at a time during cutover.** Cordoning all nodes at
  once causes mass pod rescheduling.
- **Batch limit for fleet-wide remediation.** Sort by savings, batch of
  at most 3 node groups, single CONFIRM per batch, verify before next batch.
- **Capture pre-state before changes:**
  `aws eks describe-nodegroup --cluster-name <c> --nodegroup-name <ng> --output json > /tmp/<ng>-pre-$(date +%s).json`
- **Verify Savings Plan coverage post-commitment.** Takes up to 1 hour to
  propagate. Verify with `aws ce get-savings-plans-coverage`.
