---
name: eks-autoscaling-automator
description: Designs and implements EKS cluster autoscaling automation. Compares and deploys Cluster Autoscaler vs Karpenter (provisioner node templates, consolidation policies, disruption budgets), configures node-group scaling policies, builds HPA (Horizontal Pod Autoscaler) with custom and external metrics, explains VPA (Vertical Pod Autoscaler) caveats and incompatibilities, deploys KEDA for event-driven scaling (Kafka, SQS, Prometheus), handles spot instance interruption (termination handler, graceful drain), configures overprovisioning pause-pods for fast scale-up, sets up pod disruption budgets to protect quorum, defines priority classes for workload preemption, and deploys descheduler for bin-packing optimization. Emits AUTOMATION_DEPLOYED with ready-to-apply Helm values + manifests or REVIEW_REQUIRED with the specific gap. Use when building EKS autoscaling, choosing Karpenter vs Cluster Autoscaler, or optimizing an existing scaling setup.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI or kubectl required for offline workflow design. Live deployment uses helm install/upgrade (Cluster Autoscaler, Karpenter, KEDA, descheduler), kubectl apply (HPA, VPA, PDB, priority classes, Karpenter NodePool/NodeClaim), aws eks update-nodegroup-config (managed node group scaling) — AWS CLI v2, kubectl, helm v3.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
  when_to_use: Building EKS autoscaling (Karpenter or Cluster Autoscaler), configuring HPA/VPA/KEDA for workload scaling, handling spot instance interruptions, optimizing scale-up latency with overprovisioning, protecting workloads with PDBs and priority classes, or improving bin-packing with descheduler.
  activation_triggers: EKS autoscaling, Karpenter setup, Cluster Autoscaler, horizontal pod autoscaler, KEDA event-driven scaling, spot interruption handling, overprovisioning pause pods, pod disruption budget, descheduler bin-packing, node group scaling policy
  invocation_schema: 'Input: either (a) an EKS cluster description (version, node count, workload mix, scaling requirements, spot/on-demand ratio) plus observability metrics, OR (b) an autoscaling request ("set up Karpenter with spot diversification", "configure HPA with custom metrics for the API deployment"). Output: deterministic AUTOSCALING block — TOOLING/PROVISIONING/POD_SCALING/SPOT/SAFETY/VERDICT — where VERDICT is AUTOMATION_DEPLOYED (Helm values + manifests ready) or REVIEW_REQUIRED (specific gap cited).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: EKS autoscaling, Karpenter, Cluster Autoscaler, Horizontal Pod Autoscaler, HPA, Vertical Pod Autoscaler, VPA, KEDA, spot instance interruption, overprovisioning, pod disruption budget, priority class, descheduler, consolidation, disruption budget
  tags: eks, karpenter, cluster-autoscaler, hpa, keda, spot, autoscaling, automate
---

# EKS Autoscaling Automator

## Mindset

**One-line takeaway:** every EKS autoscaling system operates at two
layers — **cluster autoscaling** (adding/removing nodes: Karpenter or
Cluster Autoscaler) and **pod autoscaling** (adding/removing pods: HPA
or KEDA). A gap in either layer produces a silent failure: pods are
Pending because no node has capacity, or nodes sit idle because pod
count never scales with load.

- **Cluster Autoscaler and Karpenter are mutually exclusive.** Running
  both causes conflicting scaling decisions — CA provisions a node,
  Karpenter de-provisions it, ad infinitum.
- **HPA without custom metrics is just CPU autoscaling.** For request-
  driven workloads (latency, queue depth), HPA needs custom/external
  metrics via Prometheus Adapter or KEDA.
- **Spot without interruption handling is an outage waiting to happen.**
  Spot instances get a 2-minute warning. Without the termination handler
  or Karpenter's native disruption, pods are killed ungracefully.

## Quick navigation

| You want to... | Go to |
|---|---|
| Choose Karpenter vs Cluster Autoscaler | Step 1 |
| Deploy Karpenter with NodePool + disruption budget | Step 2 |
| Deploy Cluster Autoscaler with auto-discovery | Step 3 |
| Configure managed node group scaling | Step 4 |
| Set up HPA with custom metrics | Step 5 |
| Understand VPA caveats | Step 6 |
| Deploy KEDA for event-driven scaling | Step 7 |
| Handle spot interruptions | Step 8 |
| Configure overprovisioning pause-pods | Step 9 |
| Set up PDBs and priority classes | Step 10 |
| Deploy descheduler for bin-packing | Step 11 |

## Critical rules at a glance (do NOT bury these)

1. **Karpenter consolidation replaces nodes aggressively.**
   `WhenEmptyOrUnderutilized` will DELETE underutilized nodes and
   reschedule pods. For production, use `disruptionBudgets` to cap how
   many nodes Karpenter disrupts at once. Without a budget, Karpenter
   can drain 50% of nodes simultaneously.

2. **Spot diversification across instance families is mandatory.** A
   NodePool requesting only `c5.large` spot will be evicted en masse
   when c5 capacity disappears. Diversify across at least 3-4 families
   (c5, m5, c6i, m6i).

3. **Overprovisioning pause-pods create headroom for fast scale-up.**
   Without them, new pods wait 2-5 minutes for a node to boot. Pause-
   pods (low priority) occupy scheduled capacity; real workloads preempt
   them and schedule immediately.

4. **HPA and VPA are incompatible for the same CPU/Memory dimension.**
   HPA scales replicas based on CPU; VPA adjusts CPU requests. Running
   both on CPU causes oscillation. Use VPA in `Off` mode alongside HPA,
   or VPA for memory only.

5. **PDBs protect against voluntary disruption only.** A PDB with
   `minAvailable: 2` prevents `kubectl drain` from evicting below 2
   replicas. It does NOT protect against spot termination (involuntary).
   For spot, combine PDB + termination handler + topology spread.

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| EKS cluster version | `eks describe-cluster` | Karpenter v1 requires 1.27+ |
| Current node count/type | `kubectl get nodes -o wide` | Baseline fleet |
| Workload resource requests | `kubectl get pods -A -o json` | Drives node sizing |
| Current HPA/VPA/KEDA | `kubectl get hpa,vpa -A` | Don't duplicate |
| Spot vs on-demand ratio | Business requirements | Cost target |
| Metrics server health | `kubectl top pods` | Required for default HPA |
| Prometheus (if custom metrics) | `kubectl get svc -n monitoring` | For custom-metric HPA |

**If the input is malformed**, emit:
```text
AUTOSCALING: <reference>
VERDICT: ERROR
REASON: Cannot design autoscaling — cluster version, node count, and workload requests are required.
GAP: Run kubectl get nodes -o wide and kubectl get pods -A -o json.
```

## Process — Autoscaling design (apply in order)

### Step 0: Expert knowledge — non-obvious autoscaling behaviors

- **Karpenter v1 replaced `AWSNodeTemplate` with `EC2NodeClass` and
  `Provisioner` with `NodePool`.** A v0.32 manifest will NOT work on v1+
  without migration.

- **Karpenter consolidation has two modes.** `WhenEmpty` (only delete
  nodes with zero pods) is conservative. `WhenEmptyOrUnderutilized`
  (delete underutilized nodes, reschedule pods) is aggressive but
  disruptive. Start with `WhenEmpty`, graduate to
  `WhenEmptyOrUnderutilized` with disruption budgets.

- **Cluster Autoscaler does NOT scale down nodes with pods that have
  PDBs blocking eviction, anti-affinity constraints, or local storage.**
  These nodes stay forever, inflating costs.

- **KEDA scalers are triggered, not polled.** KEDA activates HPA when
  the trigger threshold is met (Kafka lag, SQS depth). When the trigger
  drops to zero, KEDA scales the deployment to zero (HPA alone cannot).

- **Spot interruption notices arrive via IMDS.** Karpenter handles this
  natively via `interruptionQueue`. NTH (Node Termination Handler) also
  polls IMDS. Do NOT run both — they conflict.

- **Overprovisioning pause-pods must use a priority class BELOW real
  workloads.** If pause-pods have equal or higher priority, real pods
  cannot preempt them, and the headroom is wasted.

- **VPA `Auto` mode recreates pods to apply new requests.** This causes
  brief outages. Never use `Auto` on single-replica Deployments. Use
  `Initial` (sets on creation) or `Off` (recommendations only).

- **descheduler `PodLifeTime` evicts old pods.** Set
  `maxNoOfPodsToEvictPerNode` and run in `DryRun` first.

- **Managed node group `desiredSize` is overridden by CA.** If CA is
  running, it adjusts `desiredSize` within min/max range. Do NOT set it
  manually.

### Step 1: Choose Karpenter vs Cluster Autoscaler

| Dimension | Karpenter | Cluster Autoscaler |
|---|---|---|
| Scaling speed | ~30s (direct EC2 API) | ~2-5 min (ASG lifecycle) |
| Node selection | Flexible (any type, AZ, spot+OD mix) | Rigid (ASG instance types) |
| Consolidation | Yes (deletes underutilized nodes) | Limited (empty nodes only) |
| Spot handling | Native disruption + diversified | Via ASG mixed policy |
| Maturity | v1 GA (2024) | Battle-tested, stable |
| Best for | Dynamic, spot-heavy, fast scale | Stable, predictable capacity |

Choose **Karpenter** if: spot priority, < 1 min scale-up, consolidation
needed, heterogeneous types. Choose **CA** if: fixed types in managed
node groups, simplicity priority.

**NEVER run both.** Migrate: uninstall CA first, then install Karpenter.

### Step 2: Deploy Karpenter with NodePool and disruption budgets

```bash
helm install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --namespace kube-system \
  --set clusterName=my-prod-cluster \
  --set interruptionQueue=true \
  --version 1.0.0
```

NodePool with spot diversification + disruption budget:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 30s
    budgets:
      - nodes: "20%"
      - schedule: "0 9 * * Mon-Fri"
        duration: 8h
        nodes: "0"
```

EC2NodeClass:

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiSelectorTerms:
    - alias: al2023@latest
  subnetSelectorTerms:
    - tags: {Name: my-prod-cluster-private-*}
  securityGroupSelectorTerms:
    - tags: {kubernetes.io/cluster/my-prod-cluster: owned}
  role: KarpenterNodeRole-my-prod-cluster
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs: {volumeSize: 100Gi, volumeType: gp3, encrypted: true}
```

**Key configuration:**
- `disruption.budgets`: First budget allows 20% disruption normally.
  Second budget blocks ALL disruption Mon-Fri 09:00-17:00. Critical for
  production stability.
- Spot diversification: `instance-category: [c, m]` + `generation: >5`
  allows 8+ instance types. If c5 spot disappears, Karpenter tries m5
  or c6i immediately.
- `interruptionQueue: true`: enables native spot interruption handling
  via SQS + EventBridge. Do NOT install NTH when this is enabled.

See **references/karpenter-configuration.md** for full API reference,
requirement keys, and consolidation troubleshooting.

### Step 3: Deploy Cluster Autoscaler with auto-discovery

```bash
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set autoDiscovery.clusterName=my-prod-cluster \
  --set awsRegion=us-east-1 \
  --version 9.34.0
```

Auto-discovery tags (must be on node group ASGs):
```
k8s.io/cluster-autoscaler/my-prod-cluster = owned
k8s.io/cluster-autoscaler/enabled = true
```

Key tuning: `scaleDownUnneededTime: "30m"`,
`scaleDownUtilizationThreshold: "0.5"`,
`skipNodesWithLocalStorage: true`, `expander: "least-waste"`.

### Step 4: Configure managed node group scaling

```bash
aws eks update-nodegroup-config \
  --cluster-name my-prod-cluster --nodegroup-name my-ng \
  --scaling-config desiredSize=5,minSize=3,maxSize=20
```

For EKS Auto Mode (2025+, simplest path for new clusters):
```bash
aws eks update-cluster-config --name my-prod-cluster \
  --compute-config '{"nodeRoleArn":"arn:...","enabled":true}'
```

### Step 5: Set up HPA with custom metrics

HPA with CPU + custom metric + behavior tuning:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-server-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-server
  minReplicas: 3
  maxReplicas: 50
  metrics:
    - type: Resource
      resource:
        name: cpu
        target: {type: Utilization, averageUtilization: 70}
    - type: Pods
      pods:
        metric: {name: http_requests_per_second}
        target: {type: AverageValue, averageValue: "1000"}
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent, value: 100, periodSeconds: 15
        - type: Pods, value: 4, periodSeconds: 15
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent, value: 10, periodSeconds: 60
      selectPolicy: Min
```

**Behavior tuning guide:** scale UP fast (users waiting), scale DOWN
slow (avoid thrashing). `scaleDown.stabilizationWindowSeconds: 300`
minimum for production.

See **references/hpa-keda-descheduler.md** for custom metrics setup,
KEDA triggers, and descheduler strategies.

### Step 6: VPA caveats and incompatibilities

| Mode | Behavior | Production-safe? |
|---|---|---|
| `Auto` | Recreates pods to apply requests | No (causes restarts) |
| `Initial` | Sets requests only on NEW pods | Yes |
| `Off` | Recommendations only | Yes |

**HPA + VPA CPU conflict:** VPA raises CPU request → HPA sees lower
utilization → HPA scales down → loop. Resolution: VPA `Off` mode (apply
manually) or VPA for memory only.

### Step 7: Deploy KEDA for event-driven scaling

```bash
helm install keda kedacore/keda --namespace keda-system --create-namespace --version 2.15.0
```

SQS-triggered ScaledObject (scale-to-zero):

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: sqs-consumer-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sqs-consumer
  minReplicaCount: 0          # Scale to zero when idle
  maxReplicaCount: 30
  pollingInterval: 30
  cooldownPeriod: 300
  triggers:
    - type: aws-sqs-queue
      metadata:
        queueURL: https://sqs.us-east-1.amazonaws.com/111111111111/my-queue
        queueLength: "10"
        awsRegion: us-east-1
        identityOwner: operator
```

**KEDA vs HPA:** use KEDA when you need scale-to-zero, external-system
triggers, or multiple trigger sources. Use HPA when CPU/Memory suffices.

### Step 8: Handle spot instance interruptions

**Karpenter approach (recommended):** Set `interruptionQueue: true`.
Karpenter watches SQS fed by EventBridge, receives 2-min notice, cordons
+ drains + provisions replacement. No additional components.

**Cluster Autoscaler approach (NTH):**
```bash
helm install aws-node-termination-handler eks/aws-node-termination-handler \
  --namespace kube-system \
  --set enableSpotInterruptionDraining=true \
  --set enableQueueProcessing=true \
  --set awsRegion=us-east-1
```

**NEVER run both** — they conflict on the same SQS queue.

**Spot diversification rules:**

| Rule | Why |
|---|---|
| 3+ instance families | Reduces mass-reclamation risk |
| 2+ instance sizes | Same |
| 2+ AZs | Capacity shortages are AZ-specific |
| `capacity-type: [spot, on-demand]` | Fallback to on-demand |

### Step 9: Configure overprovisioning pause-pods

Priority class (MUST be lower than default):

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: overprovisioning
value: -1
description: "Pause-pod priority (lowest)."
```

Pause-pod Deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pause-pods
  namespace: kube-system
spec:
  replicas: 10
  strategy: {type: Recreate}
  selector: {matchLabels: {app: pause-pod}}
  template:
    metadata: {labels: {app: pause-pod}}
    spec:
      priorityClassName: overprovisioning
      containers:
        - name: pause
          image: registry.k8s.io/pause:3.9
          resources:
            requests: {cpu: 1, memory: 1Gi}
```

Each pause-pod occupies 1 CPU + 1 GiB. For 10 pods headroom, Karpenter
provisions 10 pods worth of extra nodes. When a real deployment scales
up, it preempts pause-pods and schedules immediately.

### Step 10: Pod disruption budgets and priority classes

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-server-pdb
spec:
  minAvailable: 2
  selector: {matchLabels: {app: api-server}}
```

Priority classes:

```yaml
# production-critical: value 1000000
# production-standard: value 100000
# batch-default: value 10000
# default (globalDefault): value 0
# overprovisioning: value -1
```

Preemption flow: when a node is full, the scheduler checks if lower-
priority pods can be evicted to make room for a higher-priority pod.

### Step 11: Deploy descheduler for bin-packing

```bash
helm install descheduler descheduler/descheduler \
  --namespace kube-system \
  --set kind=Deployment \
  --set schedule="0 */2 * * *" \
  --set deschedulingInterval=2h \
  --version 0.31.0
```

Key safety settings: `maxNoOfPodsToEvictPerNode: 3`,
`maxNoOfPodsToEvictTotal: 50`, `evictSystemCriticalPods: false`,
`nodeFit: true` (CRITICAL — prevents evicting pods with nowhere to go).

Run in DryRun mode first: `--set dryDescheduling=true`.

## Output format

```text
AUTOSCALING: <reference>
CLUSTER: <EKS version + node count>
TOOLING:
  - Cluster autoscaler: Karpenter <ver> | CA <ver> | EKS Auto Mode
  - Pod autoscaler: HPA | KEDA | VPA (Off)
  - Metrics: metrics-server | Prometheus Adapter
PROVISIONING:
  - NodePool: <name> / Instance types: <diversified list>
  - Spot ratio: <%> / Disruption budget: <nodes per window>
POD_SCALING:
  - HPA: <deployment> min=N max=N metric=<type>
  - KEDA: <deployment> trigger=<type> min=N max=N
  - VPA: <deployment> mode=<Off|Initial>
SPOT:
  - Interruption handling: Karpenter native | NTH
  - Diversification: <families> / Graceful drain: enabled|disabled
SAFETY:
  - Overprovisioning: <N> x <cpu/mem>
  - PDB: <deployment> minAvailable=N
  - Priority classes: <list> / Descheduler: enabled|disabled
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <Helm values + kubectl manifests>
```

### Worked example — AUTOMATION_DEPLOYED

```text
AUTOSCALING: prod-cluster-autoscaling
CLUSTER: EKS 1.30, 25 nodes
TOOLING: Karpenter 1.0.0 (interruptionQueue) | HPA + KEDA | metrics-server + Prom Adapter
PROVISIONING: default NodePool / c5,m5,c6i,m6i / 70% spot 30% OD / 20% budget, freeze biz hrs
POD_SCALING: HPA api-server 3-50 (CPU+custom) | KEDA sqs-consumer 1-30 (SQS) | VPA Off
SPOT: Karpenter native / 4 families / graceful drain
SAFETY: 10 pause-pods x 1CPU/1Gi / PDB api-server minAvail=2 / 4 priority classes / descheduler on
VERDICT: AUTOMATION_DEPLOYED
GAP: None
```

### Worked example — REVIEW_REQUIRED

```text
AUTOSCALING: staging-cluster-autoscaling
CLUSTER: EKS 1.28, 8 nodes
TOOLING: NONE | NONE | NOT INSTALLED
VERDICT: REVIEW_REQUIRED
GAP: (1) metrics-server not installed — HPA cannot function. (2) No HPA configured. (3) No PDBs. (4) On-demand only — cost savings available. (5) No overprovisioning — 2-5 min scale-up latency.
TEMPLATE: (blocked until metrics-server installed)
```

## Anti-Patterns — NEVER do these things

- NEVER run Karpenter and Cluster Autoscaler simultaneously. They
  conflict: CA provisions, Karpenter deletes, CA re-provisions.

- NEVER use `WhenEmptyOrUnderutilized` without a disruption budget in
  production. Karpenter can simultaneously disrupt a large fraction of
  nodes during consolidation.

- NEVER use spot from a single instance family. Diversify across at
  least 3-4 families to survive capacity reclamation events.

- NEVER run NTH alongside Karpenter's interruption handling. Both watch
  the same SQS queue, causing double-drain race conditions.

- NEVER set HPA `scaleDown.stabilizationWindowSeconds: 0`. Zero causes
  immediate scale-down on transient dips, then scale-back-up — thrashing.
  Set at least 300s.

- NEVER use VPA `Auto` on single-replica Deployments. VPA recreates the
  pod, causing an outage. Use `Off` or `Initial`.

- NEVER run HPA on CPU AND VPA on CPU simultaneously. They oscillate:
  VPA raises request → HPA sees lower utilization → HPA scales down.

- NEVER set pause-pod priority equal to or higher than real workloads.
  Must be lower (e.g., `-1`) so real pods can preempt them.

- NEVER omit PDBs for multi-replica production workloads. Without PDB,
  voluntary disruption can evict all replicas simultaneously.

- NEVER run descheduler without `maxNoOfPodsToEvictPerNode` and
  `maxNoOfPodsToEvictTotal`. Without caps, mass eviction overwhelms the
  scheduler. Start with 3/node and 50 total.

- NEVER set CA `scaleDownUtilizationThreshold` above 0.7. Too high
  prevents scale-down; too low causes churn. 0.5 is the sweet spot.

- NEVER rely on PDB alone for spot workloads. PDB protects against
  voluntary disruption only. Combine with Karpenter/NTH + topology
  spread constraints.

- NEVER enable KEDA without `cooldownPeriod`. Default is 300s; setting
  to 0 causes rapid scale-up/scale-down oscillation for bursty workloads.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE** before any state-changing operation.
- **Before CA→Karpenter migration:** scale workloads with 20% headroom,
  uninstall CA, wait 10 min, install Karpenter, verify NodeClaims.
- **Before `WhenEmptyOrUnderutilized`:** run `WhenEmpty` for 1 week.
- **Before descheduler in prod:** run in DryRun for 24h.
- **For spot clusters:** verify SQS interruption queue receives events.

## Appendix A — Karpenter vs CA decision tree

```
New cluster? → Karpenter (AWS-recommended) unless org needs CA stability
Existing CA? → Consolidation needed? → Yes: migrate to Karpenter
                                  → No: keep CA
EKS Auto Mode available (1.29+)? → Use Auto Mode (simplest)
```

## Appendix B — HPA behavior quick reference

| Scenario | scaleUp | scaleDown | Stabilization |
|---|---|---|---|
| API (bursty) | Max(100%/15s, 4 pods/15s) | Min(10%/60s) | Down: 300s |
| Worker (queue) | Max(100%/15s) | Min(5%/60s) | Down: 600s |
| Batch | Max(2 pods/60s) | Min(1/120s) | Down: 600s |

**Rule:** scale UP fast (users waiting), scale DOWN slow (avoid thrash).

## Appendix C — Spot instance diversification

| Workload | Families | Min size |
|---|---|---|
| General web | c5, m5, c6i, m6i | large (2 vCPU) |
| Memory-heavy | r5, r6i, x2iedn | large |
| Compute-heavy | c5, c6i, c7i | xlarge (4 vCPU) |
| GPU (ML) | g4dn, g5, g6 | xlarge |

Karpenter flexible selector (AMD64, cost-optimized):
```yaml
requirements:
  - {key: karpenter.k8s.aws/instance-category, operator: In, values: ["c", "m"]}
  - {key: karpenter.k8s.aws/instance-generation, operator: Gt, values: ["5"]}
  - {key: karpenter.k8s.aws/instance-cpu, operator: In, values: ["2", "4", "8", "16"]}
  - {key: karpenter.sh/capacity-type, operator: In, values: ["spot", "on-demand"]}
```

## Recent AWS features (2024-2026)

- **Karpenter v1 GA (2024):** Breaking API changes — `Provisioner` →
  `NodePool`, `AWSNodeTemplate` → `EC2NodeClass`.
- **Disruption budgets (2024):** `disruption.budgets` on NodePool caps
  simultaneous node disruption. Use `nodes: "20%"` + business-hours
  freeze.
- **EKS Auto Mode (2025):** AWS-managed Karpenter + node lifecycle.
  Simplest path for new clusters. Enable via `update-cluster-config`.
- **KEDA v2.15 (2024-2025):** CloudWatch trigger, improved SQS scaler,
  scale-to-zero stabilization.
- **HPA v2 behavior (stable):** Fine-grained scale-up/down control with
  stabilization windows and policy selection.
- **VPA in-place resize (2025, K8s 1.33+):** Alpha feature allowing VPA
  to adjust requests WITHOUT recreating pods. EKS support expected 1.33+.

## Expert heuristic: autoscaling blast radius

> ALWAYS start with conservative settings (Karpenter `WhenEmpty`, HPA
> 300s stabilization, descheduler DryRun). Enable aggressive settings
> only after observing conservative behavior for 1 week in production.

**Why:** autoscaling components interact: Karpenter consolidation feeds
pods to the scheduler, which respects priority + topology spread, which
affects HPA decisions, which affect KEDA triggers. A change in ANY
component can cascade.

**Wave-enabling pattern:**

| Phase | Karpenter | HPA | KEDA | Descheduler |
|---|---|---|---|---|
| 1 | `WhenEmpty` | CPU, 300s stab | Not installed | DryRun |
| 2 | `WhenEmpty` | + custom metrics | Installed (min 1) | DryRun |
| 3 | `WhenEmptyOrUnderutilized` + 20% budget | As 2 | As 2 | Enabled (3/node) |
| 4 | + spot + pause-pods | As 3 | Scale-to-zero | As 3 |

**Failure detection:** alarm on `karpenter_pods_state` Pending > 5 min
(capacity issue). Alarm on HPA `CurrentReplicas` oscillating > 50%
in 10 min (thrashing). Alarm on node count dropping > 20% in 5 min
(aggressive consolidation or mass spot eviction).

## Domain

AWS CloudOps / Compute Automation — EKS autoscaling.

## AWS documentation

- **Karpenter** — https://karpenter.sh/docs/
- **Cluster Autoscaler on EKS** — https://docs.aws.amazon.com/eks/latest/userguide/cluster-autoscaler.html
- **Horizontal Pod Autoscaler** — https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/
- **KEDA** — https://keda.sh/docs/
- **EKS Auto Mode** — https://docs.aws.amazon.com/eks/latest/userguide/auto-mode.html
