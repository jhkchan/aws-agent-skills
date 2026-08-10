---
name: eks-pod-troubleshooter
description: >-
  Diagnoses why Kubernetes pods fail on Amazon EKS — CrashLoopBackOff,
  ImagePullBackOff / ErrImagePull, Pending (FailedScheduling), OOMKilled,
  unhealthy probes (Liveness/Readiness), and Init:CrashLoopBackOff — via a
  symptom-to-cause decision tree that combines kubectl describe pod events,
  container lastState (exit code, OOMKilled), kubectl logs --previous for
  application errors, kubectl get events timeline, ECR auth and node-role
  permissions, node taints and resource pressure, and probe path/port
  misconfiguration. Emits a deterministic verdict
  (ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE) with the specific failure
  category and evidence from kubectl describe / logs / get-events /
  aws eks describe-cluster. Use when a pod is stuck in Pending, crash-looping,
  cannot pull an image, fails liveness/readiness probes, is OOMKilled, or has
  a failing init container.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline diagnosis works on supplied kubectl describe / logs /
  get-events output. Live-cluster diagnosis uses kubectl get pods, describe
  pod, logs (incl. --previous and -c <container>), get events, top nodes,
  top pods, aws eks describe-cluster, aws ec2 describe-vpc-endpoints, and
  aws ecr describe-images (kubectl v1.27+, AWS CLI v2, SSO or key-based
  credentials, kubeconfig pointing at the EKS cluster).
keywords:
  - EKS
  - Kubernetes
  - pod
  - CrashLoopBackOff
  - ImagePullBackOff
  - ErrImagePull
  - Pending
  - FailedScheduling
  - OOMKilled
  - Liveness probe
  - Readiness probe
  - Init container
  - ECR
  - kubectl
  - pod lifecycle
  - taints
  - tolerations
  - node affinity
tags: [eks, kubernetes, compute, troubleshoot, pod-failure, crashloop, oom, image-pull, health-check]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Compute
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
  when_to_use: >-
    Diagnosing why a Kubernetes pod on EKS is stuck Pending, crash-looping
    (CrashLoopBackOff), cannot pull a container image (ImagePullBackOff /
    ErrImagePull), is repeatedly OOMKilled, fails liveness or readiness
    probes while Running, or has an init container stuck in
    Init:CrashLoopBackOff; interpreting kubectl describe pod events,
    container lastState.exitCode, lastState.reason, and conditions.
  activation_triggers:
    - "EKS pod CrashLoopBackOff"
    - "EKS pod ImagePullBackOff"
    - "EKS pod ErrImagePull"
    - "EKS pod Pending"
    - "EKS pod FailedScheduling"
    - "EKS pod OOMKilled"
    - "EKS pod liveness probe failing"
    - "EKS pod readiness probe failing"
    - "EKS init container failing"
    - "EKS pod keeps restarting"
    - "kubectl pod status"
  invocation_schema: >-
    Input: either (a) a symptom description (pod name, namespace, observed
    state, restart count, any error strings from kubectl get pods), OR (b)
    a live-cluster scenario where the agent runs kubectl describe pod /
    logs / get events to gather evidence. Output: a deterministic INCIDENT
    / VERDICT / ROOT_CAUSE / EVIDENCE / REMEDIATION block where VERDICT ∈
    {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and ROOT_CAUSE names the
    specific failure category (CRASH_LOOP / IMAGE_PULL / PENDING / OOM /
    PROBE_FAILURE / INIT_FAILURE) and the offending config element.
---

# EKS Pod Troubleshooter

## Activation

Activate this skill when the user reports a Kubernetes pod failure on an
EKS cluster. Trigger phrases: "EKS pod CrashLoopBackOff", "EKS pod
ImagePullBackOff", "EKS pod Pending", "EKS pod FailedScheduling", "EKS
pod OOMKilled", "EKS pod liveness probe failing", "EKS pod readiness
probe failing", "EKS init container failing", "EKS pod keeps restarting",
"kubectl pod status".

## Mindset

**One-line takeaway:** every Kubernetes pod failure surfaces in three
places — `kubectl describe pod` (Events + container lastState), `kubectl
logs --previous` (application error), and `kubectl get events` (timeline
of what the kubelet and scheduler did). Read all three before declaring
a root cause.

Three facts make EKS pod troubleshooting different from generic container
debugging:

- **The pod phase is the entry point to the decision tree.** `Pending`
  means the scheduler has not placed the pod — the failure is in
  resources, taints, affinity, or PersistentVolume binding. `Running`
  with restarts means a container is exiting — the failure is in the
  application or its probe. `ContainerCreating` means the kubelet cannot
  finish setup — usually image pull, secret volume, or CSI driver.
  Diagnosing without the phase is guessing.
- **`kubectl describe pod` Events are the kubelet/scheduler voice, but
  they age out after ~1 hour.** Events are the authoritative narrative
  for what the control plane tried and what went wrong, but the kubelet
  deletes events older than the retention window (default 1h). Capture
  them early with `kubectl get events --sort-by='.lastTimestamp'` and
  filter by `involvedObject.name=<pod>`.
- **`kubectl logs` without `--previous` shows nothing for a
  CrashLoopBackOff.** The current container has just started; the logs
  that explain the crash are in the *previous* container instance. Always
  use `kubectl logs <pod> --previous` (or `-c <container> --previous` for
  a specific container) when the pod is in CrashLoopBackOff.

## Quick reference — symptom to failure category

| Observed state | Failure category | First probe |
|---|---|---|
| `STATUS=Pending`, `REASON=FailedScheduling` in events | PENDING | `kubectl describe pod` → Events: `FailedScheduling` message; check `top nodes` capacity |
| `STATUS=ImagePullBackOff` / `ErrImagePull` | IMAGE_PULL | `kubectl describe pod` Events: `Failed to pull image` message; verify ECR auth |
| `STATUS=CrashLoopBackOff`, restart count climbing | CRASH_LOOP | `kubectl logs <pod> --previous` for the application error |
| Container `Last State: Terminated`, `Reason: OOMKilled`, exit 137 | OOM | `kubectl describe pod` containers[].lastState; check `resources.limits.memory` |
| `STATUS=Running` but liveness/readiness probes failing; restart count climbing | PROBE_FAILURE | `kubectl describe pod` Events: `Liveness probe failed` / `Readiness probe failed`; verify probe path/port |
| `STATUS=Init:CrashLoopBackOff` / `Init:Error` | INIT_FAILURE | `kubectl logs <pod> -c <init-container> --previous` |

See the ordered steps below for the full diagnostic walk.

## Quick navigation

- **Step 0** — Capture the failure signal (pod name, namespace, phase).
- **Step 1** — Map the symptom to a category letter (A-F).
- **Step 2** — PENDING diagnostic (FailedScheduling).
- **Step 3** — IMAGE_PULL diagnostic (ImagePullBackOff).
- **Step 4** — CRASH_LOOP diagnostic (CrashLoopBackOff, exit code).
- **Step 5** — OOM diagnostic (OOMKilled).
- **Step 6** — PROBE_FAILURE diagnostic (Liveness/Readiness).
- **Step 7** — INIT_FAILURE diagnostic (Init:CrashLoopBackOff).
- **Step 8** — Root-cause catalog (top patterns + canonical fixes).
- **Step 9** — Verify the fix.
- **Step 10** — Decide VERDICT (ROOT_CAUSE_FOUND / NEED_MORE_INFO / ESCALATE).

## Process — Diagnostic decision tree (apply in order)

### Step 0: Capture the failure signal

Gather these three pieces. Each step below branches on which is present.

| Signal | Source | Why required |
|---|---|---|
| **Pod name + namespace** | User-provided or `kubectl get pods -A --field-selector status.phase!=Running` | All describe/logs calls need this |
| **Phase + container statuses + restart count** | `kubectl get pod <pod> -n <ns> -o wide` | Drives the symptom category |
| **Events + lastState** | `kubectl describe pod <pod> -n <ns>` | Narrows from symptom to cause |

If the user has not provided the pod name or namespace, output:

```text
INCIDENT: <namespace>/<pod> — <symptom>
VERDICT: NEED_MORE_INFO
REASON: Cannot diagnose without the pod name and namespace. Identify
the failing pod with: kubectl get pods -A --field-selector
status.phase!=Running  (or: kubectl get pods -n <ns>
--field-selector status.containerStatuses[*].restartCount>0)
MISSING:
  - Pod name and namespace
  - Last observed status (Pending / ContainerCreating /
    Running / CrashLoopBackOff / ImagePullBackOff)
```

If the user reports "pods keep failing" but does not know which pod,
ask for the namespace and deployment/pod label. Then run:

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

### Step 1: Identify the symptom category

Map the observed state to one of six categories. Each category has a
different diagnostic walk in Steps 2-7.

| Category | Signature | Diagnostic step |
|---|---|---|
| **A. PENDING** | `STATUS=Pending`; Events contain `FailedScheduling` | Step 2 |
| **B. IMAGE_PULL** | `STATUS=ImagePullBackOff` or `ErrImagePull`; Events contain `Failed to pull image` / `rpc error: code = Unknown desc = Error response from daemon` | Step 3 |
| **C. CRASH_LOOP** | `STATUS=CrashLoopBackOff`; `status.containerStatuses[].restartCount` climbing; `lastState` has exit code 1/255/etc | Step 4 |
| **D. OOM** | `status.containerStatuses[].lastState.reason: OOMKilled`; exit code 137 | Step 5 |
| **E. PROBE_FAILURE** | `STATUS=Running` but Events show `Liveness probe failed` / `Readiness probe failed`; restart count climbing or pod stuck not-ready | Step 6 |
| **F. INIT_FAILURE** | `STATUS=Init:CrashLoopBackOff` / `Init:Error` / `Init:ImagePullBackOff`; `status.initContainerStatuses` populated | Step 7 |

**Earliest-transition rule.** If the symptom matches more than one
category, pick the EARLIEST transition failure in the pod lifecycle.
PENDING precedes IMAGE_PULL precedes INIT_FAILURE precedes CRASH_LOOP /
OOM / PROBE_FAILURE. The pod cannot be crash-looping if it never
scheduled.

### Step 2: PENDING diagnostic (FailedScheduling)

A pod in `Pending` has not been bound to a node. The failure is in the
scheduler: insufficient resources, taints without tolerations, node
affinity/selector with no match, or a pending PersistentVolumeClaim.

| Events message sub-string | Root cause | Probe |
|---|---|---|
| `Insufficient cpu` / `Insufficient memory` | Node free resources < pod `resources.requests` | `kubectl top nodes`; `kubectl describe nodes` Allocatable vs Requests |
| `node(s) had taints that the pod didn't tolerate` | All nodes tainted; pod has no matching toleration | `kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints` |
| `node(s) didn't match Pod's node affinity/selector` | `nodeSelector` or `nodeAffinity` excludes all nodes | `kubectl get nodes --show-labels`; compare to pod `nodeSelector` / `requiredDuringScheduling` |
| `node(s) were unschedulable` | All matching nodes are `cordoned` (Unschedulable) | `kubectl get nodes -o wide`; look for `SchedulingDisabled` / `NotReady` |
| `pod has unbound immediate PersistentVolumeClaims` | PVC is Pending — no StorageClass match, exhausted volume IDs, or EBS AZ mismatch | `kubectl get pvc -n <ns>`; `kubectl get pv`; `kubectl describe pvc <pvc> -n <ns>` |
| `Insufficient <device>` (e.g. gpu) | Limited resource (NVIDIA GPU) — pod requests a resource no node advertutes via device plugin | `kubectl describe nodes` Capacity; verify device-plugin DaemonSet |
| `maximum graceful delete duration` etc. (rare) | Pod stuck in termination — different walk; not Pending | Check `deletionTimestamp` |

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

**Common fix patterns:**

- **Insufficient CPU/memory:** raise the cluster's `desired` size, add a
  Karpenter `NodePool` Provisioner with the right instance categories,
  or lower the pod `resources.requests`. On EKS with Karpenter, check
  `kubectl logs -n karpenter deployment/karpenter` for `cannot schedule`
  events.
- **Taint without toleration:** add a `tolerations` entry to the pod
  spec, or remove the taint (`kubectl taint node <node> <key>-`).
- **Affinity no match:** add the matching label to nodes (`kubectl label
  nodes <node> <key>=<value>`) or relax the affinity.
- **Cordoned nodes:** `kubectl uncordon <node>` once the node is healthy.
- **PVC Pending:** for `gp2`/`gp3` StorageClass on EBS, the PVC AZ must
  match a node AZ. Use `volumeBindingMode: WaitForFirstConsumer` (default
  for gp3) or pin the pod's `nodeSelector` to the AZ with capacity.

### Step 3: IMAGE_PULL diagnostic (ImagePullBackOff / ErrImagePull)

The kubelet cannot pull the container image. On EKS the cause is almost
always one of: image tag typo, ECR auth from the node role, missing VPC
endpoint for ECR in a private subnet, or a cross-account ECR repo
without a `Private` namespace identity policy.

| Events message sub-string | Root cause | Probe |
|---|---|---|
| `manifest unknown` / `Requested image not found` | Tag does not exist (typo, never pushed, or ECR lifecycle policy purged it) | `aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>` |
| `not authorized` / `403 Forbidden` | ECR auth failing — node IAM role lacks `ecr:GetDownloadUrlForLayer` / `ecr:BatchGetImage`, OR cross-account repo policy missing caller | `aws iam simulate-principal-policy` against the *node* instance role ARN |
| `RequestError: send request failed` / `i/o timeout` | Network: no route to ECR (private subnet, missing VPC endpoint, broken NAT) | `aws ec2 describe-vpc-endpoints`; verify route table 0.0.0.0/0 via NAT or `com.amazonaws.<region>.ecr.dkr` endpoint |
| `no space left on device` | Node disk full (image cache) | `kubectl debug node/<node> -it --image=busybox -- df -h /var/lib/containerd`; drain and roll the node |
| Pull works for other pods on same node but not this pod | Cross-account ECR — image ARN includes a different account ID | Compare `image: <acct>.dkr.ecr.<region>.amazonaws.com/...`; verify node role trust + repo policy BOTH allow caller |
| Pull works on newer nodes but fails on older | ECR token rotation + stale `aws-ecr-credential-provider` config on old AMI | Check node AMI version; upgrade the node group |

**Diagnostic walk:**

1. **Read the full event message** in `kubectl describe pod` Events.
   The sub-string after `rpc error: code = Unknown desc =` is the
   containerd error, which distinguishes auth vs manifest vs network.
2. **Verify the image exists in ECR:**
   `aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>`.
   If this returns `ImageNotFoundException`, the tag is wrong or purged.
3. **Identify the node's instance role** and verify ECR read perms. The
   four required actions are `ecr:GetAuthorizationToken`,
   `ecr:BatchCheckLayerAvailability`, `ecr:GetDownloadUrlForLayer`,
   `ecr:BatchGetImage`. The managed policy
   `AmazonEC2ContainerRegistryReadOnly` covers all four. The managed
   add-on `AmazonEKS_CNI_Policy` does NOT — do not confuse the two.
4. **For cross-account ECR (image in account B, pod runs in A):** both
   the node role in A AND the ECR repo policy in B must allow the pull.
   This is the cross-account intersection rule. The EKS doc on cross-
   account ECR is at https://repost.aws/knowledge-center/eks-ecs-cross-account-container-pull.
5. **Verify the ECR VPC endpoints exist** if the pod's node is in a
   private subnet: `com.amazonaws.<region>.ecr.api` AND
   `com.amazonaws.<region>.ecr.dkr`. The `dkr` endpoint is what
   containerd actually calls; the `api` endpoint is for registry API
   calls. Both are needed.
6. **Check the ECR lifecycle policy** if the tag worked yesterday but
   fails today: `aws ecr get-lifecycle-policy --repository-name <repo>`.
   A rule that purges `untagged` or `older than N images` can delete the
   image. `describe-images` will then return `ImageNotFoundException`.

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

**Common fix patterns:**

- Wrong tag: pin the image to the actual tag in ECR or use a digest
  reference (`<repo>@sha256:...`).
- Node role missing ECR perms: attach
  `AmazonEC2ContainerRegistryReadOnly` to the node instance role, OR if
  you run IRSA / Pod Identity, attach the policy to the *service
  account* role and reference it via `serviceAccountName` with
  `pod-security.kubernetes.io/enforce: restricted` annotations.
- Network: add VPC endpoints for ECR (interface endpoints, both `.api`
  and `.dkr`), or fix the NAT gateway route.
- Cross-account: update the ECR repo policy in the image-owning account
  to include `arn:aws:iam::<caller-acct>:root` in `Principal`.
- Disk full: drain the node (`kubectl drain <node> --ignore-daemonsets
  --delete-emptydir-data`) and let the autoscaler replace it, or upgrade
  the node AMI to a larger root volume.

### Step 4: CRASH_LOOP diagnostic (CrashLoopBackOff)

A CrashLoopBackOff means the kubelet restarted the container repeatedly
with exponential backoff. The exit code and application logs narrow the
cause; `kubectl describe pod` Events alone are too generic.

| Exit code | Meaning | First probe |
|---|---|---|
| 0 | Clean exit — application thinks it is done | `kubectl logs --previous` — is the workload a batch? Should `restartPolicy: Never` or `OnFailure` be set instead of `Always`? |
| 1 | General application error | `kubectl logs <pod> -c <container> --previous` — exception traceback |
| 2 / 126 / 127 | `command not found` / `exec format error` / wrong entrypoint | Check `command` / `args` in pod spec; verify image architecture (ARM64 vs AMD64) |
| 137 | SIGKILL — usually OOM killer | Step 5 (OOM) |
| 139 | SIGSEGV — native crash, JNI / cgo bug | `kubectl logs --previous` for native stack; image arch mismatch |
| 255 | Application-defined error | `kubectl logs --previous` |
| Empty + Events mention `CreateContainerConfigError` | kubelet could not construct the container spec — missing ConfigMap/Secret referenced in `envFrom` or `env.valueFrom` | `kubectl describe pod` Events; verify referenced Secret/ConfigMap exists in the namespace |

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

**Common CRASH_LOOP root causes:**

- **Missing required environment variable.** The application reads an
  env var that is not in the pod spec (`KeyError`, `NameError`,
  `ReferenceError`). Fix: add it via `env.value` or `env.valueFrom`.
- **Missing Secret/ConfigMap reference.** `envFrom.configMapKeyRef.name`
  points at a ConfigMap that does not exist in the namespace. The pod
  fails before the container starts; Events shows
  `CreateContainerConfigError` or `container has no logs`.
- **Database / downstream dependency unreachable.** Logs show
  `Connection refused` / `i/o timeout`. Fix: verify Service name, DNS
  resolution, NetworkPolicy, security group.
- **Wrong command / args.** `command: ["./app"]` but the binary is at
  `/app/server`. Logs: `no such file or directory`. Fix: pin the command
  to an absolute path inside the image.
- **Image architecture mismatch.** Built for `linux/amd64`, deployed to
  a Graviton (`arm64`) node group — or vice versa. Logs show
  `exec format error` (exit 126 / 127 / 139). Fix: build a multi-arch
  image (`docker buildx build --platform linux/amd64,linux/arm64`).
- **Liveness probe killing the container too aggressively.** See Step 6
  — if the liveness probe is misconfigured, the kubelet kills the
  container, restart count climbs, and the pod looks like it is
  crash-looping. The give-away: Events shows `Liveness probe failed` +
  `Container containerX killed`.

### Step 5: OOM diagnostic (OOMKilled)

Out-of-memory has two flavors:

### 5a. Container OOM (`OOMKilled`, exit 137)

The container exceeded its `resources.limits.memory` cgroup. The kernel
OOM-killer (cgroup v2) or Docker OOM-killer (cgroup v1) SIGKILLs the
process.

| Cause | Probe | Fix |
|---|---|---|
| `limits.memory` too low for the workload | `kubectl describe pod` lastState; compare to application RSS | Raise `resources.limits.memory` |
| Memory leak in application | `kubectl top pod <pod> -n <ns>` over time (or Prometheus `container_memory_rss`) | Fix the leak; meanwhile add a periodic restart via Deployment rollout |
| Java JVM heap > limit | `-Xmx` set higher than `limits.memory`, OR unset and JVM uses host hints | Set `-XX:MaxRAMPercentage=75` so heap tracks the cgroup limit |
| Off-heap / native memory growth | `kubectl top pod` shows RSS growth beyond JVM heap | Profile native allocations; raise `limits.memory` |
| sidecar (e.g. Envoy, Istio) consuming memory | Two containers in one pod, summed over pod limit | Tune sidecar; raise pod limit; split sidecar to own pod |

### 5b. Node OOM (kernel OOM-killer picks a victim)

The container did NOT exceed its own limit, but the node ran out of
memory. The kernel OOM-killer picks any victim (often the highest-RSS
container, sometimes the kubelet itself).

| Cause | Probe | Fix |
|---|---|---|
| No `limits.memory` on co-located pods | `kubectl describe pod` for each pod on the node | Set `limits.memory` on every pod (and `requests.memory` so the scheduler accounts for it) |
| Node oversubscribed (lots of `BestEffort` or `Burstable` pods) | `kubectl describe node <node>` Allocated resources > 90% | Add `requests.memory` everywhere; lower pod density via `topologySpreadConstraints` or node taints |
| DaemonSet (logging agent, CNI) consuming memory | `kubectl top pods -A --sort-by=memory` for DaemonSet pods | Resize the DaemonSet, or upgrade the node instance type |

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

**EKS-specific note.** EKS nodes by default run cgroup v2 on AL2023
AMIs (Kubernetes 1.29+). cgroup v2 enforces memory at the pod cgroup,
not per container — so a pod with two containers and a single pod-level
limit will be killed as a unit if either container drives the total
over. Set per-container `limits.memory` AND a pod total implied by the
sum.

**Java workloads.** Use `-XX:MaxRAMPercentage=75` (or `-XX:InitialRAMPercentage`)
so the JVM heap tracks the cgroup limit. Never set `-Xmx` higher than
`resources.limits.memory`; the JVM will be OOMKilled before it ever
reaches the heap ceiling.

### Step 6: PROBE_FAILURE diagnostic (Liveness / Readiness)

A pod is `Running` but the kubelet reports failing probes. Liveness
failures cause restarts; readiness failures cause the pod to be removed
from Service endpoints (no traffic).

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `Liveness probe failed: HTTP probe failed ... 500 / 404` | Probe path returns non-200 | `kubectl exec` into the pod and `curl localhost:<port><path>`; verify the app actually serves it |
| `Liveness probe failed: connect: connection refused` | Probe port wrong, OR application hasn't bound yet (initialDelaySeconds too short) | Check `livenessProbe.httpGet.port` vs `containerPort`; raise `initialDelaySeconds` |
| `Readiness probe failed` and Service endpoints exclude this pod | App not ready; readiness probe path requires a dependency | `kubectl describe endpoints <svc> -n <ns>`; check if the app has a /ready that depends on DB |
| Intermittent failures | Probe timeout too short; app slow on cold cache | Raise `timeoutSeconds` / `periodSeconds`; lower `successThreshold` |
| Liveness killing the container repeatedly | Misconfigured liveness path being confused for a real crash (loop into Step 4) | Look at Events ordering — Liveness failures precede the kill |
| gRPC probe failing | `grpcProbe` configured but app doesn't enable gRPC health checks | Use `grpc.health.v1.Health/Check` per the gRPC health protocol |

**Diagnostic walk:**

1. **Identify which probe is failing** — liveness (causes restarts) vs
   readiness (causes not-ready). Read Events:
   `kubectl get events -n <ns> --field-selector involvedObject.name=<pod>`
   and grep for `Liveness probe failed` vs `Readiness probe failed`.
2. **Read the probe config:**
   `kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.containers[*].livenessProbe}'`
   (and `.readinessProbe`). Note the path, port, scheme, initial delay,
   period, timeout, thresholds.
3. **Reproduce the probe from inside the pod:**
   `kubectl exec -n <ns> <pod> -c <container> -- curl -i http://localhost:<port><path>`.
   If this returns 200, the probe config is wrong (wrong port, wrong
   path, wrong scheme, TLS cert mismatch). If non-200, the application
   has a bug or its dependency is down.
4. **For liveness specifically:** if the probe passes when curled
   manually but fails when the kubelet runs it, check whether the probe
   path requires CPU that the app does not have under load. Raise
   `timeoutSeconds` or lower `periodSeconds`.
5. **Check `initialDelaySeconds`.** If the application needs 60 seconds
   to start and the probe begins at 5 seconds, the kubelet will kill
   the container before the app is ready — restart count climbs,
   presenting as CrashLoopBackOff.
6. **Verify the Service endpoints:**
   `kubectl describe endpoints <svc> -n <ns>` (or
   `kubectl get endpointslices -n <ns>`). A readiness failure shows the
   pod IP missing from the endpoints list.

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

**Common fix patterns:**

- **Path/port mismatch:** align `livenessProbe.httpGet.path` and `.port`
  with the application's actual endpoint. Common: `/health` vs `/healthz`
  vs `/api/health`; `containerPort: 8080` but probe port `80`.
- **`initialDelaySeconds` too short:** raise it above the application's
  known startup time. For Spring Boot / Java, use 90+ seconds. Better,
  use a `startupProbe` (introduced in 1.16, GA in 1.20) so the liveness
  probe only runs after startup completes.
- **TLS scheme:** if the app serves HTTPS only, set
  `livenessProbe.httpGet.scheme: HTTPS`. The kubelet does not follow
  redirects from HTTP to HTTPS.
- **Readiness depends on a dependency:** the readiness probe path should
  fail (return non-200) when a *required* dependency is down. If the
  readiness probe path always returns 200, it is not actually testing
  readiness.

### Step 7: INIT_FAILURE diagnostic (Init:CrashLoopBackOff / Init:Error)

Init containers run sequentially before the main containers start. A
failing init container blocks the main container from starting — the pod
stays in `Init:CrashLoopBackOff` (or `Init:Error`, `Init:ImagePullBackOff`)
indefinitely.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `Init:CrashLoopBackOff`, init container exit 1 | Application error in init container | `kubectl logs <pod> -c <init-container-name> --previous` |
| `Init:ImagePullBackOff` | Init container image fails to pull (same causes as Step 3) | `kubectl describe pod` Events; verify the init container image separately from main |
| Init container takes too long, pod stuck in `Init:i/N` | Init container doing too much (loading huge dataset) — not a failure but appears stuck | `kubectl logs <pod> -c <init-container-name> -f` to watch progress |
| Init container runs once but pod recreated by controller | Init containers re-run on every pod start — if it expects state from previous run, it fails | Make init containers idempotent; never depend on prior-run state |

**Diagnostic walk:**

1. **List init container statuses:**
   `kubectl get pod <pod> -n <ns> -o jsonpath='{.status.initContainerStatuses}'`.
   Identify which init container is failing (the one whose `state` is
   not `terminated` with `reason: Completed`).
2. **Read its logs with `--previous`:**
   `kubectl logs <pod> -n <ns> -c <init-container-name> --previous`.
   The init container may be in a tight crash loop; the current logs
   may be empty.
3. **If the init container waits on a dependency (waiting for DB migration):**
   verify the dependency is reachable from the pod network. Init
   containers share the pod network, so Service DNS should resolve.
4. **Verify init container ordering:** init containers run sequentially
   in spec order. If init container 2 depends on something init container
   1 sets up (e.g., a shared volume), verify the volume mount is
   bidirectional.

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

**Common INIT_FAILURE root causes:**

- **Database migration that fails on schema mismatch.** Fix the
  migration script or pre-flight check it.
- **Waiting for a Service that does not exist yet.** Use a
  `Job`-orchestrated init or remove the dependency.
- **Permissions on a mounted Secret / ConfigMap** — the init container
  tries to write to a `readOnly: true` mount. Fix the volume mount or
  use an `emptyDir`.
- **Init container image is wrong / not built** — same IMAGE_PULL tree
  (Step 3) but for the init container's image field.

### Step 8: Map to root-cause catalog

After the walk identifies the category, cross-reference with this
catalog. The catalog names the top EKS pod-failure patterns and their
canonical fixes.

| # | Root cause | Category | Fix pattern |
|---|---|---|---|
| 1 | Node insufficient CPU/memory for pod `requests` | PENDING | Scale the node group (or Karpenter NodePool); right-size pod `resources.requests` |
| 2 | Taint without toleration; all nodes tainted | PENDING | Add `tolerations` matching the taint, OR remove the taint, OR add untainted nodes |
| 3 | PVC Pending (StorageClass AZ mismatch, gp3) | PENDING | Use `volumeBindingMode: WaitForFirstConsumer`; verify AZ has capacity |
| 4 | Image tag typo / image purged by ECR lifecycle policy | IMAGE_PULL | Pin to existing tag (or digest); relax lifecycle policy |
| 5 | Node instance role lacks ECR read perms | IMAGE_PULL | Attach `AmazonEC2ContainerRegistryReadOnly` to the node instance role |
| 6 | Cross-account ECR repo policy missing caller | IMAGE_PULL | Update ECR repo policy in image-owning account to allow caller's account |
| 7 | Application crash on missing env var / missing ConfigMap | CRASH_LOOP | Add the env var / `envFrom` reference; verify Secret/ConfigMap exists in namespace |
| 8 | Image architecture mismatch (AMD64 vs ARM64) | CRASH_LOOP | Build multi-arch image with `docker buildx --platform linux/amd64,linux/arm64` |
| 9 | Container `limits.memory` too low (OOM 137) | OOM | Raise `resources.limits.memory`; for Java use `-XX:MaxRAMPercentage=75` |
| 10 | Liveness probe path/port/initialDelaySeconds wrong | PROBE_FAILURE | Align probe with application endpoint; add `startupProbe`; raise `initialDelaySeconds` |
| 11 | Readiness probe missing — pod never enters Service endpoints | PROBE_FAILURE | Add a `readinessProbe` that tests a real dependency |
| 12 | Init container failing (DB migration, missing dep) | INIT_FAILURE | Fix init container script; make idempotent; verify init container image and perms |

### Step 9: Verify the fix

Before applying, validate the proposed fix with one of:

- **For pod spec changes:** apply to a single pod via `kubectl apply` or
  `kubectl edit`, watch the pod come up with
  `kubectl get pod <pod> -w` before rolling the Deployment.
- **For probe changes:** use `kubectl exec` to curl the probe path
  manually before trusting the kubelet verdict.
- **For node scaling:** wait for the new nodes to be `Ready` and the
  pending pods to bind before declaring the fix complete.
- **For image changes:** verify the new tag exists in ECR and pull it
  locally first (`docker pull <image>`).

### Step 10: Decide — ROOT_CAUSE_FOUND vs NEED_MORE_INFO vs ESCALATE

- **ROOT_CAUSE_FOUND.** The walk identified a specific failure category
  and a specific configuration element (pod spec field, node IAM policy,
  PVC StorageClass, probe config). Output REMEDIATION with the exact
  change.
- **NEED_MORE_INFO.** The walk reached a step where the operator cannot
  supply evidence (e.g., `kubectl logs --previous` requires access to a
  namespace the operator cannot read). Output the list of missing
  inputs.
- **ESCALATE.** The walk identifies a cause outside the operator's
  scope: node IAM role owned by the platform team, ECR repo in another
  account, Karpenter NodePool owned by another team, NetworkPolicy
  enforced cluster-wide. Output the escalation target and the specific
  request to make.

## Output format

```text
INCIDENT: <namespace>/<pod> on node <node> — <symptom>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <category name> — <specific failing config element>
EVIDENCE:
  - kubectl describe pod: <event line>
  - kubectl logs --previous: <key log line>
  - kubectl get pod (jsonpath): <lastState / probe / resource field>
  - aws iam/ecr/ec2: <AWS-side signal>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <specific config change with field name>
  2. <verification command>
  3. <post-apply monitoring>
```

### Worked example — CrashLoopBackOff from missing env var

```text
INCIDENT: production/api-server-5d4b6c7d8-x9fk2 on node ip-10-0-3-42 —
CrashLoopBackOff (restart count 14, climbing)
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: CRASH_LOOP — application reads `DB_HOST` env var but pod
spec does not set it; container exits with code 1 in <1s
EVIDENCE:
  - kubectl describe pod: Last State: Terminated, Reason: Error, Exit
    Code: 1, Started/Finished ~0.8s apart
  - kubectl logs api-server-5d4b6c7d8-x9fk2 -c api --previous:
    "Traceback ... KeyError: 'DB_HOST'"
  - kubectl get pod -o jsonpath
    '{.spec.containers[0].env}': returns the env list — DB_HOST is
    missing
  - kubectl get events -n production --field-selector
    involvedObject.name=api-server-5d4b6c7d8-x9fk2: "Back-off
    restarting failed container" × N
ROOT_CAUSE_CATALOG: #7 (missing env var)
REMEDIATION:
  1. Patch the Deployment to add the env var (recommended: sourced from
     a ConfigMap so it is centralised):
     kubectl set env deployment/api-server -n production \
       DB_HOST=postgres.production.svc.cluster.local
     (or kubectl edit deployment api-server -n production and add to
     spec.template.spec.containers[0].env)
  2. Watch the rollout:
     kubectl rollout status deployment/api-server -n production
  3. Verify the new pod reaches Running with restart count 0:
     kubectl get pods -n production -l app=api-server -w
  4. If DB connectivity is also wrong (logs then show
     "Connection refused"), check the Service name and NetworkPolicy.
```

## Expert heuristic — "The pod troubleshooting trinity"

Three commands, in order, give you 90% of all pod diagnoses. Run them
before reaching for anything else.

1. **Events first:** `kubectl describe pod <pod> -n <ns> | grep -A 10 Events`
   — the Events section is the kubelet/scheduler narrative. It tells
   you WHAT the control plane tried and HOW it failed:
   `FailedScheduling: 0/6 nodes are available`, `Failed to pull image
   "X"`, `Liveness probe failed: HTTP probe failed with status 500`,
   `CreateContainerConfigError: configmap "Y" not found`.
2. **Logs second:** `kubectl logs <pod> -n <ns> -c <container> --previous`
   — the `--previous` flag is critical for CrashLoopBackOff; it shows
   the logs of the container instance that crashed, not the brand-new
   one that just started. The application error is here: `KeyError`,
   `ConnectionRefusedError`, `exec format error`, `OOMKilled` (no logs —
   killed by kernel).
3. **Events again (timeline):**
   `kubectl get events -n <ns> --field-selector
   involvedObject.name=<pod> --sort-by='.lastTimestamp'` — this shows
   the ORDER things happened, which is critical for distinguishing cause
   from consequence. Liveness-failed-then-killed vs killed-then-restart
   vs ImagePullBackOff-from-the-start are three different diagnoses and
   the timeline disambiguates them.

Everything else (top, metrics-server, Prometheus, AWS API calls) is
confirmatory. The trinity alone identifies the root cause in the
majority of cases.

## Anti-Patterns — NEVER

- **NEVER** declare the root cause from `kubectl get pods` alone. The
  STATUS column is a symptom (`CrashLoopBackOff`), not a cause. Always
  run `kubectl describe pod` + `kubectl logs --previous` before
  declaring ROOT_CAUSE_FOUND.

- **NEVER** read `kubectl logs` without `--previous` for a
  CrashLoopBackOff pod. The current container just started; its logs
  are empty or partial. The crash cause is in the *previous* container
  instance's logs.

- **NEVER** confuse the node instance role with the pod's IRSA / Pod
  Identity role. ECR pulls use the *node* instance role unless IRSA or
  EKS Pod Identity is configured AND the pod has
  `serviceAccountName` set with the right annotation. Misidentifying
  which role pulls the image leads to fixing the wrong IAM policy.

- **NEVER** raise `resources.limits.memory` without checking whether
  the OOM is container-level (`OOMKilled` in lastState) or node-level
  (kernel OOM-killer, no per-container reason). The fixes are
  different: container OOM raises the limit; node OOM requires
  `requests.memory` everywhere and possibly larger nodes.

- **NEVER** recommend `privileged: true` as a fix for any Kubernetes
  failure. Privileged grants full host access; the real fix is almost
  always a missing capability, a mount permission, or a network policy.
  Privileged is a security anti-pattern and forbidden by Pod Security
  Standards `restricted`.

- **NEVER** declare ROOT_CAUSE_FOUND without reading the application
  logs. A crash-looping pod has its cause in `kubectl logs --previous`,
  not in any kubectl field. If you cannot access logs (RBAC), emit
  NEED_MORE_INFO.

- **NEVER** confuse a `livenessProbe` with a `readinessProbe`. Liveness
  failures cause restarts; readiness failures cause the pod to be
  removed from Service endpoints (no traffic). Mixing them up leads to
  "the pod is healthy but the Service is broken" confusion.

- **NEVER** lower `livenessProbe` thresholds (`failureThreshold`,
  `periodSeconds`) as a fix. If the probe is failing, the application
  is not healthy or the probe is wrong. Making the probe more forgiving
  hides the real problem.

- **NEVER** recommend `imagePullPolicy: Always` as a fix for
  ImagePullBackOff. The policy affects whether the kubelet checks the
  registry for a new digest; it does not fix auth or manifest issues.

- **NEVER** assume `kubectl describe pod` Events are exhaustive. Events
  age out after ~1 hour (default `--event-ttl`). For incidents older
  than an hour, the Events may be gone — fall back to Control Plane
  Logs (`kube-apiserver` / `kube-scheduler`) if enabled on the EKS
  cluster.

- **NEVER** assume a Pending pod is unschedulable because of resources.
  Taints, affinity, PVC binding, and `PriorityClass` preemption can all
  cause Pending. Always read the Events `FailedScheduling` message
  verbatim.

- **NEVER** "fix" an Init:CrashLoopBackOff by deleting the init
  container. The init container is doing a job the main container
  depends on. Fix the init container's actual failure.

- **NEVER** trust `kubectl top pod` for OOM diagnosis in isolation. Top
  is a real-time snapshot; if the pod already crashed, top shows
  nothing. Use it while the pod is alive, or use Prometheus
  `container_memory_rss` historical data.

- **NEVER** conclude "the application has a memory leak" without
  evidence of monotonic RSS growth. A single OOMKilled is more likely
  a too-low limit. A leak shows a sawtooth or rising trend over hours
  or days.

- **NEVER** delete a PVC to "fix" a Pending pod. Deleting the PVC can
  orphan or lose data. Read `kubectl describe pvc` Events first; the
  StorageClass, AZ, and `WaitForFirstConsumer` binding mode are the
  usual culprits.

- **NEVER** declare IMAGE_PULL without verifying the image exists in
  ECR. The error string "manifest unknown" is also returned for
  transient registry issues. Run
  `aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>`
  to confirm.

- **NEVER** assume the EKS API server is reachable from your pod. If
  `kubectl exec` fails with `error: unable to upgrade connection`,
  check the API server endpoint access (public vs private), the
  pod's subnet route, and security group on the control plane.

- **NEVER** recommend raising `livenessProbe.timeoutSeconds` past a
  few seconds without investigation. A probe that takes 10+ seconds
  to respond means the application is pathologically slow; raise
  `timeoutSeconds` only after ruling out real latency.

- **NEVER** "fix" CrashLoopBackOff by setting `restartPolicy: Never`.
  This hides the loop by not restarting — the pod still fails, just
  without the visible BackOff. Use `Never` only for true Jobs.

## Remediation guidance

### For PENDING

1. Read the Events `FailedScheduling` message verbatim. The sub-string
   after the colon is the discriminator (`Insufficient cpu`, `had
   taints`, `didn't match node affinity`, `unschedulable`).
2. For resource pressure: `kubectl top nodes` and
   `kubectl describe node <node>` to see Allocatable vs Requests. Scale
   the EKS managed node group (`aws eks update-nodegroup-config` to bump
   desiredSize) or check Karpenter NodePool.
3. For taints: list taints
   (`kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints`)
   and either add a toleration or remove the taint.
4. For PVC: `kubectl describe pvc <pvc> -n <ns>` — check StorageClass
   exists, has capacity, and AZ matches pod's affinity.

### For IMAGE_PULL

1. Verify the image exists in ECR with `aws ecr describe-images`.
2. Identify the puller's IAM identity (node role, or IRSA/Pod Identity
   role via `serviceAccountName`) and verify ECR read permissions using
   `aws iam simulate-principal-policy`.
3. Verify network reachability (VPC endpoints for ECR or NAT gateway).
4. For cross-account ECR, update the repo policy in the image-owning
   account to include the caller's account root.

### For CRASH_LOOP

1. Read `kubectl logs <pod> -c <container> --previous`.
2. Cross-reference the exit code and log pattern with common causes
   (missing env var, dependency outage, version mismatch, arch
   mismatch).
3. If the deployment controller is rolling back (Deployment with
   `progressDeadlineSeconds` exceeded), look at the underlying pod
   failure, not the rollout state.
4. Roll back to the last known-good image tag if the fix is not
   immediately available.

### For OOM

1. Identify container-level vs node-level OOM from
   `status.containerStatuses[].lastState.reason`.
2. For container OOM: raise `resources.limits.memory`. For Java: use
   `-XX:MaxRAMPercentage=75` so the JVM tracks the cgroup limit.
3. For node OOM: set `resources.requests.memory` on every pod; consider
   ` Guaranteed` QoS for critical pods; add nodes.
4. Enable metrics-server and a long-term metrics sink (Prometheus) to
   catch memory leaks before they OOM.

### For PROBE_FAILURE

1. Identify liveness vs readiness failure from Events.
2. Reproduce the probe manually:
   `kubectl exec -n <ns> <pod> -c <container> -- curl -i http://localhost:<port><path>`.
3. Align probe path/port/scheme with the application's actual endpoint.
4. Add a `startupProbe` so liveness does not fire during application
   startup; raise `initialDelaySeconds` if startupProbe is unavailable.
5. For readiness failures, verify the readiness path actually depends
   on a real dependency (DB, downstream service).

### For INIT_FAILURE

1. List init container statuses with
   `kubectl get pod -o jsonpath='{.status.initContainerStatuses}'`.
2. Read the failing init container's logs with `--previous`.
3. Fix the init container's script / image / permissions; make it
   idempotent.

## Recent AWS features (2024-2026)

- **EKS Pod Identity (2023 GA, widely adopted 2024-2026):** EKS Pod
  Identity is the recommended replacement for IRSA. The agent
  (`eks-pod-identity-agent`) running as a DaemonSet vends AWS credentials
  via a Unix socket. Troubleshoot Pod Identity failures by checking
  `kubectl get pods -n kube-system -l app.kubernetes.io/name=eks-pod-identity-agent`
  and the pod's `serviceAccountName` + the `EksPodIdentityAgent` add-on
  version.
- **Karpenter (default in many EKS blueprints 2024-2026):** Karpenter
  replaces Cluster Autoscaler. Pending pods trigger Karpenter
  provisioning; check `kubectl logs -n karpenter
  deployment/karpenter` for `bucketing`, `cannot schedule`, or
  `inflight` messages. Karpenter v1 removed `Provisioner` in favor of
  `NodePool` + `NodeClaim`.
- **Amazon Linux 2023 node AMI (default for EKS 1.29+):** AL2023 runs
  cgroup v2 and containerd natively (no `dockershim`). cgroup v2
  changes OOM behavior: memory is enforced at the pod cgroup by default.
  Troubleshoot by reading `/sys/fs/cgroup/` from inside the container.
- **gp3 EBS volumes default for new StorageClasses (2024+):** gp3
  decouples IOPS from volume size. If PVC is Pending on a gp3
  StorageClass, the AZ may lack gp3 capacity — try `volumeBindingMode:
  WaitForFirstConsumer` or a different AZ.
- **EKS Auto Mode (late 2024 GA):** EKS Auto Mode manages node
  provisioning for you via an embedded Karpenter. Pending pods that
  should auto-provision may fail if the `EKS_AUTO_NODEGROUP` role or
  the `nodeclass` / `nodepool` config is wrong. Check
  `kubectl get nodepool,nodeclaim -A`.
- **Network Policies via Amazon VPC CNI Network Policy Engine (2024):**
  NetworkPolicy enforcement is built into the VPC CNI; an unintended
  default deny can block ECR pulls and Service-to-Service traffic,
  presenting as image pull timeouts or readiness failures. Check
  `kubectl get networkpolicy -A` and the VPC CNI ConfigMap.

## References

See `references/failure-decision-tree.md` for the full symptom-to-cause
walk with worked examples per category, and `references/diagnostic-
commands.md` for the canonical command script for each failure category.

## Domain

AWS CloudOps / EKS Compute Reliability & Kubernetes Pod Operations.

## AWS documentation

- **Amazon EKS User Guide** — https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html
- **EKS troubleshooting** — https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html
- **Kubernetes pod lifecycle** — https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
- **Kubernetes probes** — https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-probes
- **Kubernetes init containers** — https://kubernetes.io/docs/concepts/workloads/pods/init-containers/
- **Kubernetes debug a pod** — https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/
- **EKS Pod Identity** — https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html
- **Karpenter** — https://karpenter.sh/
- **ECR cross-account pull for EKS** — https://repost.aws/knowledge-center/eks-ecs-cross-account-container-pull
- **kubectl reference** — https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands
