---
name: eks-autoscaling-automator
description: >-
  Designs and implements EKS cluster autoscaling automation. Compares and
  deploys Cluster Autoscaler vs Karpenter (provisioner node templates,
  consolidation policies, disruption budgets), configures node-group
  scaling policies (managed node groups, min/desired/max), builds HPA
  (Horizontal Pod Autoscaler) with custom and external metrics, explains
  VPA (Vertical Pod Autoscaler) caveats and incompatibilities, deploys
  KEDA for event-driven scaling (Kafka, SQS, Prometheus), handles spot
  instance interruption (termination handler, graceful drain),
  configures overprovisioning pause-pods for fast scale-up, sets up pod
  disruption budgets to protect quorum, defines priority classes for
  workload preemption, and deploys descheduler for bin-packing
  optimization. Emits AUTOMATION_DEPLOYED with ready-to-apply Helm
  values + manifests or REVIEW_REQUIRED with the specific gap. Use when
  building EKS autoscaling, choosing Karpenter vs Cluster Autoscaler,
  or optimizing an existing scaling setup.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI or kubectl required for offline workflow
  design. Live deployment uses helm install/upgrade (Cluster Autoscaler,
  Karpenter, KEDA, descheduler), kubectl apply (HPA, VPA, PDB,
  priority classes, Karpenter NodePool/NodeClaim), aws eks update-nodegroup-config
  (managed node group scaling), and aws ec2 describe-spot-price-history
  (spot diversification analysis) — AWS CLI v2, kubectl, helm v3.
keywords:
  - EKS autoscaling
  - Karpenter
  - Cluster Autoscaler
  - Horizontal Pod Autoscaler
  - HPA
  - Vertical Pod Autoscaler
  - VPA
  - KEDA
  - spot instance interruption
  - overprovisioning
  - pod disruption budget
  - priority class
  - descheduler
  - node group scaling
  - bin-packing
  - consolidation
  - disruption budget
tags: [eks, karpenter, cluster-autoscaler, hpa, keda, spot, autoscaling, automate]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Compute
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "AUTOMATION_DEPLOYED | REVIEW_REQUIRED"
  when_to_use: >-
    Building EKS autoscaling (Karpenter or Cluster Autoscaler), configuring
    HPA/VPA/KEDA for workload scaling, handling spot instance interruptions,
    optimizing scale-up latency with overprovisioning, protecting workloads
    with PDBs and priority classes, or improving bin-packing with
    descheduler.
  activation_triggers:
    - "EKS autoscaling"
    - "Karpenter setup"
    - "Cluster Autoscaler"
    - "horizontal pod autoscaler"
    - "KEDA event-driven scaling"
    - "spot interruption handling"
    - "overprovisioning pause pods"
    - "pod disruption budget"
    - "descheduler bin-packing"
    - "node group scaling policy"
  invocation_schema: >-
    Input: either (a) an EKS cluster description (version, node count,
    workload mix, scaling requirements, spot/on-demand ratio) plus
    observability metrics, OR (b) an autoscaling request ("set up
    Karpenter with spot diversification", "configure HPA with custom
    metrics for the API deployment"). Output: deterministic AUTOSCALING
    block — TOOLING/PROVISIONING/POD_SCALING/SPOT/SAFETY/VERDICT —
    where VERDICT is AUTOMATION_DEPLOYED (Helm values + manifests ready)
    or REVIEW_REQUIRED (specific gap cited).
---

# EKS Autoscaling Automator

## Mindset

**One-line takeaway:** every EKS autoscaling system operates at two
layers — **cluster autoscaling** (adding/removing nodes, Karpenter or
Cluster Autoscaler) and **pod autoscaling** (adding/removing pods, HPA
or KEDA). A gap in either layer produces a silent failure: pods are
Pending because no node has capacity (cluster autoscaler missing), or
nodes sit idle because pod count never scales with load (HPA missing).

- **Cluster Autoscaler and Karpenter are mutually exclusive.** Running
  both causes conflicting scaling decisions — CA provisions a node,
  Karpenter de-provisions it, CA re-provisions, ad infinitum. Choose
  one. Karpenter is the newer, faster, more flexible option; CA is the
  stable, battle-tested default.
- **HPA without custom metrics is just CPU autoscaling.** Default HPA
  scales on CPU/Memory utilization. For request-driven workloads (API
  latency, queue depth, concurrent connections), HPA needs custom or
  external metrics via Prometheus Adapter or KEDA.
- **Spot without interruption handling is an outage waiting to happen.**
  Spot instances receive a 2-minute warning before termination. Without
  the node-termination handler (or Karpenter's native disruption
  handling), pods are killed ungracefully — in-flight requests lost,
  databases left in dirty state.

## Quick navigation

| You want to... | Go to |
|---|---|
| Choose Karpenter vs Cluster Autoscaler | Step 1 |
| Deploy Karpenter with NodePool + disruption budget | Step 2 |
| Deploy Cluster Autoscaler with auto-discovery | Step 3 |
| Configure managed node group scaling policies | Step 4 |
| Set up HPA with custom metrics | Step 5 |
| Understand VPA caveats and incompatibilities | Step 6 |
| Deploy KEDA for event-driven scaling | Step 7 |
| Handle spot instance interruptions | Step 8 |
| Configure overprovisioning pause-pods | Step 9 |
| Set up pod disruption budgets and priority classes | Step 10 |
| Deploy descheduler for bin-packing | Step 11 |
| Avoid common autoscaling pitfalls | Anti-Patterns |
| Recent features (Karpenter v1, disruption budgets) | Recent AWS features |

## Critical rules at a glance (do NOT bury these)

1. **Karpenter consolidation replaces nodes aggressively.** The
   `consolidationPolicy: WhenUnderutilized` (now `WhenEmptyOrUnderutilized`)
   will DELETE underutilized nodes and reschedule pods. For production,
   use `disruption budgets` (`disruptionBudgets`) to cap how many nodes
   Karpenter can disrupt at once. Without a budget, Karpenter can
   drain 50% of your nodes simultaneously during a consolidation sweep.

2. **Spot diversification across instance families is mandatory.** A
   Karpenter NodePool that requests only `c5.large` spot instances will
   be evicted en masse when c5 spot capacity disappears. Diversify
   across at least 3 instance families (e.g., `c5`, `m5`, `c6i`,
   `m6i`) with `requirements` using flexible selectors. Karpenter's
   `nodeClaims` make this explicit.

3. **Overprovisioning pause-pods create headroom for fast scale-up.**
   Without pause-pods, new pods wait for a node to boot (2-5 minutes).
   Pause-pods (low priority, resource-requesting placeholders) occupy
   scheduled capacity; when a real workload arrives, it preempts the
   pause-pods and schedules immediately. This is the single most
   effective latency-reduction technique for EKS autoscaling.

4. **HPA and VPA are incompatible for the same CPU/Memory dimension.**
   HPA scales replicas based on CPU utilization; VPA adjusts CPU
   requests per pod. Running both on CPU causes oscillation: VPA
   increases requests, HPA sees lower utilization and scales down, VPA
   adjusts again. Use VPA in `Off` recommendation mode alongside HPA,
   or use VPA for memory only.

5. **Pod disruption budgets protect against voluntary disruption only.**
   A PDB with `minAvailable: 2` prevents `kubectl drain` (voluntary)
   from evicting pods below 2. It does NOT protect against spot
   termination, node failure, or pod crash (involuntary). For spot
   workloads, combine PDB with the node-termination handler AND
   topology spread constraints.

## Pre-flight: data requirements

Designing an EKS autoscaling system requires these inputs:

| Input | Source | Why |
|---|---|---|
| EKS cluster version | `aws eks describe-cluster` | Karpenter v1 requires EKS 1.27+; some features need 1.29+ |
| Current node count and type | `kubectl get nodes -o wide` | Baseline fleet size |
| Workload resource requests | `kubectl get pods -A -o json` | Drives node sizing |
| Current HPA/VPA/KEDA state | `kubectl get hpa,vpa,kedas -A` | Don't duplicate |
| Spot vs on-demand ratio | Business requirements | Cost optimization target |
| Metrics server health | `kubectl top pods` | Required for default HPA |
| Prometheus stack (if applicable) | `kubectl get svc -n monitoring` | Required for custom-metric HPA |
| Karpenter version (if installed) | `kubectl get deployment -n kube-system karpenter` | v1 has breaking API changes |

**If the input is malformed** (missing cluster version, zero nodes,
unknown workload mix), emit:

```text
AUTOSCALING: <reference>
VERDICT: ERROR
REASON: Cannot design autoscaling — cluster version, node count, and workload resource requests are required.
GAP: Run kubectl get nodes -o wide and kubectl get pods -A -o json to supply the baseline.
```

## Process — Autoscaling design (apply in order)

### Step 0: Expert knowledge — non-obvious autoscaling behaviors

These behaviors change the workflow design if ignored:

- **Karpenter v1 replaced `AWSNodeTemplate` with `NodeClaim`.** The
  `EC2NodeClass` (previously `AWSNodeTemplate`) defines AMI, security
  groups, subnet selection. The `NodePool` (previously `Provisioner`)
  defines scheduling constraints, taints, and disruption budgets. A
  v0.32 Karpenter manifest will NOT work on v1+ without migration.

- **Karpenter consolidation has three modes.** `WhenEmpty` (only delete
  nodes with zero pods) is conservative. `WhenEmptyOrUnderutilized`
  (delete nodes with low utilization and reschedule pods to other
  nodes) is aggressive and cost-saving but disruptive. Production
  should start with `WhenEmpty` and graduate to
  `WhenEmptyOrUnderutilized` with disruption budgets.

- **Cluster Autoscaler does NOT scale down nodes with
  `cluster-autoscaler-enabled=false` annotation or pods that cannot
  be rescheduled.** A pod with `PodDisruptionBudget` blocking
  eviction, a `DoNotSchedule` inter-pod anti-affinity, or local
  storage (emptyDir with data) prevents scale-down. Nodes with these
  pods stay forever, inflating costs.

- **HPA `scaleTargetRef` must point to a scalable resource
  (Deployment, StatefulSet, or custom resource with a scale
  subresource).** A bare Pod, Job, or CronJob cannot be HPA-scaled.
  For Jobs, use KEDA's `ScaledJob` instead.

- **KEDA scalers are triggered, not polled.** KEDA watches the external
  system (Kafka topic lag, SQS queue depth) and activates the HPA when
  the trigger threshold is met. When the trigger drops to zero, KEDA
  scales the deployment to zero (HPA alone cannot scale to zero).
  This is the primary reason to use KEDA over raw HPA.

- **Spot instance interruption notices arrive via the Instance Metadata
  Service (IMDS) at the EC2 level.** The AWS Node Termination Handler
  (NTH) polls IMDS and triggers a cordon+drain before the 2-minute
  deadline. Karpenter has native disruption handling via
  `disruptionBudgets` and watches for spot interruption notices
  directly. If using Karpenter, do NOT also install NTH — it conflicts.

- **Overprovisioning pause-pods must use a priority class BELOW the
  real workloads.** The pause-pod priority class (e.g., `priority:
  -10`) must be lower than the default workload priority (usually
  `0` or higher). If the pause-pods have the same or higher priority,
  real workloads cannot preempt them, and the headroom is wasted.

- **VPA in `Auto` mode recreates pods to apply new resource requests.**
  This causes a brief outage per pod during resize. VPA cannot
  in-place resize (unlike some sidecar injection tools). Never use
  VPA `Auto` mode on production workloads with a single replica. Use
  `Initial` mode (only sets requests on pod creation) or `Off` mode
  (recommendations only, applied manually).

- **descheduler `PodLifeTime` strategy evicts old pods.** This is
  useful for forcing rescheduling onto better-packed nodes, but it
  causes pod churn. Set `maxNoOfPodsToEvictPerNode` and
  `maxNoOfPodsToEvictTotal` to avoid mass eviction. Run descheduler
  in `DryRun` mode first to preview impact.

- **Managed node group scaling via `update-nodegroup-config` is a
  separate scaling layer from CA/Karpenter.** If you set a managed
  node group's `minSize: 3, maxSize: 10, desiredSize: 5`, and ALSO
  run Cluster Autoscaler, CA will adjust `desiredSize` within the
  min/max range. Setting `desiredSize` manually is overridden by CA
  on the next scaling event.

### Step 1: Choose Karpenter vs Cluster Autoscaler

| Dimension | Karpenter | Cluster Autoscaler |
|---|---|---|
| Scaling speed | Fast (provisions in ~30s via direct EC2 API) | Slower (~2-5 min via ASG lifecycle) |
| Node selection | Flexible (any instance type, any AZ, spot+on-demand mix) | Rigid (tied to ASG/managed node group instance types) |
| Consolidation | Yes (deletes underutilized nodes) | Limited (only removes empty nodes) |
| Spot handling | Native (disruption budgets, diversified selection) | Via ASG (mixed instance policy) |
| Bin-packing | Yes (consolidation rebalances) | No |
| Maturity | v1 GA (2024), rapidly evolving | Battle-tested, stable |
| Setup complexity | Medium (Helm + NodePool + NodeClass) | Low (Helm + node group tags) |
| Cost optimization | Higher (consolidation + spot diversity) | Moderate |
| Best for | Dynamic workloads, spot-heavy, fast scale-up | Stable workloads, predictable capacity |

**Decision rule:** choose **Karpenter** if any of the following are
true: (a) spot instance usage is a priority, (b) scale-up latency must
be < 1 minute, (c) you want consolidation/bin-packing, (d) the fleet
has heterogeneous instance types. Choose **Cluster Autoscaler** if:
(a) the fleet uses fixed instance types in managed node groups, (b)
operational simplicity is more important than cost optimization, (c)
the organization needs a battle-tested, slow-moving component.

**NEVER run both.** If migrating from CA to Karpenter, uninstall CA
first, then install Karpenter. Running both causes conflicting scaling
decisions.

### Step 2: Deploy Karpenter with NodePool and disruption budgets

Helm install:

```bash
helm install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --namespace kube-system \
  --set clusterName=my-prod-cluster \
  --set interruptionQueue=true \
  --set settings.clusterName=my-prod-cluster \
  --version 1.0.0
```

NodePool with spot diversification and disruption budget:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    metadata:
      labels:
        nodepool: default
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: kubernetes.io/os
          operator: In
          values: ["linux"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values:
            - c5.large
            - c5.xlarge
            - m5.large
            - m5.xlarge
            - c6i.large
            - c6i.xlarge
            - m6i.large
            - m6i.xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      taints: []
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 30s
    budgets:
      - nodes: "20%"
      - schedule: "0 9 * * Mon-Fri"
        duration: 8h
        nodes: "0"
  deletionPolicy: Delete
```

EC2NodeClass (AMI, subnets, security groups):

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiSelectorTerms:
    - alias: al2023@latest
  subnetSelectorTerms:
    - tags:
        Name: my-prod-cluster-private-*
  securityGroupSelectorTerms:
    - tags:
        kubernetes.io/cluster/my-prod-cluster: owned
  role: KarpenterNodeRole-my-prod-cluster
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        encrypted: true
        deleteOnTermination: true
```

**Key configuration explained:**

- **`consolidationPolicy: WhenEmptyOrUnderutilized`** — Karpenter will
  delete nodes that are empty OR underutilized (pods rescheduled to
  other nodes). Use `WhenEmpty` for a conservative start.

- **`disruption.budgets`** — First budget allows 20% of nodes to be
  disrupted at any time. Second budget blocks ALL disruption during
  business hours (Mon-Fri 09:00-17:00). This is critical for production
  stability.

- **Spot diversification** — The `instance-category: In [c, m]` and
  `instance-generation: Gt 5` selectors allow Karpenter to pick from
  8+ instance types across 2 categories and 2+ generations. If c5
  spot capacity disappears, Karpenter immediately tries m5 or c6i.

- **`interruptionQueue: true`** — Enables Karpenter's native spot
  interruption handling via SQS + EventBridge. When a spot instance
  receives a 2-minute notice, Karpenter drains it and provisions a
  replacement before the deadline. Do NOT install the separate Node
  Termination Handler when this is enabled.

### Step 3: Deploy Cluster Autoscaler with auto-discovery

For clusters using managed node groups without Karpenter:

```bash
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set autoDiscovery.clusterName=my-prod-cluster \
  --set awsRegion=us-east-1 \
  --set rbac.create=true \
  --set rbac.serviceAccount.name=cluster-autoscaler \
  --set rbac.serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::111111111111:role/cluster-autoscaler-role \
  --version 9.34.0
```

**Auto-discovery tags** (must be on the node group's ASG):

```
k8s.io/cluster-autoscaler/my-prod-cluster = owned
k8s.io/cluster-autoscaler/enabled = true
```

Managed node groups automatically tag their ASGs. For self-managed
ASGs, add these tags manually.

**Key Cluster Autoscaler settings:**

```yaml
# Helm values for tuning
settings:
  scaleDownDelayAfterAdd: "10m"        # Wait 10m after scale-up before considering scale-down
  scaleDownDelayAfterDelete: "0s"      # Re-evaluate immediately after a node is deleted
  scaleDownDelayAfterFailure: "3m"     # Wait 3m after a failed scale-down
  scaleDownUnneededTime: "30m"         # A node must be unneeded for 30m before scale-down
  scaleDownUtilizationThreshold: "0.5" # Scale down nodes below 50% utilization
  maxNodeProvisionTime: "15m"          # Max time to wait for a node to provision
  skipNodesWithLocalStorage: true      # Do not scale down nodes with local storage
  skipNodesWithSystemPods: true        # Do not scale down nodes with kube-system pods
  expander: "least-waste"              # Choose node group that wastes least CPU/mem
```

### Step 4: Configure managed node group scaling policies

```bash
aws eks update-nodegroup-config \
  --cluster-name my-prod-cluster \
  --nodegroup-name my-node-group \
  --scaling-config desiredSize=5,minSize=3,maxSize=20
```

For Cluster Autoscaler, the `minSize` and `maxSize` define the scaling
range. CA adjusts `desiredSize` within this range. Do NOT set
`desiredSize` manually — it will be overridden by CA.

**Capacity provider for Fargate/EKS Auto Mode (2025+):**

EKS Auto Mode (introduced 2025) provides built-in node autoscaling
without Karpenter or CA. It uses Karpenter under the hood but is
managed by AWS. Enable via:

```bash
aws eks update-cluster-config \
  --name my-prod-cluster \
  --compute-config '{"nodeRoleArn":"arn:aws:iam::111111111111:role/EKSAutoNodeRole","enabled":true}'
```

This is the simplest path for new clusters. Existing clusters migrating
from CA to Auto Mode should uninstall CA first.

### Step 5: Set up HPA with custom metrics

**Prerequisite:** metrics-server for CPU/Memory HPA, or Prometheus
Adapter for custom metrics.

Default HPA (CPU-based):

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-server-hpa
  namespace: production
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
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
        - type: Pods
          value: 4
          periodSeconds: 15
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
      selectPolicy: Min
```

Custom-metric HPA (requires Prometheus Adapter):

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-server-custom-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-server
  minReplicas: 3
  maxReplicas: 50
  metrics:
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "1000"
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

**HPA behavior tuning guide:**

| Parameter | Effect | Production default |
|---|---|---|
| `scaleUp.stabilizationWindowSeconds` | Wait N seconds before scaling up (prevents flapping) | `0` (scale up immediately) |
| `scaleUp.policies[].type: Percent` | Scale up by N% of current replicas per period | `100%` per 15s |
| `scaleUp.policies[].type: Pods` | Scale up by N pods per period | `4` per 15s |
| `scaleDown.stabilizationWindowSeconds` | Wait N seconds before scaling down | `300` (5 min) |
| `scaleDown.policies[].type: Percent` | Scale down by N% per period | `10%` per 60s |

### Step 6: VPA caveats and incompatibilities

VPA has four modes:

| Mode | Behavior | Safe for production? |
|---|---|---|
| `Auto` | Recreates pods to apply recommended requests | No (causes pod restarts) |
| `Recreate` | Same as Auto but forces immediate recreation | No |
| `Initial` | Sets requests only on NEW pods (no restart) | Yes |
| `Off` | Recommendations only, no action | Yes (use for tuning) |

**VPA + HPA incompatibility:** if HPA scales on CPU utilization and
VPA adjusts CPU requests, they fight. VPA raises the request → HPA
sees lower utilization → HPA scales down → VPA raises again → loop.

**Resolution:** use VPA in `Off` mode to get recommendations, apply
them manually to the Deployment spec. Or use VPA for memory only (HPA
on CPU, VPA on memory — they don't conflict).

VPA manifest (recommendation-only mode):

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: api-server-vpa
  namespace: production
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: api-server
  updatePolicy:
    updateMode: "Off"
  resourcePolicy:
    containerPolicies:
      - containerName: "*"
        minAllowed:
          cpu: 100m
          memory: 128Mi
        maxAllowed:
          cpu: 4
          memory: 4Gi
        controlledResources: ["memory"]
```

### Step 7: Deploy KEDA for event-driven scaling

KEDA is the primary tool for scaling based on external systems (SQS,
Kafka, Prometheus, CloudWatch). It also enables scale-to-zero.

Helm install:

```bash
helm install keda kedacore/keda \
  --namespace keda-system \
  --create-namespace \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::111111111111:role/keda-role \
  --version 2.15.0
```

SQS-triggered ScaledObject:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: sqs-consumer-scaler
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sqs-consumer
  minReplicaCount: 1
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

Kafka-triggered ScaledObject:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: kafka-consumer-scaler
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: kafka-consumer
  minReplicaCount: 0
  maxReplicaCount: 50
  pollingInterval: 30
  triggers:
    - type: kafka
      metadata:
        bootstrapServers: kafka-broker.production:9092
        consumerGroup: my-consumer-group
        topic: events
        lagThreshold: "1000"
        offsetResetPolicy: latest
```

**KEDA vs HPA decision:** use KEDA when (a) you need scale-to-zero, (b)
the scaling trigger is an external system (not CPU/Memory), or (c) you
need multiple trigger sources. Use HPA when (a) CPU/Memory-based
scaling is sufficient, or (b) you want a simpler setup without an
additional operator.

### Step 8: Handle spot instance interruptions

**Karpenter approach (recommended):**

Karpenter handles spot interruptions natively when
`interruptionQueue: true` is set. No additional components needed.
Karpenter watches the SQS queue fed by EventBridge, receives the
2-minute notice, and:
1. Cordons the node (marks it unschedulable).
2. Drains the node (evicts pods gracefully).
3. Provisions a replacement node immediately.
4. Terminates the spot instance after drain completes.

```bash
# Create the EventBridge rule + SQS queue for Karpenter
# This is done automatically by the Karpenter Helm chart when
# interruptionQueue is set. Verify:
kubectl logs -n kube-system -l app.kubernetes.io/name=karpenter | grep "interruption"
```

**Cluster Autoscaler approach (AWS Node Termination Handler):**

```bash
helm install aws-node-termination-handler eks/aws-node-termination-handler \
  --namespace kube-system \
  --set enableSpotInterruptionDraining=true \
  --set enableReconciliationMonitoring=true \
  --set enableQueueProcessing=true \
  --set awsRegion=us-east-1 \
  --set queueURL=https://sqs.us-east-1.amazonaws.com/111111111111/nth-queue
```

**NEVER run both Karpenter's interruption handling AND NTH.** They
both watch the same SQS queue and both try to drain the same node,
causing race conditions and double-drain errors.

**Spot diversification rules (mandatory for production):**

| Rule | Why |
|---|---|
| Use at least 3 instance families | Reduces the chance that all instances are reclaimed simultaneously |
| Use at least 2 instance sizes | Same reason |
| Use at least 2 AZs | Capacity shortages are often AZ-specific |
| Set `capacity-type: [spot, on-demand]` with weights | Karpenter will prefer spot but fall back to on-demand if spot is unavailable |
| Monitor `karpenter_pods_state` metric | Shows pods in `Pending` state — indicates spot capacity exhaustion |

### Step 9: Configure overprovisioning pause-pods

Overprovisioning creates "headroom" by scheduling low-priority
placeholder pods that occupy node capacity. When real workloads
arrive, they preempt the placeholders and schedule immediately.

Priority class for pause-pods:

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: overprovisioning
value: -1
globalDefault: false
description: "Priority class for overprovisioning pause-pods (lowest priority)."
```

Pause-pod deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pause-pods
  namespace: kube-system
spec:
  replicas: 10
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: pause-pod
  template:
    metadata:
      labels:
        app: pause-pod
    spec:
      priorityClassName: overprovisioning
      containers:
        - name: pause
          image: registry.k8s.io/pause:3.9
          resources:
            requests:
              cpu: 1
              memory: 1Gi
      topologySpreadConstraints:
        - maxSkew: 1
          topology: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: pause-pod
```

**Sizing:** each pause-pod occupies 1 CPU + 1 GiB memory. For a 10-pod
headroom, Karpenter/CA will provision 10 pods worth of extra nodes.
When a real deployment scales up (e.g., +5 pods), those 5 pods preempt
5 pause-pods, which are rescheduled to new nodes by Karpenter/CA.

**Key:** the pause-pod priority (`-1`) must be LOWER than the default
priority (`0`). If equal or higher, real pods cannot preempt them.

### Step 10: Pod disruption budgets and priority classes

Pod Disruption Budget (protect quorum during voluntary disruption):

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-server-pdb
  namespace: production
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: api-server
```

Or use `maxUnavailable`:

```yaml
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: api-server
```

**`minAvailable` vs `maxUnavailable`:** use `minAvailable` for quorum
workloads (databases, stateful services) where a minimum count must
always be running. Use `maxUnavailable` for rolling-update-friendly
workloads where a percentage can be down.

Priority classes (control preemption order):

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: production-critical
value: 1000000
globalDefault: false
preemptionPolicy: PreemptLowerPriority
description: "Critical production workloads — preempt anything lower."

---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: production-standard
value: 100000
globalDefault: false
description: "Standard production workloads."

---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: batch-default
value: 10000
globalDefault: false
description: "Batch jobs — preempted by production workloads."

---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: default
value: 0
globalDefault: true
description: "Default priority for uncategorized workloads."
```

**Preemption flow:** when a node is full and a new pod is scheduled,
the scheduler checks if any lower-priority pods can be preempted. If
yes, it evicts the lower-priority pod(s) and schedules the new one.
The preempted pod goes back to Pending and waits for a new node
(Karpenter/CA provisions one).

### Step 11: Deploy descheduler for bin-packing

The descheduler evicts pods from underutilized nodes so they can be
rescheduled onto better-packed nodes (which Karpenter consolidation
then benefits from).

Helm install:

```bash
helm install descheduler descheduler/descheduler \
  --namespace kube-system \
  --set kind=Deployment \
  --set schedule="0 */2 * * *" \
  --set deschedulingInterval=2h \
  --version 0.31.0
```

Descheduler policy (strategies):

```yaml
apiVersion: "descheduler/v1alpha2"
kind: "DeschedulerPolicy"
profiles:
  - name: default
    pluginConfig:
      - name: DefaultEvictor
        args:
          maxNoOfPodsToEvictPerNode: 3
          maxNoOfPodsToEvictTotal: 50
          evictFailedBarePods: false
          evictLocalStoragePods: false
          evictSystemCriticalPods: false
          ignorePvcPods: false
      - name: RemoveDuplicates
        args:
          excludeOwnerKinds: ["ReplicaSet", "Deployment"]
          namespaces:
            include: ["production"]
      - name: RemovePodsHavingTooManyRestarts
        args:
          podRestartThreshold: 10
          includingInitContainers: true
      - name: RemovePodsViolatingNodeAffinity
        args:
          nodeAffinityType:
            - requiredDuringSchedulingIgnoredDuringExecution
      - name: RemovePodsViolatingNodeTaints
      - name: RemovePodsViolatingTopologySpreadConstraint
        args:
          constraints:
            - DoNotSchedule
            - ScheduleAnyway
      - name: LowNodeUtilization
        args:
          thresholds:
            cpu: 20
            memory: 20
            pods: 20
          targetThresholds:
            cpu: 50
            memory: 50
            pods: 50
    plugins:
      balance:
        enabled:
          - RemoveDuplicates
          - RemovePodsViolatingTopologySpreadConstraint
          - LowNodeUtilization
      deschedule:
        enabled:
          - RemovePodsHavingTooManyRestarts
          - RemovePodsViolatingNodeAffinity
          - RemovePodsViolatingNodeTaints
```

**Key safety settings:**
- `maxNoOfPodsToEvictPerNode: 3` — never evict more than 3 pods per
  node per run.
- `maxNoOfPodsToEvictTotal: 50` — never evict more than 50 pods total
  per run.
- `evictSystemCriticalPods: false` — never evict kube-system pods.
- Run in `DryRun` mode first: `--set deschedulingInterval=2h --set
  dryDescheduling=true`.

## Output format

```text
AUTOSCALING: <reference>
CLUSTER: <EKS version + node count>
TOOLING:
  - Cluster autoscaler: Karpenter <version> | Cluster Autoscaler <version> | EKS Auto Mode
  - Pod autoscaler: HPA | KEDA | VPA (Off)
  - Metrics: metrics-server | Prometheus Adapter
PROVISIONING:
  - NodePool/NodeGroup: <name>
  - Instance types: <list or diversified>
  - Spot ratio: <percentage or flexible>
  - Disruption budget: <nodes per window>
POD_SCALING:
  - HPA: <deployment> min=N max=N metric=<type>
  - KEDA: <deployment> trigger=<type> min=N max=N
  - VPA: <deployment> mode=<Off|Initial>
SPOT:
  - Interruption handling: Karpenter native | NTH
  - Diversification: <instance families>
  - Graceful drain: enabled | disabled
SAFETY:
  - Overprovisioning: <pause-pod count> x <cpu/mem>
  - PDB: <deployment> minAvailable=N
  - Priority classes: <list>
  - Descheduler: enabled | disabled
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <Helm values + kubectl manifests>
```

### Worked example — AUTOMATION_DEPLOYED, Karpenter + HPA + KEDA

```text
AUTOSCALING: prod-cluster-autoscaling
CLUSTER: EKS 1.30, 25 nodes (mix of c5/m5/c6i)
TOOLING:
  - Cluster autoscaler: Karpenter 1.0.0 (interruptionQueue enabled)
  - Pod autoscaler: HPA (CPU + custom metric) + KEDA (SQS)
  - Metrics: metrics-server + Prometheus Adapter
PROVISIONING:
  - NodePool: default (spot+on-demand, c5/m5/c6i/m6i)
  - Instance types: diversified across 4 families, 2+ sizes
  - Spot ratio: 70% spot, 30% on-demand (flexible)
  - Disruption budget: 20% nodes max, 0 during business hours
POD_SCALING:
  - HPA: api-server min=3 max=50 (CPU 70%, http_requests 1000/s)
  - KEDA: sqs-consumer min=1 max=30 (SQS lag threshold=10)
  - VPA: api-server mode=Off (recommendations only)
SPOT:
  - Interruption handling: Karpenter native (SQS + EventBridge)
  - Diversification: c5, m5, c6i, m6i (4 families)
  - Graceful drain: enabled (Karpenter cordons + drains before termination)
SAFETY:
  - Overprovisioning: 10 pause-pods x 1CPU/1Gi (headroom for fast scale-up)
  - PDB: api-server minAvailable=2, kafka-consumer maxUnavailable=1
  - Priority classes: production-critical (1M), production-standard (100K), overprovisioning (-1)
  - Descheduler: enabled (LowNodeUtilization + RemoveDuplicates, max 3 evictions/node)
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  helm install karpenter oci://public.ecr.aws/karpenter/karpenter --namespace kube-system --set clusterName=prod-cluster --set interruptionQueue=true --version 1.0.0
  kubectl apply -f nodepool-default.yaml
  kubectl apply -f ec2nodeclass-default.yaml
  kubectl apply -f hpa-api-server.yaml
  kubectl apply -f keda-scaledobject-sqs.yaml
  kubectl apply -f priority-classes.yaml
  kubectl apply -f pause-pods.yaml
  helm install descheduler descheduler/descheduler --namespace kube-system --version 0.31.0
```

### Worked example — REVIEW_REQUIRED, missing metrics server

```text
AUTOSCALING: staging-cluster-autoscaling
CLUSTER: EKS 1.28, 8 nodes
TOOLING:
  - Cluster autoscaler: Cluster Autoscaler 9.34.0
  - Pod autoscaler: NONE (HPA not configured)
  - Metrics: NOT INSTALLED
PROVISIONING:
  - Node group: managed, c5.large x 3-10
  - Spot ratio: 0% (on-demand only)
  - Disruption budget: N/A
POD_SCALING: NONE
SPOT:
  - Interruption handling: N/A (no spot)
  - Diversification: N/A
SAFETY:
  - Overprovisioning: none
  - PDB: none
  - Priority classes: default only
  - Descheduler: not installed
VERDICT: REVIEW_REQUIRED
GAP: (1) metrics-server is not installed — HPA cannot function without CPU/Memory metrics. Install: helm install metrics-server metrics-server/metrics-server --namespace kube-system. (2) No HPA configured for any workload — pods do not scale with load. (3) No PDBs — voluntary disruption (node drain, spot eviction) can take down all replicas simultaneously. (4) Only on-demand instances — significant cost savings available with spot diversification. (5) No overprovisioning — scale-up latency is 2-5 minutes (node boot time) with no headroom.
TEMPLATE: (blocked until metrics-server is installed)
```

## Anti-Patterns — NEVER do these things

- NEVER run Karpenter and Cluster Autoscaler simultaneously. They
  conflict: CA provisions a node, Karpenter's consolidation deletes
  it because it's underutilized, CA re-provisions. This creates
  infinite node churn, wastes capacity, and destabilizes the cluster.
  Uninstall one before installing the other.

- NEVER use Karpenter `consolidationPolicy: WhenEmptyOrUnderutilized`
  without a disruption budget in production. Without a budget,
  Karpenter can simultaneously disrupt a large fraction of nodes
  during a consolidation sweep, causing cascading pod rescheduling
  and potential service degradation. Always set `disruption.budgets`
  with a `nodes: "20%"` cap and a business-hours freeze window.

- NEVER use spot instances from a single instance family. When that
  family's spot capacity is reclaimed (and AWS reclaims entire instance
  families during capacity pressure), ALL spot nodes go down
  simultaneously. Diversify across at least 3 families (c5, m5, c6i,
  m6i) using Karpenter's flexible `requirements`.

- NEVER run the AWS Node Termination Handler alongside Karpenter's
  native interruption handling. Both watch the same SQS queue and
  both try to drain the same node. This causes double-drain errors,
  race conditions, and potential data loss. Use one or the other,
  not both.

- NEVER set HPA `scaleDown.stabilizationWindowSeconds` to `0`. A zero
  stabilization window causes the HPA to scale down immediately when
  load drops, then scale back up when load returns — creating
  oscillation (thrashing). Set at least `300` (5 minutes) for
  production workloads.

- NEVER use VPA in `Auto` mode on single-replica Deployments. VPA
  recreates the pod to apply new resource requests, causing a brief
  outage. For single-replica workloads, use VPA `Off` mode and apply
  recommendations manually, or increase replicas before enabling VPA.

- NEVER run HPA on CPU utilization AND VPA on CPU requests
  simultaneously. VPA raises the CPU request → HPA sees lower
  utilization → HPA scales down → VPA adjusts → oscillation. If using
  both, use VPA for memory only and HPA for CPU.

- NEVER set overprovisioning pause-pod priority equal to or higher
  than real workloads. Pause-pods must use a LOWER priority class
  (e.g., `overprovisioning: -1`) so real pods can preempt them. Equal
  or higher priority means the headroom is never reclaimed —
  pause-pods block real workloads from scheduling.

- NEVER omit PodDisruptionBudgets for multi-replica workloads in
  production. Without a PDB, a voluntary disruption (node drain,
  Karpenter consolidation, K8s upgrade) can evict all replicas
  simultaneously. A PDB with `minAvailable: 1` (or `maxUnavailable:
  1`) is the minimum safety net.

- NEVER run descheduler without `maxNoOfPodsToEvictPerNode` and
  `maxNoOfPodsToEvictTotal`. Without these caps, descheduler can evict
  hundreds of pods in a single run, causing a cascade of rescheduling
  that overwhelms the scheduler and Karpenter. Start with 3 per node
  and 50 total, then adjust based on observed impact.

- NEVER set Cluster Autoscaler `scaleDownUtilizationThreshold` above
  0.7 for production. A threshold of 0.7 means nodes below 70%
  utilization are candidates for scale-down. Setting it too high (e.g.,
  0.9) prevents scale-down almost entirely; too low (e.g., 0.3) causes
  premature scale-down and rescheduling churn.

- NEVER use EKS managed node groups with a fixed `desiredSize` when
  Cluster Autoscaler is running. CA adjusts `desiredSize` within the
  min/max range. Setting `desiredSize` manually is overridden on the
  next scaling event, and the manual value may conflict with CA's
  calculated optimal size.

- NEVER enable KEDA without setting `cooldownPeriod`. The default is
  `300` seconds, but if you set it to `0`, KEDA scales to zero
  immediately when the trigger drops, then scales back when the trigger
  returns — causing rapid scale-up/scale-down oscillation for bursty
  workloads.

- NEVER rely on PDB alone for spot workloads. PDB protects against
  voluntary disruption (drain, upgrade) but NOT against involuntary
  disruption (spot termination, hardware failure). For spot workloads,
  combine PDB with Karpenter's native interruption handling (or NTH)
  AND topology spread constraints to ensure replicas are distributed
  across nodes/AZs.

## Pre-flight safety checks (run before applying any autoscaling manifest)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (Karpenter NodePool apply, HPA apply, descheduler install, node group
  scaling config change), emit:
  `CONFIRM: About to <action> for cluster <cluster>. This affects
  <consequence>. Proceed? (yes/no)`

- **Before switching from Cluster Autoscaler to Karpenter:**
  1. Scale all workloads to fit within current nodes with 20% headroom.
  2. Uninstall Cluster Autoscaler.
  3. Wait 10 minutes for CA's scaling decisions to stabilize.
  4. Install Karpenter.
  5. Verify Karpenter picks up existing nodes via `kubectl get nodeclaims`.

- **Before enabling Karpenter `WhenEmptyOrUnderutilized` consolidation:**
  Run in `WhenEmpty` mode for at least 1 week. Monitor for unexpected
  pod rescheduling. Only switch to `WhenEmptyOrUnderutilized` after
  confirming `WhenEmpty` is stable.

- **Before deploying descheduler in production:** run in DryRun mode
  for at least 24 hours. Review the eviction list. Confirm no
  StatefulSet or critical pods are targeted.

- **For spot-heavy clusters:** verify that the interruption queue
  (SQS) is receiving events. Deploy a test spot instance, manually
  trigger a termination notice (via EC2 console), and verify
  Karpenter/NTH drains the node before the 2-minute deadline.

## Appendix A — Karpenter vs Cluster Autoscaler decision matrix

```
Is this a new EKS cluster?
├─ Yes → Use Karpenter (v1 GA, AWS-recommended for new clusters)
│        Unless: the organization requires a battle-tested component
│        with minimal API churn → Cluster Autoscaler
└─ No  → Is Cluster Autoscaler already running?
        ├─ Yes → Is consolidation/cost-optimization a priority?
        │       ├─ Yes → Migrate to Karpenter (uninstall CA first!)
        │       └─ No  → Keep Cluster Autoscaler (if it ain't broke...)
        └─ No  → Is EKS Auto Mode available (EKS 1.29+)?
                ├─ Yes → Use EKS Auto Mode (simplest path)
                └─ No  → Use Karpenter
```

## Appendix B — HPA behavior tuning quick reference

| Scenario | scaleUp policy | scaleDown policy | Stabilization |
|---|---|---|---|
| API (bursty traffic) | `Max(100% per 15s, 4 pods per 15s)` | `Min(10% per 60s)` | Down: 300s |
| Worker (queue-driven) | `Max(100% per 15s)` | `Min(5% per 60s)` | Down: 600s |
| Batch (predictable) | `Max(2 pods per 60s)` | `Min(1 pod per 120s)` | Down: 600s |
| WebSocket (sticky) | `Max(50% per 30s)` | `Min(10% per 120s)` | Down: 600s |

**Rule of thumb:** scale UP fast (users are waiting), scale DOWN slow
(don't thrash on transient dips). The `stabilizationWindowSeconds` on
scale-down should be at least 5 minutes for most workloads.

## Appendix C — Karpenter instance-type flexibility guide

| Workload type | Recommended families | Min sizes | Diversification |
|---|---|---|---|
| General-purpose web | `c5`, `m5`, `c6i`, `m6i` | `large` (2 vCPU) | 4 families |
| Memory-intensive | `r5`, `r6i`, `x2iedn` | `large` (2 vCPU) | 3 families |
| Compute-intensive | `c5`, `c6i`, `c7i` | `xlarge` (4 vCPU) | 3 families |
| GPU (ML/inference) | `g4dn`, `g5`, `g6` | `xlarge` | 3 families (limited) |
| Cost-optimized spot | `c5`, `m5`, `c6i`, `m6i`, `c6a`, `m6a` | `large` | 6 families |

**Karpenter flexible selector pattern (AMD64, cost-optimized):**

```yaml
requirements:
  - key: karpenter.k8s.aws/instance-category
    operator: In
    values: ["c", "m"]
  - key: karpenter.k8s.aws/instance-generation
    operator: Gt
    values: ["5"]
  - key: karpenter.k8s.aws/instance-cpu
    operator: In
    values: ["2", "4", "8", "16"]
  - key: karpenter.sh/capacity-type
    operator: In
    values: ["spot", "on-demand"]
```

This allows Karpenter to select from c5/c6i/c6a/c7i/m5/m6i/m6a/m7i in
sizes 2/4/8/16 vCPU — 32+ instance types. If one is unavailable,
Karpenter immediately tries the next.

## Recent AWS features (2024-2026)

- **Karpenter v1 GA (2024):** The v1 release includes breaking API
  changes: `Provisioner` → `NodePool`, `AWSNodeTemplate` →
  `EC2NodeClass`. The `consolidationPolicy` values changed
  (`WhenUnderutilized` → `WhenEmptyOrUnderutilized`). Migration from
  v0.3x requires manifest conversion.

- **Karpenter disruption budgets (2024):** `disruption.budgets` on
  NodePool allows capping how many nodes Karpenter can disrupt per
  time window. Critical for production stability. Use `nodes: "20%"`
  as a baseline and add a business-hours freeze.

- **EKS Auto Mode (2025):** AWS-managed Karpenter + node lifecycle.
  Eliminates the need to self-manage Karpenter. Enable via
  `update-cluster-config --compute-config`. Simplest path for new
  clusters. Limited customization compared to self-managed Karpenter.

- **KEDA v2.15 (2024-2025):** Added CloudWatch trigger scaler, improved
  SQS scaler with batch-aware scaling, and scale-to-zero stabilization.
  The `cooldownPeriod` now has a `stabilizationWindowSeconds` equivalent
  per trigger.

- **HPA v2 behavior API (stable, 2024):** The `behavior` field on HPA
  v2 is now stable and widely supported. It provides fine-grained
  control over scale-up/scale-down rates, stabilization windows, and
  policy selection (`Max`, `Min`, `Disabled`).

- **VPA in-place resize (2025, K8s 1.33+):** Kubernetes 1.33 introduced
  in-place pod resize (alpha), allowing VPA to adjust CPU/Memory
  requests WITHOUT recreating the pod. This eliminates the VPA pod-
  restart problem. Requires feature gate `InPlacePodVerticalScaling`.
  EKS support expected in EKS 1.33+.

- **descheduler v0.31 (2024):** New plugin architecture with
  `DeschedulerPolicy` v1alpha2. Added `RemovePodsViolatingTopologySpreadConstraint`
  strategy. Improved `LowNodeUtilization` with configurable thresholds.

## Expert heuristic: autoscaling blast radius

Autoscaling misconfiguration is the highest-frequency cause of EKS
production incidents. A Karpenter NodePool without a disruption budget
can simultaneously drain 50% of nodes. A single bad priority class can
cause production pods to be preempted by batch jobs. An HPA without a
stabilization window can oscillate a deployment between 1 and 50
replicas within minutes.

**The rule (non-obvious but critical):**

> ALWAYS start with the most conservative autoscaling settings
> (Karpenter `WhenEmpty`, HPA with 300s scale-down stabilization,
> descheduler in DryRun). Gradually enable aggressive settings only
> after observing the conservative behavior for at least 1 week in
> production.

**Why this rule exists:** Autoscaling components interact in complex
ways. Karpenter consolidation feeds pods to the scheduler, which
respects priority classes and topology spread constraints, which in
turn affect HPA scaling decisions, which affect KEDA triggers. A
change in ANY component can cascade. Conservative settings limit the
blast radius of a misconfiguration.

**Wave-enabling pattern:**

| Phase | Karpenter | HPA | KEDA | Descheduler | Duration |
|---|---|---|---|---|---|
| 1 (baseline) | `WhenEmpty` consolidation | CPU-based, 300s stabilization | Not installed | DryRun | 1 week |
| 2 (pod scaling) | `WhenEmpty` | Custom metrics added | Installed (min 1 replica) | DryRun | 1 week |
| 3 (consolidation) | `WhenEmptyOrUnderutilized` + 20% budget | As phase 2 | As phase 2 | Enabled (3 evictions/node) | 1 week |
| 4 (spot + overprovisioning) | Spot diversified + pause-pods | As phase 3 | Scale-to-zero enabled | As phase 3 | Ongoing |

**Pre-production validation protocol:**

1. **Cycle 1 — Conservative in staging.** Deploy Karpenter with
   `WhenEmpty` consolidation, HPA with CPU metrics, no KEDA, no
   descheduler. Load-test and verify scaling behavior. Monitor for
   unexpected node churn.

2. **Cycle 2 — Aggressive in staging.** Switch Karpenter to
   `WhenEmptyOrUnderutilized` with 20% disruption budget. Add custom-
   metric HPA. Install KEDA with SQS trigger. Enable descheduler.
   Load-test and verify consolidation behavior.

3. **Cycle 3 — Conservative in prod.** Promote phase 1 settings to
   production. Monitor for 1 week. If stable, promote phase 2. If
   stable, promote phase 3.

**Detection of autoscaling failure post-deploy:** CloudWatch alarm on
`karpenter_pods_state` showing pods `Pending` for > 5 minutes
(suggests capacity exhaustion or NodePool misconfiguration). Alarm on
HPA `CurrentReplicas` oscillating by > 50% within 10 minutes
(suggests thrashing). Alarm on node count dropping by > 20% within
5 minutes (suggests aggressive consolidation or mass spot eviction).

**Surface in the output:** for any recommended autoscaling automation,
include `BLAST_RADIUS: <scope>` (e.g., `cluster-wide`,
`nodepool-scoped`, `deployment-scoped`) and `VALIDATION_STATUS:
<phase-1 | phase-2 | phase-3 | phase-4>`. If `VALIDATION_STATUS` is
not `phase-4`, do NOT mark the recommendation as fully deployed.

## Domain

AWS CloudOps / Compute Automation — EKS autoscaling.

## AWS documentation

- **Karpenter** — https://karpenter.sh/docs/
- **Cluster Autoscaler on EKS** — https://docs.aws.amazon.com/eks/latest/userguide/cluster-autoscaler.html
- **Horizontal Pod Autoscaler** — https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/
- **KEDA** — https://keda.sh/docs/
- **EKS Auto Mode** — https://docs.aws.amazon.com/eks/latest/userguide/auto-mode.html
