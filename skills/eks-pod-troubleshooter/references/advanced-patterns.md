
<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 46-66 -->

## Mindset — three EKS-specific facts

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

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 419-429 -->

## Step 5 — EKS-specific OOM notes (cgroup v2, Java)

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

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 675-700 -->

## Expert heuristic — the pod troubleshooting trinity

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

<!-- Moved verbatim from SKILL.md (eks-pod-troubleshooter) — progressive-disclosure restructure, lines 872-902 -->

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

