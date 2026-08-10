---
allowed-tools: Read, Bash, Grep
description: "Diagnose Kubernetes pod failures on EKS — CrashLoopBackOff, ImagePullBackOff, Pending/OOMKilled, liveness/readiness probe failures, and init container failures"
nl_triggers:
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
  - "kubernetes pod status"
  - "kubectl pod failure"
  - "EKS pod unhealthy"
  - "diagnose EKS pod"
routes_to: eks-pod-troubleshooter
---

# /aws:troubleshoot-eks-pod

Activate the `eks-pod-troubleshooter` skill and diagnose a Kubernetes
pod failure on an EKS cluster.

## What it does

Reads the pod's failure signal (kubectl get pods, describe pod Events,
container lastState, restart count, kubectl logs --previous) and walks
the symptom-to-cause decision tree across six categories:

1. PENDING — `FailedScheduling` (insufficient CPU/memory, taints,
   affinity, PVC binding).
2. IMAGE_PULL — `ImagePullBackOff` / `ErrImagePull` (ECR auth, missing
   tag, cross-account repo policy, VPC endpoint missing).
3. CRASH_LOOP — `CrashLoopBackOff` (missing env var / ConfigMap,
   dependency outage, image arch mismatch).
4. OOM — `OOMKilled` exit 137 (container limit too low, JVM heap,
   node-level pressure).
5. PROBE_FAILURE — Liveness/Readiness (path/port wrong,
   initialDelaySeconds too short, missing startupProbe).
6. INIT_FAILURE — `Init:CrashLoopBackOff` (init container crash, init
   image missing).

Emits a deterministic VERDICT per pod:

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

## When to invoke

Paste any of the following:

- A pod status (`CrashLoopBackOff`, `ImagePullBackOff`, `Pending`,
  `OOMKilled`).
- `kubectl describe pod` output for a failing pod.
- `kubectl logs --previous` output for a crash-looping pod.
- A `FailedScheduling` event message.
- "My EKS pod is failing" / "pod keeps restarting" / "liveness probe
  failing."

A bare pod name + namespace + any troubleshoot verb also routes here.

## Inputs

- Pod name and namespace (or a label selector that identifies the pod's
  controller).
- `kubectl describe pod <pod> -n <ns>` output (esp. Events and
  container lastState).
- `kubectl logs <pod> -n <ns> -c <container> --previous` for
  CrashLoopBackOff.
- `kubectl get events -n <ns> --field-selector involvedObject.name=<pod>`
  for the timeline.
- For IMAGE_PULL: `aws ecr describe-images` and the node's instance
  role ARN.

## Outputs

- One VERDICT block per pod (earliest-transition-failure wins).
- EVIDENCE citing the specific kubectl fields and log lines.
- REMEDIATION with exact kubectl / aws CLI commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for EKS Compute).
- `/aws:troubleshoot-ecs-task` for the ECS/Fargate equivalent.
- `/aws:audit-eks-cluster` for cluster-level security/config audits
  (separate from per-pod diagnosis).
