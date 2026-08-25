# EKS Pod Diagnostic Commands — Reference

Supplementary reference for the EKS Pod Troubleshooter skill. The
canonical command script per failure category, with sample outputs and
interpretation notes.

## Universal first commands (run for any pod failure)

```bash
# 1. Find failing pods across the cluster.
kubectl get pods -A --field-selector status.phase!=Running,status.phase!=Succeeded

# 2. Find pods that are running but crash-looping / image-pulling.
kubectl get pods -A -o custom-columns=NS:.metadata.namespace,\
NAME:.metadata.name,STATUS:.status.phase,\
REASON:.status.containerStatuses[0].state.waiting.reason,\
RESTARTS:.status.containerStatuses[0].restartCount \
  | grep -E "CrashLoop|ImagePull|Pending|ErrImage"

# 3. Drill into one pod.
kubectl get pod <pod> -n <ns> -o wide
```

The `REASON` column is the discriminator. Common values:

- `Pending` — scheduler has not bound the pod
- `ContainerCreating` — kubelet pulling image / mounting volumes
- `CrashLoopBackOff` — container exits repeatedly
- `ImagePullBackOff` / `ErrImagePull` — image pull failing
- `CreateContainerConfigError` — kubelet cannot construct the spec
- `Evicted` — node pressure (MemoryPressure / DiskPressure) kicked the pod

## Per-category command scripts

### Category A: PENDING

```bash
# Read the exact FailedScheduling message.
kubectl describe pod <pod> -n <ns> | sed -n '/Events:/,$p'

# Or filter events by reason:
kubectl get events -n <ns> \
  --field-selector involvedObject.name=<pod>,reason=FailedScheduling \
  -o custom-columns=TIME:.lastTimestamp,MESSAGE:.message

# Node capacity:
kubectl top nodes
kubectl describe nodes | grep -E "Name:|Allocated resources|cpu|memory" -A 3

# Taints:
kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints

# Affinity / labels:
kubectl get nodes --show-labels

# Cordoned / unschedulable nodes:
kubectl get nodes -o custom-columns=NAME:.metadata.name,READY:.status.conditions[-1].type,SCHEDULABLE:.spec.unschedulable

# PVC status:
kubectl get pvc -n <ns>
kubectl describe pvc <pvc> -n <ns> | sed -n '/Events:/,$p'
```

**Interpretation:**

- The sub-string in `FailedScheduling` after `0/N nodes are available:`
  is the discriminator: `Insufficient cpu`, `Insufficient memory`,
  `node(s) had taints`, `didn't match Pod's node affinity/selector`,
  `node(s) were unschedulable`, `pod has unbound immediate
  PersistentVolumeClaims`.
- If `top nodes` shows CPU > 85% on all nodes, the cluster is
  oversubscribed.
- If PVC is `Pending`, check the StorageClass binding mode first.

### Category B: IMAGE_PULL

```bash
# Read the exact pull error:
kubectl describe pod <pod> -n <ns> | grep -A 2 "Failed to pull\|Failed.*image"

# Get the node and instance:
NODE=$(kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.nodeName}')
INSTANCE_ID=$(kubectl get node "$NODE" -o jsonpath='{.spec.providerID}' | sed 's|.*/||')

# Verify the image exists in ECR:
aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>

# List images for the repo:
aws ecr list-images --repository-name <repo> --filter tagStatus=TAGGED

# Get the node's instance role:
aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].IamInstanceProfile.Arn'

# Simulate the node role's ECR permissions:
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::<account>:role/<node-instance-role> \
  --action-names ecr:GetAuthorizationToken ecr:BatchCheckLayerAvailability \
                  ecr:GetDownloadUrlForLayer ecr:BatchGetImage \
  --resource-arns arn:aws:ecr:<region>:<account>:repository/<repo>

# Cross-account: read the repo policy in the image-owning account:
aws ecr get-repository-policy --repository-name <repo> --profile <image-acct-profile>

# Verify VPC endpoints for ECR:
aws ec2 describe-vpc-endpoints \
  --filters Name=service-name,Values=com.amazonaws.<region>.ecr.api \
                     com.amazonaws.<region>.ecr.dkr \
  --query 'VpcEndpoints[*].{id:VpcEndpointId,service:ServiceName,state:State,subnets:SubnetIds}'

# Verify ECR lifecycle policy:
aws ecr get-lifecycle-policy --repository-name <repo>
```

**Interpretation:**

- `manifest unknown` / `Requested image not found` → tag missing or
  purged by lifecycle policy.
- `unauthorized: Not Authorized` / `403 Forbidden` → node role / IRSA
  / Pod Identity missing ECR perms.
- `i/o timeout` / `dial tcp: i/o timeout` → network issue (NAT or VPC
  endpoint missing).
- `no space left on device` → node disk full; drain and roll.

### Category C: CRASH_LOOP

```bash
# Read lastState (exit code, reason, timing):
kubectl get pod <pod> -n <ns> -o jsonpath='{.status.containerStatuses[*].lastState}'

# Read application logs from the PREVIOUS (crashed) container:
kubectl logs <pod> -n <ns> --previous
kubectl logs <pod> -n <ns> -c <container> --previous

# Read events for this pod, sorted by time:
kubectl get events -n <ns> \
  --field-selector involvedObject.name=<pod> \
  --sort-by='.lastTimestamp' \
  -o custom-columns=TIME:.lastTimestamp,TYPE:.type,REASON:.reason,MESSAGE:.message

# Read the pod spec for env / command / args / image:
kubectl get pod <pod> -n <ns> -o yaml | grep -A 20 "containers:"

# Verify referenced ConfigMaps / Secrets exist:
kubectl get configmap,secret -n <ns> | grep -E "<cm-name>|<secret-name>"

# For image arch mismatch, inspect the image locally:
docker inspect <image> | grep Architecture
```

**Interpretation:**

- Exit 1 + `KeyError: 'X'` / `NameError` / `ReferenceError` → missing
  env var.
- Exit 1 + `Connection refused` / `i/o timeout` → dependency outage.
- Exit 127 / 126 + `exec format error` → image arch mismatch.
- Exit 1 + `CreateContainerConfigError` in Events → ConfigMap/Secret
  referenced but missing.
- Exit 0 + `restartPolicy: Always` → application thinks it is done; if
  it's a batch, use `restartPolicy: Never` + a `Job`.

### Category D: OOM

```bash
# Read the OOM signal:
kubectl get pod <pod> -n <ns> -o jsonpath='{.status.containerStatuses[*].lastState}'
# Expect: {"terminated":{"exitCode":137,"reason":"OOMKilled",...}}

# Read the pod's memory spec:
kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.containers[*].{name:name,resources:resources}}'

# Pod memory usage right before death (if metrics-server is up):
kubectl top pod <pod> -n <ns>
kubectl top pod <pod> -n <ns> --containers

# Node-level memory pressure:
kubectl describe node <node> | grep -A 3 "MemoryPressure\|Allocated resources"

# For longer history, query Prometheus (if installed):
# sum(container_memory_rss{namespace="<ns>",pod="<pod>"}) by (container)
```

**Interpretation:**

- `lastState.reason: OOMKilled` + exit 137 → container OOM (raise
  `limits.memory`).
- No per-container `OOMKilled` reason, but node `MemoryPressure=True`
  → node OOM (kernel OOM-killer picked a victim).
- `container_memory_rss` rising monotonically over hours/days → memory
  leak (fix the leak; meanwhile schedule restarts).

### Category E: PROBE_FAILURE

```bash
# Read probe config + container port:
kubectl get pod <pod> -n <ns> -o yaml | grep -A 15 "livenessProbe\|readinessProbe\|startupProbe\|containerPort"

# Filter probe events:
kubectl get events -n <ns> --field-selector involvedObject.name=<pod> \
  | grep -E "probe failed|Unhealthy|Killing"

# Reproduce the probe from inside the pod:
kubectl exec -n <ns> <pod> -c <container> -- \
  curl -i --max-time 5 http://localhost:<port><path>

# Check Service endpoint membership (readiness gate):
kubectl describe endpoints <svc> -n <ns>
kubectl get endpointslices -n <ns> -o wide

# For NetworkPolicy-related probe failures (kubelet runs probes on the
# node; node IP must be allowed):
kubectl get networkpolicy -n <ns>
kubectl describe networkpolicy <policy> -n <ns>
```

**Interpretation of common `kubectl get events` messages:**

- `Liveness probe failed: HTTP probe failed with statuscode: 404` →
  probe path wrong.
- `Liveness probe failed: HTTP probe failed with statuscode: 500` →
  application returning error; app has a bug.
- `Liveness probe failed: connect: connection refused` → port wrong OR
  application hasn't bound yet (initialDelaySeconds too short).
- `Readiness probe failed` + endpoints missing this pod → readiness
  path is doing its job; check what the readiness path is testing.
- `Killing container with id ... Container failed liveness probe` →
  kubelet has reached `failureThreshold` consecutive failures.

### Category F: INIT_FAILURE

```bash
# List init container statuses (find the failing one):
kubectl get pod <pod> -n <ns> \
  -o jsonpath='{range .status.initContainerStatuses[*]}{.name}{"  "}{.state}{"\n"}{end}'

# Read the failing init container's previous logs:
kubectl logs <pod> -n <ns> -c <init-container-name> --previous

# Watch live progress if the init container is slow:
kubectl logs <pod> -n <ns> -c <init-container-name> -f

# Verify the init container's image (separate from main):
kubectl get pod <pod> -n <ns> \
  -o jsonpath='{range .spec.initContainers[*]}{.name}{": "}{.image}{"\n"}{end}'

# Check init container ordering (init containers run sequentially):
kubectl get pod <pod> -n <ns> \
  -o jsonpath='{range .spec.initContainers[*]}{.name}{"\n"}{end}'
```

**Interpretation:**

- Init container `state.waiting.reason: CrashLoopBackOff` → init
  container is crashing; read its previous logs.
- Init container `state.waiting.reason: ImagePullBackOff` → init
  container image failing to pull (treat as IMAGE_PULL but for the init
  image).
- Init container `state.terminated.reason: Completed` for all init
  containers, but main containers still not starting → check
  `shareProcessNamespace`, `volumes`, and `volumeMounts` conflicts.

## Combining signals — the diagnostic trinity

```bash
# 1. EVENTS — the control plane narrative:
kubectl describe pod <pod> -n <ns> | sed -n '/Events:/,$p'

# 2. LOGS — the application error:
kubectl logs <pod> -n <ns> -c <container> --previous

# 3. EVENTS TIMELINE — order of events:
kubectl get events -n <ns> \
  --field-selector involvedObject.name=<pod> \
  --sort-by='.lastTimestamp' \
  -o custom-columns=TIME:.lastTimestamp,REASON:.reason,MESSAGE:.message
```

The richest single source is `kubectl describe pod`. It surfaces:

- `Status`, `Reason`, `Message` (top of output).
- `Containers:` section — `State` (current), `Last State` (terminated
  containers with exit code, reason, started/finished times).
- `Conditions:` — `PodScheduled`, `Initialized`, `ContainersReady`,
  `Ready`. The first `False` condition tells you where in the lifecycle
  the pod is stuck.
- `Events:` — the kubelet/scheduler narrative (last ~1 hour).

Always start with `kubectl describe pod`. The category letter (A-F)
follows from the section that contains the failure signal.

## Live-cluster EKS context commands

When you need cluster-level context (not just the pod):

```bash
# Cluster version, platform, endpoint:
aws eks describe-cluster --name <cluster> \
  --query 'cluster.{version:version,endpoint:endpoint,platform:platformVersion,ipFamily:kubernetesNetworkConfig.ipFamily}'

# Is the API server endpoint public or private?
aws eks describe-cluster --name <cluster> \
  --query 'cluster.resourcesVpcConfig.{public:endpointPublicAccess,private:endpointPrivateAccess,sg:clusterSecurityGroupId}'

# Are control-plane logs enabled? (for incident forensics past the
# 1-hour Events TTL):
aws eks describe-cluster --name <cluster> \
  --query 'cluster.logging.clusterLogging[*].{types:types,enabled:enabled}'

# List node groups and their capacity:
aws eks list-nodegroups --cluster-name <cluster>
aws eks describe-nodegroup --cluster-name <cluster> --nodegroup-name <ng> \
  --query 'nodegroup.{status:status,desired:scalingConfig.desiredSize,min:scalingConfig.minSize,max:scalingConfig.maxSize,instanceTypes:instanceTypes,amiType:amiType}'

# Verify EKS add-ons (Pod Identity agent, VPC CNI, etc.):
aws eks list-addons --cluster-name <cluster>
aws eks describe-addon --cluster-name <cluster> --addon-name eks-pod-identity-agent
```

## Output verification commands

After applying a fix:

```bash
# For Deployment spec changes: watch the rollout.
kubectl rollout status deployment/<name> -n <ns> --timeout=5m

# For pod spec changes: watch the new pod.
kubectl get pod -n <ns> -l <pod-label> -w

# For node scaling: watch the node come up.
kubectl get nodes -w
kubectl describe node <new-node> | grep -E "Ready|Conditions" -A 5

# For probe fixes: reproduce the probe from inside the pod before
# trusting the kubelet verdict.
kubectl exec -n <ns> <pod> -c <container> -- \
  curl -i --max-time 5 http://localhost:<port><path>

# For image changes: verify the new tag exists.
aws ecr describe-images --repository-name <repo> --image-ids imageTag=<new-tag>

# For PVC fixes: watch PVC bind.
kubectl get pvc <pvc> -n <ns> -w
```

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 125-136 -->

## Step 0 — locate the failing pod(s) when name/namespace is unknown

```bash
kubectl get pods -n <namespace> -o wide \
  -o custom-columns=NAME:.metadata.name,NS:.metadata.namespace,\
NODE:.spec.nodeName,STATUS:.status.phase,RESTARTS:.status.containerStatuses[0].restartCount,\
REASON:.status.containerStatuses[0].state.waiting.reason

# Find pods in a known-bad state across all namespaces:
kubectl get pods -A --field-selector status.phase!=Running,status.phase!=Succeeded

# Drill into a specific controller's pods (ReplicaSet backing a Deployment):
kubectl get pods -n <namespace> -l app=<label> -o wide
```

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 174-198 -->

## Step 2 — PENDING (FailedScheduling) commands

**Diagnostic commands:**

```bash
# Capture the exact scheduler message:
kubectl describe pod <pod> -n <ns> | grep -A 5 -i "Events\|FailedScheduling"

# Or filter events directly:
kubectl get events -n <ns> \
  --field-selector involvedObject.name=<pod>,reason=FailedScheduling \
  -o custom-columns=TIME:.lastTimestamp,MESSAGE:.message

# Node capacity vs requests:
kubectl describe nodes | grep -E "Name:|Allocated|cpu|memory|Conditions|Taints"

# Compute pressure quickly:
kubectl top nodes
kubectl top pods -n <ns> --sort-by=cpu

# Taint inventory:
kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints,READY:.status.conditions[-1].type

# PVC status (for volume-bound failures):
kubectl get pvc -n <ns>
kubectl describe pvc <pvc> -n <ns>
```

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 260-290 -->

## Step 3 — IMAGE_PULL commands

**Diagnostic commands:**

```bash
# Events with full message (the sub-string is the discriminator):
kubectl describe pod <pod> -n <ns> | grep -A 2 "Failed to pull\|Failed.*image"

# Find the node's instance identity (then map to an IAM role via the
# EC2 console or describe-instances):
kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.nodeName}'
NODE=$(kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.nodeName}')
INSTANCE_ID=$(kubectl get node "$NODE" -o jsonpath='{.spec.providerID}' | sed 's|.*/||')

# Verify the image exists:
aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>

# Verify the node instance role has ECR read perms (use the instance profile role):
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::<account>:role/<node-instance-role> \
  --action-names ecr:GetAuthorizationToken ecr:BatchCheckLayerAvailability \
                  ecr:GetDownloadUrlForLayer ecr:BatchGetImage \
  --resource-arns arn:aws:ecr:<region>:<account>:repository/<repo>

# Verify VPC endpoints for ECR:
aws ec2 describe-vpc-endpoints \
  --filters Name=service-name,Values=com.amazonaws.<region>.ecr.api \
                     com.amazonaws.<region>.ecr.dkr \
  --query 'VpcEndpoints[*].{id:VpcEndpointId,service:ServiceName,state:State,subnets:SubnetIds}'

# Verify the repo policy (cross-account):
aws ecr get-repository-policy --repository-name <repo>
```

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 325-344 -->

## Step 4 — CRASH_LOOP commands

**Diagnostic command:**

```bash
# The current container just started; the logs that explain the crash
# are in the PREVIOUS instance:
kubectl logs <pod> -n <ns> --previous
# For a specific container (when the pod has multiple):
kubectl logs <pod> -n <ns> -c <container> --previous

# Describe the pod to read lastState (exit code, reason, finishedAt):
kubectl describe pod <pod> -n <ns> | grep -A 8 "Last State\|State:"
# Or get lastState as JSON for precise parsing:
kubectl get pod <pod> -n <ns> -o jsonpath='{.status.containerStatuses[*].lastState}'

# Events timeline (filter by this pod):
kubectl get events -n <ns> \
  --field-selector involvedObject.name=<pod> \
  --sort-by='.lastTimestamp' \
  -o custom-columns=TIME:.lastTimestamp,REASON:.reason,MESSAGE:.message
```

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 401-417 -->

## Step 5 — OOM commands

**Diagnostic commands:**

```bash
# Read the OOM signal from lastState:
kubectl get pod <pod> -n <ns> -o jsonpath='{.status.containerStatuses[*].lastState}'
# Expect: {"terminated":{"reason":"OOMKilled","exitCode":137,...}}

# Pod memory usage right before death (if metrics-server is installed):
kubectl top pod <pod> -n <ns>
kubectl top pod <pod> -n <ns> --containers

# Node-level pressure:
kubectl describe node <node> | grep -A 5 "Allocated\|MemoryPressure"

# Read the pod's memory spec:
kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.containers[*].name}{"\n"}{.spec.containers[*].resources}'
```

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 474-492 -->

## Step 6 — PROBE_FAILURE commands

**Diagnostic commands:**

```bash
# Read both probes + container ports in one shot:
kubectl get pod <pod> -n <ns> -o yaml | grep -A 15 "livenessProbe\|readinessProbe\|startupProbe"
kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.containers[*].{name:name,ports:ports,liveness:livenessProbe,readiness:readinessProbe,startup:startupProbe}}'

# Filter probe events:
kubectl get events -n <ns> --field-selector involvedObject.name=<pod> \
  | grep -E "probe failed|Killing|Unhealthy"

# Reproduce the probe from inside the pod:
kubectl exec -n <ns> <pod> -c <container> -- curl -i \
  http://localhost:<port><path>

# Service endpoint membership (readiness gate):
kubectl describe endpoints <svc> -n <ns>
kubectl get endpointslices -n <ns> -o wide
```

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 543-555 -->

## Step 7 — INIT_FAILURE commands

**Diagnostic commands:**

```bash
# List init containers and their status:
kubectl get pod <pod> -n <ns> \
  -o jsonpath='{range .status.initContainerStatuses[*]}{.name}{"  "}{.state}{"\n"}{end}'

# Read the failing init container's previous logs:
kubectl logs <pod> -n <ns> -c <init-container-name> --previous

# Watch live progress if the init container is slow but not failing:
kubectl logs <pod> -n <ns> -c <init-container-name> -f
```

