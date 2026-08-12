# HPA, KEDA, and Descheduler Reference

Supplementary reference for the EKS Autoscaling Automator skill. Use
when configuring HPA behavior, deploying KEDA scalers, tuning
descheduler strategies, or debugging pod-scaling oscillation.

## HPA behavior API (autoscaling/v2)

The `behavior` field on HPA v2 provides fine-grained control over
scaling rates and stabilization. Without it, HPA uses default behavior
that can cause thrashing.

### Complete behavior example with comments

```yaml
behavior:
  scaleUp:
    stabilizationWindowSeconds: 0    # No stabilization for scale-up (react immediately)
    selectPolicy: Max                # Use the most aggressive policy
    policies:
      - type: Percent                # Scale up by up to 100% of current replicas
        value: 100
        periodSeconds: 15            # ... every 15 seconds
      - type: Pods                   # OR scale up by up to 4 pods
        value: 4
        periodSeconds: 15            # ... every 15 seconds
  scaleDown:
    stabilizationWindowSeconds: 300  # Wait 5 min of low load before scaling down
    selectPolicy: Min                # Use the least aggressive policy
    policies:
      - type: Percent                # Scale down by at most 10% of current replicas
        value: 10
        periodSeconds: 60            # ... every 60 seconds
```

### How HPA calculates scaling decisions

1. **Desired replicas formula (resource-based):**
   ```
   desiredReplicas = ceil(currentReplicas * (currentMetric / targetMetric))
   ```
   Example: 10 replicas, CPU at 90%, target 70%:
   `ceil(10 * (90/70)) = ceil(12.85) = 13`

2. **Tolerance:** HPA does not act if `currentMetric` is within
   `tolerance` (default 10%) of `targetMetric`. For target 70%,
   tolerance 10%: no action between 63% and 77%.

3. **Stabilization window (scale-down):** HPA considers the MINIMUM
   desired replica count over the past `stabilizationWindowSeconds`.
   This prevents immediate scale-down on a transient metric dip.

### Custom metrics via Prometheus Adapter

Prometheus Adapter config (`adapter-config.yaml`):

```yaml
rules:
  - seriesQuery: 'http_requests_per_second{namespace!="",pod!=""}'
    resources:
      overrides:
        namespace: {resource: "namespace"}
        pod: {resource: "pod"}
    name:
      matches: "^(.*)_per_second"
      as: "http_requests_per_second"
    metricsQuery: 'sum(rate(<<.Series>>{<<.LabelMatchers>>}[2m])) by (<<.GroupBy>>)'
```

This maps the Prometheus metric `http_requests_per_second` to the
Kubernetes custom metric `http_requests_per_second`, queryable by HPA
via `type: Pods`.

## KEDA scaler reference

### KEDA architecture

KEDA consists of three components:
1. **Operator** — watches ScaledObject/ScaledJob resources and creates/
   updates an internal HPA.
2. **Metrics Server** — serves external metrics (SQS depth, Kafka lag)
   to the Kubernetes metrics API, consumed by HPA.
3. **Trigger Authentication** — manages credentials for external systems
   (IRSA, connection strings, etc.).

### ScaledObject vs ScaledJob

| Feature | ScaledObject | ScaledJob |
|---|---|---|
| Target | Deployment, StatefulSet | Job (creates new Jobs on trigger) |
| Scale to zero | Yes | Yes (no Jobs running) |
| Use case | Long-running consumers (HTTP, queue workers) | Batch processing (one Job per message) |
| Pod lifetime | Continuous (Deployment lifecycle) | Per-message (Job completes) |

### Common KEDA triggers

**AWS SQS:**

```yaml
triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.us-east-1.amazonaws.com/111111111111/my-queue
      queueLength: "10"          # Target messages per replica
      awsRegion: us-east-1
      identityOwner: operator    # Use KEDA's IRSA (not workload's)
```

Scaling formula: `desiredReplicas = ceil(ceil(queueDepth / queueLength))`
Example: queue depth = 55, queueLength = 10 → `ceil(55/10) = 6` replicas.

**Kafka:**

```yaml
triggers:
  - type: kafka
    metadata:
      bootstrapServers: kafka.production:9092
      consumerGroup: my-consumer-group
      topic: events
      lagThreshold: "1000"       # Scale up when consumer group lag > 1000
      offsetResetPolicy: latest
      partitionOffsetEncryption: false
```

**Prometheus:**

```yaml
triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus-server.monitoring:9090
      metricName: http_requests_total
      threshold: "100"
      query: sum(rate(http_requests_total{namespace="production"}[2m]))
```

**CloudWatch:**

```yaml
triggers:
  - type: aws-cloudwatch
    metadata:
      namespace: AWS/ApplicationELB
      metricName: RequestCount
      dimensions:
        - name: LoadBalancer
          value: app/my-alb/1234567890
      targetMetricValue: "500"
      minMetricValue: "0"
      awsRegion: us-east-1
```

### TriggerAuthentication (IRSA for AWS)

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: aws-sqs-trigger-auth
  namespace: production
spec:
  podIdentity:
    provider: aws-eks  # Uses IRSA — no secrets needed
```

Reference in ScaledObject:

```yaml
spec:
  triggers:
    - type: aws-sqs-queue
      authenticationRef:
        name: aws-sqs-trigger-auth
```

### KEDA scale-to-zero behavior

When the trigger value drops to zero (e.g., SQS queue empty):
1. KEDA's HPA scales the deployment to `minReplicaCount`.
2. If `minReplicaCount: 0`, KEDA's operator scales the Deployment to
   `replicas: 0` and stops the HPA from re-activating.
3. When the trigger returns (e.g., new SQS message), KEDA re-activates
   the HPA and scales from 0 to `minReplicaCount` (or higher based on
   trigger value).

**Scale-from-zero latency:** the first pod after scale-from-zero takes
~30-60 seconds (pod scheduling + container startup + application init).
Use overprovisioning pause-pods to reduce this to near-zero (the pod
preempts a pause-pod on an existing node).

## Descheduler strategies reference

### Strategy comparison

| Strategy | What it does | When to use |
|---|---|---|
| `RemoveDuplicates` | Evicts duplicate pods (same ReplicaSet on same node) | After node events (add/remove) that break distribution |
| `LowNodeUtilization` | Evicts pods from underutilized nodes so they can be deleted | To feed Karpenter consolidation |
| `RemovePodsViolatingInterPodAntiAffinity` | Evicts pods violating anti-affinity rules | After topology changes |
| `RemovePodsViolatingNodeAffinity` | Evicts pods that no longer match node affinity | After node label changes |
| `RemovePodsViolatingNodeTaints` | Evicts pods that no longer tolerate node taints | After taint changes |
| `RemovePodsViolatingTopologySpreadConstraint` | Evicts pods to restore topology spread | For uneven AZ/node distribution |
| `RemovePodsHavingTooManyRestarts` | Evicts pods with excessive restarts | For crash-loop detection |
| `PodLifeTime` | Evicts pods older than a threshold | Force periodic rescheduling |

### LowNodeUtilization configuration

```yaml
- name: LowNodeUtilization
  args:
    thresholds:
      cpu: 20        # Node is "underutilized" if CPU < 20%
      memory: 20     # AND memory < 20%
      pods: 20       # AND pod count < 20% of capacity
    targetThresholds:
      cpu: 50        # Pods are evicted to nodes below these thresholds
      memory: 50
      pods: 50
    useDeviationThresholds: false  # If true, thresholds are relative to mean
```

**How it works:**
1. Descheduler identifies nodes below `thresholds` (underutilized).
2. It identifies nodes below `targetThresholds` (can accept more pods).
3. It evicts pods from underutilized nodes, targeting nodes below
   `targetThresholds`.

If no nodes are below `targetThresholds`, no eviction occurs (pods
have nowhere to go). This is the most common "descheduler does nothing"
scenario.

### Safe eviction settings

```yaml
- name: DefaultEvictor
  args:
    maxNoOfPodsToEvictPerNode: 3      # Max 3 pods evicted per node per run
    maxNoOfPodsToEvictTotal: 50       # Max 50 pods evicted total per run
    evictFailedBarePods: false        # Don't evict failed bare pods (no controller)
    evictLocalStoragePods: false      # Don't evict pods with local storage
    evictSystemCriticalPods: false    # Don't evict kube-system pods
    ignorePvcPods: false             # Don't skip pods with PVCs
    nodeFit: true                     # Only evict if the pod can fit on another node
```

**`nodeFit: true` is critical.** Without it, descheduler evicts pods
that cannot be rescheduled (no node has capacity), leaving them
Pending indefinitely. Always enable `nodeFit` in production.

## Common pod-scaling issues and fixes

| Issue | Likely cause | Fix |
|---|---|---|
| HPA never scales up | metrics-server unhealthy or custom metric not found | Verify `kubectl top pods` and `kubectl get --raw /apis/custom.metrics.k8s.io/v1beta1` |
| HPA oscillates (thrashing) | No scale-down stabilization | Set `scaleDown.stabilizationWindowSeconds: 300` |
| KEDA does not scale to zero | `minReplicaCount > 0` or trigger not detecting zero | Verify trigger metric reaches zero; check KEDA operator logs |
| KEDA cannot read SQS | IRSA not configured or wrong queue URL | Verify TriggerAuthentication and podIdentity provider |
| Descheduler evicts nothing | No nodes below targetThresholds | Lower targetThresholds or add more nodes |
| Descheduler evicts too many | No maxNoOfPodsToEvict caps | Set `maxNoOfPodsToEvictPerNode: 3` and `maxNoOfPodsToEvictTotal: 50` |
| Scale-up is slow (2-5 min) | No overprovisioning headroom | Deploy pause-pods with low priority class |
| Pods Pending after spot eviction | Karpenter cannot provision (capacity issue) | Diversify instance families; increase NodePool limits |
