# End-to-end usage scenario: eks-autoscaling-automator

A walkthrough showing the skill designing autoscaling for a production
EKS cluster: an AUTOMATION_DEPLOYED Karpenter + HPA + KEDA + spot +
overprovisioning workflow, and a REVIEW_REQUIRED staging cluster that
is missing the metrics-server prerequisite.

## Input (user prompt)

> We need to set up autoscaling for two EKS clusters. Production needs
> Karpenter with spot diversification, HPA on the API, KEDA for SQS
> consumers, and overprovisioning. Staging just needs basic HPA but
> we haven't installed metrics-server yet.

```
Design reference: prod-autoscaling-rollout-2026
Account: 111111111111
Region: us-east-1

Production cluster:
  Name: my-prod-cluster
  Version: EKS 1.30
  Nodes: 25 (managed node groups, c5.large + m5.large, on-demand only)
  metrics-server: installed, healthy
  Prometheus Adapter: installed, http_requests_per_second available
  Workloads:
    - api-server: Deployment, 5 replicas, needs CPU + custom metric HPA
    - sqs-consumer: Deployment, 3 replicas, scales on SQS depth
    - background-worker: Deployment, 10 replicas, CPU-based HPA
  Spot ratio target: 70% spot, 30% on-demand
  Instance diversification: c5, m5, c6i, m6i
  Disruption budget: 20% max, freeze Mon-Fri 09:00-17:00
  Overprovisioning: 10 pause-pods x 1CPU/1Gi
  PDB: api-server minAvailable=2, background-worker maxUnavailable=1
  Descheduler: enabled
  Current autoscaler: none (greenfield)

Staging cluster:
  Name: staging-cluster
  Version: EKS 1.28
  Nodes: 8 (managed node group, c5.large)
  metrics-server: NOT installed
  Current autoscaler: none
```

## Skill output

```text
AUTOSCALING: prod-autoscaling-rollout-2026
CLUSTER: EKS 1.30, 25 nodes
TOOLING:
  - Cluster autoscaler: Karpenter 1.0.0 (interruptionQueue enabled, native spot handling)
  - Pod autoscaler: HPA (api-server: CPU + custom; background-worker: CPU) + KEDA (sqs-consumer: SQS)
  - Metrics: metrics-server (installed) + Prometheus Adapter (installed)
PROVISIONING:
  - NodePool: default (spot+on-demand, c5/m5/c6i/m6i, 2-16 vCPU)
  - Instance types: diversified across 4 families, 2+ sizes (8+ type options)
  - Spot ratio: 70% spot, 30% on-demand (flexible via karpenter.sh/capacity-type)
  - Disruption budget: 20% nodes max normally; 0 during Mon-Fri 09:00-17:00
POD_SCALING:
  - HPA: api-server min=3 max=50 (CPU 70%, http_requests_per_second 1000/s)
  - HPA: background-worker min=5 max=30 (CPU 75%)
  - KEDA: sqs-consumer min=1 max=30 (SQS queueLength=10, cooldownPeriod=300)
  - VPA: none (not needed — HPA + KEDA cover all scaling dimensions)
SPOT:
  - Interruption handling: Karpenter native (SQS + EventBridge, interruptionQueue=true)
  - Diversification: c5, m5, c6i, m6i (4 families, 2+ generations)
  - Graceful drain: enabled (Karpenter cordons + drains before 2-min deadline)
SAFETY:
  - Overprovisioning: 10 pause-pods x 1CPU/1Gi (priority: overprovisioning=-1)
  - PDB: api-server minAvailable=2, background-worker maxUnavailable=1
  - Priority classes: production-critical (1M), production-standard (100K), overprovisioning (-1)
  - Descheduler: enabled (LowNodeUtilization + RemoveDuplicates, max 3/node, 50 total, nodeFit=true)
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  helm install karpenter oci://public.ecr.aws/karpenter/karpenter --namespace kube-system --set clusterName=my-prod-cluster --set interruptionQueue=true --version 1.0.0
  kubectl apply -f nodepool-default.yaml
  kubectl apply -f ec2nodeclass-default.yaml
  kubectl apply -f hpa-api-server.yaml
  kubectl apply -f hpa-background-worker.yaml
  helm install keda kedacore/keda --namespace keda-system --create-namespace --version 2.15.0
  kubectl apply -f keda-scaledobject-sqs.yaml
  kubectl apply -f priority-classes.yaml
  kubectl apply -f pause-pods.yaml
  kubectl apply -f pdb-api-server.yaml
  kubectl apply -f pdb-background-worker.yaml
  helm install descheduler descheduler/descheduler --namespace kube-system --version 0.31.0

---

AUTOSCALING: prod-autoscaling-rollout-2026
CLUSTER: EKS 1.28, 8 nodes (staging)
TOOLING:
  - Cluster autoscaler: NONE
  - Pod autoscaler: NONE (HPA not configured)
  - Metrics: NOT INSTALLED
PROVISIONING:
  - Node group: managed, c5.large x 3-10 (fixed type)
  - Spot ratio: 0% (on-demand only)
  - Disruption budget: N/A
POD_SCALING: NONE
SPOT:
  - Interruption handling: N/A
  - Diversification: N/A
SAFETY:
  - Overprovisioning: none
  - PDB: none
  - Priority classes: default only
  - Descheduler: not installed
VERDICT: REVIEW_REQUIRED
GAP: (1) metrics-server is NOT installed — HPA cannot function without CPU/Memory metrics. Install: helm install metrics-server metrics-server/metrics-server --namespace kube-system --set args='{--kubelet-preferred-address-types=InternalIP}'. (2) No HPA configured for any workload — pods do not scale with load. After metrics-server is installed, create HPA for each deployment. (3) No PDBs — voluntary disruption (node drain, spot eviction) can take down all replicas. (4) Only on-demand c5.large — significant cost savings available with spot diversification (estimated 60-70% reduction for non-critical staging workloads). (5) No overprovisioning — scale-up latency is 2-5 minutes. For staging this may be acceptable. (6) EKS 1.28 — consider upgrading to 1.30+ for EKS Auto Mode support.
TEMPLATE: (blocked until metrics-server is installed)
```

**Aggregate verdict: AUTOMATION_DEPLOYED for prod + REVIEW_REQUIRED
for staging.** Deploy the prod autoscaling stack immediately; the
staging cluster requires metrics-server installation before any HPA
configuration.

## What the skill caught that a generic assistant misses

1. **The CA/Karpenter mutual exclusion.** A generic assistant might
   suggest "add Karpenter alongside your existing autoscaler for
   better spot handling." The skill refuses — running both causes
   conflicting scaling decisions and node churn. Karpenter only, CA
   uninstalled.

2. **The disruption budget for production.** A generic assistant
   creates a Karpenter NodePool with `WhenEmptyOrUnderutilized`
   consolidation and no budget. The skill adds a 20% disruption cap
   with a business-hours freeze — without this, Karpenter can drain
   half the fleet during a consolidation sweep at 2pm on a Tuesday.

3. **The spot diversification across 4 families.** A generic assistant
   requests `c5.large` spot only. The skill specifies c5, m5, c6i, m6i
   with flexible category+generation selectors — when c5 spot capacity
   disappears (and it does, during regional events), Karpenter
   immediately tries m5 or c6i.

4. **The overprovisioning priority inversion.** A generic assistant
   deploys pause-pods with default priority. The skill explicitly sets
   `priorityClassName: overprovisioning` with value `-1` — lower than
   default (`0`). Without this, real workloads cannot preempt
   pause-pods and the headroom is wasted.

5. **The VPA/HPA CPU conflict awareness.** A generic assistant might
   recommend VPA alongside HPA for "better resource tuning." The skill
   explicitly omits VPA (noting "HPA + KEDA cover all scaling
   dimensions") to avoid the CPU-request oscillation that VPA+HPA
   causes.

6. **The descheduler nodeFit safety.** A generic assistant deploys
   descheduler without `nodeFit: true`. The skill enables it — without
   nodeFit, descheduler evicts pods that cannot be rescheduled, leaving
   them Pending indefinitely.

7. **The KEDA scale-from-zero latency.** A generic assistant deploys
   KEDA with `minReplicaCount: 0` and moves on. The skill notes that
   scale-from-zero takes 30-60 seconds and recommends overprovisioning
   pause-pods to eliminate this latency (the first real pod preempts a
   pause-pod on an existing warm node).

8. **The metrics-server prerequisite for staging.** A generic assistant
   creates HPA manifests for staging without checking if metrics-server
   is installed. The skill blocks — REVIEW_REQUIRED — because HPA
   cannot function without metrics-server, and deploying HPA manifests
   that reference unavailable metrics produces a silent "Conditions:
   ScalingActive: False (FailedGetResourceMetric)" state.

## Slash-command invocation

```
/aws:automate-eks-autoscaling
```

Or via the orchestrator:

```
/aws:pipeline
You: "set up Karpenter with spot for EKS"
```

## CLI routing

```bash
node cli/bin/cli.js route "EKS autoscaling"
# [Phase: Automate | Skills routed: eks-autoscaling-automator]
```

## Live-cluster invocation (requires kubectl + AWS CLI)

```bash
# Check cluster version and node count
kubectl get nodes -o wide
aws eks describe-cluster --query 'cluster.version' --output text

# Check existing autoscaling components
kubectl get deployment -n kube-system cluster-autoscaler
kubectl get deployment -n kube-system karpenter
kubectl get pods -n keda-system
kubectl get hpa -A
kubectl get vpa -A

# Check metrics-server health
kubectl top pods -n default
kubectl get apiservice v1beta1.metrics.k8s.io

# Check Prometheus Adapter custom metrics
kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1/namespaces/default/pods/*/http_requests_per_second"

# Check existing PDBs and priority classes
kubectl get pdb -A
kubectl get priorityclass

# Check node utilization
kubectl describe nodes | grep -A 5 "Allocated resources"

# Check spot instance types and pricing
aws ec2 describe-spot-price-history \
  --instance-types c5.large m5.large c6i.large m6i.large \
  --product-descriptions "Linux/UNIX" \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --query 'SpotPriceHistory[].{Type:InstanceType,Price:SpotPrice,AZ:AvailabilityZone}' \
  --output table --region us-east-1 --profile default
```

Then paste the output into the skill for autoscaling design.
