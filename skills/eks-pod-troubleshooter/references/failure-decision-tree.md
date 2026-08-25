# EKS Pod Failure Decision Tree — Reference

Supplementary reference for the EKS Pod Troubleshooter skill. Walks the
full symptom-to-cause tree with worked examples per category.

## Pod lifecycle and where each failure category strikes

```
   submitted
        │
        ▼
   [PENDING] ───── FailedScheduling ─────►  [A] PENDING
        │                                     ├── Insufficient cpu/memory
        │                                     ├── Taints / affinity
        │                                     ├── Cordoned nodes
        │                                     └── PVC Pending
        ▼
   [ContainerCreating]
        │                                     [B] IMAGE_PULL
        │                                     ├── tag missing
        │                                     ├── ECR auth (node role / IRSA / Pod Identity)
        ├── image pull ─────────── fails ──── ├── cross-account repo policy
        │                                     └── network (VPC endpoint / NAT)
        ├── mount secret/configmap ─ fails ── [C] CRASH_LOOP (CreateContainerConfigError)
        │
        ▼
   [Running]
        │                                     [F] INIT_FAILURE (before main)
        │                                     ├── init:CrashLoopBackOff
        ├── init containers ───────  fails ─── └── init:ImagePullBackOff
        │
        ├── main container exits  ── 0/1/255 ── [C] CRASH_LOOP
        │                          ── 137 ───── [D] OOM
        │                          ── 139 ───── native crash / arch mismatch
        │
        ├── Liveness probe fails ─────────── [E] PROBE_FAILURE → kill → restart
        ├── Readiness probe fails ────────── [E] PROBE_FAILURE → not-ready (no traffic)
        │
        ▼
   restart cycle (CrashLoopBackOff)
```

Category letters map to the steps in SKILL.md:

- A = PENDING (Step 2)
- B = IMAGE_PULL (Step 3)
- C = CRASH_LOOP (Step 4)
- D = OOM (Step 5)
- E = PROBE_FAILURE (Step 6)
- F = INIT_FAILURE (Step 7)

**Rule:** pick the EARLIEST transition failure as the root cause. Later
categories are consequences. A pod that fails image pull never reaches
Running, so a probe diagnosis is wrong.

## Category A: PENDING

The scheduler has not bound the pod to a node. The Events section of
`kubectl describe pod` shows `FailedScheduling` with the exact reason.

### Worked example — Insufficient CPU on a managed node group

**Symptom:** pod is `Pending` for 3+ minutes. Events shows
`0/3 nodes are available: 3 Insufficient cpu`.

**Walk:**

1. `kubectl describe pod <pod> -n <ns>` Events:
   ```
   Warning  FailedScheduling  default-scheduler
   0/3 nodes are available: 3 Insufficient cpu.
   ```
2. `kubectl top nodes`:
   ```
   NAME              CPU(cores)   MEMORY(bytes)
   ip-10-0-1-10      940m (49%)   1450Mi (38%)
   ip-10-0-2-20      910m (48%)   1610Mi (42%)
   ip-10-0-3-30      970m (51%)   1500Mi (39%)
   ```
3. `kubectl describe node ip-10-0-1-10` Allocated resources:
   `Allocated resources: cpu 940m / 1900m (49%)`. The pod requests
   `1200m` — no node has that much remaining.

**Root cause:** PENDING — insufficient CPU (catalog #1).

**Fix:** scale the managed node group:

```bash
aws eks update-nodegroup-config \
  --cluster-name <cluster> --nodegroup-name <ng> \
  --scaling-config desiredSize=<current+2>,minSize=<min>,maxSize=<max>

# Or with Karpenter, verify the NodePool:
kubectl get nodepool -A -o yaml
```

### Worked example — Taint without toleration

**Symptom:** pod Pending. Events shows
`0/3 nodes are available: 3 node(s) had taints that the pod didn't tolerate`.

**Walk:**

1. `kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints`:
   ```
   NAME              TAINTS
   ip-10-0-1-10      [map[effect:NoSchedule key:dedicated value:batch]]
   ip-10-0-2-20      [map[effect:NoSchedule key:dedicated value:batch]]
   ip-10-0-3-30      [map[effect:NoSchedule key:dedicated value:batch]]
   ```
2. Pod spec has no `tolerations`.

**Root cause:** PENDING — all nodes tainted `dedicated=batch:NoSchedule`,
pod has no matching toleration (catalog #2).

**Fix:** add a toleration to the pod spec:

```yaml
spec:
  tolerations:
    - key: "dedicated"
      operator: "Equal"
      value: "batch"
      effect: "NoSchedule"
```

Or remove the taint: `kubectl taint node ip-10-0-1-10 dedicated=batch:NoSchedule-`.

### Worked example — PVC Pending on gp3 EBS

**Symptom:** pod Pending. Events shows
`pod has unbound immediate PersistentVolumeClaims`.

**Walk:**

1. `kubectl get pvc -n <ns>`:
   ```
   NAME         STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS
   data-pvc     Pending                                      gp3
   ```
2. `kubectl describe pvc data-pvc -n <ns>` Events:
   ```
   Warning  ProvisioningFailed  ebs.csi.eks.amazonaws.com
   could not zone 1a: InsufficientVolumeCon...
   ```
3. The StorageClass has `volumeBindingMode: Immediate`. The pod's
   nodeSelector pins AZ=us-east-1a but gp3 has no capacity in 1a.

**Root cause:** PENDING — PVC stuck on AZ capacity (catalog #3).

**Fix:** switch the StorageClass to `WaitForFirstConsumer` so the CSI
driver waits until the pod is scheduled, then provisions in the same AZ:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-wffc
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
```

## Category B: IMAGE_PULL

The kubelet cannot pull the container image.

### Worked example — Node role missing ECR permissions

**Symptom:** pod `ImagePullBackOff`. Events shows
`Failed to pull image "111111111111.dkr.ecr.us-east-1.amazonaws.com/app:v1":
rpc error: code = Unknown desc = Error response from daemon:
Head "https://111111111111.dkr.ecr.us-east-1.amazonaws.com/v2/app/manifests/v1":
unauthorized: Not Authorized`.

**Walk:**

1. `aws ecr describe-images --repository-name app --image-ids imageTag=v1`
   returns the image — the tag exists.
2. `kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.nodeName}'` →
   `ip-10-0-2-20`.
3. The node's instance role is `eksctl-my-cluster-nodegroup-standard-NodeInstanceRole-XYZ`.
   `aws iam list-attached-role-policies --role-name <role>` shows only
   `AmazonSSMManagedInstanceCore` and `AmazonEKS_CNI_Policy` — no ECR.
4. `aws iam simulate-principal-policy --policy-source-arn
   arn:aws:iam::111111111111:role/<role> --action-names ecr:BatchGetImage`
   returns `implicitDeny`.

**Root cause:** IMAGE_PULL — node instance role missing ECR read perms
(catalog #5).

**Fix:** attach `AmazonEC2ContainerRegistryReadOnly` to the node role:

```bash
aws iam attach-role-policy \
  --role-name eksctl-my-cluster-nodegroup-standard-NodeInstanceRole-XYZ \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

# Force the kubelet to retry sooner:
kubectl delete pod <pod> -n <ns>   # controller will recreate
```

### Worked example — Cross-account ECR repo policy missing caller

**Symptom:** pod ImagePullBackOff. Image is at
`222222222222.dkr.ecr.us-east-1.amazonaws.com/shared/lib:v3`. The pod
runs in account `111111111111`.

**Walk:**

1. Node role in `111111111111` HAS
   `arn:aws:ecr:us-east-1:222222222222:repository/shared/lib` in its
   identity policy — identity side OK.
2. `aws ecr get-repository-policy --repository-name shared/lib --profile acct222`
   shows the repo policy allows only `arn:aws:iam::222222222222:root`.
3. Cross-account intersection rule: BOTH identity AND resource policy
   must allow. The resource policy is missing the caller.

**Root cause:** IMAGE_PULL — cross-account repo policy (catalog #6).

**Fix:** update the repo policy in `222222222222`:

```bash
aws ecr set-repository-policy --repository-name shared/lib \
  --policy-text file://cross-acct-policy.json --profile acct222
```

`cross-acct-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CrossAccountPull",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::111111111111:root" },
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ]
    }
  ]
}
```

### Worked example — Private subnet, no VPC endpoint for ECR

**Symptom:** pod ImagePullBackOff. Events shows
`rpc error: code = Unknown desc = Error response from daemon:
Get "https://111111111111.dkr.ecr.us-east-1.amazonaws.com/v2/":
dial tcp: i/o timeout`.

**Walk:**

1. Node is in a private subnet (`kubectl get node <node> -o jsonpath='{.metadata.labels.topology\.kubernetes\.io/zone}'`
   then check subnets in EC2).
2. Route table for the subnet has 0.0.0.0/0 → NAT gateway. NAT
   gateway is present but its ENI is in a different route table.
3. No VPC endpoint for ECR exists.

**Root cause:** IMAGE_PULL — network (no route to ECR).

**Fix:** add interface VPC endpoints for ECR (cheaper than fixing NAT
routes for prod traffic):

```bash
aws ec2 create-vpc-endpoint \
  --vpc-id <vpc-id> --service-name com.amazonaws.us-east-1.ecr.api \
  --vpc-endpoint-type Interface --subnet-ids <private-subnet-1> <private-subnet-2> \
  --security-group-ids <sg-allow-https>
aws ec2 create-vpc-endpoint \
  --vpc-id <vpc-id> --service-name com.amazonaws.us-east-1.ecr.dkr \
  --vpc-endpoint-type Interface --subnet-ids <private-subnet-1> <private-subnet-2> \
  --security-group-ids <sg-allow-https>
```

## Category C: CRASH_LOOP

Pod is `CrashLoopBackOff`; restart count climbs; container exits with
the same code each time.

### Worked example — Missing env var

**Symptom:** pod CrashLoopBackOff, restart count 7. `kubectl logs
<pod> -c app --previous`:
```
Traceback (most recent call last):
  File "/app/main.py", line 12, in <module>
    db_host = os.environ["DB_HOST"]
  File "/usr/lib/python3.11/os.py", line 680, in __getitem__
    raise KeyError(key) from None
KeyError: 'DB_HOST'
```

**Walk:**

1. `kubectl describe pod <pod>`: Last State: Terminated, Reason: Error,
   Exit Code: 1, Started/Finished ~0.8s apart.
2. `kubectl logs --previous` has the traceback above.
3. `kubectl get pod -o jsonpath='{.spec.containers[0].env}'` does not
   list `DB_HOST`.

**Root cause:** CRASH_LOOP — missing env var (catalog #7).

**Fix:**

```bash
kubectl set env deployment/api-server -n production \
  DB_HOST=postgres.production.svc.cluster.local

# Or source from a ConfigMap:
# spec.template.spec.containers[0].envFrom:
#   - configMapRef:
#       name: api-config
```

### Worked example — Image architecture mismatch (Graviton)

**Symptom:** pod CrashLoopBackOff. New Graviton (arm64) node group.
Image built for `linux/amd64` only.

**Walk:**

1. `kubectl logs <pod> -c app --previous`:
   `standard_init_linux.go:228: exec user process caused: exec format error`
2. `docker inspect <image>` locally: `Architecture: amd64`.
3. `kubectl get node <node> -o jsonpath='{.status.nodeInfo.architecture}'`
   returns `arm64`.

**Root cause:** CRASH_LOOP — image arch mismatch (catalog #8).

**Fix:** rebuild the image as multi-arch:

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t 111111111111.dkr.ecr.us-east-1.amazonaws.com/app:v2 \
  --push .
```

### Worked example — CreateContainerConfigError (missing ConfigMap)

**Symptom:** pod Pending/ContainerCreating, never starts. Events shows
`CreateContainerConfigError: configmap "api-config" not found`. No
container logs exist (container never ran).

**Walk:**

1. `kubectl describe pod` Events:
   ```
   Warning  CreateContainerConfigError  kubelet
   configmap "api-config" not found
   ```
2. Pod spec has `envFrom: [{configMapRef: {name: api-config}}]`.
3. `kubectl get configmap -n <ns>` does NOT list `api-config`.

**Root cause:** CRASH_LOOP variant — ConfigMap referenced but missing
(catalog #7 variant).

**Fix:** create the ConfigMap, or fix the reference name.

```bash
kubectl create configmap api-config -n <ns> \
  --from-literal=DB_HOST=postgres.production.svc.cluster.local \
  --from-literal=LOG_LEVEL=info
```

## Category D: OOM

### Worked example — Container OOM with JVM heap too large

**Symptom:** Java container OOMKilled periodically. Container ran ~2h
each time. `kubectl top pod` shows memory climbing toward the limit.

**Walk:**

1. `kubectl get pod -o jsonpath='{.status.containerStatuses[0].lastState}'`:
   `{"terminated":{"reason":"OOMKilled","exitCode":137}}`.
2. Pod spec: `resources.limits.memory: 1Gi`. JVM CMD:
   `java -Xmx2g -jar app.jar` — heap set to 2GB but limit is 1GB.
3. Container Insights / Prometheus: `container_memory_rss` rose to
   ~1.0Gi just before each kill.

**Root cause:** OOM — JVM heap > container limit (catalog #9).

**Fix:** either raise `limits.memory` to `3Gi` (heap + JVM overhead),
or — preferred — use cgroup-relative sizing:

```yaml
command: ["java"]
args: ["-XX:MaxRAMPercentage=75", "-jar", "app.jar"]
resources:
  limits:
    memory: "2Gi"
```

### Worked example — Node OOM with no per-pod limits

**Symptom:** multiple pods on the same node all restart simultaneously.
No single pod is over its limit (none has a limit set).

**Walk:**

1. `kubectl describe node <node>` Conditions:
   `MemoryPressure=True`. Allocated resources > 95%.
2. `kubectl describe pod` for each: no `OOMKilled` reason; the kernel
   killed the process directly (outside the cgroup OOM-killer).
3. `/var/log/messages` on the node (or `dmesg` via node debug):
   `Out of memory: Killed process 12345 (java)`.

**Root cause:** Node OOM — no `limits.memory` on co-located pods.

**Fix:**

- Set `requests.memory` on every pod so the scheduler accounts for it.
- Set `limits.memory` on every pod to bound per-pod usage.
- Resize the node (`t3.medium` → `t3.large`) or reduce pod density.

## Category E: PROBE_FAILURE

### Worked example — Liveness probe path mismatch

**Symptom:** pod `Running` but restart count climbs. Events shows
`Liveness probe failed: HTTP probe failed with statuscode: 404`.

**Walk:**

1. `kubectl get pod -o jsonpath='{.spec.containers[0].livenessProbe}'`:
   `httpGet: {path: /healthz, port: 8080}`.
2. `kubectl exec` into the pod and curl:
   ```
   $ kubectl exec -n prod api-xyz -c api -- curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/healthz
   404
   $ kubectl exec -n prod api-xyz -c api -- curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/api/health
   200
   ```
3. Application defines health at `/api/health`, not `/healthz`.

**Root cause:** PROBE_FAILURE — liveness path mismatch (catalog #10).

**Fix:**

```bash
kubectl patch deployment api -n prod --type=json \
  -p='[{"op":"replace","path":"/spec/template/spec/containers/0/livenessProbe/httpGet/path","value":"/api/health"}]'
```

### Worked example — Liveness kills the app before it is ready

**Symptom:** pod CrashLoopBackOff. Restart count climbs from 0. Events
shows `Liveness probe failed: Get ...: connect: connection refused`
then `Killing container with id ... Container failed liveness probe`.
Application takes ~60s to bind the port.

**Walk:**

1. `kubectl get pod -o jsonpath='{.spec.containers[0].livenessProbe}'`:
   `initialDelaySeconds: 5, periodSeconds: 10, failureThreshold: 3`.
2. Total time before kill: 5 + 3*10 = 35s. App needs 60s.
3. Events timeline: liveness starts failing at T+5s, kills at T+35s,
   pod restarts, liveness starts failing again, kills at T+35s, ...

**Root cause:** PROBE_FAILURE — initialDelaySeconds too short (catalog #10).

**Fix:** add a `startupProbe` so liveness doesn't run during startup:

```yaml
startupProbe:
  httpGet:
    path: /api/health
    port: 8080
  failureThreshold: 30      # 30 * 10s = 5 minutes max startup
  periodSeconds: 10
livenessProbe:
  httpGet:
    path: /api/health
    port: 8080
  periodSeconds: 10
  failureThreshold: 3
```

## Category F: INIT_FAILURE

### Worked example — Init container crash on DB migration

**Symptom:** pod `Init:CrashLoopBackOff`. Main containers never start.

**Walk:**

1. `kubectl get pod -o jsonpath='{.status.initContainerStatuses}'`:
   ```
   [{"name":"migrate","state":{"waiting":{"reason":"CrashLoopBackOff"}}}]
   ```
2. `kubectl logs <pod> -c migrate --previous`:
   ```
   sqlalchemy.exc.OperationalError: (psycopg2.OperationalError)
   could not connect to server: Connection refused
   ```
3. The migration job runs before the Service `postgres` is reachable.

**Root cause:** INIT_FAILURE — DB migration blocked on unreachable
dependency (catalog #12).

**Fix:** verify the Service exists and the app connects to the right
DNS name; add a retry loop in the migration script; or run the migration
as a Helm hook (`"helm.sh/hook": pre-install`) with retries.

### Worked example — Init container ImagePullBackOff

**Symptom:** pod `Init:ImagePullBackOff`. Main image is fine.

**Walk:**

1. `kubectl describe pod` Events:
   `Failed to pull image "init-tools:v1": manifest unknown`.
2. Init container image `init-tools:v1` doesn't exist in ECR. The
   main container's image does — they come from different repos.

**Root cause:** INIT_FAILURE — init container image missing.

**Fix:** push the init container image, or pin the tag, then
`kubectl delete pod <pod> -n <ns>` to force the controller to retry.

## Cross-category decision flowchart

```
START
  │
  ▼
Phase = Pending?
  ├── YES ──→ Events FailedScheduling?
  │            │
  │            ├── Insufficient cpu/mem ──→ scale nodes / lower requests
  │            ├── taints ───────────────── add toleration or remove taint
  │            ├── affinity ─────────────── match labels or relax
  │            ├── PVC unbound ──────────── WaitForFirstConsumer / capacity
  │            └── cordoned ─────────────── uncordon or add nodes
  │
  ▼ NO
Phase = ContainerCreating or status.waiting.reason = ImagePullBackOff?
  ├── YES ──→ Category B (IMAGE_PULL)
  │            ├── manifest unknown ── verify tag in ECR
  │            ├── unauthorized ────── node role ECR perms
  │            ├── i/o timeout ─────── VPC endpoint / NAT
  │            └── cross-account ───── repo policy in image owner
  │
  ▼ NO
status.initContainerStatuses has failing init container?
  ├── YES ──→ Category F (INIT_FAILURE)
  │            ├── init CrashLoopBackOff ── kubectl logs -c <init> --previous
  │            └── init ImagePullBackOff ── verify init image
  │
  ▼ NO
Phase = Running, restart count climbing?
  ├── YES ──→ Events mention probe failed?
  │            ├── YES ────→ Category E (PROBE_FAILURE)
  │            │              ├── path/port wrong ── kubectl exec curl
  │            │              ├── initialDelay too short ── add startupProbe
  │            │              └── app slow ── raise timeoutSeconds
  │            └── NO ─────→ Exit code 137 + OOMKilled? ── Category D (OOM)
  │                          Else exit 1/255 + app logs? ── Category C (CRASH_LOOP)
  │                            ├── missing env var
  │                            ├── missing ConfigMap/Secret
  │                            ├── dependency outage
  │                            ├── arch mismatch
  │                            └── version mismatch
  │
  ▼
NEED_MORE_INFO — gather more context
```

## Common diagnostic shortcuts

- If the pod is `Pending` and Events mentions `Insufficient`, check
  `kubectl top nodes` and the pod's `resources.requests` first.
- If the pod is `ImagePullBackOff`, verify the image exists in ECR
  before diagnosing auth or network.
- If the pod is `CrashLoopBackOff` and `kubectl logs` (current) is
  empty, ALWAYS add `--previous`.
- If the pod is `Running` but restart count climbs, ALWAYS check Events
  for `Liveness probe failed` before assuming an application crash.
- If multiple pods on the same node fail simultaneously, suspect node
  pressure (MemoryPressure, DiskPressure, PIDPressure) —
  `kubectl describe node <node>` Conditions.
- If only pods in one AZ fail, suspect AZ-specific capacity or EBS gp3
  exhaustion in that AZ.
- If new pods fail after a deploy but old pods are fine, suspect image
  change, env var change, or RBAC/ServiceAccount change in the new
  revision.
- If the pod was healthy yesterday and fails today with no change,
  suspect an ECR lifecycle policy purge, a rotated secret, or a
  dependency outage.

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 200-214 -->

## Step 2 — PENDING common fix patterns

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

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 232-258 -->

## Step 3 — IMAGE_PULL diagnostic walk

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

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 292-307 -->

## Step 3 — IMAGE_PULL common fix patterns

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

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 346-369 -->

## Step 4 — CRASH_LOOP common root causes

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

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 446-472 -->

## Step 6 — PROBE_FAILURE diagnostic walk

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

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 494-509 -->

## Step 6 — PROBE_FAILURE common fix patterns

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

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 525-541 -->

## Step 7 — INIT_FAILURE diagnostic walk

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

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 557-567 -->

## Step 7 — INIT_FAILURE common root causes

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

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 592-602 -->

## Step 9 — verify the fix

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

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 803-868 -->

## Remediation guidance by category

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

