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
